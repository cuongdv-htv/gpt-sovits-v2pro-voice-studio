# -*- coding: utf-8 -*-
"""Điểm vào ứng dụng GPT-SoVITS v2Pro Voice Studio."""

import ctypes
import os
import sys
from pathlib import Path

# Cho phép chạy trực tiếp `python app/main.py` lẫn `python -m app.main`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui_main import MainWindow


def resource_path(rel: str) -> str:
    """Đường dẫn tài nguyên: chạy source → gốc repo; đóng gói → _internal."""
    base = Path(getattr(sys, "_MEIPASS",
                        Path(__file__).resolve().parent.parent))
    return str(base / rel)


def main():
    # AppUserModelID riêng để Windows taskbar dùng icon của app
    # (không nhóm chung với python.exe)
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "cuongdv.VoiceStudio")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("GPT-SoVITS v2Pro Voice Studio")
    app.setOrganizationName("VoiceStudio")
    icon_path = resource_path("assets/icon.png")
    if Path(icon_path).is_file():
        app.setWindowIcon(QIcon(icon_path))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
