from datetime import datetime
from pathlib import Path

import pandas as pd

from ad_security_reporter.exporters.report_exporter import build_report_path, export_csv, export_html


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


def test_build_report_path_adds_timestamp_suffix(tmp_path: Path) -> None:
    generated_at = datetime(2024, 1, 2, 3, 4, 5)

    report_path = build_report_path(tmp_path, "password_audit", ".html", generated_at)

    assert report_path.name == "password_audit_20240102_030405.html"


def test_export_html_renders_missing_values_as_empty_cells(tmp_path: Path) -> None:
    df = pd.DataFrame(
        [
            {"Дней без смены пароля": float("nan"), "Дней с последнего входа": pd.NA},
        ]
    )
    report_path = tmp_path / "missing_values_report.html"

    export_html(df, report_path, "Тест NaN")

    html = report_path.read_text(encoding="utf-8")
    assert ">NaN<" not in html
    assert ">nan<" not in html
    assert "<td></td>" in html


def test_export_csv_writes_missing_values_as_empty_strings(tmp_path: Path) -> None:
    df = pd.DataFrame(
        [
            {"Дней без смены пароля": float("nan"), "Дней с последнего входа": pd.NA},
        ]
    )
    csv_path = tmp_path / "report.csv"

    export_csv(df, csv_path)

    content = csv_path.read_text(encoding="utf-8-sig")
    assert "NaN" not in content
    assert "<NA>" not in content
