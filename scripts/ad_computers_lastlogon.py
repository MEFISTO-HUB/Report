from __future__ import annotations

import argparse
from pathlib import Path

from ad_security_reporter.config.settings import load_settings
from ad_security_reporter.connectors.powershell_connector import PowerShellConnector
from ad_security_reporter.core.computer_audit import collect_computer_audit
from ad_security_reporter.exporters.report_exporter import build_report_path, export_csv, export_html, export_xlsx


def main() -> int:
    parser = argparse.ArgumentParser(description="AD computers last logon reporter (defensive only)")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--output-dir", default="exports")
    args = parser.parse_args()

    settings = load_settings(Path(args.config))
    connector = PowerShellConnector(executable=settings.powershell_executable)
    result = collect_computer_audit(settings, connector)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = build_report_path(out_dir, "computers_lastlogon", ".csv")
    xlsx_path = build_report_path(out_dir, "computers_lastlogon", ".xlsx")
    html_path = build_report_path(out_dir, "computers_lastlogon", ".html")

    export_csv(result.dataframe, csv_path)
    export_xlsx(result.dataframe, xlsx_path, result.summary)
    export_html(result.dataframe, html_path, "Отчет по последнему входу компьютеров", result.summary, result.notes)

    print("Computers report generated:")
    print(csv_path)
    print(xlsx_path)
    print(html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
