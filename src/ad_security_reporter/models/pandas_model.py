from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class PandasTableModel(QAbstractTableModel):
    def __init__(self, dataframe: pd.DataFrame | None = None) -> None:
        super().__init__()
        self._df = dataframe if dataframe is not None else pd.DataFrame()

    def set_dataframe(self, dataframe: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = dataframe.copy()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._df.iat[index.row(), index.column()]
        if role == Qt.DisplayRole:
            return "" if pd.isna(value) else str(value)
        if role == Qt.UserRole:
            return value
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)
