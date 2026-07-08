# -*- coding: utf-8 -*-
"""Test tầng GUI (offscreen, không cần màn hình).

Chỉ test LOGIC của widget — không test pixel. Trọng tâm là những chỗ đã
từng hỏng: signal bắn ra giữa lúc dựng dòng bảng, nhãn độ dài ref audio,
vòng đời tham số của voice profile.
"""

import sys

import pytest

# QtWidgets cần plugin nền tảng; máy CI Linux tối giản có thể thiếu.
pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.i18n import I18n  # noqa: E402
from app.profiles import VoiceProfile  # noqa: E402
from app.pron_dialog import (COL_ENABLED, COL_PATTERN, COL_REGEX,  # noqa: E402
                             COL_REPLACE, PronunciationDialog)
from app.pronunciation import PronunciationStore, apply_rules  # noqa: E402
from tests.conftest import make_wav  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def fail_on_swallowed_qt_exception(monkeypatch):
    """Exception ném ra trong một Qt slot KHÔNG làm test đỏ — Qt bắt nó, gọi
    sys.excepthook rồi chạy tiếp. Đó đúng là cách bug `cellWidget() → None`
    lọt qua bộ test tay trước đây: preview âm thầm không cập nhật.

    Fixture này biến mọi exception bị nuốt thành test thất bại."""
    swallowed = []

    def hook(exctype, value, tb):
        swallowed.append(f"{exctype.__name__}: {value}")

    monkeypatch.setattr(sys, "excepthook", hook)
    yield
    assert not swallowed, ("exception bị Qt nuốt trong slot: "
                           + "; ".join(swallowed))


@pytest.fixture
def pron_dialog(qapp):
    store = PronunciationStore()
    store.rules = [{"pattern": "TSMC", "replace": "ティーエスエムシー",
                    "regex": False, "enabled": True}]
    dlg = PronunciationDialog(I18n("vi"), store)
    yield dlg
    dlg.deleteLater()


# ==================================================== PronunciationDialog
def test_nap_rule_co_san(pron_dialog):
    assert pron_dialog.tbl.rowCount() == 1
    assert pron_dialog.tbl.item(0, COL_PATTERN).text() == "TSMC"


def test_them_dong_khong_nem_loi_khi_chua_co_checkbox(pron_dialog):
    """Regression: _add_row() gọi setItem() làm itemChanged bắn ra TRƯỚC khi
    checkbox của dòng kịp tạo → cellWidget() trả None → AttributeError bị Qt
    nuốt im lặng (preview âm thầm không cập nhật)."""
    pron_dialog.ed_test.setPlainText("TSMC")
    pron_dialog._add_row()                     # không được ném
    assert pron_dialog.tbl.rowCount() == 2
    assert pron_dialog._collect_rules()        # vẫn thu được rule cũ


def test_collect_rules_bo_qua_dong_trong(pron_dialog):
    pron_dialog._add_row()                     # dòng trống, pattern rỗng
    rules = pron_dialog._collect_rules()
    assert len(rules) == 1
    assert rules[0]["pattern"] == "TSMC"


def test_preview_cap_nhat_khi_go_van_ban(pron_dialog):
    pron_dialog.ed_test.setPlainText("TSMCの5Gチップ")
    prev = pron_dialog.lbl_preview.text()
    assert "ティーエスエムシー" in prev
    assert "TSMC" in prev.split("—")[1]        # phần liệt kê rule đã khớp


def test_preview_bao_khong_khop(pron_dialog):
    pron_dialog.ed_test.setPlainText("không có gì khớp")
    assert pron_dialog.i18n.tr("pron_no_hit") in pron_dialog.lbl_preview.text()


def test_preview_rong_khi_khong_co_van_ban_thu(pron_dialog):
    pron_dialog.ed_test.setPlainText("")
    assert pron_dialog.lbl_preview.text() == ""


def test_rule_moi_an_vao_preview_ngay(pron_dialog):
    pron_dialog.ed_test.setPlainText("5G")
    pron_dialog._add_row()
    pron_dialog.tbl.item(1, COL_PATTERN).setText("5G")
    pron_dialog.tbl.item(1, COL_REPLACE).setText("ファイブジー")
    assert "ファイブジー" in pron_dialog.lbl_preview.text()


def test_tat_checkbox_thi_preview_doi(pron_dialog):
    pron_dialog.ed_test.setPlainText("TSMC")
    pron_dialog.tbl.cellWidget(0, COL_ENABLED).chk.setChecked(False)
    assert "ティーエスエムシー" not in pron_dialog.lbl_preview.text()


def test_regex_hong_thi_canh_bao_do(pron_dialog):
    pron_dialog._add_row()
    pron_dialog.tbl.item(1, COL_PATTERN).setText("(unclosed")
    pron_dialog.tbl.cellWidget(1, COL_REGEX).chk.setChecked(True)
    assert "⚠" in pron_dialog.lbl_hint.text()
    assert "c0392b" in pron_dialog.lbl_hint.styleSheet()   # màu đỏ


def test_regex_sua_lai_thi_het_canh_bao(pron_dialog):
    pron_dialog._add_row()
    item = pron_dialog.tbl.item(1, COL_PATTERN)
    item.setText("(unclosed")
    pron_dialog.tbl.cellWidget(1, COL_REGEX).chk.setChecked(True)
    item.setText(r"\d+")
    assert "⚠" not in pron_dialog.lbl_hint.text()


