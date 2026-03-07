from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def export_xlsx(df: pd.DataFrame, path: Path, summary: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        if summary:
            pd.DataFrame(list(summary.items()), columns=["Metric", "Value"]).to_excel(
                writer, sheet_name="Summary", index=False
            )


def export_html(df: pd.DataFrame, path: Path, title: str, summary: dict[str, Any] | None = None, notes: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cards = ""
    if summary:
        palette = ["blue", "violet", "teal", "amber", "rose", "emerald"]
        cards = "".join(
            (
                f'<div class="card {palette[i % len(palette)]}">'
                f"<h3>{k}</h3><p>{v}</p></div>"
            )
            for i, (k, v) in enumerate(summary.items())
            if not isinstance(v, dict)
        )
    notes_html = "".join(f"<li>{n}</li>" for n in (notes or []))
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
    background: linear-gradient(165deg, #0b1220 0%, #111827 45%, #1f2937 100%);
    color: #e5e7eb;
}}
.container {{ max-width: 1360px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 32px; margin: 0 0 18px; letter-spacing: .4px; }}
.generated-at {{ color: #93c5fd; margin: 0 0 16px; font-size: 14px; }}
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
.notes {{ margin: 0 0 18px; padding-left: 20px; color: #d1d5db; }}
table {{ border-collapse: collapse; width:100%; background:#0f172a; border-radius: 12px; overflow: hidden; }}
th, td {{ border: 1px solid #334155; padding:10px; text-align:left; font-size:12px; }}
th {{ background:#1e293b; color:#f8fafc; text-transform: uppercase; font-size:11px; letter-spacing: .6px; }}
tr:nth-child(even) td {{ background:#111b31; }}
</style>
</head>
<body>
<div class='container'>
<h1>{title}</h1>
<div class='generated-at'>Дата формирования отчета: {generated_at}</div>
<div class='cards'>{cards}</div>
<ul class='notes'>{notes_html}</ul>
{df.to_html(index=False, classes='report-table')}
</div>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
