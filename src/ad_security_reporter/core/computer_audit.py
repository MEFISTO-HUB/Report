from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from ad_security_reporter.config.settings import AppSettings
from ad_security_reporter.connectors.ad_queries import computers_query
from ad_security_reporter.connectors.powershell_connector import PowerShellConnector


@dataclass
class ComputerAuditResult:
    dataframe: pd.DataFrame
    summary: dict
    notes: list[str]


def _to_datetime(value):
    if value in (None, "", "null"):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", utc=True)


def _days_since(ts: pd.Series) -> pd.Series:
    now = datetime.now(timezone.utc)
    return (now - ts).dt.days


def _stale_status(days: float, settings: AppSettings) -> str:
    if pd.isna(days):
        return "Unknown"
    if days > settings.risk.critical_days:
        return "Critical"
    if days > settings.risk.high_days:
        return "Stale"
    if days > settings.risk.warn_days:
        return "Warning"
    return "Active"


def collect_computer_audit(settings: AppSettings, connector: PowerShellConnector) -> ComputerAuditResult:
    raw = connector.run_json(computers_query(settings.domain_controller))
    df = pd.DataFrame(raw)
    if df.empty:
        return ComputerAuditResult(dataframe=df, summary={}, notes=["No AD computers returned"])

    df["LastLogonDate"] = df["LastLogonDate"].apply(_to_datetime)
    df["PasswordLastSet"] = df["PasswordLastSet"].apply(_to_datetime)
    df["WhenCreated"] = df["WhenCreated"].apply(_to_datetime)

    df["DaysSinceLastLogon"] = _days_since(df["LastLogonDate"])
    df["DaysSincePasswordSet"] = _days_since(df["PasswordLastSet"])
    df["StaleStatus"] = df["DaysSinceLastLogon"].apply(lambda d: _stale_status(d, settings))

    summary = {
        "total_computers": int(len(df)),
        "active": int((df["StaleStatus"] == "Active").sum()),
        "warning_over_30": int((df["DaysSinceLastLogon"] > 30).sum()),
        "stale_over_90": int((df["DaysSinceLastLogon"] > 90).sum()),
        "critical_over_180": int((df["DaysSinceLastLogon"] > 180).sum()),
        "os_distribution": df["OperatingSystem"].fillna("Unknown").value_counts().to_dict(),
    }
    notes = [
        "Report defaults to LastLogonDate/LastLogonTimestamp for practical multi-DC reporting.",
        "Exact LastLogon is per-DC and can be added in optional exact mode via targeted polling.",
    ]
    return ComputerAuditResult(dataframe=df, summary=summary, notes=notes)
