import pandas as pd
from typing import List, Dict, Any, Optional

from config import (
    VIOLATION_WEIGHTS,
    BURST_PENALTY,
    AUTH_FAILURE_PENALTY,
    SHORT_EXAM_PENALTY,
    MAX_SCORE,
    RISK_CATEGORIES,
    DEFAULT_RULES
)


class ExamityAnalyzer:

    def __init__(self):
        self.results = []

    def analyze(
        self,
        df: pd.DataFrame,
        violations_df: pd.DataFrame,
        rules: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:

        if rules is None:
            rules = DEFAULT_RULES.copy()

        if len(violations_df) > 0:
            violation_counts = (
                violations_df
                .groupby(['session_id', 'candidate_id', 'violation_type'])
                .size()
                .reset_index(name='count')
            )
        else:
            violation_counts = pd.DataFrame(
                columns=['session_id', 'candidate_id', 'violation_type', 'count']
            )

        for idx, row in df.iterrows():
            session_id = row.get('sessionid', f'ROW_{idx}')
            candidate_id = row.get('candidateid', 'UNKNOWN')
            duration = row.get('durationsec', 0)

            score_breakdown = []
            total_score = 0

            session_violations = violation_counts[violation_counts['session_id'] == session_id]

            for _, v_row in session_violations.iterrows():
                v_type = v_row['violation_type']
                v_count = int(v_row['count'])
                weight = VIOLATION_WEIGHTS.get(v_type, 5)
                points = v_count * weight
                total_score += points
                score_breakdown.append({
                    'factor': f"Violation: {v_type}",
                    'detail': f"{v_count} occurrence(s) × {weight} pts",
                    'points': points
                })

            session_v_times = violations_df[
                violations_df['session_id'] == session_id
            ]['violation_time'].tolist()

            cluster = self._detect_violation_clustering(session_v_times, window_sec=120)
            if cluster:
                total_score += BURST_PENALTY
                score_breakdown.append({
                    'factor': 'Violation burst',
                    'detail': f"{cluster['count']} violations within {cluster['window_sec']}s",
                    'points': BURST_PENALTY
                })

            auth_status = str(row.get('authstatus', '')).lower()
            if 'fail' in auth_status:
                total_score += AUTH_FAILURE_PENALTY
                score_breakdown.append({
                    'factor': 'Authentication failure',
                    'detail': f"Auth status: {row.get('authstatus')}",
                    'points': AUTH_FAILURE_PENALTY
                })

            if not pd.isna(duration) and duration < rules['min_exam_duration_sec']:
                total_score += SHORT_EXAM_PENALTY
                score_breakdown.append({
                    'factor': 'Short exam duration',
                    'detail': f"{int(duration)}s (minimum: {rules['min_exam_duration_sec']}s)",
                    'points': SHORT_EXAM_PENALTY
                })

            total_score = min(total_score, MAX_SCORE)

            risk_category = self._get_risk_category(total_score)

            total_violations = int(session_violations['count'].sum()) if len(session_violations) > 0 else 0

            self.results.append({
                'session_id': session_id,
                'candidate_id': candidate_id,
                'exam_id': row.get('examid', ''),
                'proctor_mode': row.get('proctormode', ''),
                'duration_sec': int(duration) if not pd.isna(duration) else None,
                'total_violations': total_violations,
                'risk_score': total_score,
                'risk_label': risk_category['label'],
                'risk_color': risk_category['color'],
                'risk_action': risk_category['action'],
                'score_breakdown': score_breakdown,
                'video_url': row.get('videourl', ''),
                'flags': [{'rule': s['factor'], 'detail': s['detail']}
                          for s in score_breakdown],
            })

        self.results.sort(key=lambda x: x['risk_score'], reverse=True)

        flagged_count = sum(1 for r in self.results if r['risk_score'] >= 20)
        print(f"[ANALYZER] {len(self.results)} sessions scored. "
              f"{flagged_count} above low-risk threshold.")

        return self.results

    def _detect_violation_clustering(
        self,
        timestamps: list,
        window_sec: int = 120
    ) -> Optional[Dict]:
        
        if len(timestamps) < 3:
            return None

        parsed = []
        for ts in timestamps:
            if isinstance(ts, str):
                try:
                    parsed.append(pd.to_datetime(ts, utc=True))
                except Exception:
                    continue
            elif isinstance(ts, pd.Timestamp):
                parsed.append(ts)

        if len(parsed) < 3:
            return None

        parsed.sort()

        for i in range(len(parsed) - 2):
            window = (parsed[i + 2] - parsed[i]).total_seconds()
            if window <= window_sec:
                return {
                    'count': 3,
                    'window_sec': int(window),
                    'start_time': parsed[i].isoformat()
                }
        return None

    def _get_risk_category(self, score: int) -> Dict:
        for cat in RISK_CATEGORIES:
            if cat['min'] <= score <= cat['max']:
                return cat
        return RISK_CATEGORIES[-1]  # Fallback to Critical

    def print_console_summary(self, results: List[Dict] = None):
        if results is None:
            results = self.results

        if not results:
            print("[SUMMARY] No results to summarise.")
            return

        print("\n" + "=" * 70)
        print("EXAMITY PROCTORING ANALYSIS — RISK SCORING SUMMARY")
        print("=" * 70)
        print(f"Total sessions analysed:  {len(results)}")
        print(f"Average risk score:       {sum(r['risk_score'] for r in results) / len(results):.1f}")
        print("-" * 70)

        print("\nRisk Distribution:")
        for cat in RISK_CATEGORIES:
            count = sum(1 for r in results if cat['min'] <= r['risk_score'] <= cat['max'])
            pct = count / len(results) * 100
            bar = '█' * int(pct / 2)
            print(f"  {cat['label']:<16} {count:>4} ({pct:>5.1f}%)  {bar}")

        print("-" * 70)
        print("\nTop 5 Highest-Risk Sessions:")
        for r in results[:5]:
            print(f"\n  🔴 Score {r['risk_score']:>3}/100 [{r['risk_label']}] — "
                  f"Session {r['session_id']} (Student {r['candidate_id']})")
            for s in r['score_breakdown']:
                print(f"     → {s['factor']}: {s['detail']} (+{s['points']} pts)")
            if r['video_url']:
                print(f"     📹 {r['video_url']}")

        print("\n" + "=" * 70)