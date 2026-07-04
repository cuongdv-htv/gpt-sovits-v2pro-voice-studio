# -*- coding: utf-8 -*-
"""Điểm vào ứng dụng GPT-SoVITS v2Pro Voice Studio."""

import sys
from pathlib import Path

# Cho phép chạy trực tiếp `python app/main.py` lẫn `python -m app.main`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from app.ui_main import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GPT-SoVITS v2Pro Voice Studio")
    app.setOrganizationName("VoiceStudio")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
