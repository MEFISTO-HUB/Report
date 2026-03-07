import unittest

import pandas as pd

from ad_security_reporter.core.computer_audit import _days_since


class ComputerAuditTests(unittest.TestCase):
    def test_days_since_handles_tz_naive_series(self) -> None:
        series = pd.Series(["2026-01-01 00:00:00", None])

        result = _days_since(series)

        self.assertEqual(len(result), 2)
        self.assertTrue(pd.isna(result.iloc[1]))
        self.assertTrue(pd.notna(result.iloc[0]))

    def test_days_since_handles_tz_aware_series(self) -> None:
        series = pd.Series(["2026-01-01T00:00:00+03:00", "2026-01-01T00:00:00Z"])

        result = _days_since(series)

        self.assertEqual(len(result), 2)
        self.assertTrue((result >= 0).all())


if __name__ == "__main__":
    unittest.main()
