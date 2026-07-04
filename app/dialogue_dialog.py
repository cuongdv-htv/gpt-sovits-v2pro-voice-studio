# -*- coding: utf-8 -*-
"""Hộp thoại 'Hội thoại đa giọng': soạn kịch bản [Vai] → gán voice profile
cho từng vai → tạo file hội thoại hoàn chỉnh."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QHeaderView,
                               QLabel, QMessageBox, QProgressBar, QPushButton,
                               QTableWidget, QTableWidgetItem, QTextEdit,
                               QVBoxLayout)

from app.dialogue import (DialogueWorker, SpeakerVoice, dialogue_tags,
                          parse_dialogue)
from app.i18n import TEXT_LANGS


class DialogueDialog(QDialog):
    """result_dir chứa thư mục kết quả sau khi tạo thành công (None nếu chưa)."""

    def __init__(self, i18n, profiles, client, make_cfg, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.profiles = profiles
        self.client = client
        self.make_cfg = make_cfg      # callable → TtsJobConfig hiện hành
        self.worker = None
        self.result_dir = None
        tr = i18n.tr

        self.setWindowTitle(tr("dlg_title"))
        self.resize(820, 640)
        lay = QVBoxLayout(self)

        self.lbl_hint = QLabel(tr("dlg_hint"))
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color:#556;")
        lay.addWidget(self.lbl_hint)

        self.ed_script = QTextEdit()
        self.ed_script.setPlaceholderText(tr("dlg_script_placeholder"))
        self.ed_script.setMinimumHeight(220)
        lay.addWidget(self.ed_script, 2)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("text_lang")))
        self.cmb_lang = QComboBox()
        for c in TEXT_LANGS:
            self.cmb_lang.addItem(i18n.lang_label(c), c)
        row.addWidget(self.cmb_lang)
        row.addStretch(1)
        self.btn_scan = QPushButton(tr("dlg_scan"))
        row.addWidget(self.btn_scan)
        lay.addLayout(row)

        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels([tr("dlg_col_tag"),
                                            tr("dlg_col_profile")])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setMinimumHeight(120)
        lay.addWidget(self.tbl, 1)

        self.pb = QProgressBar()
        self.pb.setValue(0)
        self.lbl_status = QLabel("")
        lay.addWidget(self.pb)
        lay.addWidget(self.lbl_status)

        row2 = QHBoxLayout()
        self.btn_generate = QPushButton(tr("dlg_generate"))
        self.btn_generate.setObjectName("primary")
        self.btn_cancel_run = QPushButton(tr("btn_cancel_batch"))
        self.btn_cancel_run.setEnabled(False)
        self.btn_close = QPushButton(tr("cancel"))
        row2.addStretch(1)
        row2.addWidget(self.btn_generate)
        row2.addWidget(self.btn_cancel_run)
        row2.addWidget(self.btn_close)
        lay.addLayout(row2)

        self.btn_scan.clicked.connect(self._scan_tags)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_cancel_run.clicked.connect(self._cancel_run)
        self.btn_close.clicked.connect(self.reject)

    # ------------------------------------------------------------------
    def _scan_tags(self) -> bool:
        tr = self.i18n.tr
        try:
            lines = parse_dialogue(self.ed_script.toPlainText())
        except ValueError:
            QMessageBox.warning(self, tr("warning"), tr("dlg_parse_error"))
            return False
        if not lines:
            QMessageBox.warning(self, tr("warning"), tr("dlg_parse_empty"))
            return False

        # Giữ lựa chọn cũ nếu tag không đổi
        old = {self.tbl.item(r, 0).text(): self.tbl.cellWidget(r, 1).currentText()
               for r in range(self.tbl.rowCount())
               if self.tbl.item(r, 0) and self.tbl.cellWidget(r, 1)}
        names = self.profiles.names()
        tags = dialogue_tags(lines)
        self.tbl.setRowCount(len(tags))
        for r, tag in enumerate(tags):
            it = QTableWidgetItem(tag)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tbl.setItem(r, 0, it)
            cmb = QComboBox()
            cmb.addItems(names)
            # ưu tiên chọn lại như cũ; hoặc profile trùng tên tag
            if tag in old and old[tag] in names:
                cmb.setCurrentText(old[tag])
            elif tag in names:
                cmb.setCurrentText(tag)
            self.tbl.setCellWidget(r, 1, cmb)
        self._lines = lines
        return True

    def _generate(self):
        tr = self.i18n.tr
        if not self.profiles.names():
            QMessageBox.warning(self, tr("warning"), tr("dlg_need_profiles"))
            return
        if not self._scan_tags():
            return
        speakers = {}
        for r in range(self.tbl.rowCount()):
            tag = self.tbl.item(r, 0).text()
            prof = self.profiles.get(self.tbl.cellWidget(r, 1).currentText())
            if prof is None or not prof.ref_audio_path:
                QMessageBox.warning(self, tr("warning"),
                                    f"{tr('dlg_unmapped')} [{tag}]")
                return
            speakers[tag] = SpeakerVoice(
                ref_audio_path=prof.ref_audio_path,
                prompt_text=prof.prompt_text,
                prompt_lang=prof.prompt_lang,
                aux_ref_audio_paths=prof.aux_ref_audio_paths,
            )

        self.pb.setValue(0)
        self.pb.setMaximum(len(self._lines))
        self.lbl_status.setText(tr("dlg_running"))
        self.btn_generate.setEnabled(False)
        self.btn_cancel_run.setEnabled(True)
        self.worker = DialogueWorker(
            self.client, self.make_cfg(), self._lines, speakers,
            self.cmb_lang.currentData() or "auto",
            self.ed_script.toPlainText())
        self.worker.sig_progress.connect(
            lambda d, t: (self.pb.setMaximum(t), self.pb.setValue(d)))
        self.worker.sig_log.connect(self.lbl_status.setText)
        self.worker.sig_done.connect(self._on_done)
        self.worker.start()

    def _cancel_run(self):
        if self.worker:
            self.worker.cancel()
            self.btn_cancel_run.setEnabled(False)

    @Slot(bool, str)
    def _on_done(self, ok: bool, payload: str):
        tr = self.i18n.tr
        self.btn_generate.setEnabled(True)
        self.btn_cancel_run.setEnabled(False)
        self.worker = None
        if ok:
            self.result_dir = payload
            self.lbl_status.setText(f"{tr('dlg_done')} {payload}")
            self.accept()
        elif payload == "cancelled":
            self.lbl_status.setText(tr("msg_batch_cancelled"))
        else:
            self.lbl_status.setText(payload)
            QMessageBox.warning(self, tr("error"), payload)

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(5000)
        super().closeEvent(e)
