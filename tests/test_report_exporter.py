from pathlib import Path

import pandas as pd

from ad_security_reporter.exporters.report_exporter import export_html


def test_export_html_adds_generated_date_without_changing_table_columns(tmp_path: Path) -> None:
    df = pd.DataFrame(
        [
            {"Колонка 1": "A", "Колонка 2": "B"},
        ]
    )
    report_path = tmp_path / "report.html"

    export_html(df, report_path, "Тестовый отчет")

    html = report_path.read_text(encoding="utf-8")
    assert "Дата формирования отчета:" in html
    assert "<th>Колонка 1</th>" in html
    assert "<th>Колонка 2</th>" in html
    assert html.count("<th>") == 2
