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

        for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp1251", "cp866"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _iter_decoded_outputs(data: bytes | None) -> list[str]:
        if not data:
            return [""]

        candidates: list[str] = []
        seen: set[str] = set()

        def add(value: str) -> None:
            if value in seen:
                return
            seen.add(value)
            candidates.append(value)

        add(PowerShellConnector._decode_output(data))

        for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1251", "cp866"):
            try:
                add(data.decode(encoding))
            except UnicodeDecodeError:
                continue

        return candidates

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

        parsed = None
        parse_error: json.JSONDecodeError | None = None
        for decoded_output in self._iter_decoded_outputs(result.stdout):
            payload = self._extract_json_payload(decoded_output.strip())
            try:
                parsed = json.loads(payload)
                stdout = decoded_output.strip()
                break
            except json.JSONDecodeError as exc:
                parse_error = exc

        if parsed is None:
            logger.error("JSON decode failed")
            preview = stdout.splitlines()[:5]
            raise PowerShellExecutionError(
                "Invalid JSON from PowerShell: "
                f"{parse_error}. Output preview: {' | '.join(preview)}"
            ) from parse_error
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
