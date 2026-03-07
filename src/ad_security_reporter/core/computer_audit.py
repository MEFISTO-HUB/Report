from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from ad_security_reporter.config.settings import AppSettings
from ad_security_reporter.connectors.ad_queries import computers_query
from ad_security_reporter.connectors.powershell_connector import PowerShellConnector


COMPUTERS_REPORT_COLUMN_NAMES = {
    "Name": "Имя компьютера",
    "DNSHostName": "DNS-имя",
    "OperatingSystem": "Операционная система",
    "CanonicalName": "OU",
    "Enabled": "Включенная УЗ",
    "LastLogonDate": "Последний вход",
    "WhenCreated": "Дата создания",
    "PasswordLastSet": "Пароль изменен",
    "DaysSinceLastLogon": "Дней с последнего входа",
    "IPv4Address": "IPv4",
    "Description": "Описание",
    "StaleStatus": "Статус активности",
}

COMPUTERS_REPORT_DROP_COLUMNS = [
    "OperatingSystemVersion",
    "DistinguishedName",
    "DaysSincePasswordSet",
    "StaleStatus",
]

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
    ts = pd.to_datetime(ts, errors="coerce", utc=True)
    now = datetime.now(timezone.utc)
    return (now - ts).dt.days


def _format_datetime(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce", utc=True)
    return dt.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")


def _localize_bools(df: pd.DataFrame) -> pd.DataFrame:
    localized = df.copy()
    bool_columns = localized.select_dtypes(include=["bool"]).columns
    for col in bool_columns:
        localized[col] = localized[col].map({True: "Да", False: "Нет"})
    return localized


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

    df["LastLogonDate"] = _format_datetime(df["LastLogonDate"])
    df["PasswordLastSet"] = _format_datetime(df["PasswordLastSet"])
    df["WhenCreated"] = _format_datetime(df["WhenCreated"])

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
    report_df = df.drop(columns=COMPUTERS_REPORT_DROP_COLUMNS, errors="ignore")
    report_df = _localize_bools(report_df).rename(columns=COMPUTERS_REPORT_COLUMN_NAMES)
    return ComputerAuditResult(dataframe=report_df, summary=summary, notes=notes)
