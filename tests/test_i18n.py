# -*- coding: utf-8 -*-
"""i18n: mọi chuỗi phải có đủ 3 ngôn ngữ. Thiếu → UI rơi về tiếng Việt lặng lẽ."""

import pytest

from app.i18n import (CUT_METHODS, LANGS, NEXT_LANG_LABEL, PROMPT_LANGS,
                      STRINGS, TEXT_LANG_LABELS, TEXT_LANGS, I18n)


def test_moi_chuoi_co_du_ba_ngon_ngu():
    thieu = {key: [l for l in LANGS if l not in entry]
             for key, entry in STRINGS.items()
             if any(l not in entry for l in LANGS)}
    assert thieu == {}, f"chuỗi thiếu bản dịch: {thieu}"


def test_khong_chuoi_nao_bo_trong():
    rong = [f"{k}.{l}" for k, e in STRINGS.items()
            for l in LANGS if not str(e.get(l, "")).strip()]
    assert rong == []


def test_moi_ngon_ngu_doc_deu_co_nhan():
    for code in TEXT_LANGS:
        assert code in TEXT_LANG_LABELS
        for lang in LANGS:
            assert TEXT_LANG_LABELS[code].get(lang)


def test_tieng_viet_khong_nam_trong_ngon_ngu_doc():
    """v2Pro không đọc được tiếng Việt — lọt 'vi' vào đây là engine trả 400."""
    assert "vi" not in TEXT_LANGS
    assert "vi" not in PROMPT_LANGS


def test_prompt_langs_khong_co_auto():
    """prompt_lang phải là ngôn ngữ cụ thể; 'auto' chỉ hợp lệ cho text_lang."""
    assert "auto" not in PROMPT_LANGS
    assert "auto" in TEXT_LANGS


def test_vong_chuyen_ngu_quay_ve_diem_dau():
    i18n = I18n("vi")
    assert [i18n.toggle() for _ in LANGS] == ["ja", "en", "vi"]


def test_next_lang_label_day_du():
    assert set(NEXT_LANG_LABEL) == set(LANGS)


def test_ngon_ngu_khong_hop_le_thi_ve_tieng_viet():
    assert I18n("klingon").lang == "vi"


def test_tr_khoa_khong_ton_tai_tra_ve_chinh_khoa():
    assert I18n("vi").tr("khoa_khong_co") == "khoa_khong_co"


@pytest.mark.parametrize("lang", LANGS)
def test_tr_tra_dung_ngon_ngu(lang):
    assert I18n(lang).tr("cancel") == STRINGS["cancel"][lang]


def test_cut_methods_khop_voi_engine():
    assert CUT_METHODS == ["cut0", "cut1", "cut2", "cut3", "cut4", "cut5"]
