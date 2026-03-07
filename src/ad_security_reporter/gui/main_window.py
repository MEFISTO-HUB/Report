from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QHeaderView,
)

from ad_security_reporter.config.settings import AppSettings, save_settings
from ad_security_reporter.connectors.powershell_connector import PowerShellConnector
from ad_security_reporter.core.computer_audit import collect_computer_audit
from ad_security_reporter.core.password_audit import collect_password_audit
from ad_security_reporter.exporters.report_exporter import export_csv, export_html, export_xlsx
from ad_security_reporter.models.pandas_model import PandasTableModel

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, settings_path: Path):
        super().__init__()
        self.settings = settings
        self.settings_path = settings_path
        self.connector = PowerShellConnector(executable=settings.powershell_executable)
        self.password_df = pd.DataFrame()
        self.password_summary: dict = {}
        self.password_notes: list[str] = []
        self.computers_df = pd.DataFrame()
        self.computers_summary: dict = {}
        self.computers_notes: list[str] = []

        self.setWindowTitle("AD Security Reporter")
        self.resize(1400, 820)
        self.statusBar().showMessage("Ready")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.statusBar().addPermanentWidget(self.progress)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.password_tab = self._build_password_tab()
        self.computers_tab = self._build_computers_tab()
        self.settings_tab = self._build_settings_tab()
        self.export_tab = self._build_export_tab()

        self.tabs.addTab(self.password_tab, "Password Audit")
        self.tabs.addTab(self.computers_tab, "Computers Last Logon")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.export_tab, "Export / Reports")

    def _build_password_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QHBoxLayout()
        self.password_collect_btn = QPushButton("Собрать данные")
        self.password_collect_btn.clicked.connect(self.collect_password_data)
        self.password_search = QLineEdit()
        self.password_search.setPlaceholderText("Поиск по таблице...")
        self.password_search.textChanged.connect(self._on_password_search)
        controls.addWidget(self.password_collect_btn)
        controls.addWidget(self.password_search)

        self.password_cards = QLabel("Статистика: нет данных")
        self.password_cards.setWordWrap(True)

        self.password_model = PandasTableModel()
        self.password_proxy = QSortFilterProxyModel()
        self.password_proxy.setSourceModel(self.password_model)
        self.password_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.password_proxy.setFilterKeyColumn(-1)
        self.password_table = QTableView()
        self.password_table.setSortingEnabled(True)
        self.password_table.setModel(self.password_proxy)
        self.password_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.password_table.horizontalHeader().setStretchLastSection(True)

        layout.addLayout(controls)
        layout.addWidget(self.password_cards)
        layout.addWidget(self.password_table)
        return widget

    def _build_computers_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QHBoxLayout()
        self.computers_collect_btn = QPushButton("Собрать данные")
        self.computers_collect_btn.clicked.connect(self.collect_computers_data)
        self.computers_search = QLineEdit()
        self.computers_search.setPlaceholderText("Поиск по таблице...")
        self.computers_search.textChanged.connect(self._on_computers_search)
        controls.addWidget(self.computers_collect_btn)
        controls.addWidget(self.computers_search)

        self.computers_cards = QLabel("Статистика: нет данных")
        self.computers_cards.setWordWrap(True)

        self.computers_model = PandasTableModel()
        self.computers_proxy = QSortFilterProxyModel()
        self.computers_proxy.setSourceModel(self.computers_model)
        self.computers_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.computers_proxy.setFilterKeyColumn(-1)
        self.computers_table = QTableView()
        self.computers_table.setSortingEnabled(True)
        self.computers_table.setModel(self.computers_proxy)
        self.computers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.computers_table.horizontalHeader().setStretchLastSection(True)

        layout.addLayout(controls)
        layout.addWidget(self.computers_cards)
        layout.addWidget(self.computers_table)
        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self.domain_input = QLineEdit(self.settings.domain)
        self.dc_input = QLineEdit(self.settings.domain_controller)
        self.optional_csv_input = QLineEdit(self.settings.optional_password_audit_csv)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.settings.theme)
        self.medium_input = QLineEdit(str(self.settings.risk.medium_days))
        self.high_input = QLineEdit(str(self.settings.risk.high_days))
        self.critical_input = QLineEdit(str(self.settings.risk.critical_days))

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self.save_settings)

        layout.addRow("Домен", self.domain_input)
        layout.addRow("DC", self.dc_input)
        layout.addRow("Optional fingerprint CSV", self.optional_csv_input)
        layout.addRow("Theme", self.theme_combo)
        layout.addRow("Risk medium days", self.medium_input)
        layout.addRow("Risk high days", self.high_input)
        layout.addRow("Risk critical days", self.critical_input)
        layout.addRow(save_btn)
        return widget

    def _build_export_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        export_pwd_btn = QPushButton("Экспорт Password Audit")
        export_pwd_btn.clicked.connect(lambda: self._export_dataset("password"))
        export_comp_btn = QPushButton("Экспорт Computers")
        export_comp_btn.clicked.connect(lambda: self._export_dataset("computers"))
        export_all_btn = QPushButton("Экспорт всех отчетов")
        export_all_btn.clicked.connect(self.export_all)
        layout.addWidget(export_pwd_btn)
        layout.addWidget(export_comp_btn)
        layout.addWidget(export_all_btn)
        return widget

    def _on_password_search(self, text: str) -> None:
        self.password_proxy.setFilterFixedString(text)

    def _on_computers_search(self, text: str) -> None:
        self.computers_proxy.setFilterFixedString(text)

    def collect_password_data(self) -> None:
        self.progress.setValue(10)
        try:
            result = collect_password_audit(self.settings, self.connector)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить password audit: {exc}")
            logger.exception("Password audit failed")
            self.progress.setValue(0)
            return
        self.password_df = result.dataframe
        self.password_summary = result.summary
        self.password_notes = result.notes
        self.password_model.set_dataframe(self.password_df)
        self.password_cards.setText(" | ".join(f"{k}: {v}" for k, v in self.password_summary.items() if k != "risk_distribution"))
        self.progress.setValue(100)
        self.statusBar().showMessage("Password audit complete")

    def collect_computers_data(self) -> None:
        self.progress.setValue(10)
        try:
            result = collect_computer_audit(self.settings, self.connector)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить computer audit: {exc}")
            logger.exception("Computer audit failed")
            self.progress.setValue(0)
            return
        self.computers_df = result.dataframe
        self.computers_summary = result.summary
        self.computers_notes = result.notes
        self.computers_model.set_dataframe(self.computers_df)
        self.computers_cards.setText(" | ".join(f"{k}: {v}" for k, v in self.computers_summary.items() if k != "os_distribution"))
        self.progress.setValue(100)
        self.statusBar().showMessage("Computer audit complete")

    def _export_dataset(self, name: str) -> None:
        df = self.password_df if name == "password" else self.computers_df
        summary = self.password_summary if name == "password" else self.computers_summary
        notes = self.password_notes if name == "password" else self.computers_notes
        if df.empty:
            QMessageBox.warning(self, "Нет данных", "Сначала соберите данные")
            return

        folder = QFileDialog.getExistingDirectory(self, "Выберите папку экспорта")
        if not folder:
            return
        base = Path(folder) / f"{name}_report"
        export_csv(df, base.with_suffix(".csv"))
        export_xlsx(df, base.with_suffix(".xlsx"), summary)
        export_html(df, base.with_suffix(".html"), f"{name.title()} report", summary, notes)
        self.statusBar().showMessage(f"Экспорт завершен: {base}")

    def export_all(self) -> None:
        self._export_dataset("password")
        self._export_dataset("computers")

    def save_settings(self) -> None:
        self.settings.domain = self.domain_input.text().strip()
        self.settings.domain_controller = self.dc_input.text().strip()
        self.settings.optional_password_audit_csv = self.optional_csv_input.text().strip()
        self.settings.theme = self.theme_combo.currentText()
        self.settings.risk.medium_days = int(self.medium_input.text())
        self.settings.risk.high_days = int(self.high_input.text())
        self.settings.risk.critical_days = int(self.critical_input.text())

        save_settings(self.settings_path, self.settings)
        self.connector = PowerShellConnector(executable=self.settings.powershell_executable)
        self.statusBar().showMessage("Настройки сохранены")
