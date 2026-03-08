from __future__ import annotations

import re

import pandas as pd


_DOTNET_DATE_RE = re.compile(r"^/Date\((?P<epoch_ms>-?\d+)(?:[+-]\d+)?\)/$")


def to_utc_datetime(value: object) -> pd.Timestamp | pd.NaT:
    if value in (None, "", "null"):
        return pd.NaT

    if isinstance(value, str):
        match = _DOTNET_DATE_RE.match(value.strip())
        if match:
            epoch_ms = int(match.group("epoch_ms"))
            return pd.to_datetime(epoch_ms, unit="ms", utc=True, errors="coerce")

    return pd.to_datetime(value, errors="coerce", utc=True)


def format_datetime(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce", utc=True)
    return dt.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
