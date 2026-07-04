# -*- coding: utf-8 -*-
"""Cửa sổ chính — bố cục: (trái) Voice clone + Input/Queue · (phải) Settings ·
(dưới) Engine status + Progress + Log/Results + audio player."""

import os
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSlider, QSpinBox, QSplitter,
    QStyle, QSystemTrayIcon, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
    QHeaderView, QAbstractItemView, QFormLayout, QSizePolicy,
)

from app.engine_client import GptSovitsClient
from app.engine_manager import EngineManager
from app.errors import classify_error
from app.history import append_history, load_history
from app.i18n import CUT_METHODS, I18n, PROMPT_LANGS, TEXT_LANGS
from app.profiles import (ProfileStore, VoiceProfile, delete_voice_files,
                          store_voice_files)
from app.settings import Settings, config_dir
from app.transcribe import TranscribeWorker, WHISPER_TO_PROMPT_LANG
from app.trim_dialog import TrimDialog
from app.vram import VramMonitor
from app.worker import (BatchWorker, EngineStartWorker, ModelApplyWorker,
                        PreviewWorker, QueueItem, TtsJobConfig)

AUDIO_FILTER = "Audio (*.wav *.mp3 *.flac *.ogg *.m4a);;All files (*.*)"

STYLE = """
QMainWindow, QWidget { font-size: 10.5pt; }
QGroupBox {
    font-weight: 600; border: 1px solid #c9ccd4; border-radius: 8px;
    margin-top: 10px; padding-top: 6px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton {
    border: 1px solid #b7bcc7; border-radius: 6px; padding: 5px 12px;
    background: #f4f5f8;
}
QPushButton:hover { background: #e8ebf2; }
QPushButton:pressed { background: #dde1ea; }
QPushButton#primary {
    background: #2f6fed; color: white; border-color: #2b62d1; font-weight: 600;
}
QPushButton#primary:hover { background: #2b62d1; }
QPushButton#danger { background: #e5534b; color: white; border-color: #c9433c; }
QProgressBar { border: 1px solid #c9ccd4; border-radius: 6px; text-align: center; }
QProgressBar::chunk { background-color: #2f6fed; border-radius: 5px; }
QPlainTextEdit, QTextEdit, QLineEdit, QListWidget, QTableWidget {
    border: 1px solid #c9ccd4; border-radius: 6px;
}
"""


class DropLineEdit(QLineEdit):
    """Ô đường dẫn hỗ trợ kéo-thả file."""

    fileDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(path)
            self.fileDropped.emit(path)


class DropTableWidget(QTableWidget):
    """Bảng hàng đợi nhận kéo-thả file .txt / thư mục từ Explorer."""

    filesDropped = Signal(list)  # danh sách đường dẫn .txt

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if not e.mimeData().hasUrls():
            super().dropEvent(e)
            return
        paths = []
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                paths.extend(sorted(str(x) for x in p.glob("*.txt")))
            elif p.suffix.lower() == ".txt":
                paths.append(str(p))
        if paths:
            self.filesDropped.emit(paths)
        e.acceptProposedAction()


