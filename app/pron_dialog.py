# -*- coding: utf-8 -*-
"""Hộp thoại 'Từ điển phát âm': biên tập quy tắc thay thế + thử ngay tại chỗ."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QHeaderView,
                               QLabel, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from app.pronunciation import preview, valid_regex

COL_PATTERN, COL_REPLACE, COL_REGEX, COL_ENABLED = range(4)


def _centered_checkbox(checked: bool) -> QWidget:
    """QCheckBox căn giữa trong ô bảng (Qt không tự căn cellWidget)."""
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setAlignment(Qt.AlignCenter)
    chk = QCheckBox()
    chk.setChecked(checked)
    lay.addWidget(chk)
    box.chk = chk
    return box


class PronunciationDialog(QDialog):
    """Sửa xong bấm Lưu → store.rules được cập nhật và ghi xuống đĩa."""

    def __init__(self, i18n, store, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.store = store
        tr = i18n.tr

        self.setWindowTitle(tr("pron_title"))
        self.resize(840, 620)
        lay = QVBoxLayout(self)

        self.lbl_hint = QLabel(tr("pron_hint"))
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color:#556;")
        lay.addWidget(self.lbl_hint)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels([
            tr("pron_col_find"), tr("pron_col_replace"),
            tr("pron_col_regex"), tr("pron_col_enabled")])
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(COL_PATTERN, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_REPLACE, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_REGEX, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(COL_ENABLED, QHeaderView.ResizeToContents)
        self.tbl.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl, 3)

        row = QHBoxLayout()
        self.btn_add = QPushButton(tr("pron_add"))
        self.btn_del = QPushButton(tr("pron_del"))
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        self.btn_up.setToolTip(tr("pron_order_tip"))
        self.btn_down.setToolTip(tr("pron_order_tip"))
        for b in (self.btn_add, self.btn_del, self.btn_up, self.btn_down):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addWidget(QLabel(tr("pron_test")))
        self.ed_test = QTextEdit()
        self.ed_test.setPlaceholderText(tr("pron_test_placeholder"))
        self.ed_test.setMaximumHeight(70)
        lay.addWidget(self.ed_test)
        self.lbl_preview = QLabel()
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_preview.setStyleSheet(
            "background:#f4f5f8; border:1px solid #c9ccd4; "
            "border-radius:6px; padding:6px;")
        self.lbl_preview.setMinimumHeight(56)
        lay.addWidget(self.lbl_preview, 1)

        row2 = QHBoxLayout()
        self.btn_save = QPushButton(tr("pron_save"))
        self.btn_save.setObjectName("primary")
        self.btn_close = QPushButton(tr("cancel"))
        row2.addStretch(1)
        row2.addWidget(self.btn_save)
        row2.addWidget(self.btn_close)
        lay.addLayout(row2)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._del_row)
        self.btn_up.clicked.connect(lambda: self._move_row(-1))
        self.btn_down.clicked.connect(lambda: self._move_row(1))
        self.btn_save.clicked.connect(self._save)
        self.btn_close.clicked.connect(self.reject)
        self.tbl.itemChanged.connect(lambda _i: self._refresh_preview())
        self.ed_test.textChanged.connect(self._refresh_preview)

        self._load_rows()
        self._refresh_preview()

    # ------------------------------------------------------------------
    def _set_row(self, r: int, rule: dict):
        # Chặn itemChanged khi đang dựng dòng: setItem() sẽ kích _refresh_preview()
        # trong lúc 2 checkbox của dòng chưa kịp tạo → cellWidget() trả None.
        self.tbl.blockSignals(True)
        try:
            self.tbl.setItem(r, COL_PATTERN,
                             QTableWidgetItem(rule.get("pattern", "")))
            self.tbl.setItem(r, COL_REPLACE,
                             QTableWidgetItem(rule.get("replace", "")))
            for col, key in ((COL_REGEX, "regex"), (COL_ENABLED, "enabled")):
                box = _centered_checkbox(bool(rule.get(key, key == "enabled")))
                box.chk.stateChanged.connect(lambda _s: self._refresh_preview())
                self.tbl.setCellWidget(r, col, box)
        finally:
            self.tbl.blockSignals(False)

    def _checked(self, r: int, col: int, default: bool) -> bool:
        """Trạng thái checkbox của ô; dòng đang dựng dở → giá trị mặc định."""
        box = self.tbl.cellWidget(r, col)
        return box.chk.isChecked() if box is not None else default

    def _load_rows(self):
        self.tbl.setRowCount(0)
        for rule in self.store.rules:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self._set_row(r, rule)

    def _add_row(self):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)
        self._set_row(r, {"pattern": "", "replace": "", "regex": False,
                          "enabled": True})
        self.tbl.editItem(self.tbl.item(r, COL_PATTERN))

    def _del_row(self):
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.tbl.removeRow(r)
        self._refresh_preview()

    def _move_row(self, delta: int):
        r = self.tbl.currentRow()
        n = self.tbl.rowCount()
        if r < 0 or not (0 <= r + delta < n):
            return
        rules = self._collect_rules()
        rules[r], rules[r + delta] = rules[r + delta], rules[r]
        self.store.rules = rules            # tạm, chỉ để vẽ lại
        self._load_rows()
        self.tbl.setCurrentCell(r + delta, COL_PATTERN)
        self._refresh_preview()

    def _collect_rules(self) -> list:
        rules = []
        for r in range(self.tbl.rowCount()):
            it_pat = self.tbl.item(r, COL_PATTERN)
            it_rep = self.tbl.item(r, COL_REPLACE)
            pattern = it_pat.text().strip() if it_pat else ""
            if not pattern:
                continue                    # dòng trống → bỏ
            rules.append({
                "pattern": pattern,
                "replace": it_rep.text() if it_rep else "",
                "regex": self._checked(r, COL_REGEX, False),
                "enabled": self._checked(r, COL_ENABLED, True),
            })
        return rules

    # ------------------------------------------------------------------
    def _refresh_preview(self):
        tr = self.i18n.tr
        rules = self._collect_rules()
        bad = [r["pattern"] for r in rules
               if r["regex"] and valid_regex(r["pattern"])]
        text = self.ed_test.toPlainText()
        if not text.strip():
            self.lbl_preview.setText("")
        else:
            out, hits = preview(text, [r for r in rules if r.get("enabled")])
            note = (f"\n\n— {tr('pron_hits')} {', '.join(hits)}" if hits
                    else f"\n\n— {tr('pron_no_hit')}")
            self.lbl_preview.setText(out + note)
        if bad:
            self.lbl_hint.setText(f"⚠ {tr('pron_invalid_regex')} {', '.join(bad)}")
            self.lbl_hint.setStyleSheet("color:#c0392b; font-weight:600;")
        else:
            self.lbl_hint.setText(tr("pron_hint"))
            self.lbl_hint.setStyleSheet("color:#556;")

    def _save(self):
        tr = self.i18n.tr
        rules = self._collect_rules()
        for r in rules:
            if r["regex"]:
                err = valid_regex(r["pattern"])
                if err:
                    QMessageBox.warning(
                        self, tr("error"),
                        f"{tr('pron_invalid_regex')} {r['pattern']}\n\n{err}")
                    return
        self.store.rules = rules
        self.store.save()
        self.accept()
