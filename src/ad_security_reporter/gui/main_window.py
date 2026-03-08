from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QFrame,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
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
from ad_security_reporter.exporters.report_exporter import build_report_path, export_html
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

        self.setWindowTitle("Отчет по безопасности Active Directory")
        self.resize(1400, 820)
        self.statusBar().showMessage("Готово к работе")

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

        self.tabs.addTab(self.password_tab, "Аудит паролей")
        self.tabs.addTab(self.computers_tab, "Последний вход компьютеров")
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.export_tab, "Экспорт / Отчеты")

    @staticmethod
    def _create_section_title(text: str) -> QLabel:
        title = QLabel(text)
        title.setProperty("class", "sectionTitle")
        return title

    def _build_password_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QHBoxLayout()
        self.password_collect_btn = QPushButton("Собрать данные")
        self.password_collect_btn.clicked.connect(self.collect_password_data)
        self.password_clear_filter_btn = QPushButton("Сбросить фильтр")
        self.password_clear_filter_btn.clicked.connect(lambda: self.password_search.clear())
        self.password_search = QLineEdit()
        self.password_search.setPlaceholderText("Поиск по таблице...")
        self.password_search.textChanged.connect(self._on_password_search)
        controls.addWidget(self.password_collect_btn)
        controls.addWidget(self.password_clear_filter_btn)
        controls.addWidget(self.password_search)

        quick_stats = QFrame()
        quick_stats.setProperty("class", "quickStats")
        quick_stats_layout = QHBoxLayout(quick_stats)
        quick_stats_layout.setContentsMargins(10, 8, 10, 8)
        self.password_rows_label = QLabel("Строк: 0")
        self.password_filtered_label = QLabel("После фильтра: 0")
        quick_stats_layout.addWidget(self.password_rows_label)
        quick_stats_layout.addWidget(self.password_filtered_label)
        quick_stats_layout.addStretch(1)

        self.password_cards = QLabel("Статистика: данные еще не загружены")
        self.password_cards.setProperty("class", "statCards")
        self.password_cards.setWordWrap(True)

        self.password_model = PandasTableModel()
        self.password_proxy = QSortFilterProxyModel()
        self.password_proxy.setSourceModel(self.password_model)
        self.password_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.password_proxy.setFilterKeyColumn(-1)
        self.password_proxy.rowsInserted.connect(self._update_password_counts)
        self.password_proxy.rowsRemoved.connect(self._update_password_counts)
        self.password_proxy.modelReset.connect(self._update_password_counts)
        self.password_table = QTableView()
        self.password_table.setSortingEnabled(True)
        self.password_table.setAlternatingRowColors(True)
        self.password_table.setModel(self.password_proxy)
        self.password_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.password_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self._create_section_title("Учетные записи и парольная гигиена"))
        layout.addLayout(controls)
        layout.addWidget(quick_stats)
        layout.addWidget(self.password_cards)
        layout.addWidget(self.password_table)
        return widget

    def _build_computers_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QHBoxLayout()
        self.computers_collect_btn = QPushButton("Собрать данные")
        self.computers_collect_btn.clicked.connect(self.collect_computers_data)
        self.computers_clear_filter_btn = QPushButton("Сбросить фильтр")
        self.computers_clear_filter_btn.clicked.connect(lambda: self.computers_search.clear())
        self.computers_search = QLineEdit()
        self.computers_search.setPlaceholderText("Поиск по таблице...")
        self.computers_search.textChanged.connect(self._on_computers_search)
        controls.addWidget(self.computers_collect_btn)
        controls.addWidget(self.computers_clear_filter_btn)
        controls.addWidget(self.computers_search)

        quick_stats = QFrame()
        quick_stats.setProperty("class", "quickStats")
        quick_stats_layout = QHBoxLayout(quick_stats)
        quick_stats_layout.setContentsMargins(10, 8, 10, 8)
        self.computers_rows_label = QLabel("Строк: 0")
        self.computers_filtered_label = QLabel("После фильтра: 0")
        quick_stats_layout.addWidget(self.computers_rows_label)
        quick_stats_layout.addWidget(self.computers_filtered_label)
        quick_stats_layout.addStretch(1)

        self.computers_cards = QLabel("Статистика: данные еще не загружены")
        self.computers_cards.setProperty("class", "statCards")
        self.computers_cards.setWordWrap(True)

        self.computers_model = PandasTableModel()
        self.computers_proxy = QSortFilterProxyModel()
        self.computers_proxy.setSourceModel(self.computers_model)
        self.computers_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.computers_proxy.setFilterKeyColumn(-1)
        self.computers_proxy.rowsInserted.connect(self._update_computers_counts)
        self.computers_proxy.rowsRemoved.connect(self._update_computers_counts)
        self.computers_proxy.modelReset.connect(self._update_computers_counts)
        self.computers_table = QTableView()
        self.computers_table.setSortingEnabled(True)
        self.computers_table.setAlternatingRowColors(True)
        self.computers_table.setModel(self.computers_proxy)
        self.computers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.computers_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self._create_section_title("Активность рабочих станций и серверов"))
        layout.addLayout(controls)
        layout.addWidget(quick_stats)
        layout.addWidget(self.computers_cards)
        layout.addWidget(self.computers_table)
        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        general_group = QGroupBox("Подключение и оформление")
        general_form = QFormLayout(general_group)

        self.domain_input = QLineEdit(self.settings.domain)
        self.dc_input = QLineEdit(self.settings.domain_controller)
        self.optional_csv_input = QLineEdit(self.settings.optional_password_audit_csv)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.settings.theme)
        self.medium_input = QLineEdit(str(self.settings.risk.medium_days))
        self.high_input = QLineEdit(str(self.settings.risk.high_days))
        self.critical_input = QLineEdit(str(self.settings.risk.critical_days))

        thresholds_group = QGroupBox("Пороговые значения риска")
        thresholds_grid = QGridLayout(thresholds_group)
        thresholds_grid.addWidget(QLabel("Средний риск (дни)"), 0, 0)
        thresholds_grid.addWidget(self.medium_input, 0, 1)
        thresholds_grid.addWidget(QLabel("Высокий риск (дни)"), 1, 0)
        thresholds_grid.addWidget(self.high_input, 1, 1)
        thresholds_grid.addWidget(QLabel("Критический риск (дни)"), 2, 0)
        thresholds_grid.addWidget(self.critical_input, 2, 1)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self.save_settings)

        general_form.addRow("Домен", self.domain_input)
        general_form.addRow("DC", self.dc_input)
        general_form.addRow("Доп. CSV с отпечатками паролей", self.optional_csv_input)
        general_form.addRow("Тема", self.theme_combo)

        layout.addWidget(general_group)
        layout.addWidget(thresholds_group)
        layout.addWidget(save_btn, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        return widget

    def _build_export_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        export_pwd_btn = QPushButton("Экспорт отчета: аудит паролей (.html)")
        export_pwd_btn.clicked.connect(lambda: self._export_dataset("password"))
        export_comp_btn = QPushButton("Экспорт отчета: компьютеры (.html)")
        export_comp_btn.clicked.connect(lambda: self._export_dataset("computers"))
        export_all_btn = QPushButton("Экспортировать все отчеты (.html)")
        export_all_btn.clicked.connect(self.export_all)
        layout.addWidget(export_pwd_btn)
        layout.addWidget(export_comp_btn)
        layout.addWidget(export_all_btn)
        return widget

    def _on_password_search(self, text: str) -> None:
        self.password_proxy.setFilterFixedString(text)
        self._update_password_counts()

    def _on_computers_search(self, text: str) -> None:
        self.computers_proxy.setFilterFixedString(text)
        self._update_computers_counts()

    def _update_password_counts(self) -> None:
        total = self.password_model.rowCount()
        filtered = self.password_proxy.rowCount()
        self.password_rows_label.setText(f"Строк: {total}")
        self.password_filtered_label.setText(f"После фильтра: {filtered}")

    def _update_computers_counts(self) -> None:
        total = self.computers_model.rowCount()
        filtered = self.computers_proxy.rowCount()
        self.computers_rows_label.setText(f"Строк: {total}")
        self.computers_filtered_label.setText(f"После фильтра: {filtered}")

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
        self._update_password_counts()
        self.progress.setValue(100)
        self.statusBar().showMessage("Аудит паролей завершен")

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
        self._update_computers_counts()
        self.progress.setValue(100)
        self.statusBar().showMessage("Аудит компьютеров завершен")

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
        folder_path = Path(folder)
        titles = {
            "password": "Отчет по аудиту паролей",
            "computers": "Отчет по активности компьютеров",
        }
        report_path = build_report_path(folder_path, f"{name}_report", ".html")
        export_html(df, report_path, titles.get(name, "Отчет"), summary, notes)
        self.statusBar().showMessage(f"Экспорт завершен: {report_path}")

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