class AudioPlayer(QWidget):
    """Trình nghe thử: play/pause + seek + thời gian (QtMultimedia)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.slider = QSlider(Qt.Horizontal)
        self.lbl_time = QLabel("0:00 / 0:00")
        self.lbl_file = QLabel("—")
        self.lbl_file.setStyleSheet("color:#667;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.btn_play)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.lbl_time)
        lay.addWidget(self.lbl_file, 1)

        self.btn_play.clicked.connect(self._toggle)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_state)

    def load(self, path: str):
        if not path or not Path(path).is_file():
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.lbl_file.setText(Path(path).name)

    def play(self, path: str = ""):
        if path:
            self.load(path)
        self.player.play()

    def _toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_state(self, st):
        self.btn_play.setText("⏸" if st == QMediaPlayer.PlayingState else "▶")

    @staticmethod
    def _fmt(ms: int) -> str:
        s = int(ms / 1000)
        return f"{s // 60}:{s % 60:02d}"

    def _on_pos(self, pos):
        if not self.slider.isSliderDown():
            self.slider.setValue(pos)
        self.lbl_time.setText(f"{self._fmt(pos)} / {self._fmt(self.player.duration())}")

    def _on_dur(self, dur):
        self.slider.setRange(0, dur)


class MainWindow(QWidget):
    sig_engine_log = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.i18n = I18n(self.settings.get("ui_lang", "vi"))
        self.profiles = ProfileStore()
        self.client = GptSovitsClient(self.settings.get("host"),
                                      self.settings.get("port"))
        self.engine = EngineManager(on_log=self.sig_engine_log.emit)
        self.sig_engine_log.connect(self.append_log)

        self.queue: list[QueueItem] = []
        self.batch_worker: BatchWorker | None = None
        self.engine_worker: EngineStartWorker | None = None
        self.model_worker: ModelApplyWorker | None = None
        self.engine_state = "stopped"

        self.preview_worker: PreviewWorker | None = None
        self.transcribe_worker: TranscribeWorker | None = None
        self._eta_chars_done = 0
        self._eta_secs_done = 0.0
        self._item_t0 = 0.0

        self.setStyleSheet(STYLE)
        self._build_ui()
        self._load_from_settings()
        self.retranslate()
        self.resize(1360, 860)

        # Khay hệ thống — để bắn thông báo Windows khi batch xong
        tray_icon = self.windowIcon()
        if tray_icon.isNull():
            tray_icon = self.style().standardIcon(QStyle.SP_MediaVolume)
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("GPT-SoVITS v2Pro Voice Studio")
        self.tray.setVisible(True)

        # Theo dõi VRAM (máy không có nvidia-smi → thread tự thoát, label ẩn)
        self.vram_monitor = VramMonitor(interval=5.0)
        self.vram_monitor.sig_vram.connect(self._on_vram)
        self.vram_monitor.start()

        # Phát hiện engine chết giữa chừng (poll tiến trình mỗi 3 giây)
        self._crash_timer = QTimer(self)
        self._crash_timer.setInterval(3000)
        self._crash_timer.timeout.connect(self._check_engine_alive)
        self._crash_timer.start()

        # Lịch sử kết quả từ các phiên trước (chỉ hiện thư mục còn tồn tại)
        for d in load_history():
            if Path(d).is_dir():
                self._add_result_row(d, record=False)

        # Tự khởi động engine nếu được bật và đường dẫn hợp lệ
        if (self.settings.get("auto_start_engine")
                and self.engine.find_api_script(
                    self.settings.get("engine_folder") or "")):
            QTimer.singleShot(600, self._start_engine)

    # ==================================================================
    # UI BUILD
    # ==================================================================
    def _build_ui(self):
        tr = self.i18n.tr
        root = QVBoxLayout(self)

        # ---- Top bar ----
        top = QHBoxLayout()
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size:15pt; font-weight:700;")
        self.lbl_note = QLabel()
        self.lbl_note.setStyleSheet("color:#b3541e;")
        self.btn_lang = QPushButton()
        self.btn_lang.setFixedWidth(90)
        self.btn_lang.clicked.connect(self._toggle_lang)
        top.addWidget(self.lbl_title)
        top.addStretch(1)
        top.addWidget(self.btn_lang)
        root.addLayout(top)
        root.addWidget(self.lbl_note)

        # ---- Middle splitter: left column | right settings ----
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        # ================= LEFT =================
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0)

        # --- Voice clone panel ---
        self.grp_voice = QGroupBox()
        vl = QVBoxLayout(self.grp_voice)
        self.lbl_ref = QLabel()
        self.ed_ref = DropLineEdit()
        self.btn_ref_browse = QPushButton()
        self.btn_ref_play = QPushButton()
        self.btn_ref_trim = QPushButton()
        h = QHBoxLayout()
        h.addWidget(self.ed_ref, 1)
        h.addWidget(self.btn_ref_browse)
        h.addWidget(self.btn_ref_play)
        h.addWidget(self.btn_ref_trim)
        vl.addWidget(self.lbl_ref)
        vl.addLayout(h)

        self.lbl_prompt = QLabel()
        self.ed_prompt = QTextEdit()
        self.ed_prompt.setMaximumHeight(64)
        vl.addWidget(self.lbl_prompt)
        vl.addWidget(self.ed_prompt)

        h2 = QHBoxLayout()
        self.lbl_prompt_lang = QLabel()
        self.cmb_prompt_lang = QComboBox()
        for c in PROMPT_LANGS:
            self.cmb_prompt_lang.addItem(c, c)
        h2.addWidget(self.lbl_prompt_lang)
        h2.addWidget(self.cmb_prompt_lang)
        self.btn_transcribe = QPushButton()
        h2.addWidget(self.btn_transcribe)
        h2.addStretch(1)
        vl.addLayout(h2)

        self.lbl_aux = QLabel()
        self.list_aux = QListWidget()
        self.list_aux.setMaximumHeight(64)
        h3 = QHBoxLayout()
        self.btn_aux_add = QPushButton()
        self.btn_aux_del = QPushButton()
        h3.addWidget(self.btn_aux_add)
        h3.addWidget(self.btn_aux_del)
        h3.addStretch(1)
        vl.addWidget(self.lbl_aux)
        vl.addWidget(self.list_aux)
        vl.addLayout(h3)

        # profiles row
        hp = QHBoxLayout()
        self.lbl_profiles = QLabel()
        self.cmb_profiles = QComboBox()
        self.btn_prof_load = QPushButton()
        self.btn_prof_save = QPushButton()
        self.btn_prof_del = QPushButton()
        hp.addWidget(self.lbl_profiles)
        hp.addWidget(self.cmb_profiles, 1)
        hp.addWidget(self.btn_prof_load)
        hp.addWidget(self.btn_prof_save)
        hp.addWidget(self.btn_prof_del)
        vl.addLayout(hp)
        ll.addWidget(self.grp_voice)

        # --- Input ---
        self.grp_input = QGroupBox()
        il = QVBoxLayout(self.grp_input)
        self.ed_text = QTextEdit()
        self.ed_text.setMinimumHeight(70)
        il.addWidget(self.ed_text)
        hi = QHBoxLayout()
        self.lbl_text_lang = QLabel()
        self.cmb_text_lang = QComboBox()
        for c in TEXT_LANGS:
            self.cmb_text_lang.addItem(c, c)
        hi.addWidget(self.lbl_text_lang)
        hi.addWidget(self.cmb_text_lang)
        hi.addStretch(1)
        self.btn_preview = QPushButton()
        hi.addWidget(self.btn_preview)
        self.btn_generate = QPushButton()
        self.btn_generate.setObjectName("primary")
        hi.addWidget(self.btn_generate)
        il.addLayout(hi)
        hi2 = QHBoxLayout()
        self.btn_add_queue = QPushButton()
        self.btn_import_txt = QPushButton()
        self.btn_import_dir = QPushButton()
        hi2.addWidget(self.btn_add_queue)
        hi2.addWidget(self.btn_import_txt)
        hi2.addWidget(self.btn_import_dir)
        hi2.addStretch(1)
        il.addLayout(hi2)
        ll.addWidget(self.grp_input)

        # --- Queue ---
        self.grp_queue = QGroupBox()
        ql = QVBoxLayout(self.grp_queue)
        self.tbl_queue = DropTableWidget(0, 4)
        self.tbl_queue.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_queue.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        ql.addWidget(self.tbl_queue, 1)
        hq = QHBoxLayout()
        self.btn_q_up = QPushButton("⬆")
        self.btn_q_up.setFixedWidth(36)
        self.btn_q_down = QPushButton("⬇")
        self.btn_q_down.setFixedWidth(36)
        self.btn_q_edit = QPushButton()
        self.btn_q_remove = QPushButton()
        self.btn_q_clear = QPushButton()
        hq.addWidget(self.btn_q_up)
        hq.addWidget(self.btn_q_down)
        hq.addWidget(self.btn_q_edit)
        hq.addWidget(self.btn_q_remove)
        hq.addWidget(self.btn_q_clear)
        hq.addStretch(1)
        self.btn_retry = QPushButton()
        self.btn_generate_all = QPushButton()
        self.btn_generate_all.setObjectName("primary")
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setEnabled(False)
        hq.addWidget(self.btn_retry)
        hq.addWidget(self.btn_generate_all)
        hq.addWidget(self.btn_cancel)
        ql.addLayout(hq)
        ll.addWidget(self.grp_queue, 1)

        split.addWidget(left)

        # ================= RIGHT: Settings =================
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0)

        # --- Engine ---
        self.grp_engine = QGroupBox()
        ef = QFormLayout(self.grp_engine)
        self.ed_engine = DropLineEdit()
        self.btn_engine_browse = QPushButton()
        he = QHBoxLayout()
        he.addWidget(self.ed_engine, 1)
        he.addWidget(self.btn_engine_browse)
        self.lbl_engine_folder = QLabel()
        ef.addRow(self.lbl_engine_folder, he)
        self.ed_engine_python = QLineEdit()
        self.lbl_engine_python = QLabel()
        ef.addRow(self.lbl_engine_python, self.ed_engine_python)
        self.ed_host = QLineEdit()
        self.sp_port = QSpinBox()
        self.sp_port.setRange(1024, 65535)
        hh = QHBoxLayout()
        self.lbl_host = QLabel()
        self.lbl_port = QLabel()
        hh.addWidget(self.ed_host, 1)
        hh.addWidget(self.lbl_port)
        hh.addWidget(self.sp_port)
        ef.addRow(self.lbl_host, hh)
        self.chk_autostart = QCheckBox()
        ef.addRow("", self.chk_autostart)
        hs = QHBoxLayout()
        self.btn_engine_start = QPushButton()
        self.btn_engine_start.setObjectName("primary")
        self.btn_engine_stop = QPushButton()
        self.btn_engine_stop.setEnabled(False)
        hs.addWidget(self.btn_engine_start)
        hs.addWidget(self.btn_engine_stop)
        hs.addStretch(1)
        ef.addRow("", hs)
        rl.addWidget(self.grp_engine)

        # --- Model ---
        self.grp_model = QGroupBox()
        mf = QFormLayout(self.grp_model)
        self.cmb_variant = QComboBox()
        self.cmb_variant.addItems(["v2Pro", "v2ProPlus"])
        self.lbl_variant = QLabel()
        mf.addRow(self.lbl_variant, self.cmb_variant)
        self.ed_gpt = QLineEdit()
        self.btn_gpt_browse = QPushButton()
        hg = QHBoxLayout()
        hg.addWidget(self.ed_gpt, 1)
        hg.addWidget(self.btn_gpt_browse)
        self.lbl_gpt = QLabel()
        mf.addRow(self.lbl_gpt, hg)
        self.ed_sovits = QLineEdit()
        self.btn_sovits_browse = QPushButton()
        hv = QHBoxLayout()
        hv.addWidget(self.ed_sovits, 1)
        hv.addWidget(self.btn_sovits_browse)
        self.lbl_sovits = QLabel()
        mf.addRow(self.lbl_sovits, hv)
        self.lbl_model_hint = QLabel()
        self.lbl_model_hint.setStyleSheet("color:#667; font-weight:400;")
        self.lbl_model_hint.setWordWrap(True)
        mf.addRow(self.lbl_model_hint)
        self.btn_apply_model = QPushButton()
        mf.addRow("", self.btn_apply_model)
        rl.addWidget(self.grp_model)

        # --- Synthesis ---
        self.grp_synth = QGroupBox()
        sf = QFormLayout(self.grp_synth)
        self.sl_speed = QSlider(Qt.Horizontal)
        self.sl_speed.setRange(50, 200)   # 0.50–2.00
        self.lbl_speed_val = QLabel("1.00×")
        hsp = QHBoxLayout()
        hsp.addWidget(self.sl_speed, 1)
        hsp.addWidget(self.lbl_speed_val)
        self.lbl_speed = QLabel()
        sf.addRow(self.lbl_speed, hsp)
        self.cmb_cut = QComboBox()
        for c in CUT_METHODS:
            self.cmb_cut.addItem(c, c)
        self.lbl_cut = QLabel()
        sf.addRow(self.lbl_cut, self.cmb_cut)
        rl.addWidget(self.grp_synth)

        # --- Advanced (gập lại được) ---
        self.grp_adv = QGroupBox()
        self.grp_adv.setCheckable(True)
        self.grp_adv.setChecked(False)
        self.adv_body = QWidget()
        af = QFormLayout(self.adv_body)
        self.sp_topk = QSpinBox(); self.sp_topk.setRange(1, 100)
        self.sp_topp = QDoubleSpinBox(); self.sp_topp.setRange(0.01, 1.0); self.sp_topp.setSingleStep(0.05)
        self.sp_temp = QDoubleSpinBox(); self.sp_temp.setRange(0.01, 2.0); self.sp_temp.setSingleStep(0.05)
        self.sp_rep = QDoubleSpinBox(); self.sp_rep.setRange(0.5, 3.0); self.sp_rep.setSingleStep(0.05)
        self.sp_frag = QDoubleSpinBox(); self.sp_frag.setRange(0.01, 2.0); self.sp_frag.setSingleStep(0.05)
        self.sp_batch = QSpinBox(); self.sp_batch.setRange(1, 32)
        af.addRow("top_k", self.sp_topk)
        af.addRow("top_p", self.sp_topp)
        af.addRow("temperature", self.sp_temp)
        af.addRow("repetition_penalty", self.sp_rep)
        af.addRow("fragment_interval", self.sp_frag)
        af.addRow("batch_size", self.sp_batch)
        hseed = QHBoxLayout()
        self.chk_seed_random = QCheckBox()
        self.sp_seed = QSpinBox(); self.sp_seed.setRange(0, 2**31 - 1)
        hseed.addWidget(self.chk_seed_random)
        hseed.addWidget(self.sp_seed, 1)
        self.lbl_seed = QLabel()
        af.addRow(self.lbl_seed, hseed)
        gl = QVBoxLayout(self.grp_adv)
        gl.addWidget(self.adv_body)
        self.adv_body.setVisible(False)
        self.grp_adv.toggled.connect(self.adv_body.setVisible)
        rl.addWidget(self.grp_adv)

        # --- Output ---
        self.grp_output = QGroupBox()
        of = QFormLayout(self.grp_output)
        self.chk_mp3 = QCheckBox()
        self.lbl_format = QLabel()
        of.addRow(self.lbl_format, self.chk_mp3)
        self.chk_srt = QCheckBox()
        of.addRow("", self.chk_srt)
        self.chk_norm = QCheckBox()
        of.addRow("", self.chk_norm)
        self.chk_audiobook = QCheckBox()
        of.addRow("", self.chk_audiobook)
        self.sp_gap = QDoubleSpinBox()
        self.sp_gap.setRange(0.0, 5.0)
        self.sp_gap.setSingleStep(0.1)
        self.sp_gap.setDecimals(1)
        self.sp_gap.setSuffix(" s")
        self.sp_gap.setMaximumWidth(110)
        self.lbl_gap = QLabel()
        of.addRow(self.lbl_gap, self.sp_gap)
        self.ed_outbase = QLineEdit()
        self.btn_out_browse = QPushButton()
        self.btn_out_open = QPushButton()
        ho = QHBoxLayout()
        ho.addWidget(self.ed_outbase, 1)
        ho.addWidget(self.btn_out_browse)
        ho.addWidget(self.btn_out_open)
        self.lbl_outbase = QLabel()
        of.addRow(self.lbl_outbase, ho)
        rl.addWidget(self.grp_output)
        rl.addStretch(1)

        right_scroll.setWidget(right)
        split.addWidget(right_scroll)
        split.setSizes([760, 560])

        # ================= BOTTOM =================
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 4, 0, 0)

        hb = QHBoxLayout()
        self.lamp = QLabel("●")
        self.lamp.setStyleSheet("color:#999; font-size:14pt;")
        self.lbl_engine_state = QLabel()
        hb.addWidget(self.lamp)
        hb.addWidget(self.lbl_engine_state)
        hb.addSpacing(24)
        self.lbl_prog_item = QLabel()
        self.pb_item = QProgressBar()
        self.pb_item.setMaximumWidth(220)
        self.lbl_prog_total = QLabel()
        self.pb_total = QProgressBar()
        self.pb_total.setMaximumWidth(220)
        hb.addWidget(self.lbl_prog_item)
        hb.addWidget(self.pb_item)
        hb.addWidget(self.lbl_prog_total)
        hb.addWidget(self.pb_total)
        self.lbl_eta = QLabel("")
        self.lbl_eta.setStyleSheet("color:#556; font-weight:600;")
        hb.addWidget(self.lbl_eta)
        hb.addStretch(1)
        self.lbl_vram = QLabel("")
        self.lbl_vram.setToolTip("GPU VRAM (nvidia-smi)")
        hb.addWidget(self.lbl_vram)
        bl.addLayout(hb)

        self.tabs = QTabWidget()
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(5000)
        self.tbl_results = QTableWidget(0, 3)
        self.tbl_results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_results.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabs.addTab(self.txt_log, "")
        self.tabs.addTab(self.tbl_results, "")
        self.tabs.setMinimumHeight(110)
        bl.addWidget(self.tabs)

        hplay = QHBoxLayout()
        self.lbl_player = QLabel()
        self.player = AudioPlayer()
        hplay.addWidget(self.lbl_player)
        hplay.addWidget(self.player, 1)
        bl.addLayout(hplay)

        root.addWidget(bottom)

        # ---- Connections ----
        self.btn_ref_browse.clicked.connect(self._browse_ref)
        self.btn_ref_play.clicked.connect(lambda: self.player.play(self.ed_ref.text()))
        self.btn_ref_trim.clicked.connect(self._open_trim_dialog)
        self.btn_transcribe.clicked.connect(self._transcribe_ref)
        self.btn_preview.clicked.connect(self._preview_one)
        self.btn_q_up.clicked.connect(lambda: self._move_queue_item(-1))
        self.btn_q_down.clicked.connect(lambda: self._move_queue_item(1))
        self.btn_q_edit.clicked.connect(self._edit_queue_item)
        self.btn_retry.clicked.connect(self._retry_errors)
        self.tbl_queue.filesDropped.connect(self._add_txt_files)
        self.chk_audiobook.toggled.connect(self.sp_gap.setEnabled)
        self.btn_aux_add.clicked.connect(self._add_aux)
        self.btn_aux_del.clicked.connect(self._del_aux)
        self.btn_prof_save.clicked.connect(self._save_profile)
        self.btn_prof_load.clicked.connect(self._load_profile)
        self.btn_prof_del.clicked.connect(self._delete_profile)
        self.btn_add_queue.clicked.connect(self._add_manual_to_queue)
        self.btn_import_txt.clicked.connect(self._import_txt)
        self.btn_import_dir.clicked.connect(self._import_dir)
        self.btn_q_remove.clicked.connect(self._remove_queue_item)
        self.btn_q_clear.clicked.connect(self._clear_queue)
        self.btn_generate.clicked.connect(self._generate_manual)
        self.btn_generate_all.clicked.connect(self._generate_all)
        self.btn_cancel.clicked.connect(self._cancel_batch)
        self.btn_engine_browse.clicked.connect(self._browse_engine)
        self.btn_engine_start.clicked.connect(self._start_engine)
        self.btn_engine_stop.clicked.connect(self._stop_engine)
        self.btn_gpt_browse.clicked.connect(lambda: self._browse_into(self.ed_gpt, "GPT (*.ckpt);;All (*.*)"))
        self.btn_sovits_browse.clicked.connect(lambda: self._browse_into(self.ed_sovits, "SoVITS (*.pth);;All (*.*)"))
        self.btn_apply_model.clicked.connect(self._apply_model)
        self.sl_speed.valueChanged.connect(
            lambda v: self.lbl_speed_val.setText(f"{v / 100:.2f}×"))
        self.btn_out_browse.clicked.connect(self._browse_outbase)
        self.btn_out_open.clicked.connect(self._open_outbase)
        self.chk_seed_random.toggled.connect(
            lambda on: self.sp_seed.setEnabled(not on))
        self.tbl_results.cellDoubleClicked.connect(self._play_result_row)

    # ==================================================================
    # i18n
    # ==================================================================
    def retranslate(self):
        tr = self.i18n.tr
        self.setWindowTitle(tr("app_title"))
        self.lbl_title.setText(tr("app_title"))
        self.lbl_note.setText(tr("vi_not_supported_note"))
        self.btn_lang.setText(self.i18n.next_lang_label())

        self.grp_voice.setTitle(tr("grp_voice"))
        self.lbl_ref.setText(tr("ref_audio"))
        self.ed_ref.setPlaceholderText(tr("ref_audio_placeholder"))
        self.btn_ref_browse.setText(tr("browse"))
        self.btn_ref_play.setText(tr("btn_play_ref"))
        self.btn_ref_trim.setText(tr("btn_trim"))
        self.btn_ref_trim.setToolTip(tr("trim_title"))
        self.lbl_prompt.setText(tr("prompt_text"))
        self.ed_prompt.setPlaceholderText(tr("prompt_text_placeholder"))
        self.lbl_prompt_lang.setText(tr("prompt_lang"))
        self.btn_transcribe.setText(tr("btn_transcribe"))
        self.btn_transcribe.setToolTip(tr("transcribe_tooltip"))
        self.lbl_aux.setText(tr("aux_refs"))
        self.btn_aux_add.setText(tr("btn_add_aux"))
        self.btn_aux_del.setText(tr("btn_remove_aux"))
        self.lbl_profiles.setText(tr("grp_profiles"))
        self.btn_prof_save.setText(tr("btn_save_profile"))
        self.btn_prof_load.setText(tr("btn_load_profile"))
        self.btn_prof_del.setText(tr("btn_delete_profile"))

        self.grp_input.setTitle(tr("grp_input"))
        self.ed_text.setPlaceholderText(tr("input_placeholder"))
        self.lbl_text_lang.setText(tr("text_lang"))
        self.cmb_text_lang.setToolTip(tr("text_lang_tooltip"))
        self.lbl_text_lang.setToolTip(tr("text_lang_tooltip"))
        for i, c in enumerate(TEXT_LANGS):
            self.cmb_text_lang.setItemText(i, self.i18n.lang_label(c))
        self.btn_add_queue.setText(tr("btn_add_to_queue"))
        self.btn_import_txt.setText(tr("btn_import_txt"))
        self.btn_import_dir.setText(tr("btn_import_folder"))
        self.btn_generate.setText(tr("btn_generate"))
        self.btn_preview.setText(tr("btn_preview"))
        self.btn_preview.setToolTip(tr("preview_tooltip"))

        self.grp_queue.setTitle(tr("grp_queue"))
        self.tbl_queue.setHorizontalHeaderLabels([
            tr("queue_col_name"), tr("queue_col_lang"),
            tr("queue_col_chars"), tr("queue_col_status")])
        self.tbl_queue.setToolTip(tr("queue_drop_hint"))
        self.btn_q_up.setToolTip(tr("tip_move_up"))
        self.btn_q_down.setToolTip(tr("tip_move_down"))
        self.btn_q_edit.setText(tr("btn_edit_item"))
        self.btn_q_remove.setText(tr("btn_remove_item"))
        self.btn_q_clear.setText(tr("btn_clear_queue"))
        self.btn_retry.setText(tr("btn_retry_errors"))
        self.btn_generate_all.setText(tr("btn_generate_all"))
        self.btn_cancel.setText(tr("btn_cancel_batch"))

        self.grp_engine.setTitle(tr("grp_engine"))
        self.lbl_engine_folder.setText(tr("engine_folder"))
        self.ed_engine.setToolTip(tr("engine_folder_tooltip"))
        self.lbl_engine_python.setText(tr("engine_python_path"))
        self.btn_engine_browse.setText(tr("browse"))
        self.lbl_host.setText(tr("host"))
        self.lbl_port.setText(tr("port"))
        self.chk_autostart.setText(tr("auto_start_engine"))
        self.btn_engine_start.setText(tr("btn_start_engine"))
        self.btn_engine_stop.setText(tr("btn_stop_engine"))

        self.grp_model.setTitle(tr("grp_model"))
        self.lbl_variant.setText(tr("model_variant"))
        self.lbl_gpt.setText(tr("gpt_weights"))
        self.lbl_sovits.setText(tr("sovits_weights"))
        self.btn_gpt_browse.setText(tr("browse"))
        self.btn_sovits_browse.setText(tr("browse"))
        self.btn_apply_model.setText(tr("btn_apply_model"))
        self.lbl_model_hint.setText(tr("model_auto_hint"))

        self.grp_synth.setTitle(tr("grp_synth"))
        self.lbl_speed.setText(tr("speed"))
        self.lbl_cut.setText(tr("cut_method"))
        for i, c in enumerate(CUT_METHODS):
            self.cmb_cut.setItemText(i, tr(c))
        self.grp_adv.setTitle(tr("grp_advanced"))
        self.lbl_seed.setText(tr("seed"))
        self.chk_seed_random.setText(tr("seed_random"))

        self.grp_output.setTitle(tr("grp_output"))
        self.lbl_format.setText(tr("out_format"))
        self.chk_mp3.setText(tr("out_mp3_too"))
        self.chk_srt.setText(tr("out_srt"))
        self.chk_srt.setToolTip(tr("out_srt_tooltip"))
        self.chk_norm.setText(tr("out_norm"))
        self.chk_norm.setToolTip(tr("out_norm_tooltip"))
        self.chk_audiobook.setText(tr("out_audiobook"))
        self.chk_audiobook.setToolTip(tr("out_audiobook_tooltip"))
        self.lbl_gap.setText(tr("audiobook_gap"))
        self.lbl_outbase.setText(tr("output_base"))
        self.btn_out_browse.setText(tr("browse"))
        self.btn_out_open.setText(tr("btn_open_output"))

        self.lbl_prog_item.setText(tr("progress_item"))
        self.lbl_prog_total.setText(tr("progress_total"))
        self.tabs.setTabText(0, tr("grp_log"))
        self.tabs.setTabText(1, tr("grp_results"))
        self.tbl_results.setHorizontalHeaderLabels([
            tr("results_col_folder"), tr("results_col_source"),
            tr("results_col_open")])
        self.lbl_player.setText(tr("player_output"))
        self._update_engine_lamp()
        self._refresh_queue_table()

    def _toggle_lang(self):
        self.i18n.toggle()
        self.settings.set("ui_lang", self.i18n.lang)
        self.settings.save()
        self.retranslate()

    # ==================================================================
    # Settings load/save
    # ==================================================================
    def _load_from_settings(self):
        s = self.settings
        self.ed_ref.setText(s.get("ref_audio_path"))
        self.ed_prompt.setPlainText(s.get("prompt_text"))
        self._set_combo_data(self.cmb_prompt_lang, s.get("prompt_lang"))
        for p in s.get("aux_ref_audio_paths", []):
            self.list_aux.addItem(p)
        self._set_combo_data(self.cmb_text_lang, s.get("text_lang"))
        self.ed_engine.setText(s.get("engine_folder"))
        self.ed_engine_python.setText(s.get("engine_python"))
        self.ed_host.setText(s.get("host"))
        self.sp_port.setValue(int(s.get("port")))
        self.chk_autostart.setChecked(bool(s.get("auto_start_engine")))
        self.cmb_variant.setCurrentText(s.get("model_variant"))
        self.ed_gpt.setText(s.get("gpt_weights"))
        self.ed_sovits.setText(s.get("sovits_weights"))
        self.sl_speed.setValue(int(float(s.get("speed_factor")) * 100))
        self.lbl_speed_val.setText(f"{float(s.get('speed_factor')):.2f}×")
        self._set_combo_data(self.cmb_cut, s.get("text_split_method"))
        self.sp_topk.setValue(int(s.get("top_k")))
        self.sp_topp.setValue(float(s.get("top_p")))
        self.sp_temp.setValue(float(s.get("temperature")))
        self.sp_rep.setValue(float(s.get("repetition_penalty")))
        self.sp_frag.setValue(float(s.get("fragment_interval")))
        self.sp_batch.setValue(int(s.get("batch_size")))
        seed = int(s.get("seed"))
        self.chk_seed_random.setChecked(seed < 0)
        self.sp_seed.setValue(max(seed, 0))
        self.sp_seed.setEnabled(seed >= 0)
        self.chk_mp3.setChecked(bool(s.get("export_mp3")))
        self.chk_srt.setChecked(bool(s.get("export_srt")))
        self.chk_norm.setChecked(bool(s.get("normalize_loudness")))
        self.chk_audiobook.setChecked(bool(s.get("audiobook_merge")))
        self.sp_gap.setValue(float(s.get("audiobook_gap")))
        self.sp_gap.setEnabled(self.chk_audiobook.isChecked())
        self.ed_outbase.setText(s.get("output_base"))
        self._refresh_profiles_combo()

    @staticmethod
    def _set_combo_data(cmb: QComboBox, value):
        idx = cmb.findData(value)
        if idx < 0:
            idx = cmb.findText(str(value))
        if idx >= 0:
            cmb.setCurrentIndex(idx)

    def _save_to_settings(self):
        s = self.settings
        s.update(
            ref_audio_path=self.ed_ref.text().strip(),
            prompt_text=self.ed_prompt.toPlainText().strip(),
            prompt_lang=self.cmb_prompt_lang.currentData(),
            aux_ref_audio_paths=[self.list_aux.item(i).text()
                                 for i in range(self.list_aux.count())],
            text_lang=self.cmb_text_lang.currentData(),
            engine_folder=self.ed_engine.text().strip(),
            engine_python=self.ed_engine_python.text().strip(),
            host=self.ed_host.text().strip() or "127.0.0.1",
            port=self.sp_port.value(),
            auto_start_engine=self.chk_autostart.isChecked(),
            model_variant=self.cmb_variant.currentText(),
            gpt_weights=self.ed_gpt.text().strip(),
            sovits_weights=self.ed_sovits.text().strip(),
            speed_factor=self.sl_speed.value() / 100.0,
            text_split_method=self.cmb_cut.currentData(),
            top_k=self.sp_topk.value(),
            top_p=self.sp_topp.value(),
            temperature=self.sp_temp.value(),
            repetition_penalty=self.sp_rep.value(),
            fragment_interval=self.sp_frag.value(),
            batch_size=self.sp_batch.value(),
            seed=-1 if self.chk_seed_random.isChecked() else self.sp_seed.value(),
            export_mp3=self.chk_mp3.isChecked(),
            export_srt=self.chk_srt.isChecked(),
            normalize_loudness=self.chk_norm.isChecked(),
            audiobook_merge=self.chk_audiobook.isChecked(),
            audiobook_gap=self.sp_gap.value(),
            output_base=self.ed_outbase.text().strip(),
            ui_lang=self.i18n.lang,
        )
        s.save()

    def closeEvent(self, e):
        self._save_to_settings()
        if hasattr(self, "vram_monitor"):
            self.vram_monitor.stop()
            self.vram_monitor.wait(2000)
        if self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.cancel()
            self.batch_worker.wait(3000)
        if self.engine_worker and self.engine_worker.isRunning():
            self.engine_worker.abort()
            self.engine_worker.wait(3000)
        self.engine.stop()
        super().closeEvent(e)

    # ==================================================================
    # Voice panel
    # ==================================================================
    def _browse_ref(self):
        p, _ = QFileDialog.getOpenFileName(self, self.i18n.tr("ref_audio"),
                                           "", AUDIO_FILTER)
        if p:
            self.ed_ref.setText(p)

    def _add_aux(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.i18n.tr("aux_refs"),
                                                "", AUDIO_FILTER)
        for p in paths:
            self.list_aux.addItem(p)

    def _del_aux(self):
        for it in self.list_aux.selectedItems():
            self.list_aux.takeItem(self.list_aux.row(it))

    def _refresh_profiles_combo(self):
        self.cmb_profiles.clear()
        self.cmb_profiles.addItems(self.profiles.names())

    def _save_profile(self):
        name, ok = QInputDialog.getText(self, self.i18n.tr("grp_profiles"),
                                        self.i18n.tr("profile_name_prompt"))
        if not ok or not name.strip():
            return
        # Copy audio vào kho app → profile sống sót kể cả khi file gốc bị
        # di chuyển/xóa
        ref_copy, aux_copies = store_voice_files(
            name.strip(),
            self.ed_ref.text().strip(),
            [self.list_aux.item(i).text() for i in range(self.list_aux.count())],
        )
        prof = VoiceProfile(
            name=name.strip(),
            ref_audio_path=ref_copy,
            prompt_text=self.ed_prompt.toPlainText().strip(),
            prompt_lang=self.cmb_prompt_lang.currentData(),
            aux_ref_audio_paths=aux_copies,
        )
        self.profiles.upsert(prof)
        self._refresh_profiles_combo()
        self.cmb_profiles.setCurrentText(prof.name)
        self.append_log(f"✓ {self.i18n.tr('profile_saved')} [{prof.name}]")

    def _load_profile(self):
        prof = self.profiles.get(self.cmb_profiles.currentText())
        if not prof:
            return
        self.ed_ref.setText(prof.ref_audio_path)
        self.ed_prompt.setPlainText(prof.prompt_text)
        self._set_combo_data(self.cmb_prompt_lang, prof.prompt_lang)
        self.list_aux.clear()
        for p in prof.aux_ref_audio_paths:
            self.list_aux.addItem(p)

    def _delete_profile(self):
        name = self.cmb_profiles.currentText()
        if name:
            self.profiles.delete(name)
            delete_voice_files(name)
            self._refresh_profiles_combo()

    # ==================================================================
    # Input / queue
    # ==================================================================
    def _current_text_lang(self) -> str:
        return self.cmb_text_lang.currentData() or "auto"

    def _add_manual_to_queue(self):
        text = self.ed_text.toPlainText().strip()
        if not text:
            self._warn(self.i18n.tr("msg_need_text"))
            return
        self.queue.append(QueueItem(name="manual", text=text,
                                    text_lang=self._current_text_lang()))
        self._refresh_queue_table()
        self.ed_text.clear()

    def _import_txt(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.i18n.tr("btn_import_txt"), "", "Text (*.txt);;All (*.*)")
        self._add_txt_files(paths)

    def _import_dir(self):
        d = QFileDialog.getExistingDirectory(self, self.i18n.tr("btn_import_folder"))
        if d:
            self._add_txt_files(sorted(str(p) for p in Path(d).glob("*.txt")))

    def _add_txt_files(self, paths):
        lang = self._current_text_lang()
        for p in paths:
            try:
                text = Path(p).read_text(encoding="utf-8", errors="replace").strip()
            except Exception as e:
                self.append_log(f"✗ read {p}: {e}")
                continue
            name = Path(p).stem
            if not text:
                self.append_log(f"{self.i18n.tr('queue_empty_skip')} {name}")
                continue
            self.queue.append(QueueItem(name=name, text=text, text_lang=lang))
        self._refresh_queue_table()

    def _refresh_queue_table(self):
        tr = self.i18n.tr
        status_map = {"pending": tr("status_pending"), "running": tr("status_running"),
                      "done": tr("status_done"), "error": tr("status_error"),
                      "skipped": tr("status_skipped")}
        t = self.tbl_queue
        t.setRowCount(len(self.queue))
        for r, item in enumerate(self.queue):
            t.setItem(r, 0, QTableWidgetItem(item.name))
            cmb = QComboBox()
            for c in TEXT_LANGS:
                cmb.addItem(self.i18n.lang_label(c), c)
            self._set_combo_data(cmb, item.text_lang)
            cmb.currentIndexChanged.connect(
                lambda _i, row=r, box=cmb: self._on_item_lang_changed(row, box))
            t.setCellWidget(r, 1, cmb)
            t.setItem(r, 2, QTableWidgetItem(str(item.chars)))
            st = QTableWidgetItem(status_map.get(item.status, item.status))
            if item.status == "error":
                st.setForeground(QColor("#c0392b"))
                st.setToolTip(item.error)
            elif item.status == "done":
                st.setForeground(QColor("#1e8449"))
            t.setItem(r, 3, st)

    def _on_item_lang_changed(self, row: int, box: QComboBox):
        if 0 <= row < len(self.queue):
            self.queue[row].text_lang = box.currentData()

    def _remove_queue_item(self):
        rows = sorted({i.row() for i in self.tbl_queue.selectedIndexes()},
                      reverse=True)
        for r in rows:
            if 0 <= r < len(self.queue):
                del self.queue[r]
        self._refresh_queue_table()

    def _clear_queue(self):
        if not self.queue:
            return
        if QMessageBox.question(self, self.i18n.tr("grp_queue"),
                                self.i18n.tr("msg_confirm_clear")) == QMessageBox.Yes:
            self.queue.clear()
            self._refresh_queue_table()

    # ==================================================================
    # Generate
    # ==================================================================
    def _validate_before_tts(self) -> bool:
        tr = self.i18n.tr
        if self.engine_state != "ready" or not self.client.is_alive():
            self._warn(tr("engine_not_ready_msg"))
            return False
        ref = self.ed_ref.text().strip()
        if not ref:
            self._warn(tr("msg_need_ref"))
            return False
        if not Path(ref).is_file():
            self._warn(f"{tr('msg_ref_not_found')}\n{ref}")
            return False
        return True

    def _make_cfg(self) -> TtsJobConfig:
        self._save_to_settings()
        s = self.settings
        return TtsJobConfig(
            ref_audio_path=s.get("ref_audio_path"),
            prompt_text=s.get("prompt_text"),
            prompt_lang=s.get("prompt_lang"),
            aux_ref_audio_paths=s.get("aux_ref_audio_paths"),
            speed_factor=s.get("speed_factor"),
            text_split_method=s.get("text_split_method"),
            batch_size=s.get("batch_size"),
            top_k=s.get("top_k"),
            top_p=s.get("top_p"),
            temperature=s.get("temperature"),
            repetition_penalty=s.get("repetition_penalty"),
            fragment_interval=s.get("fragment_interval"),
            seed=s.get("seed"),
            output_base=s.get("output_base"),
            export_mp3=s.get("export_mp3"),
            model_variant=s.get("model_variant"),
            gpt_weights=s.get("gpt_weights"),
            sovits_weights=s.get("sovits_weights"),
            export_srt=s.get("export_srt"),
            normalize_loudness=s.get("normalize_loudness"),
            audiobook_merge=s.get("audiobook_merge"),
            audiobook_gap=s.get("audiobook_gap"),
        )

    def _generate_manual(self):
        text = self.ed_text.toPlainText().strip()
        if not text:
            self._warn(self.i18n.tr("msg_need_text"))
            return
        if not self._validate_before_tts():
            return
        items = [QueueItem(name="manual", text=text,
                           text_lang=self._current_text_lang())]
        self._run_batch(items, standalone=True)

    def _generate_all(self):
        if not self.queue:
            self._warn(self.i18n.tr("msg_queue_empty"))
            return
        if not self._validate_before_tts():
            return
        for it in self.queue:
            if it.status in ("done", "error", "skipped"):
                it.status = "pending"
        self._run_batch(self.queue, standalone=False)

    def _run_batch(self, items, standalone: bool):
        cfg = self._make_cfg()
        self.batch_worker = BatchWorker(self.client, items, cfg)
        w = self.batch_worker
        self._batch_standalone = standalone
        w.sig_item_started.connect(self._on_item_started)
        w.sig_item_finished.connect(self._on_item_finished)
        w.sig_item_progress.connect(self.pb_item.setValue)
        w.sig_total_progress.connect(self._on_total_progress)
        w.sig_log.connect(self.append_log)
        w.sig_audiobook_done.connect(self._on_audiobook_done)
        w.sig_batch_finished.connect(self._on_batch_finished)
        self.pb_total.setValue(0)
        self.pb_total.setMaximum(
            max(1, len([it for it in items if it.status == "pending"])))
        self.pb_item.setValue(0)
        self._eta_chars_done = 0
        self._eta_secs_done = 0.0
        self.lbl_eta.clear()
        self._set_busy(True)
        w.start()

    def _set_busy(self, busy: bool):
        self.btn_generate.setEnabled(not busy)
        self.btn_generate_all.setEnabled(not busy)
        self.btn_retry.setEnabled(not busy)
        self.btn_preview.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.btn_apply_model.setEnabled(not busy)

    @Slot(int)
    def _on_item_started(self, idx: int):
        self._item_t0 = time.time()
        if not self._batch_standalone and 0 <= idx < len(self.queue):
            self.queue[idx].status = "running"
            self._refresh_queue_table()

    @Slot(int, str, str)
    def _on_item_finished(self, idx: int, status: str, payload: str):
        self._update_eta(idx, status)
        if not self._batch_standalone:
            self._refresh_queue_table()
        if status == "done" and payload:
            self._add_result_row(payload)
            # tự nạp kết quả mới nhất vào player
            out_wav = Path(payload) / "output.wav"
            if out_wav.is_file():
                self.player.load(str(out_wav))
        elif status == "error":
            key = classify_error(payload)
            if key:
                self.append_log(f"💡 {self.i18n.tr(key)}")

    @Slot(int, int)
    def _on_total_progress(self, done: int, total: int):
        self.pb_total.setMaximum(total)
        self.pb_total.setValue(done)

    @Slot(int, int, bool)
    def _on_batch_finished(self, ok: int, fail: int, cancelled: bool):
        self._set_busy(False)
        self.lbl_eta.clear()
        tr = self.i18n.tr
        if cancelled:
            self.append_log(tr("msg_batch_cancelled"))
        total = self.pb_total.maximum()
        summary = tr("msg_batch_done").format(ok=ok, fail=fail, total=total)
        self.append_log(summary)
        # Thông báo Windows — hữu ích khi chạy batch dài rồi làm việc khác
        if not cancelled and hasattr(self, "tray"):
            self.tray.showMessage(tr("notif_batch_title"), summary,
                                  QSystemTrayIcon.Information, 8000)
        self.batch_worker = None

    def _update_eta(self, idx: int, status: str):
        """Ước tính thời gian còn lại theo tốc độ trung bình (giây/ký tự)."""
        if not self.batch_worker or not self._item_t0:
            return
        items = self.batch_worker.items
        if status == "done" and 0 <= idx < len(items):
            self._eta_secs_done += time.time() - self._item_t0
            self._eta_chars_done += items[idx].chars
        if self._eta_chars_done <= 0:
            return
        remaining_chars = sum(it.chars for it in items if it.status == "pending")
        if remaining_chars <= 0:
            self.lbl_eta.clear()
            return
        eta = self._eta_secs_done / self._eta_chars_done * remaining_chars
        m, s = divmod(int(eta), 60)
        h, m = divmod(m, 60)
        txt = f"{h}h{m:02d}m" if h else (f"{m}m{s:02d}s" if m else f"{s}s")
        self.lbl_eta.setText(f"{self.i18n.tr('eta_prefix')} {txt}")

    def _cancel_batch(self):
        if self.batch_worker:
            self.batch_worker.cancel()
            self.btn_cancel.setEnabled(False)

    # ==================================================================
    # Thử 1 câu / chạy lại mục lỗi / chỉnh hàng đợi
    # ==================================================================
    def _preview_one(self):
        tr = self.i18n.tr
        # Nguồn văn bản: mục đang chọn trong queue → ô nhập tay → mục đầu queue
        text, lang = "", "auto"
        rows = sorted({i.row() for i in self.tbl_queue.selectedIndexes()})
        if rows and 0 <= rows[0] < len(self.queue):
            it = self.queue[rows[0]]
            text, lang = it.text, it.text_lang
        elif self.ed_text.toPlainText().strip():
            text, lang = self.ed_text.toPlainText().strip(), self._current_text_lang()
        elif self.queue:
            text, lang = self.queue[0].text, self.queue[0].text_lang
        if not text.strip():
            self._warn(tr("msg_need_text"))
            return
        if not self._validate_before_tts():
            return
        out_path = str(config_dir() / "preview.wav")
        self.btn_preview.setEnabled(False)
        self.append_log(tr("preview_generating"))
        self.preview_worker = PreviewWorker(self.client, self._make_cfg(),
                                            text, lang, out_path)
        self.preview_worker.sig_done.connect(self._on_preview_done)
        self.preview_worker.start()

    @Slot(bool, str)
    def _on_preview_done(self, ok: bool, payload: str):
        self.btn_preview.setEnabled(True)
        if ok:
            self.append_log(self.i18n.tr("preview_done"))
            self.player.play(payload)
        else:
            key = classify_error(payload)
            self._warn(self.i18n.tr(key) if key else payload)
        self.preview_worker = None

    def _retry_errors(self):
        tr = self.i18n.tr
        err_items = [it for it in self.queue if it.status == "error"]
        if not err_items:
            self._warn(tr("msg_no_error_items"))
            return
        if not self._validate_before_tts():
            return
        for it in err_items:
            it.status = "pending"
            it.error = ""
        self._refresh_queue_table()
        self._run_batch(self.queue, standalone=False)

    def _move_queue_item(self, delta: int):
        rows = sorted({i.row() for i in self.tbl_queue.selectedIndexes()})
        if len(rows) != 1:
            return
        r, nr = rows[0], rows[0] + delta
        if 0 <= r < len(self.queue) and 0 <= nr < len(self.queue):
            self.queue[r], self.queue[nr] = self.queue[nr], self.queue[r]
            self._refresh_queue_table()
            self.tbl_queue.selectRow(nr)

    def _edit_queue_item(self):
        rows = sorted({i.row() for i in self.tbl_queue.selectedIndexes()})
        if len(rows) != 1 or not (0 <= rows[0] < len(self.queue)):
            return
        item = self.queue[rows[0]]
        tr = self.i18n.tr
        text, ok = QInputDialog.getMultiLineText(
            self, tr("btn_edit_item"),
            f"{tr('edit_item_title')} {item.name}", item.text)
        if ok:
            item.text = text
            item.status = "pending"
            item.error = ""
            self._refresh_queue_table()
            self.tbl_queue.selectRow(rows[0])

    # ==================================================================
    # Whisper: tự nhận dạng prompt_text
    # ==================================================================
    def _transcribe_ref(self):
        tr = self.i18n.tr
        path = self.ed_ref.text().strip()
        if not path or not Path(path).is_file():
            self._warn(tr("msg_need_ref"))
            return
        self.btn_transcribe.setEnabled(False)
        self.append_log(tr("transcribe_running"))
        self.transcribe_worker = TranscribeWorker(path)
        self.transcribe_worker.sig_done.connect(self._on_transcribed)
        self.transcribe_worker.start()

    @Slot(bool, str, str)
    def _on_transcribed(self, ok: bool, text: str, info: str):
        tr = self.i18n.tr
        self.btn_transcribe.setEnabled(True)
        self.transcribe_worker = None
        if not ok:
            self._warn(tr("transcribe_missing") if info == "missing"
                       else f"{tr('transcribe_failed')}\n{info}")
            return
        self.ed_prompt.setPlainText(text)
        lang = WHISPER_TO_PROMPT_LANG.get(info)
        if lang:
            self._set_combo_data(self.cmb_prompt_lang, lang)
        self.append_log(f"{tr('transcribe_done')} [{info}]")

    @Slot(str)
    def _on_audiobook_done(self, out_dir: str):
        self.append_log(f"{self.i18n.tr('log_audiobook_done')} {out_dir}")
        self._add_result_row(out_dir)
        merged = Path(out_dir) / "merged.wav"
        if merged.is_file():
            self.player.load(str(merged))

    def _open_trim_dialog(self):
        tr = self.i18n.tr
        path = self.ed_ref.text().strip()
        if not path or not Path(path).is_file():
            self._warn(tr("msg_need_ref"))
            return
        try:
            dlg = TrimDialog(path, self.i18n, self)
        except Exception as e:
            self._warn(f"{tr('trim_load_error')}\n{e}")
            return
        if dlg.exec() and dlg.saved_path:
            self.ed_ref.setText(dlg.saved_path)
            self.append_log(f"✂ {Path(dlg.saved_path).name}")

    # ==================================================================
    # Results
    # ==================================================================
    def _add_result_row(self, out_dir: str, record: bool = True):
        if record:
            append_history(out_dir)
        t = self.tbl_results
        r = t.rowCount()
        t.insertRow(r)
        t.setItem(r, 0, QTableWidgetItem(Path(out_dir).name))
        t.item(r, 0).setToolTip(out_dir)
        src = "?"
        try:
            src = Path(out_dir).name.split("_", 2)[-1]
        except Exception:
            pass
        t.setItem(r, 1, QTableWidgetItem(src))
        btn = QPushButton(self.i18n.tr("btn_open_folder"))
        btn.clicked.connect(lambda _=False, d=out_dir: self._open_dir(d))
        t.setCellWidget(r, 2, btn)

    def _play_result_row(self, row: int, _col: int):
        it = self.tbl_results.item(row, 0)
        if it:
            for name in ("output.wav", "merged.wav"):
                wav = Path(it.toolTip()) / name
                if wav.is_file():
                    self.player.play(str(wav))
                    break

    @staticmethod
    def _open_dir(path: str):
        if path and Path(path).is_dir():
            os.startfile(path)  # noqa: S606 — Windows only

    # ==================================================================
    # Engine
    # ==================================================================
    def _browse_engine(self):
        d = QFileDialog.getExistingDirectory(self, self.i18n.tr("engine_folder"))
        if d:
            self.ed_engine.setText(d)

    def _browse_into(self, edit: QLineEdit, filt: str):
        p, _ = QFileDialog.getOpenFileName(self, "", "", filt)
        if p:
            edit.setText(p)

    def _browse_outbase(self):
        d = QFileDialog.getExistingDirectory(self, self.i18n.tr("output_base"))
        if d:
            self.ed_outbase.setText(d)

    def _open_outbase(self):
        d = self.ed_outbase.text().strip()
        if d:
            Path(d).mkdir(parents=True, exist_ok=True)
            os.startfile(d)

    def _start_engine(self):
        tr = self.i18n.tr
        folder = self.ed_engine.text().strip()
        if not folder or not self.engine.find_api_script(folder):
            self._warn(tr("engine_folder_invalid"))
            return
        self._save_to_settings()
        self.client.host = self.settings.get("host")
        self.client.port = int(self.settings.get("port"))
        if not self.engine.has_nvidia_gpu():
            self.append_log(tr("cpu_warning"))
        self.append_log(tr("log_engine_starting"))
        self._set_engine_state("starting")
        self.btn_engine_start.setEnabled(False)
        self.engine_worker = EngineStartWorker(
            self.engine, self.client, folder,
            self.settings.get("host"), int(self.settings.get("port")),
            self.settings.get("engine_python"))
        self.engine_worker.sig_state.connect(self._on_engine_state)
        self.engine_worker.sig_log.connect(self.append_log)
        self.engine_worker.start()

    @Slot(str)
    def _on_engine_state(self, state: str):
        tr = self.i18n.tr
        if state == "starting":
            self._set_engine_state("starting")
        elif state == "ready":
            self._set_engine_state("ready")
            self.btn_engine_stop.setEnabled(True)
            self.append_log(tr("log_engine_ready"))
        elif state.startswith("error"):
            code = state.split(":", 1)[-1]
            self._set_engine_state("error")
            self.btn_engine_start.setEnabled(True)
            msg = {"api_not_found": tr("engine_folder_invalid"),
                   "python_not_found": tr("engine_python_missing")}.get(
                code, tr("engine_start_failed"))
            self._warn(msg)
            self.engine.stop()

    def _stop_engine(self):
        self.engine.stop()
        self._set_engine_state("stopped")
        self.btn_engine_start.setEnabled(True)
        self.btn_engine_stop.setEnabled(False)
        self.append_log(self.i18n.tr("log_engine_stopped"))

    def _set_engine_state(self, state: str):
        self.engine_state = state
        self._update_engine_lamp()

    def _update_engine_lamp(self):
        tr = self.i18n.tr
        colors = {"stopped": "#999", "starting": "#e6a817",
                  "ready": "#27ae60", "error": "#e5534b",
                  "crashed": "#e5534b"}
        labels = {"stopped": tr("engine_state_stopped"),
                  "starting": tr("engine_state_starting"),
                  "ready": tr("engine_state_ready"),
                  "error": tr("engine_state_error"),
                  "crashed": tr("engine_state_crashed")}
        self.lamp.setStyleSheet(
            f"color:{colors.get(self.engine_state, '#999')}; font-size:14pt;")
        self.lbl_engine_state.setText(labels.get(self.engine_state, ""))

    def _check_engine_alive(self):
        """Đèn 'Sẵn sàng' nhưng tiến trình engine đã thoát → báo crash ngay
        thay vì đợi tới lúc gọi TTS thất bại."""
        if self.engine_state == "ready" and not self.engine.is_running():
            self._set_engine_state("crashed")
            self.btn_engine_start.setEnabled(True)
            self.btn_engine_stop.setEnabled(False)
            self.append_log(self.i18n.tr("log_engine_crashed"))
            if hasattr(self, "tray"):
                self.tray.showMessage("Voice Studio",
                                      self.i18n.tr("engine_state_crashed"),
                                      QSystemTrayIcon.Warning, 8000)

    @Slot(int, int)
    def _on_vram(self, used_mb: int, total_mb: int):
        pct = used_mb / total_mb if total_mb else 0
        color = "#c0392b" if pct >= 0.92 else ("#b3541e" if pct >= 0.80 else "#556")
        self.lbl_vram.setText(f"VRAM {used_mb / 1024:.1f} / {total_mb / 1024:.1f} GB")
        self.lbl_vram.setStyleSheet(f"color:{color}; font-weight:600;")

    # ==================================================================
    # Model
    # ==================================================================
    def _apply_model(self):
        tr = self.i18n.tr
        if self.engine_state != "ready":
            self._warn(tr("engine_not_ready_msg"))
            return
        gpt = self.ed_gpt.text().strip()
        sovits = self.ed_sovits.text().strip()
        if not gpt or not sovits:
            # tự dò weights trong pretrained_models theo phiên bản đã chọn
            g, sv = self.engine.find_pretrained_weights(
                self.ed_engine.text().strip(), self.cmb_variant.currentText())
            gpt = gpt or (g or "")
            sovits = sovits or (sv or "")
            if gpt:
                self.ed_gpt.setText(gpt)
            if sovits:
                self.ed_sovits.setText(sovits)
        if not gpt and not sovits:
            self._warn(tr("model_apply_failed") + " weights not found")
            return
        self.btn_apply_model.setEnabled(False)
        self.model_worker = ModelApplyWorker(self.client, gpt, sovits)
        self.model_worker.sig_done.connect(self._on_model_applied)
        self.model_worker.start()

    @Slot(bool, str)
    def _on_model_applied(self, ok: bool, msg: str):
        tr = self.i18n.tr
        self.btn_apply_model.setEnabled(True)
        if ok:
            self.append_log(f"✓ {tr('model_applied')}")
        else:
            key = classify_error(msg)
            self._warn(f"{tr('model_apply_failed')}\n{tr(key) if key else msg}")
        self.model_worker = None

    # ==================================================================
    # Helpers
    # ==================================================================
    @Slot(str)
    def append_log(self, line: str):
        self.txt_log.appendPlainText(line)

    def _warn(self, msg: str):
        QMessageBox.warning(self, self.i18n.tr("warning"), msg)
