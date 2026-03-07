from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class RiskThresholds:
    medium_days: int = 60
    high_days: int = 90
    critical_days: int = 180
    warn_days: int = 30


@dataclass
class AppSettings:
    domain: str = "serbsky.lan"
    domain_controller: str = "kp-dc01"
    theme: str = "dark"
    optional_password_audit_csv: str = ""
    powershell_executable: str = "powershell"
    risk: RiskThresholds = field(default_factory=RiskThresholds)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        risk = RiskThresholds(**data.get("risk", {}))
        base = {k: v for k, v in data.items() if k != "risk"}
        return cls(**base, risk=risk)

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        data["risk"] = self.risk.__dict__.copy()
        return data


def load_settings(path: Path) -> AppSettings:
    if not path.exists():
        return AppSettings()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return AppSettings.from_dict(raw)


def save_settings(path: Path, settings: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(settings.to_dict(), fh, sort_keys=False, allow_unicode=True)
