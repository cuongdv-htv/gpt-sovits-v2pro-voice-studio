# -*- coding: utf-8 -*-
"""Hậu xử lý audio: ghép file + khoảng lặng, chuẩn hóa loudness (ffmpeg),
tách câu, sinh phụ đề SRT, đọc audio đa định dạng.

Không hard-code sample rate — luôn lấy từ dữ liệu thực tế.
"""

import io
import os
import re
import subprocess
import tempfile
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ---------------------------------------------------------------- đọc/ghi
def load_audio_any(path: str) -> Tuple[np.ndarray, int]:
    """Đọc wav/flac/ogg qua soundfile; mp3/m4a... fallback qua ffmpeg (pydub).
    Trả về (float32 array shape (n, channels), samplerate)."""
    try:
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        return data, int(sr)
    except Exception:
        import imageio_ffmpeg
        from pydub import AudioSegment
        AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
        seg = AudioSegment.from_file(path)
        arr = np.array(seg.get_array_of_samples(), dtype="float32")
        arr /= float(1 << (8 * seg.sample_width - 1))
        arr = arr.reshape(-1, seg.channels)
        return arr, int(seg.frame_rate)


def wav_bytes_to_array(wav_bytes: bytes) -> Tuple[np.ndarray, int]:
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32", always_2d=True)
    return data, int(sr)


def array_to_wav_bytes(data: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def wav_duration(wav_bytes: bytes) -> float:
    info = sf.info(io.BytesIO(wav_bytes))
    return info.frames / float(info.samplerate)


# ---------------------------------------------------------------- ghép
def concat_with_silence(wav_list: List[bytes], gap_seconds: float) -> bytes:
    """Ghép nhiều WAV (cùng sample rate — cùng ra từ một engine) thành một,
    chèn khoảng lặng gap_seconds giữa các đoạn."""
    if not wav_list:
        raise ValueError("empty wav list")
    parts = []
    sr = None
    channels = None
    for b in wav_list:
        data, s = wav_bytes_to_array(b)
        if sr is None:
            sr, channels = s, data.shape[1]
        elif s != sr:
            raise ValueError(f"sample rate mismatch: {s} != {sr}")
        if data.shape[1] != channels:
            data = data.mean(axis=1, keepdims=True).repeat(channels, axis=1)
        parts.append(data)
    silence = np.zeros((max(0, int(round(gap_seconds * sr))), channels),
                       dtype="float32")
    chunks = []
    for i, p in enumerate(parts):
        if i > 0 and len(silence):
            chunks.append(silence)
        chunks.append(p)
    return array_to_wav_bytes(np.vstack(chunks), sr)


# ---------------------------------------------------------------- loudness
def normalize_loudness(wav_bytes: bytes, target_lufs: float = -14.0,
                       true_peak: float = -1.5, lra: float = 11.0) -> bytes:
    """Chuẩn hóa loudness theo EBU R128 / ITU BS.1770 bằng ffmpeg loudnorm.
    Giữ nguyên sample rate gốc (loudnorm nội bộ resample 192k → ép -ar về gốc).
    Lỗi ffmpeg → ném RuntimeError (caller quyết định bỏ qua hay báo)."""
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    info = sf.info(io.BytesIO(wav_bytes))
    sr = int(info.samplerate)

    fin = fout = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            fin = f.name
        fout = fin[:-4] + "_norm.wav"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-i", fin,
               "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}",
               "-ar", str(sr), "-c:a", "pcm_s16le", fout]
        r = subprocess.run(cmd, capture_output=True,
                           creationflags=CREATE_NO_WINDOW, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(
                f"ffmpeg loudnorm failed: {r.stderr.decode(errors='replace')[:300]}")
        with open(fout, "rb") as f:
            return f.read()
    finally:
        for p in (fin, fout):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


# ---------------------------------------------------------------- tách câu
# Câu kết thúc bằng 。．.！!？?… hoặc xuống dòng. Đơn giản, đủ dùng cho SRT;
# số thập phân kiểu "3.14" có thể bị tách — ghi chú trong tài liệu.
_SENT_RE = re.compile(r"[^。．！？!?…\n\.]+[。．！？!?…\.]*")
_HAS_CONTENT = re.compile(r"[0-9A-Za-zÀ-ɏЀ-ӿ"
                          r"぀-ヿ㐀-䶿一-鿿"
                          r"가-힯]")


def split_sentences(text: str) -> List[str]:
    """Tách văn bản thành danh sách câu (giữ dấu câu cuối)."""
    out = []
    for line in text.splitlines():
        for m in _SENT_RE.findall(line):
            s = m.strip()
            if s and _HAS_CONTENT.search(s):
                out.append(s)
    return out


# ---------------------------------------------------------------- SRT
def sec_to_srt_time(t: float) -> str:
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(entries: List[Tuple[float, float, str]]) -> str:
    """entries: [(start_sec, end_sec, text), ...] → nội dung file .srt"""
    lines = []
    for i, (start, end, text) in enumerate(entries, 1):
        lines.append(str(i))
        lines.append(f"{sec_to_srt_time(start)} --> {sec_to_srt_time(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def offset_srt_entries(entries: List[Tuple[float, float, str]],
                       offset: float) -> List[Tuple[float, float, str]]:
    return [(s + offset, e + offset, t) for s, e, t in entries]
