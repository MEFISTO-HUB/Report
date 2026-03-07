from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class PowerShellExecutionError(RuntimeError):
    pass


@dataclass
class PowerShellConnector:
    executable: str = "powershell"

    def run_json(self, script: str) -> list[dict]:
        command = [
            self.executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ]
        logger.info("Running PowerShell command")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("PowerShell failed: %s", result.stderr.strip())
            raise PowerShellExecutionError(result.stderr.strip() or "PowerShell command failed")
        stdout = result.stdout.strip()
        if not stdout:
            return []
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.exception("JSON decode failed")
            raise PowerShellExecutionError(f"Invalid JSON from PowerShell: {exc}") from exc
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
