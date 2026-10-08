# main.py
from loader import DataLoader
from analyzer import ExamityAnalyzer
from reporter import ReportGenerator
from config import DEFAULT_RULES

def main():

    loader = DataLoader('mock_examity_export.csv', fmt='csv')
    df, violations_df = loader.load_and_clean()

    analyzer = ExamityAnalyzer()
    results = analyzer.analyze(df, violations_df, rules=DEFAULT_RULES)

    reporter = ReportGenerator(results, violations_df)
    reporter.generate_csv_report('risk_report.csv')
    reporter.generate_html_report('proctoring_report.html')
    
    analyzer.print_console_summary(results)

if __name__ == '__main__':
    main()