def test_luu_ghi_xuong_dia_va_giu_thu_tu(pron_dialog):
    pron_dialog._add_row()
    pron_dialog.tbl.item(1, COL_PATTERN).setText(r"(\d+),(\d+)億円")
    pron_dialog.tbl.item(1, COL_REPLACE).setText(r"\1\2オクエン")
    pron_dialog.tbl.cellWidget(1, COL_REGEX).chk.setChecked(True)
    pron_dialog._save()

    reloaded = PronunciationStore()
    assert [r["pattern"] for r in reloaded.rules] == ["TSMC", r"(\d+),(\d+)億円"]
    assert apply_rules("1,200億円", reloaded.enabled_rules()) == "1200オクエン"


def test_doi_thu_tu_bang_nut_len(pron_dialog):
    pron_dialog._add_row()
    pron_dialog.tbl.item(1, COL_PATTERN).setText("5G")
    pron_dialog.tbl.setCurrentCell(1, COL_PATTERN)
    pron_dialog._move_row(-1)
    order = [pron_dialog.tbl.item(r, COL_PATTERN).text() for r in range(2)]
    assert order == ["5G", "TSMC"]


def test_move_row_ngoai_bien_khong_nem(pron_dialog):
    pron_dialog.tbl.setCurrentCell(0, COL_PATTERN)
    pron_dialog._move_row(-1)                  # đã ở đầu bảng
    assert pron_dialog.tbl.rowCount() == 1


# ==================================================== MainWindow
@pytest.fixture
def main_window(qapp):
    from app.ui_main import MainWindow
    w = MainWindow()
    yield w
    w.vram_monitor.stop()
    w.vram_monitor.wait(2000)
    w._crash_timer.stop()
    w.deleteLater()


def test_nhan_do_dai_ref_hop_le(main_window, tmp_path):
    p = tmp_path / "ref.wav"
    p.write_bytes(make_wav(7.46))
    main_window.ed_ref.setText(str(p))
    assert "7.46" in main_window.lbl_ref_dur.text()
    assert main_window.lbl_ref_dur.text().startswith("✓")


def test_nhan_do_dai_ref_ngoai_khoang(main_window, tmp_path):
    p = tmp_path / "dai.wav"
    p.write_bytes(make_wav(12.0))
    main_window.ed_ref.setText(str(p))
    assert main_window.lbl_ref_dur.text().startswith("✗")
    assert "c0392b" in main_window.lbl_ref_dur.styleSheet()


def test_nhan_do_dai_xoa_khi_file_khong_ton_tai(main_window):
    main_window.ed_ref.setText("D:/khong/ton/tai.wav")
    assert main_window.lbl_ref_dur.text() == ""


def test_nhan_do_dai_dich_lai_khi_doi_ngon_ngu(main_window, tmp_path):
    p = tmp_path / "ref.wav"
    p.write_bytes(make_wav(7.46))
    main_window.ed_ref.setText(str(p))
    vi = main_window.lbl_ref_dur.text()
    main_window._toggle_lang()
    ja = main_window.lbl_ref_dur.text()
    assert vi != ja
    assert "7.46" in ja


def _pretend_engine_ready(win):
    """Qua được cửa kiểm tra engine để test các cửa phía sau."""
    win.engine_state = "ready"
    win.client.is_alive = lambda: True


def test_validate_chan_ref_ngoai_khoang(main_window, tmp_path):
    """Không để engine nạp model xong rồi mới trả 400."""
    p = tmp_path / "dai.wav"
    p.write_bytes(make_wav(12.0))
    main_window.ed_ref.setText(str(p))
    _pretend_engine_ready(main_window)
    warnings = []
    main_window._warn = warnings.append
    assert main_window._validate_before_tts() is False
    assert "3–10" in warnings[0]


def test_validate_cho_qua_ref_hop_le(main_window, tmp_path):
    p = tmp_path / "ok.wav"
    p.write_bytes(make_wav(7.0))
    main_window.ed_ref.setText(str(p))
    _pretend_engine_ready(main_window)
    main_window._warn = lambda msg: pytest.fail(f"không được cảnh báo: {msg}")
    assert main_window._validate_before_tts() is True


def test_validate_chan_khi_engine_chua_san_sang(main_window, tmp_path):
    p = tmp_path / "ok.wav"
    p.write_bytes(make_wav(7.0))
    main_window.ed_ref.setText(str(p))
    main_window.engine_state = "stopped"
    warnings = []
    main_window._warn = warnings.append
    assert main_window._validate_before_tts() is False
    assert warnings                      # báo về engine, không phải ref


def test_profile_params_round_trip(main_window):
    main_window.sl_speed.setValue(85)
    main_window.sp_temp.setValue(0.70)
    main_window.sp_topk.setValue(20)
    saved = main_window._current_params()

    main_window.profiles.upsert(
        VoiceProfile("kể chuyện", "r.wav", "", "ja", params=saved))
    main_window._refresh_profiles_combo()

    main_window.sl_speed.setValue(110)          # đổi sang bộ khác
    main_window.sp_temp.setValue(1.20)

    main_window.cmb_profiles.setCurrentText("kể chuyện")
    main_window._load_profile()

    p = main_window._current_params()
    assert p["speed_factor"] == pytest.approx(0.85)
    assert p["temperature"] == pytest.approx(0.70)
    assert p["top_k"] == 20
    assert main_window.lbl_speed_val.text() == "0.85×"


def test_profile_cu_khong_dung_toi_widget(main_window):
    main_window.sl_speed.setValue(110)
    main_window.profiles.upsert(VoiceProfile("cũ", "r.wav", "", "ja"))
    main_window._refresh_profiles_combo()
    main_window.cmb_profiles.setCurrentText("cũ")
    main_window._load_profile()
    assert main_window._current_params()["speed_factor"] == pytest.approx(1.10)
