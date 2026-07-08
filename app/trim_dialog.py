# -*- coding: utf-8 -*-
"""Hộp thoại cắt audio mẫu: hiển thị waveform, kéo 2 mốc đầu/cuối,
nghe thử đoạn chọn, lưu bản cắt 3–10 giây (giới hạn engine GPT-SoVITS)."""

from pathlib import Path

import numpy as np
import soundfile as sf
from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QDialog, QDoubleSpinBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from app.audio_post import REF_MAX_SEC as MAX_SEC
from app.audio_post import REF_MIN_SEC as MIN_SEC
from app.audio_post import load_audio_any


class WaveformWidget(QWidget):
    """Vẽ envelope waveform + vùng chọn; kéo chuột để chỉnh mốc gần nhất."""

    selectionChanged = Signal(float, float)  # start_sec, end_sec

    def __init__(self, mono: np.ndarray, sr: int, parent=None):
        super().__init__(parent)
        self.duration = len(mono) / float(sr)
        self.sel_start = 0.0
        self.sel_end = min(self.duration, MAX_SEC)
        self._drag = None  # "start" | "end" | None
        self.setMinimumHeight(140)
        self.setCursor(Qt.CrossCursor)

        # Envelope min/max theo ~1400 cột
        n_bins = min(1400, max(1, len(mono)))
        hop = max(1, len(mono) // n_bins)
        trimmed = mono[: (len(mono) // hop) * hop].reshape(-1, hop)
        self.env_min = trimmed.min(axis=1)
        self.env_max = trimmed.max(axis=1)

    # ---- chọn vùng ----
    def set_selection(self, start: float, end: float, emit: bool = True):
        start = max(0.0, min(start, self.duration))
        end = max(0.0, min(end, self.duration))
        if end - start < 0.2:  # tối thiểu 0.2s để 2 mốc không dính nhau
            return
        self.sel_start, self.sel_end = start, end
        self.update()
        if emit:
            self.selectionChanged.emit(start, end)

    def _x_to_sec(self, x: float) -> float:
        return max(0.0, min(self.duration, x / max(1, self.width()) * self.duration))

    def mousePressEvent(self, e):
        t = self._x_to_sec(e.position().x())
        self._drag = ("start"
                      if abs(t - self.sel_start) <= abs(t - self.sel_end)
                      else "end")
        self._drag_to(t)

    def mouseMoveEvent(self, e):
        if self._drag:
            self._drag_to(self._x_to_sec(e.position().x()))

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def _drag_to(self, t: float):
        if self._drag == "start":
            self.set_selection(min(t, self.sel_end - 0.2), self.sel_end)
        elif self._drag == "end":
            self.set_selection(self.sel_start, max(t, self.sel_start + 0.2))

    # ---- vẽ ----
    def paintEvent(self, _e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        mid = h / 2
        p.fillRect(0, 0, w, h, QColor("#f4f5f8"))

        # vùng chọn
        x1 = int(self.sel_start / self.duration * w) if self.duration else 0
        x2 = int(self.sel_end / self.duration * w) if self.duration else 0
        p.fillRect(x1, 0, max(1, x2 - x1), h, QColor(47, 111, 237, 40))

        # waveform
        p.setPen(QPen(QColor("#5b7fc7"), 1))
        n = len(self.env_min)
        for col in range(w):
            i = int(col / max(1, w) * n)
            if i >= n:
                break
            y1 = mid - self.env_max[i] * (mid - 4)
            y2 = mid - self.env_min[i] * (mid - 4)
            p.drawLine(col, int(y1), col, int(y2))

        # 2 mốc
        for x, color in ((x1, "#1e8449"), (x2, "#c0392b")):
            p.setPen(QPen(QColor(color), 2))
            p.drawLine(x, 0, x, h)
        p.end()


class TrimDialog(QDialog):
    """Trả về đường dẫn file đã cắt qua thuộc tính saved_path (None nếu hủy)."""

    def __init__(self, audio_path: str, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.audio_path = audio_path
        self.saved_path = None
        tr = i18n.tr
        self.setWindowTitle(tr("trim_title"))
        self.resize(760, 320)

        data, sr = load_audio_any(audio_path)  # có thể ném exception — caller bắt
        self.data, self.sr = data, sr
        mono = data.mean(axis=1)
        peak = float(np.abs(mono).max()) or 1.0
        self.wave = WaveformWidget(mono / peak, sr)

        lay = QVBoxLayout(self)
        self.lbl_file = QLabel(f"{Path(audio_path).name} — "
                               f"{self.wave.duration:.2f}s, {sr} Hz")
        lay.addWidget(self.lbl_file)
        lay.addWidget(self.wave, 1)

        row = QHBoxLayout()
        self.sp_start = QDoubleSpinBox()
        self.sp_end = QDoubleSpinBox()
        for sp in (self.sp_start, self.sp_end):
            sp.setRange(0.0, self.wave.duration)
            sp.setDecimals(2)
            sp.setSingleStep(0.1)
            sp.setSuffix(" s")
        self.sp_start.setValue(self.wave.sel_start)
        self.sp_end.setValue(self.wave.sel_end)
        row.addWidget(QLabel(tr("trim_start")))
        row.addWidget(self.sp_start)
        row.addWidget(QLabel(tr("trim_end")))
        row.addWidget(self.sp_end)
        self.lbl_len = QLabel()
        row.addWidget(self.lbl_len, 1)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.btn_play = QPushButton(tr("trim_play"))
        self.btn_save = QPushButton(tr("trim_save"))
        self.btn_save.setObjectName("primary")
        self.btn_cancel = QPushButton(tr("cancel"))
        row2.addWidget(self.btn_play)
        row2.addStretch(1)
        row2.addWidget(self.btn_save)
        row2.addWidget(self.btn_cancel)
        lay.addLayout(row2)

        # player nghe thử đoạn chọn
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.player.setSource(QUrl.fromLocalFile(audio_path))
        self.player.positionChanged.connect(self._auto_stop)

        self.wave.selectionChanged.connect(self._on_wave_changed)
        self.sp_start.valueChanged.connect(self._on_spin_changed)
        self.sp_end.valueChanged.connect(self._on_spin_changed)
        self.btn_play.clicked.connect(self._play_selection)
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self.reject)
        self._update_len_label()

    # ---- đồng bộ ----
    def _on_wave_changed(self, start, end):
        self.sp_start.blockSignals(True)
        self.sp_end.blockSignals(True)
        self.sp_start.setValue(start)
        self.sp_end.setValue(end)
        self.sp_start.blockSignals(False)
        self.sp_end.blockSignals(False)
        self._update_len_label()

    def _on_spin_changed(self, _v):
        self.wave.set_selection(self.sp_start.value(), self.sp_end.value(),
                                emit=False)
        self._update_len_label()

    def _sel_len(self) -> float:
        return self.wave.sel_end - self.wave.sel_start

    def _update_len_label(self):
        ln = self._sel_len()
        ok = MIN_SEC <= ln <= MAX_SEC
        self.lbl_len.setText(
            f"{self.i18n.tr('trim_length')} {ln:.2f}s  "
            f"({self.i18n.tr('trim_range_hint')})")
        self.lbl_len.setStyleSheet(
            "color:#1e8449; font-weight:600;" if ok else
            "color:#c0392b; font-weight:600;")
        self.btn_save.setEnabled(ok)

    # ---- nghe thử ----
    def _play_selection(self):
        self.player.setPosition(int(self.wave.sel_start * 1000))
        self.player.play()

    def _auto_stop(self, pos_ms: int):
        if (self.player.playbackState() == QMediaPlayer.PlayingState
                and pos_ms >= int(self.wave.sel_end * 1000)):
            self.player.pause()

    # ---- lưu ----
    def _save(self):
        src = Path(self.audio_path)
        out = src.with_name(f"{src.stem}_cut.wav")
        n = 2
        while out.exists():
            out = src.with_name(f"{src.stem}_cut{n}.wav")
            n += 1
        a = int(self.wave.sel_start * self.sr)
        b = int(self.wave.sel_end * self.sr)
        try:
            sf.write(str(out), self.data[a:b], self.sr, subtype="PCM_16")
        except Exception as e:
            QMessageBox.warning(self, self.i18n.tr("error"), str(e))
            return
        self.player.stop()
        self.saved_path = str(out)
        self.accept()
