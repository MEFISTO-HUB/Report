from __future__ import annotations

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
    cards = ""
    if summary:
        cards = "".join(
            f'<div class="card"><h3>{k}</h3><p>{v}</p></div>' for k, v in summary.items() if not isinstance(v, dict)
        )
    notes_html = "".join(f"<li>{n}</li>" for n in (notes or []))
    html = f"""
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<title>{title}</title>
<style>
body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #111827; color: #e5e7eb; }}
.cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }}
.card {{ background:#1f2937; border-radius:12px; padding:12px; min-width: 180px; }}
table {{ border-collapse: collapse; width:100%; background:#0b1220; }}
th, td {{ border: 1px solid #374151; padding:8px; text-align:left; font-size:12px; }}
th {{ background:#1f2937; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class='cards'>{cards}</div>
<ul>{notes_html}</ul>
{df.to_html(index=False, classes='report-table')}
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
