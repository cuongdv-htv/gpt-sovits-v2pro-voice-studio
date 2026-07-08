# -*- coding: utf-8 -*-
"""dialogue: phân tích kịch bản [Vai] → lời thoại."""

import pytest

from app.dialogue import dialogue_tags, parse_dialogue


def test_parse_co_ban():
    assert parse_dialogue("[A] xin chào\n[B] chào bạn") == \
        [("A", "xin chào"), ("B", "chào bạn")]


def test_dong_khong_tag_noi_vao_vai_ngay_tren():
    lines = parse_dialogue("[A] câu một\ncâu hai\n[B] câu ba")
    assert lines == [("A", "câu một\ncâu hai"), ("B", "câu ba")]


def test_dong_trong_bi_bo_qua():
    assert parse_dialogue("[A] một\n\n\n[B] hai") == [("A", "một"), ("B", "hai")]


def test_tag_khong_co_loi_thoai_bi_loai():
    assert parse_dialogue("[A]\n[B] có lời") == [("B", "có lời")]


def test_noi_dung_truoc_tag_dau_tien_thi_nem_loi():
    with pytest.raises(ValueError):
        parse_dialogue("lời thoại không có vai\n[A] xin chào")


def test_kich_ban_rong():
    assert parse_dialogue("") == []


def test_tag_tieng_nhat():
    assert parse_dialogue("[田中] こんにちは。") == [("田中", "こんにちは。")]


def test_tag_co_khoang_trang_thua():
    assert parse_dialogue("[  A  ]   xin chào  ") == [("A", "xin chào")]


def test_dialogue_tags_duy_nhat_va_giu_thu_tu():
    lines = [("B", "x"), ("A", "y"), ("B", "z"), ("C", "w")]
    assert dialogue_tags(lines) == ["B", "A", "C"]


def test_dialogue_tags_rong():
    assert dialogue_tags([]) == []
