import json
import unittest
from unittest.mock import patch

from ad_security_reporter.connectors.powershell_connector import (
    PowerShellConnector,
    PowerShellExecutionError,
)


class _CompletedProcess:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes = b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class PowerShellConnectorTests(unittest.TestCase):
    def test_run_json_parses_utf16be_output(self) -> None:
        payload = json.dumps([{"Name": "PK-DC-01"}], ensure_ascii=False)
        process_result = _CompletedProcess(returncode=0, stdout=payload.encode("utf-16-be"))

        with patch("subprocess.run", return_value=process_result):
            connector = PowerShellConnector()
            data = connector.run_json("Get-ADComputer ...")

        self.assertEqual(data, [{"Name": "PK-DC-01"}])

    def test_run_json_raises_for_invalid_json(self) -> None:
        process_result = _CompletedProcess(returncode=0, stdout=b"not json")

        with patch("subprocess.run", return_value=process_result):
            connector = PowerShellConnector()
            with self.assertRaises(PowerShellExecutionError):
                connector.run_json("Get-ADComputer ...")


if __name__ == "__main__":
    unittest.main()
