import unittest

import pandas as pd

from ad_security_reporter.models.pandas_model import _is_missing_value


class PandasModelTests(unittest.TestCase):
    def test_is_missing_value_handles_scalar_values(self) -> None:
        self.assertTrue(_is_missing_value(pd.NA))
        self.assertFalse(_is_missing_value("value"))

    def test_is_missing_value_handles_array_like_values(self) -> None:
        self.assertFalse(_is_missing_value(["a", "b"]))
        self.assertTrue(_is_missing_value([None, float("nan")]))


if __name__ == "__main__":
    unittest.main()
