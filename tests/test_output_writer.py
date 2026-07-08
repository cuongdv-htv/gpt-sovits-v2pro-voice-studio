# -*- coding: utf-8 -*-
"""output_writer: làm sạch tên thư mục Windows, chống trùng, ghi trọn bộ."""

import json
from pathlib import Path

from app.output_writer import create_output_dir, sanitize_name, write_result
from tests.conftest import make_wav


# ------------------------------------------------------------- sanitize_name
def test_sanitize_thay_ky_tu_cam_cua_windows():
    assert sanitize_name('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_khoang_trang_thanh_gach_duoi():
    assert sanitize_name("tên  có   khoảng trắng") == "tên_có_khoảng_trắng"


def test_sanitize_cat_dau_cham_va_khoang_trang_hai_dau():
    assert sanitize_name("  .tên.  ") == "tên"


def test_sanitize_ten_rong_thanh_untitled():
    assert sanitize_name("") == "untitled"
    assert sanitize_name("   ...   ") == "untitled"


def test_sanitize_cat_do_dai():
    assert len(sanitize_name("a" * 200)) == 60
    assert len(sanitize_name("a" * 200, max_len=10)) == 10


def test_sanitize_giu_tieng_nhat():
    assert sanitize_name("第一章") == "第一章"


# ------------------------------------------------------------- create_output_dir
def test_create_output_dir_them_hau_to_khi_trung(tmp_path, monkeypatch):
    """Hai kết quả trong cùng một giây không được ghi đè nhau."""
    class FrozenDatetime:
        @staticmethod
        def now():
            import datetime as _dt
            return _dt.datetime(2026, 7, 8, 23, 30, 0)

    monkeypatch.setattr("app.output_writer.datetime", FrozenDatetime)
    base = str(tmp_path / "out")

    first = create_output_dir(base, "chuong")
    second = create_output_dir(base, "chuong")
    third = create_output_dir(base, "chuong")

    assert first.name == "20260708_233000_chuong"
    assert second.name == "20260708_233000_chuong_2"
    assert third.name == "20260708_233000_chuong_3"
    assert all(d.is_dir() for d in (first, second, third))


def test_create_output_dir_tao_ca_thu_muc_goc(tmp_path):
    out = create_output_dir(str(tmp_path / "chua" / "ton" / "tai"), "x")
    assert out.is_dir()


# ------------------------------------------------------------- write_result
def test_write_result_ghi_du_bo_file(tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(make_wav(5.0))
    wav = make_wav(2.0)

    out = write_result(output_base=str(tmp_path / "out"), source_name="chương 1",
                       wav_bytes=wav, text="nội dung", ref_audio_path=str(ref),
                       meta={"seed_actual": 42}, srt_text="1\n...\n")

    assert (out / "output.wav").read_bytes() == wav      # ghi nguyên bytes
    assert (out / "input.txt").read_text(encoding="utf-8") == "nội dung"
    assert (out / "output.srt").exists()
    assert (out / "ref_used.wav").read_bytes() == ref.read_bytes()

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["seed_actual"] == 42
    assert meta["srt_exported"] is True
    assert meta["duration_seconds"] == 2.0
    assert meta["source_name"] == "chương 1"


def test_write_result_khong_co_srt_thi_khong_tao_file(tmp_path):
    out = write_result(output_base=str(tmp_path / "out"), source_name="x",
                       wav_bytes=make_wav(1.0), text="t", ref_audio_path="",
                       meta={})
    assert not (out / "output.srt").exists()
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["srt_exported"] is False
    assert meta["ref_audio_copied"] is None


def test_write_result_ref_khong_ton_tai_van_ghi_duoc(tmp_path):
    """Mất file ref giữa chừng không được làm hỏng kết quả đã tổng hợp."""
    out = write_result(output_base=str(tmp_path / "out"), source_name="x",
                       wav_bytes=make_wav(1.0), text="t",
                       ref_audio_path="D:/khong/ton/tai.wav", meta={})
    assert (out / "output.wav").exists()
    assert not list(Path(out).glob("ref_used.*"))
