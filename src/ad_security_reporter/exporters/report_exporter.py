from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PASSWORD_COLUMNS_TO_REMOVE = {
    "Пароль изменен",
    "Дата создания",
    "Статус возраста пароля",
}

COMPUTERS_COLUMNS_TO_REMOVE = {
    "DNS-имя",
    "Дата создания",
}

SUMMARY_LABELS_RU = {
    "total_users": "Всего пользователей",
    "enabled_users": "Активных пользователей",
    "disabled_users": "Отключенных пользователей",
    "password_never_expires": "Пароль не истекает",
    "pwd_over_30": "Пароль старше 30 дней",
    "pwd_over_60": "Пароль старше 60 дней",
    "pwd_over_90": "Пароль старше 90 дней",
    "pwd_over_180": "Пароль старше 180 дней",
    "privileged_accounts": "Привилегированных учетных записей",
    "total_computers": "Всего компьютеров",
    "active": "Активных",
    "warning_over_30": "Риск > 30 дней",
    "stale_over_90": "Риск > 90 дней",
    "critical_over_180": "Критично > 180 дней",
}

NOTES_RU = {
    "SAFE DEFAULT MODE: identical passwords are not detectable from AD-only data.": "БЕЗОПАСНЫЙ РЕЖИМ ПО УМОЛЧАНИЮ: одинаковые пароли нельзя определить только по данным AD.",
    "OPTIONAL AUDIT INPUT MODE can group accounts by PasswordFingerprintGroup if sanctioned CSV is supplied.": "ОПЦИОНАЛЬНЫЙ РЕЖИМ АУДИТА: можно группировать учетные записи по PasswordFingerprintGroup, если предоставлен согласованный CSV.",
    "Optional password fingerprint dataset loaded.": "Загружен дополнительный набор данных отпечатков паролей.",
    "Report defaults to LastLogonDate/LastLogonTimestamp for practical multi-DC reporting.": "По умолчанию отчет использует LastLogonDate/LastLogonTimestamp для практической работы в мульти-DC среде.",
    "Exact LastLogon is per-DC and can be added in optional exact mode via targeted polling.": "Точный LastLogon хранится по каждому DC и может быть добавлен в опциональном точном режиме через целевой опрос.",
}


