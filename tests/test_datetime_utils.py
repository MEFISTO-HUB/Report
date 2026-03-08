import unittest

import pandas as pd

from ad_security_reporter.core.datetime_utils import format_datetime, to_utc_datetime


class DateTimeUtilsTests(unittest.TestCase):
    def test_to_utc_datetime_supports_dotnet_format(self) -> None:
        result = to_utc_datetime('/Date(1768003200000)/')

        self.assertEqual(result.strftime('%Y-%m-%d %H:%M:%S'), '2026-01-10 00:00:00')

    def test_format_datetime_returns_empty_for_invalid(self) -> None:
        series = pd.Series([to_utc_datetime('bad-date'), to_utc_datetime('/Date(1768003200000)/')])

        result = format_datetime(series)

        self.assertEqual(result.iloc[0], '')
        self.assertEqual(result.iloc[1], '2026-01-10 00:00:00')


if __name__ == '__main__':
    unittest.main()
