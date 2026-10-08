import base64
import io
from datetime import datetime
from typing import List, Dict
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import RISK_CATEGORIES


class ReportGenerator:

    def __init__(
        self,
        results: List[Dict],
        violations_df: pd.DataFrame = None,
        source_file: str = '',
        source_fmt: str = 'csv'
    ):
        self.results = results
        self.violations_df = violations_df
        self.source_file = source_file
        self.source_fmt = source_fmt

    def generate_csv_report(self, output_path: str = 'examity_risk_report.csv'):

        if not self.results:
            print("[CSV REPORT] No results to report.")
            return

        report_rows = []
        for r in self.results:
            report_rows.append({
                'session_id': r['session_id'],
                'candidate_id': r['candidate_id'],
                'exam_id': r['exam_id'],
                'proctor_mode': r['proctor_mode'],
                'duration_sec': r['duration_sec'],
                'total_violations': r['total_violations'],
                'risk_score': r['risk_score'],
                'risk_label': r['risk_label'],
                'recommended_action': r['risk_action'],
                'score_breakdown': ' | '.join(
                    [f"{s['factor']} (+{s['points']})" for s in r['score_breakdown']]
                ),
                'video_url': r['video_url']
            })

        pd.DataFrame(report_rows).to_csv(output_path, index=False)
        print(f"[CSV REPORT] Saved to {output_path}")

    def generate_html_report(self, output_path: str = 'proctoring_report.html'):

        risk_chart_b64 = self._generate_risk_distribution_chart()
        violation_chart_b64 = self._generate_violation_breakdown_chart()

        total_sessions = len(self.results)
        avg_score = sum(r['risk_score'] for r in self.results) / total_sessions if total_sessions else 0

        category_counts = {}
        for cat in RISK_CATEGORIES:
            count = sum(1 for r in self.results if cat['min'] <= r['risk_score'] <= cat['max'])
            category_counts[cat['label']] = count

        total_violations = sum(r['total_violations'] for r in self.results)
        auth_failures = sum(1 for r in self.results
                            if any('auth' in f['rule'].lower() for f in r['flags']))

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proctoring Analysis Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            color: #1a1a1a;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #6d4aff 0%, #5836d6 100%);
            color: white;
            padding: 30px 40px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
        .header .meta {{ font-size: 13px; opacity: 0.85; }}

        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}

        .kpi-strip {{
            display: flex;
            gap: 16px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .kpi-card {{
            flex: 1;
            min-width: 150px;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
        }}
        .kpi-card .value {{ font-size: 32px; font-weight: 700; color: #6d4aff; }}
        .kpi-card .label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
        .kpi-card.warning .value {{ color: #e74c3c; }}
        .kpi-card.moderate .value {{ color: #f39c12; }}

        .chart-section {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .chart-section h2 {{ font-size: 18px; margin-bottom: 16px; color: #333; }}
        .chart-section img {{ width: 100%; height: auto; }}

        .charts-row {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .charts-row .chart-section {{ flex: 1; min-width: 400px; }}

        .risk-legend {{
            display: flex;
            gap: 12px;
            margin: 16px 0;
            flex-wrap: wrap;
        }}
        .risk-badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }}

        .session-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 5px solid #ddd;
        }}
        .session-card.critical {{ border-left-color: #e74c3c; }}
        .session-card.high {{ border-left-color: #e67e22; }}
        .session-card.moderate {{ border-left-color: #f39c12; }}
        .session-card.low {{ border-left-color: #2ecc71; }}

        .session-card .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .session-card .session-title {{ font-size: 16px; font-weight: 600; }}
        .session-card .session-meta {{ font-size: 12px; color: #999; }}

        .risk-score-badge {{
            font-size: 28px;
            font-weight: 800;
            padding: 8px 16px;
            border-radius: 8px;
            color: white;
            min-width: 60px;
            text-align: center;
        }}

        .breakdown-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 13px;
        }}
        .breakdown-table th {{
            text-align: left;
            padding: 8px;
            background: #f5f5f7;
            border-bottom: 2px solid #e0e0e0;
            font-weight: 600;
            color: #666;
        }}
        .breakdown-table td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .breakdown-table .points {{
            font-weight: 700;
            text-align: right;
        }}
        .breakdown-table .points.positive {{ color: #e74c3c; }}

        .full-table-container {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow-x: auto;
        }}
        .full-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .full-table th {{
            text-align: left;
            padding: 10px;
            background: #6d4aff;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        .full-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #eee;
        }}
        .full-table tr:hover {{ background: #f5f5f7; }}
        .full-table .score-cell {{ font-weight: 700; text-align: center; }}

        .footer {{
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 12px;
        }}
        .footer a {{ color: #6d4aff; text-decoration: none; }}
    </style>
</head>
<body>

<div class="header">
    <h1>📊 Proctoring Analysis Report</h1>
    <div class="meta">
        Generated: {datetime.now().strftime('%Y-%m-%d at %H:%M')} ·
        Source: {self.source_file} ·
        Format: {self.source_fmt.upper()}
    </div>
</div>

<div class="container">

    <div class="kpi-strip">
        <div class="kpi-card">
            <div class="value">{total_sessions}</div>
            <div class="label">Total Sessions</div>
        </div>
        <div class="kpi-card moderate">
            <div class="value">{avg_score:.0f}</div>
            <div class="label">Avg Risk Score</div>
        </div>
        <div class="kpi-card warning">
            <div class="value">{category_counts.get('High Risk', 0) + category_counts.get('Critical', 0)}</div>
            <div class="label">High+ Critical</div>
        </div>
        <div class="kpi-card">
            <div class="value">{total_violations}</div>
            <div class="label">Total Violations</div>
        </div>
        <div class="kpi-card warning">
            <div class="value">{auth_failures}</div>
            <div class="label">Auth Failures</div>
        </div>
    </div>

    <div class="risk-legend">
"""

        for cat in RISK_CATEGORIES:
            count = category_counts.get(cat['label'], 0)
            pct = (count / total_sessions * 100) if total_sessions else 0
            html += f"""        <span class="risk-badge" style="background: {cat['color']};">
            {cat['label']}: {count} ({pct:.0f}%)
        </span>\n"""

        html += """    </div>\n\n    <!-- CHARTS -->\n    <div class="charts-row">\n"""

        html += f"""        <div class="chart-section">
            <h2>Risk Score Distribution</h2>
            <img src="data:image/png;base64,{risk_chart_b64}" alt="Risk Distribution Chart" />
        </div>
        <div class="chart-section">
            <h2>Violation Types Breakdown</h2>
            <img src="data:image/png;base64,{violation_chart_b64}" alt="Violation Breakdown Chart" />
        </div>
    </div>

    <div class="chart-section">
        <h2>🚨 Top 10 Highest-Risk Sessions</h2>
"""

        for r in self.results[:10]:
            card_class = r['risk_label'].lower().replace(' ', '')
            breakdown_rows = ""
            for s in r['score_breakdown']:
                breakdown_rows += f"""                        <tr>
                            <td>{s['factor']}</td>
                            <td>{s['detail']}</td>
                            <td class="points positive">+{s['points']}</td>
                        </tr>\n"""

            video_link = ""
            if r['video_url']:
                video_link = f'<a href="{r["video_url"]}" target="_blank">📹 Review Video</a>'

            html += f"""        <div class="session-card {card_class}">
            <div class="card-header">
                <div>
                    <div class="session-title">Session {r['session_id']} — Student {r['candidate_id']}</div>
                    <div class="session-meta">
                        Exam: {r['exam_id']} · Mode: {r['proctor_mode']} ·
                        Duration: {r['duration_sec']}s ·
                        Violations: {r['total_violations']} ·
                        {video_link}
                    </div>
                </div>
                <div class="risk-score-badge" style="background: {r['risk_color']};">
                    {r['risk_score']}
                </div>
            </div>
            <table class="breakdown-table">
                <thead>
                    <tr>
                        <th>Factor</th>
                        <th>Detail</th>
                        <th style="text-align:right;">Points</th>
                    </tr>
                </thead>
                <tbody>
                    {breakdown_rows}
                </tbody>
            </table>
        </div>
"""

        html += "    </div>\n\n    <!-- FULL RESULTS TABLE -->\n"

        html += """    <div class="full-table-container">
        <h2 style="font-size: 18px; margin-bottom: 16px; color: #333;">📋 All Sessions (sorted by risk score)</h2>
        <table class="full-table">
            <thead>
                <tr>
                    <th>Session ID</th>
                    <th>Student</th>
                    <th>Exam</th>
                    <th>Mode</th>
                    <th>Duration (s)</th>
                    <th>Violations</th>
                    <th>Risk Score</th>
                    <th>Risk Level</th>
                    <th>Recommended Action</th>
                </tr>
            </thead>
            <tbody>
"""
        for r in self.results:
            html += f"""                <tr>
                    <td>{r['session_id']}</td>
                    <td>{r['candidate_id']}</td>
                    <td>{r['exam_id']}</td>
                    <td>{r['proctor_mode']}</td>
                    <td>{r['duration_sec']}</td>
                    <td>{r['total_violations']}</td>
                    <td class="score-cell" style="color: {r['risk_color']};">{r['risk_score']}</td>
                    <td><span class="risk-badge" style="background: {r['risk_color']};">{r['risk_label']}</span></td>
                    <td>{r['risk_action']}</td>
                </tr>\n"""

        html += f"""            </tbody>
        </table>
    </div>

</div>

<div class="footer">
    <p>Generated by Examity Proctoring Log Analyzer · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>Charts rendered with matplotlib · Report is fully self-contained (no external dependencies)</p>
</div>

</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"[HTML REPORT] Saved to {output_path}")

    def _generate_risk_distribution_chart(self) -> str:

        fig, ax = plt.subplots(figsize=(7, 4))

        labels = [cat['label'] for cat in RISK_CATEGORIES]
        counts = [
            sum(1 for r in self.results if cat['min'] <= r['risk_score'] <= cat['max'])
            for cat in RISK_CATEGORIES
        ]
        colors = [cat['color'] for cat in RISK_CATEGORIES]

        bars = ax.bar(labels, counts, color=colors, edgecolor='white', linewidth=0.5)

        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        str(count), ha='center', va='bottom', fontweight='bold', fontsize=12)

        ax.set_ylabel('Number of Sessions', fontsize=12)
        ax.set_title('Sessions by Risk Category', fontsize=14, fontweight='bold', pad=15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='x', labelsize=11)
        ax.tick_params(axis='y', labelsize=10)

        plt.tight_layout()

        return self._fig_to_base64(fig)

    def _generate_violation_breakdown_chart(self) -> str:

        if self.violations_df is None or len(self.violations_df) == 0:
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.text(0.5, 0.5, 'No violations recorded',
                    ha='center', va='center', fontsize=14, color='#999')
            ax.axis('off')
            return self._fig_to_base64(fig)

        type_counts = self.violations_df['violation_type'].value_counts()

        fig, ax = plt.subplots(figsize=(7, 4))

        bars = ax.barh(
            type_counts.index[::-1],
            type_counts.values[::-1],
            color='#6d4aff',
            edgecolor='white',
            linewidth=0.5
        )

        for bar, count in zip(bars, type_counts.values[::-1]):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    str(count), ha='left', va='center', fontweight='bold', fontsize=11)

        ax.set_xlabel('Total Occurrences', fontsize=12)
        ax.set_title('Violation Types Across All Sessions', fontsize=14, fontweight='bold', pad=15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='y', labelsize=10)
        ax.tick_params(axis='x', labelsize=10)

        plt.tight_layout()

        return self._fig_to_base64(fig)

    def _fig_to_base64(self, fig) -> str:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return b64