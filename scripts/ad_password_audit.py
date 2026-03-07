from __future__ import annotations

import argparse
from pathlib import Path

from ad_security_reporter.config.settings import load_settings
from ad_security_reporter.connectors.powershell_connector import PowerShellConnector
from ad_security_reporter.core.password_audit import collect_password_audit
from ad_security_reporter.exporters.report_exporter import export_csv, export_html, export_xlsx


def main() -> int:
    parser = argparse.ArgumentParser(description="AD password audit reporter (defensive only)")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--output-dir", default="exports")
    args = parser.parse_args()

    settings = load_settings(Path(args.config))
    connector = PowerShellConnector(executable=settings.powershell_executable)
    result = collect_password_audit(settings, connector)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    export_csv(result.dataframe, out_dir / "password_audit.csv")
    export_xlsx(result.dataframe, out_dir / "password_audit.xlsx", result.summary)
    export_html(result.dataframe, out_dir / "password_audit.html", "Отчет по аудиту паролей", result.summary, result.notes)

    print("Password audit report generated:")
    print(out_dir / "password_audit.csv")
    print(out_dir / "password_audit.xlsx")
    print(out_dir / "password_audit.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
