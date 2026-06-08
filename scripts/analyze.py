import argparse
from pathlib import Path
import json
import pandas as pd

from app.services.profiler import profile_dataframe
from app.services.report_generator import generate_markdown_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=str)
    parser.add_argument("--out", type=str, default="reports")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    summary = profile_dataframe(df)
    report = generate_markdown_report(csv_path.name, summary)

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "eda_report.md").write_text(report, encoding="utf-8")

    print(f"Saved summary to {out_dir / 'summary.json'}")
    print(f"Saved report to {out_dir / 'eda_report.md'}")


if __name__ == "__main__":
    main()
