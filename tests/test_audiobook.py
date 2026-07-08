# -*- coding: utf-8 -*-
"""audiobook.write_audiobook — đường ghép chung của GUI và CLI."""

import json

import pytest

from app.audio_post import wav_duration
from app.audiobook import write_audiobook
from tests.conftest import make_wav


def parts_with_srt():
    return [
        ("chuong_1", make_wav(2.0), [(0.0, 2.0, "câu một")]),
        ("chuong_2", make_wav(3.0), [(0.0, 3.0, "câu hai")]),
    ]


def parts_without_srt():
    return [("chuong_1", make_wav(2.0), None),
            ("chuong_2", make_wav(3.0), None)]


def test_ghep_dung_thoi_luong(tmp_path):
    out, meta = write_audiobook(output_base=str(tmp_path), parts=parts_with_srt(),
                                gap=1.0)
    assert wav_duration((out / "merged.wav").read_bytes()) == \
        pytest.approx(6.0, abs=0.01)                      # 2 + 1 + 3
    assert meta["duration_seconds"] == pytest.approx(6.0, abs=0.01)


def test_chapters_luon_duoc_ghi_ke_ca_khi_khong_co_srt(tmp_path):
    out, _ = write_audiobook(output_base=str(tmp_path),
                             parts=parts_without_srt(), gap=1.0)
    assert (out / "chapters.txt").read_text(encoding="utf-8") == \
        "0:00 chuong_1\n0:03 chuong_2\n"                  # 2.0 + gap 1.0


def test_meta_json_luon_duoc_ghi(tmp_path):
    """CLI trước đây KHÔNG ghi meta.json cho audiobook — lệch với GUI."""
    out, _ = write_audiobook(output_base=str(tmp_path),
                             parts=parts_without_srt(), gap=0.5)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["type"] == "audiobook"
    assert meta["parts"] == ["chuong_1", "chuong_2"]
    assert meta["chapters"] == [
        {"name": "chuong_1", "start_seconds": 0.0},
        {"name": "chuong_2", "start_seconds": 2.5},
    ]
    assert meta["gap_seconds"] == 0.5
    assert meta["srt_included"] is False


def test_srt_gop_duoc_dich_timestamp(tmp_path):
    out, meta = write_audiobook(output_base=str(tmp_path), parts=parts_with_srt(),
                                gap=1.0, export_srt=True)
    srt = (out / "merged.srt").read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:02,000" in srt        # chương 1
    assert "00:00:03,000 --> 00:00:06,000" in srt        # chương 2 dịch +3s
    assert meta["srt_included"] is True


def test_thieu_entries_o_mot_muc_thi_khong_ghi_srt(tmp_path):
    """Phụ đề gộp thiếu một chương sẽ lệch — thà không ghi còn hơn ghi sai."""
    parts = [("a", make_wav(1.0), [(0.0, 1.0, "x")]),
             ("b", make_wav(1.0), None)]
    out, meta = write_audiobook(output_base=str(tmp_path), parts=parts,
                                gap=0.0, export_srt=True)
    assert not (out / "merged.srt").exists()
    assert meta["srt_included"] is False
    assert (out / "chapters.txt").exists()               # chapters vẫn ghi


def test_khong_bat_srt_thi_khong_ghi_du_co_entries(tmp_path):
    out, meta = write_audiobook(output_base=str(tmp_path), parts=parts_with_srt(),
                                gap=0.0, export_srt=False)
    assert not (out / "merged.srt").exists()
    assert meta["srt_included"] is False


def test_mot_muc_duy_nhat(tmp_path):
    out, _ = write_audiobook(output_base=str(tmp_path),
                             parts=[("solo", make_wav(1.0), None)], gap=5.0)
    assert wav_duration((out / "merged.wav").read_bytes()) == \
        pytest.approx(1.0, abs=0.01)                     # không đệm lặng
    assert (out / "chapters.txt").read_text(encoding="utf-8") == "0:00 solo\n"


def test_parts_rong_thi_nem_loi(tmp_path):
    with pytest.raises(ValueError):
        write_audiobook(output_base=str(tmp_path), parts=[], gap=1.0)


def test_co_ghi_nhan_loudness(tmp_path):
    _out, meta = write_audiobook(output_base=str(tmp_path),
                                 parts=parts_without_srt(), gap=0.0,
                                 loudness_normalized=True)
    assert meta["loudness_normalized"] is True
