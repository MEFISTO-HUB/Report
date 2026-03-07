import unittest

from ad_security_reporter.config.settings import AppSettings
from ad_security_reporter.core.computer_audit import collect_computer_audit
from ad_security_reporter.core.password_audit import collect_password_audit


class FakeConnector:
    def run_json(self, script: str):
        if "Get-ADDefaultDomainPasswordPolicy" in script:
            return [{"ComplexityEnabled": True}]
        if "Get-ADUser" in script:
            return [
                {
                    "SamAccountName": "user1",
                    "Name": "User One",
                    "DisplayName": "User One",
                    "Enabled": True,
                    "Department": "IT",
                    "Title": "Admin",
                    "CanonicalName": "domain.local/IT/User One",
                    "MemberOf": ["CN=Domain Admins,CN=Users,DC=domain,DC=local"],
                    "PasswordLastSet": "2026-01-01T00:00:00Z",
                    "LastLogonDate": "2026-01-10T00:00:00Z",
                    "PasswordNeverExpires": False,
                    "CannotChangePassword": False,
                    "PasswordExpired": False,
                    "SmartcardLogonRequired": False,
                    "AccountExpirationDate": None,
                    "WhenCreated": "2025-01-01T00:00:00Z",
                    "adminCount": 1,
                }
            ]
        if "Get-ADComputer" in script:
            return [
                {
                    "Name": "PC01",
                    "DNSHostName": "pc01.domain.local",
                    "OperatingSystem": "Windows 11",
                    "OperatingSystemVersion": "10.0",
                    "DistinguishedName": "CN=PC01,OU=Computers,DC=domain,DC=local",
                    "CanonicalName": "domain.local/Computers/PC01",
                    "Enabled": True,
                    "LastLogonDate": "2026-01-10T00:00:00Z",
                    "WhenCreated": "2025-01-01T00:00:00Z",
                    "PasswordLastSet": "2025-12-01T00:00:00Z",
                    "IPv4Address": "10.0.0.1",
                    "Description": "Workstation",
                }
            ]
        return []


class ReportColumnsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings()
        self.connector = FakeConnector()

    def test_password_report_uses_russian_headers_and_hides_memberof(self) -> None:
        result = collect_password_audit(self.settings, self.connector)

        self.assertIn("Дней без смены пароля", result.dataframe.columns)
        self.assertIn("Дней с последнего входа", result.dataframe.columns)
        self.assertNotIn("MemberOf", result.dataframe.columns)

    def test_computer_report_uses_russian_headers_and_days_column(self) -> None:
        result = collect_computer_audit(self.settings, self.connector)

        self.assertIn("Дней с последнего входа", result.dataframe.columns)
        self.assertIn("Статус активности", result.dataframe.columns)


if __name__ == "__main__":
    unittest.main()
