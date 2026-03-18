import unittest

import pandas as pd
from PySide6.QtCore import Qt

from ad_security_reporter.models.pandas_model import PandasTableModel, _is_missing_value


class PandasModelTests(unittest.TestCase):
    def test_is_missing_value_handles_scalar_values(self) -> None:
        self.assertTrue(_is_missing_value(pd.NA))
        self.assertFalse(_is_missing_value("value"))

    def test_is_missing_value_handles_array_like_values(self) -> None:
        self.assertFalse(_is_missing_value(["a", "b"]))
        self.assertTrue(_is_missing_value([None, float("nan")]))

    def test_display_role_localizes_unknown_value(self) -> None:
        model = PandasTableModel(pd.DataFrame([{"status": "Unknown"}]))
        index = model.index(0, 0)
        self.assertEqual(model.data(index, Qt.DisplayRole), "Неизвестно")


if __name__ == "__main__":
    unittest.main()
