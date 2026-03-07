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

    @staticmethod
    def _extract_json_payload(output: str) -> str:
        trimmed = output.lstrip("\ufeff\r\n\t ")
        if not trimmed:
            return ""

        start = min((idx for idx in (trimmed.find("["), trimmed.find("{")) if idx != -1), default=-1)
        if start == -1:
            return trimmed

        candidate = trimmed[start:]
        end = max(candidate.rfind("]"), candidate.rfind("}"))
        if end != -1:
            candidate = candidate[: end + 1]
        return candidate

    @staticmethod
    def _decode_output(data: bytes | None) -> str:
        if not data:
            return ""

        for encoding in ("utf-8", "utf-16-le", "cp1251", "cp866"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        return data.decode("utf-8", errors="replace")

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
        result = subprocess.run(command, capture_output=True, text=False, check=False)
        stdout = self._decode_output(result.stdout).strip()
        stderr = self._decode_output(result.stderr).strip()

        if result.returncode != 0:
            logger.error("PowerShell failed: %s", stderr)
            raise PowerShellExecutionError(stderr or "PowerShell command failed")

        if not stdout:
            return []

        payload = self._extract_json_payload(stdout)
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.exception("JSON decode failed")
            preview = stdout.splitlines()[:5]
            raise PowerShellExecutionError(
                f"Invalid JSON from PowerShell: {exc}. Output preview: {' | '.join(preview)}"
            ) from exc
        if parsed is None:
            return []
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
