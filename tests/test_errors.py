# -*- coding: utf-8 -*-
"""errors.classify_error: lỗi engine (thường tiếng Trung/traceback) → khóa i18n."""

import pytest

from app.errors import classify_error
from app.i18n import STRINGS


@pytest.mark.parametrize("raw,key", [
    ("参考音频在3~10秒范围外", "err_ref_duration"),
    ("ref audio must be 3-10 seconds", "err_ref_duration"),
    ("CUDA out of memory. Tried to allocate 2.00 GiB", "msg_vram"),
    ("torch.OutOfMemoryError", "msg_vram"),
    ("Engine không phản hồi (ConnectionError)", "engine_not_ready_msg"),
    ("エンジン応答なし", "engine_not_ready_msg"),
    ("Max retries exceeded with url: /tts", "engine_not_ready_msg"),
    ("text_lang: vi is not supported", "msg_lang_unsupported"),
])
def test_nhan_dien_loi_quen_thuoc(raw, key):
    assert classify_error(raw) == key


@pytest.mark.parametrize("raw", ["", None, "một lỗi hoàn toàn lạ"])
def test_khong_nhan_ra_thi_tra_none(raw):
    """UI sẽ hiển thị nguyên văn thay vì đoán bừa."""
    assert classify_error(raw) is None


def test_moi_khoa_tra_ve_deu_ton_tai_trong_i18n():
    """Khóa không tồn tại → i18n.tr() trả về chính chuỗi khóa, người dùng
    nhìn thấy 'msg_vram' thay vì lời giải thích."""
    keys = {classify_error(raw) for raw in (
        "参考音频", "out of memory", "ConnectionError", "text_lang unsupported")}
    for key in keys:
        assert key in STRINGS, f"khóa {key} thiếu trong i18n.STRINGS"


def test_uu_tien_mau_cu_the_hon():
    """Lỗi vừa khớp ref-duration vừa có chữ 'error' phải ra err_ref_duration."""
    assert classify_error("Error: 参考音频 3~10") == "err_ref_duration"
