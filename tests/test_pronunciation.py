# -*- coding: utf-8 -*-
"""pronunciation: thay thế trước khi gửi engine, không đụng văn bản gốc."""

from app.pronunciation import (PronunciationStore, apply_rules, matching_rules,
                               preview, valid_regex)
from tests.conftest import rule


# ------------------------------------------------------------- apply_rules
def test_thay_the_literal():
    rules = [rule("TSMC", "ティーエスエムシー"), rule("5G", "ファイブジー")]
    assert apply_rules("TSMCの5Gチップ", rules) == \
        "ティーエスエムシーのファイブジーチップ"


def test_rule_tat_thi_khong_ap_dung():
    assert apply_rules("TSMC", [rule("TSMC", "X", enabled=False)]) == "TSMC"


def test_khong_co_rule_thi_giu_nguyen():
    assert apply_rules("TSMC", []) == "TSMC"
    assert apply_rules("TSMC", None) == "TSMC"


def test_pattern_rong_bi_bo_qua():
    assert apply_rules("abc", [rule("", "X")]) == "abc"


def test_thu_tu_cu_the_truoc_tong_quat():
    good = [rule("EUV", "イーユーブイ"), rule("EU", "イーユー")]
    assert apply_rules("EUV", good) == "イーユーブイ"


def test_thu_tu_sai_thi_hong_dung_nhu_tai_lieu_canh_bao():
    """Áp tuần tự, KHÔNG longest-match: 'EU' đứng trước ăn mất phần đầu,
    để lại chữ 'V' lơ lửng. Hành vi này được ghi rõ trong tooltip + docs."""
    bad = [rule("EU", "イーユー"), rule("EUV", "イーユーブイ")]
    assert apply_rules("EUV", bad) == "イーユーV"


# ------------------------------------------------------------- regex
def test_regex_voi_backreference():
    rules = [rule(r"(\d+),(\d+)億円", r"\1\2オクエン", regex=True)]
    assert apply_rules("1,200億円", rules) == "1200オクエン"


def test_regex_hong_thi_bo_qua_rule_khong_nem_loi():
    """Một lỗi gõ nhầm không được phép giết batch chạy 40 phút."""
    assert apply_rules("abc", [rule("(unclosed", "X", regex=True)]) == "abc"


def test_regex_hong_khong_chan_cac_rule_khac():
    rules = [rule("(unclosed", "X", regex=True), rule("abc", "def")]
    assert apply_rules("abc", rules) == "def"


def test_valid_regex():
    assert valid_regex(r"\d+") is None
    assert valid_regex("(unclosed") is not None


def test_pattern_literal_khong_bi_hieu_la_regex():
    assert apply_rules("a.c", [rule(".", "X")]) == "aXc"     # literal dấu chấm
    assert apply_rules("abc", [rule(".", "X", regex=True)]) == "XXX"


# ------------------------------------------------------------- matching_rules
def test_matching_rules_chi_liet_ke_rule_thuc_su_doi_text():
    hits = matching_rules("TSMCのチップ", [rule("TSMC", "T"), rule("EUV", "E")])
    assert hits == ["TSMC"]


def test_matching_rules_bo_qua_rule_tat():
    assert matching_rules("TSMC", [rule("TSMC", "T", enabled=False)]) == []


def test_preview_tra_ve_text_va_hits():
    out, hits = preview("5G", [rule("5G", "ファイブジー")])
    assert out == "ファイブジー"
    assert hits == ["5G"]


def test_preview_khong_khop():
    out, hits = preview("xyz", [rule("5G", "ファイブジー")])
    assert (out, hits) == ("xyz", [])


# ------------------------------------------------------------- store
def test_store_round_trip():
    store = PronunciationStore()
    store.rules = [rule("TSMC", "T"), rule("x", "y", enabled=False)]
    store.save()

    reloaded = PronunciationStore()
    assert len(reloaded.rules) == 2
    assert len(reloaded.enabled_rules()) == 1
    assert reloaded.enabled_rules()[0]["pattern"] == "TSMC"


def test_store_giu_thu_tu():
    store = PronunciationStore()
    store.rules = [rule("EUV", "1"), rule("EU", "2")]
    store.save()
    assert [r["pattern"] for r in PronunciationStore().rules] == ["EUV", "EU"]


def test_store_file_json_hong_thi_chay_khong_tu_dien():
    store = PronunciationStore()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{ broken json", encoding="utf-8")
    assert PronunciationStore().rules == []


def test_store_bo_qua_muc_khong_hop_le():
    store = PronunciationStore()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        '[{"pattern": "ok", "replace": "x"}, {"replace": "thieu pattern"}, 42]',
        encoding="utf-8")
    rules = PronunciationStore().rules
    assert len(rules) == 1
    assert rules[0]["pattern"] == "ok"
    assert rules[0]["enabled"] is True      # mặc định khi thiếu khóa


def test_store_chua_co_file_thi_rong():
    assert PronunciationStore().rules == []