def build_report_path(directory: Path, base_name: str, suffix: str, generated_at: datetime | None = None) -> Path:
    timestamp = (generated_at or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return directory / f"{base_name}_{timestamp}{suffix}"


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", na_rep="")


def export_xlsx(df: pd.DataFrame, path: Path, summary: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False, na_rep="")
        if summary:
            pd.DataFrame(list(summary.items()), columns=["Metric", "Value"]).to_excel(
                writer, sheet_name="Summary", index=False
            )


def export_html(df: pd.DataFrame, path: Path, title: str, summary: dict[str, Any] | None = None, notes: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prepared_df = _prepare_report_dataframe(df, title)

    cards = ""
    if summary:
        palette = ["blue", "violet", "teal", "amber", "rose", "emerald"]
        cards = "".join(
            (
                f'<div class="card {palette[i % len(palette)]}">'
                f"<h3>{SUMMARY_LABELS_RU.get(k, k)}</h3><p>{v}</p></div>"
            )
            for i, (k, v) in enumerate(summary.items())
            if not isinstance(v, dict)
        )
    notes_html = "".join(f"<li>{NOTES_RU.get(n, n)}</li>" for n in (notes or []))
    html = f"""
<!doctype html>
<html lang='ru'>
<head>
<meta charset='utf-8'>
<title>{title}</title>
<style>
body {{
    font-family: Inter, Segoe UI, sans-serif;
    margin: 0;
    background: #ffffff;
    color: #0f172a;
}}
.container {{ max-width: 1360px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 32px; margin: 0 0 18px; letter-spacing: .4px; }}
.generated-at {{ color: #334155; margin: 0 0 16px; font-size: 14px; }}
.cards {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px; }}
.card {{
    border-radius:14px;
    padding:14px 16px;
    min-width: 200px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, .35);
    border: 1px solid rgba(255, 255, 255, .1);
}}
.card h3 {{ margin:0; font-size:13px; color:#dbeafe; font-weight:600; }}
.card p {{ margin:6px 0 0; font-size:24px; font-weight:700; color:#ffffff; }}
.card.blue {{ background: linear-gradient(135deg, #1d4ed8, #3b82f6); }}
.card.violet {{ background: linear-gradient(135deg, #6d28d9, #8b5cf6); }}
.card.teal {{ background: linear-gradient(135deg, #0f766e, #14b8a6); }}
.card.amber {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
.card.rose {{ background: linear-gradient(135deg, #be123c, #fb7185); }}
.card.emerald {{ background: linear-gradient(135deg, #047857, #10b981); }}
.notes {{ margin: 0 0 18px; padding-left: 20px; color: #334155; }}
.table-controls {{ display: flex; justify-content: flex-end; margin-bottom: 12px; }}
.table-search {{
    min-width: 320px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 14px;
}}
table {{ border-collapse: collapse; width:100%; background:#ffffff; border-radius: 12px; overflow: hidden; }}
th, td {{ border: 1px solid #cbd5e1; padding:10px; text-align:left; font-size:12px; color: #0f172a; }}
th {{ background:#f1f5f9; color:#0f172a; text-transform: uppercase; font-size:11px; letter-spacing: .6px; cursor: pointer; user-select: none; }}
tr:nth-child(even) td {{ background:#f8fafc; }}
th.sort-asc::after {{ content: " ▲"; }}
th.sort-desc::after {{ content: " ▼"; }}
</style>
</head>
<body>
<div class='container'>
<h1>{title}</h1>
<div class='generated-at'>Дата формирования отчета: {generated_at}</div>
<div class='cards'>{cards}</div>
<ul class='notes'>{notes_html}</ul>
<div class='table-controls'>
  <input id='table-search' class='table-search' type='search' placeholder='Поиск по отчету...'>
</div>
    {prepared_df.to_html(index=False, classes='report-table', na_rep='', table_id='report-table')}
</div>
<script>
const table = document.getElementById('report-table');
const searchInput = document.getElementById('table-search');
const headers = table ? Array.from(table.querySelectorAll('th')) : [];

function getCellValue(row, index) {{
    const text = row.cells[index]?.innerText.trim() || '';
    const numericText = text.replace(',', '.').replace(/\\s+Дней$/i, '');
    const numericValue = Number(numericText);
    return Number.isNaN(numericValue) ? text.toLowerCase() : numericValue;
}}

function clearSortClasses() {{
    headers.forEach((th) => th.classList.remove('sort-asc', 'sort-desc'));
}}

headers.forEach((header, index) => {{
    header.addEventListener('click', () => {{
        const tbody = table.tBodies[0];
        const rows = Array.from(tbody.rows);
        const isAsc = !header.classList.contains('sort-asc');
        clearSortClasses();
        header.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
        rows.sort((a, b) => {{
            const aVal = getCellValue(a, index);
            const bVal = getCellValue(b, index);
            if (aVal === bVal) return 0;
            return (aVal > bVal ? 1 : -1) * (isAsc ? 1 : -1);
        }});
        rows.forEach((row) => tbody.appendChild(row));
    }});
}});

searchInput.addEventListener('input', () => {{
    const query = searchInput.value.trim().toLowerCase();
    const rows = table.tBodies[0]?.rows || [];
    Array.from(rows).forEach((row) => {{
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    }});
}});
</script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _prepare_report_dataframe(df: pd.DataFrame, title: str) -> pd.DataFrame:
    prepared = df.copy()
    if "аудиту паролей" in title.lower():
        prepared = prepared.drop(columns=PASSWORD_COLUMNS_TO_REMOVE, errors="ignore")
        if "Дней без смены пароля" in prepared.columns:
            prepared["Дней без смены пароля"] = _format_days(prepared["Дней без смены пароля"])
    if "активности компьютеров" in title.lower():
        prepared = prepared.drop(columns=COMPUTERS_COLUMNS_TO_REMOVE, errors="ignore")
        if "Дней с последнего входа" in prepared.columns:
            prepared["Дней с последнего входа"] = _format_days(prepared["Дней с последнего входа"])
    return prepared


def _format_days(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    formatted = numeric.map(lambda value: f"{int(value)} Дней" if pd.notna(value) else "")
    if series.dtype == object:
        return formatted.where(numeric.notna(), series.fillna(""))
    return formatted
