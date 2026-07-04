# -*- coding: utf-8 -*-
"""Theo dõi VRAM GPU NVIDIA bằng nvidia-smi (poll ở thread nền)."""

import os
import shutil
import subprocess
import time

from PySide6.QtCore import QThread, Signal

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class VramMonitor(QThread):
    """Phát sig_vram(used_mb, total_mb) mỗi `interval` giây.
    Máy không có nvidia-smi → thread kết thúc êm, không phát gì."""

    sig_vram = Signal(int, int)

    def __init__(self, interval: float = 5.0, parent=None):
        super().__init__(parent)
        self.interval = interval
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        if not shutil.which("nvidia-smi"):
            return
        while not self._stop:
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, timeout=5,
                    creationflags=CREATE_NO_WINDOW)
                if r.returncode == 0:
                    line = r.stdout.decode(errors="replace").strip().splitlines()[0]
                    used, total = (int(x.strip()) for x in line.split(",")[:2])
                    self.sig_vram.emit(used, total)
            except Exception:
                pass
            # ngủ chia nhỏ để stop() phản hồi nhanh
            for _ in range(int(self.interval * 10)):
                if self._stop:
                    return
                time.sleep(0.1)
