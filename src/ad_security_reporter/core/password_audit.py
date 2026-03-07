from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ad_security_reporter.config.settings import AppSettings
from ad_security_reporter.connectors.ad_queries import password_policy_query, users_query
from ad_security_reporter.connectors.powershell_connector import PowerShellConnector

logger = logging.getLogger(__name__)


PASSWORD_REPORT_COLUMN_NAMES = {
    "SamAccountName": "Логин",
    "Name": "Имя",
    "DisplayName": "Отображаемое имя",
    "Enabled": "Включен",
    "Department": "Отдел",
    "Title": "Должность",
    "CanonicalName": "Каноническое имя",
    "PasswordLastSet": "Пароль изменен",
    "DaysSincePasswordChange": "Дней без смены пароля",
    "LastLogonDate": "Последний вход",
    "DaysSinceLastLogon": "Дней с последнего входа",
    "PasswordNeverExpires": "Пароль не истекает",
    "CannotChangePassword": "Запрет смены пароля",
    "PasswordExpired": "Пароль истек",
    "SmartcardLogonRequired": "Требуется смарт-карта",
    "AccountExpirationDate": "Срок действия учетной записи",
    "WhenCreated": "Дата создания",
    "adminCount": "adminCount",
    "PrivilegedMember": "Привилегированная группа",
    "PasswordAgeStatus": "Статус возраста пароля",
    "RiskGroup": "Группа риска",
    "PasswordFingerprintGroup": "Группа отпечатка пароля",
}

SENSITIVE_GROUP_KEYWORDS = [
    "Domain Admins",
    "Enterprise Admins",
    "Administrators",
    "Schema Admins",
    "Account Operators",
]


@dataclass
class PasswordAuditResult:
    policy: dict
    dataframe: pd.DataFrame
    summary: dict
    notes: list[str]


def _to_datetime(value):
    if value in (None, "", "null"):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", utc=True)


def _days_since(ts: pd.Series) -> pd.Series:
    ts = pd.to_datetime(ts, errors="coerce", utc=True)
    now = pd.Timestamp.now(tz="UTC")
    return (now - ts).dt.days


def _contains_sensitive_group(member_of) -> bool:
    if isinstance(member_of, list):
        joined = " | ".join(member_of)
    else:
        joined = str(member_of or "")
    return any(keyword.lower() in joined.lower() for keyword in SENSITIVE_GROUP_KEYWORDS)


def _password_age_status(days: float, settings: AppSettings) -> str:
    if pd.isna(days):
        return "Unknown"
    if days >= settings.risk.critical_days:
        return "Very Old"
    if days >= settings.risk.high_days:
        return "Old"
    if days >= settings.risk.medium_days:
        return "Aging"
    return "Fresh"


def _risk_group(row: pd.Series, settings: AppSettings, complexity_enabled: bool) -> str:
    days_pwd = row.get("DaysSincePasswordChange")
    privileged = bool(row.get("PrivilegedMember"))
    admin_count = str(row.get("adminCount", "")) == "1"

    if bool(row.get("PasswordNeverExpires")):
        return "CRITICAL"
    if pd.notna(days_pwd) and days_pwd >= settings.risk.critical_days:
        return "CRITICAL"
    if privileged and pd.notna(days_pwd) and days_pwd >= settings.risk.high_days:
        return "CRITICAL"
    if not complexity_enabled and (privileged or admin_count):
        return "CRITICAL"
    if admin_count:
        return "HIGH"
    if pd.notna(days_pwd) and days_pwd >= settings.risk.high_days:
        return "HIGH"
    if not bool(row.get("Enabled", True)) and pd.notna(days_pwd) and days_pwd >= settings.risk.high_days:
        return "HIGH"
    if pd.notna(days_pwd) and days_pwd >= settings.risk.medium_days:
        return "MEDIUM"
    return "LOW"


def _load_optional_fingerprints(path: str) -> pd.DataFrame | None:
    if not path:
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        logger.warning("Optional fingerprint CSV does not exist: %s", path)
        return None
    df = pd.read_csv(csv_path)
    expected = {"SamAccountName", "PasswordFingerprintGroup"}
    if not expected.issubset(df.columns):
        logger.warning("Optional fingerprint CSV format is invalid")
        return None
    return df


def collect_password_audit(settings: AppSettings, connector: PowerShellConnector) -> PasswordAuditResult:
    policy_raw = connector.run_json(password_policy_query(settings.domain_controller))
    users_raw = connector.run_json(users_query(settings.domain_controller))

    policy = policy_raw[0] if policy_raw else {}
    complexity_enabled = bool(policy.get("ComplexityEnabled", True))

    df = pd.DataFrame(users_raw)
    if df.empty:
        return PasswordAuditResult(policy=policy, dataframe=df, summary={}, notes=["No AD users returned."])

    df["PasswordLastSet"] = df["PasswordLastSet"].apply(_to_datetime)
    df["LastLogonDate"] = df["LastLogonDate"].apply(_to_datetime)
    df["WhenCreated"] = df["WhenCreated"].apply(_to_datetime)
    df["DaysSincePasswordChange"] = _days_since(df["PasswordLastSet"])
    df["DaysSinceLastLogon"] = _days_since(df["LastLogonDate"])
    df["PrivilegedMember"] = df["MemberOf"].apply(_contains_sensitive_group)
    df["PasswordAgeStatus"] = df["DaysSincePasswordChange"].apply(lambda d: _password_age_status(d, settings))
    df["RiskGroup"] = df.apply(lambda row: _risk_group(row, settings, complexity_enabled), axis=1)

    fingerprints = _load_optional_fingerprints(settings.optional_password_audit_csv)
    notes = [
        "SAFE DEFAULT MODE: identical passwords are not detectable from AD-only data.",
        "OPTIONAL AUDIT INPUT MODE can group accounts by PasswordFingerprintGroup if sanctioned CSV is supplied.",
    ]
    if fingerprints is not None:
        df = df.merge(fingerprints, on="SamAccountName", how="left")
        notes.append("Optional password fingerprint dataset loaded.")
    else:
        df["PasswordFingerprintGroup"] = "N/A"

    summary = {
        "total_users": int(len(df)),
        "enabled_users": int(df["Enabled"].fillna(False).sum()),
        "disabled_users": int((~df["Enabled"].fillna(False)).sum()),
        "password_never_expires": int(df["PasswordNeverExpires"].fillna(False).sum()),
        "pwd_over_30": int((df["DaysSincePasswordChange"] > 30).sum()),
        "pwd_over_60": int((df["DaysSincePasswordChange"] > 60).sum()),
        "pwd_over_90": int((df["DaysSincePasswordChange"] > 90).sum()),
        "pwd_over_180": int((df["DaysSincePasswordChange"] > 180).sum()),
        "privileged_accounts": int(df["PrivilegedMember"].sum()),
        "risk_distribution": df["RiskGroup"].value_counts().to_dict(),
    }

    report_df = df.drop(columns=["MemberOf"], errors="ignore").rename(columns=PASSWORD_REPORT_COLUMN_NAMES)
    return PasswordAuditResult(policy=policy, dataframe=report_df, summary=summary, notes=notes)
