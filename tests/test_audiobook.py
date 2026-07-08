# -*- coding: utf-8 -*-
"""audiobook.write_audiobook — đường ghép chung của GUI và CLI.

Nhận đường dẫn wav (không phải bytes) và ghép streaming ra đĩa.
"""

import json

import pytest

from app.audio_post import concat_files_to_wav, wav_duration_file
from app.audiobook import write_audiobook
from tests.conftest import make_wav


def wav_file(tmp_path, name: str, seconds: float, sr: int = 32000,
             channels: int = 1) -> str:
    p = tmp_path / name
    p.write_bytes(make_wav(seconds, sr=sr, channels=channels))
    return str(p)


@pytest.fixture
def parts_srt(tmp_path):
    return [
        ("chuong_1", wav_file(tmp_path, "a.wav", 2.0), [(0.0, 2.0, "câu một")]),
        ("chuong_2", wav_file(tmp_path, "b.wav", 3.0), [(0.0, 3.0, "câu hai")]),
    ]


@pytest.fixture
def parts_plain(tmp_path):
    return [("chuong_1", wav_file(tmp_path, "a.wav", 2.0), None),
            ("chuong_2", wav_file(tmp_path, "b.wav", 3.0), None)]


# ------------------------------------------------------- concat_files_to_wav
def test_concat_files_cong_don_thoi_luong(tmp_path):
    out = tmp_path / "merged.wav"
    total = concat_files_to_wav(
        [wav_file(tmp_path, "a.wav", 1.0), wav_file(tmp_path, "b.wav", 2.0)],
        gap_seconds=0.5, out_path=out)
    assert total == pytest.approx(3.5, abs=0.01)
    assert wav_duration_file(out) == pytest.approx(3.5, abs=0.01)


def test_concat_files_khong_chen_lang_dau_cuoi(tmp_path):
    out = tmp_path / "m.wav"
    total = concat_files_to_wav([wav_file(tmp_path, "a.wav", 1.0)],
                                gap_seconds=5.0, out_path=out)
    assert total == pytest.approx(1.0, abs=0.01)


def test_concat_files_lech_sample_rate_thi_nem_loi(tmp_path):
    with pytest.raises(ValueError, match="sample rate mismatch"):
        concat_files_to_wav(
            [wav_file(tmp_path, "a.wav", 1.0, sr=32000),
             wav_file(tmp_path, "b.wav", 1.0, sr=44100)],
            gap_seconds=0.0, out_path=tmp_path / "m.wav")


def test_concat_files_rong_thi_nem_loi(tmp_path):
    with pytest.raises(ValueError):
        concat_files_to_wav([], gap_seconds=0.0, out_path=tmp_path / "m.wav")


def test_concat_files_stereo_va_mono(tmp_path):
    out = tmp_path / "m.wav"
    total = concat_files_to_wav(
        [wav_file(tmp_path, "a.wav", 1.0, channels=2),
         wav_file(tmp_path, "b.wav", 1.0, channels=1)],
        gap_seconds=0.0, out_path=out)
    assert total == pytest.approx(2.0, abs=0.01)


def test_concat_files_file_dai_hon_mot_block(tmp_path):
    """blocksize=65536 → file 3s @32kHz (96000 frame) đi qua nhiều block."""
    out = tmp_path / "m.wav"
    total = concat_files_to_wav([wav_file(tmp_path, "a.wav", 3.0)],
                                gap_seconds=0.0, out_path=out)
    assert total == pytest.approx(3.0, abs=0.01)


# ------------------------------------------------------- write_audiobook
def test_ghep_dung_thoi_luong(tmp_path, parts_srt):
    out, meta = write_audiobook(output_base=str(tmp_path / "o"),
                                parts=parts_srt, gap=1.0)
    assert wav_duration_file(out / "merged.wav") == pytest.approx(6.0, abs=0.01)
    assert meta["duration_seconds"] == pytest.approx(6.0, abs=0.01)


def test_chapters_luon_duoc_ghi_ke_ca_khi_khong_co_srt(tmp_path, parts_plain):
    out, _ = write_audiobook(output_base=str(tmp_path / "o"),
                             parts=parts_plain, gap=1.0)
    assert (out / "chapters.txt").read_text(encoding="utf-8") == \
        "0:00 chuong_1\n0:03 chuong_2\n"


def test_meta_json_luon_duoc_ghi(tmp_path, parts_plain):
    """CLI trước đây KHÔNG ghi meta.json cho audiobook — lệch với GUI."""
    out, _ = write_audiobook(output_base=str(tmp_path / "o"),
                             parts=parts_plain, gap=0.5)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["type"] == "audiobook"
    assert meta["parts"] == ["chuong_1", "chuong_2"]
    assert meta["chapters"] == [
        {"name": "chuong_1", "start_seconds": 0.0},
        {"name": "chuong_2", "start_seconds": 2.5},
    ]
    assert meta["gap_seconds"] == 0.5
    assert meta["srt_included"] is False


def test_srt_gop_duoc_dich_timestamp(tmp_path, parts_srt):
    out, meta = write_audiobook(output_base=str(tmp_path / "o"),
                                parts=parts_srt, gap=1.0, export_srt=True)
    srt = (out / "merged.srt").read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "00:00:03,000 --> 00:00:06,000" in srt
    assert meta["srt_included"] is True


def test_thieu_entries_o_mot_muc_thi_khong_ghi_srt(tmp_path):
    parts = [("a", wav_file(tmp_path, "a.wav", 1.0), [(0.0, 1.0, "x")]),
             ("b", wav_file(tmp_path, "b.wav", 1.0), None)]
    out, meta = write_audiobook(output_base=str(tmp_path / "o"), parts=parts,
                                gap=0.0, export_srt=True)
    assert not (out / "merged.srt").exists()
    assert meta["srt_included"] is False
    assert (out / "chapters.txt").exists()


def test_khong_bat_srt_thi_khong_ghi_du_co_entries(tmp_path, parts_srt):
    out, meta = write_audiobook(output_base=str(tmp_path / "o"),
                                parts=parts_srt, gap=0.0, export_srt=False)
    assert not (out / "merged.srt").exists()
    assert meta["srt_included"] is False


def test_mot_muc_duy_nhat(tmp_path):
    out, _ = write_audiobook(
        output_base=str(tmp_path / "o"),
        parts=[("solo", wav_file(tmp_path, "a.wav", 1.0), None)], gap=5.0)
    assert wav_duration_file(out / "merged.wav") == pytest.approx(1.0, abs=0.01)
    assert (out / "chapters.txt").read_text(encoding="utf-8") == "0:00 solo\n"


def test_parts_rong_thi_nem_loi(tmp_path):
    with pytest.raises(ValueError):
        write_audiobook(output_base=str(tmp_path / "o"), parts=[], gap=1.0)


def test_co_ghi_nhan_loudness(tmp_path, parts_plain):
    _out, meta = write_audiobook(output_base=str(tmp_path / "o"),
                                 parts=parts_plain, gap=0.0,
                                 loudness_normalized=True)
    assert meta["loudness_normalized"] is True


def test_lech_sample_rate_nem_loi_va_khong_de_lai_file_hong(tmp_path):
    parts = [("a", wav_file(tmp_path, "a.wav", 1.0, sr=32000), None),
             ("b", wav_file(tmp_path, "b.wav", 1.0, sr=44100), None)]
    with pytest.raises(ValueError, match="sample rate mismatch"):
        write_audiobook(output_base=str(tmp_path / "o"), parts=parts, gap=0.0)
