# -*- coding: utf-8 -*-
"""audio_post: tách câu, SRT, chapters, ghép audio, đọc độ dài."""

import pytest

from app.audio_post import (REF_MAX_SEC, REF_MIN_SEC, audio_duration,
                            build_chapters, build_srt, concat_with_silence,
                            offset_srt_entries, sec_to_chapter_time,
                            sec_to_srt_time, split_sentences, wav_duration)
from tests.conftest import make_wav


# ------------------------------------------------------------- tách câu
def test_split_sentences_giu_dau_cau():
    assert split_sentences("こんにちは。元気ですか？") == \
        ["こんにちは。", "元気ですか？"]


def test_split_sentences_tach_theo_dong():
    assert split_sentences("dòng một\ndòng hai") == ["dòng một", "dòng hai"]


def test_split_sentences_bo_dong_chi_co_dau_cau():
    assert split_sentences("……\n!!!\nOK.") == ["OK."]


def test_split_sentences_van_ban_rong():
    assert split_sentences("   \n  ") == []


def test_split_sentences_tach_nham_so_thap_phan():
    """Hành vi ĐÃ BIẾT và có ghi tài liệu: dấu '.' của số thập phân bị coi là
    kết câu. Test này khóa hành vi lại — nếu sau này sửa, phải sửa cả docs."""
    assert split_sentences("Pi là 3.14 nhé.") == ["Pi là 3.", "14 nhé."]


# ------------------------------------------------------------- SRT
@pytest.mark.parametrize("secs,expected", [
    (0, "00:00:00,000"),
    (1.5, "00:00:01,500"),
    (61.25, "00:01:01,250"),
    (3661.007, "01:01:01,007"),
    (-5, "00:00:00,000"),          # thời điểm âm bị kẹp về 0
])
def test_sec_to_srt_time(secs, expected):
    assert sec_to_srt_time(secs) == expected


def test_build_srt_danh_so_tu_1():
    srt = build_srt([(0.0, 1.0, "một"), (1.5, 2.0, "hai")])
    assert srt == (
        "1\n00:00:00,000 --> 00:00:01,000\nmột\n\n"
        "2\n00:00:01,500 --> 00:00:02,000\nhai\n"
    )


def test_build_srt_rong():
    assert build_srt([]) == ""


def test_offset_srt_entries():
    assert offset_srt_entries([(1.0, 2.0, "x")], 10.0) == [(11.0, 12.0, "x")]


# ------------------------------------------------------------- chapters
@pytest.mark.parametrize("secs,expected", [
    (0, "0:00"),
    (65, "1:05"),
    (252.7, "4:12"),
    (3600, "1:00:00"),
    (3661.2, "1:01:01"),
])
def test_sec_to_chapter_time(secs, expected):
    assert sec_to_chapter_time(secs) == expected


def test_build_chapters_dinh_dang_youtube():
    assert build_chapters([("ch1", 0.0), ("ch2", 252.7), ("ch3", 3661.2)]) == \
        "0:00 ch1\n4:12 ch2\n1:01:01 ch3\n"


def test_build_chapters_moc_dau_luon_la_0():
    """YouTube từ chối danh sách chương nếu mốc đầu không phải 0:00."""
    assert build_chapters([("mở đầu", 9.9)]).startswith("0:00 ")


# ------------------------------------------------------------- ghép audio
def test_concat_with_silence_cong_don_thoi_luong():
    merged = concat_with_silence([make_wav(1.0), make_wav(2.0)], gap_seconds=0.5)
    assert wav_duration(merged) == pytest.approx(3.5, abs=0.01)


def test_concat_khong_chen_lang_o_dau_va_cuoi():
    merged = concat_with_silence([make_wav(1.0)], gap_seconds=5.0)
    assert wav_duration(merged) == pytest.approx(1.0, abs=0.01)


def test_concat_gap_bang_khong():
    merged = concat_with_silence([make_wav(1.0), make_wav(1.0)], gap_seconds=0)
    assert wav_duration(merged) == pytest.approx(2.0, abs=0.01)


def test_concat_lech_sample_rate_thi_nem_loi():
    """Thà hỏng to còn hơn ghép ra file tua nhanh/chậm."""
    with pytest.raises(ValueError, match="sample rate mismatch"):
        concat_with_silence([make_wav(1.0, sr=32000), make_wav(1.0, sr=44100)],
                            gap_seconds=0)


def test_concat_danh_sach_rong_thi_nem_loi():
    with pytest.raises(ValueError):
        concat_with_silence([], gap_seconds=0)


def test_concat_mono_va_stereo_van_ghep_duoc():
    merged = concat_with_silence(
        [make_wav(1.0, channels=2), make_wav(1.0, channels=1)], gap_seconds=0)
    assert wav_duration(merged) == pytest.approx(2.0, abs=0.01)


# ------------------------------------------------------------- độ dài file
def test_audio_duration_doc_dung(tmp_path):
    p = tmp_path / "a.wav"
    p.write_bytes(make_wav(7.46))
    d = audio_duration(str(p))
    assert d == pytest.approx(7.46, abs=0.01)
    assert REF_MIN_SEC <= d <= REF_MAX_SEC


def test_audio_duration_file_khong_phai_audio(tmp_path):
    p = tmp_path / "rac.txt"
    p.write_text("không phải audio", encoding="utf-8")
    assert audio_duration(str(p)) is None


def test_audio_duration_file_khong_ton_tai():
    assert audio_duration("D:/khong/ton/tai.wav") is None
