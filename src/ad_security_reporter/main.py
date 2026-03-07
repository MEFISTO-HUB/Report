from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ad_security_reporter.config.settings import load_settings
from ad_security_reporter.core.logging_setup import setup_logging
from ad_security_reporter.gui.main_window import MainWindow


def main() -> int:
    base_dir = Path.cwd()
    settings_path = base_dir / "config" / "config.yaml"
    log_path = base_dir / "logs" / "ad_security_reporter.log"
    setup_logging(log_path)

    app = QApplication(sys.argv)
    settings = load_settings(settings_path)
    window = MainWindow(settings, settings_path)
    style_path = base_dir / 'src' / 'ad_security_reporter' / 'assets' / f'{settings.theme}.qss'
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding='utf-8'))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
