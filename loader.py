import json
import pandas as pd


class DataLoader:

    def __init__(self, file_path: str, fmt: str = 'csv'):
        self.file_path = file_path
        self.fmt = fmt
        self.df = None
        self.violations_expanded = None

    def load_and_clean(self):
        self._load_data()
        self._clean_data()
        self._extract_violations()

        print(f"[LOADER] {len(self.df)} sessions, "
              f"{len(self.violations_expanded)} violations extracted.")

        return self.df, self.violations_expanded

    def _load_data(self):
        if self.fmt == 'csv':
            self.df = pd.read_csv(self.file_path)
            print(f"[LOAD] Loaded {len(self.df)} sessions from CSV")

        elif self.fmt == 'json':
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                with open(self.file_path, 'r') as f:
                    data = [json.loads(line) for line in f if line.strip()]
            self.df = pd.DataFrame(data)
            print(f"[LOAD] Loaded {len(self.df)} sessions from JSON")
        else:
            raise ValueError(f"Unsupported format: {self.fmt}")

    def _clean_data(self):
        self.df.columns = (
            self.df.columns
            .str.strip()
            .str.lower()
            .str.replace(' ', '_')
        )

        for col in ['starttime', 'endtime']:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors='coerce', utc=True)

        if 'durationsec' not in self.df.columns:
            if 'starttime' in self.df.columns and 'endtime' in self.df.columns:
                self.df['durationsec'] = (
                    self.df['endtime'] - self.df['starttime']
                ).dt.total_seconds()

    def _extract_violations(self):
        all_violations = []

        for idx, row in self.df.iterrows():
            session_id = row.get('sessionid', f'ROW_{idx}')
            candidate_id = row.get('candidateid', 'UNKNOWN')

            if self.fmt == 'json' and 'violations' in row and isinstance(row['violations'], list):
                for v in row['violations']:
                    all_violations.append({
                        'session_id': session_id,
                        'candidate_id': candidate_id,
                        'violation_time': v.get('timestamp'),
                        'violation_type': v.get('type', 'unknown'),
                        'comment': v.get('comment', '')
                    })
            elif self.fmt == 'csv':
                for i in range(1, 51):
                    type_col = f'violation{i}_type'
                    if type_col not in self.df.columns:
                        break
                    v_type = row.get(type_col)
                    if pd.isna(v_type) or str(v_type).strip() == '':
                        continue
                    all_violations.append({
                        'session_id': session_id,
                        'candidate_id': candidate_id,
                        'violation_time': row.get(f'violation{i}_time'),
                        'violation_type': str(v_type).strip().lower(),
                        'comment': str(row.get(f'violation{i}_comment', ''))
                    })

        self.violations_expanded = pd.DataFrame(all_violations)