# -*- coding: utf-8 -*-
"""Ghi kết quả: mỗi đầu vào → MỘT thư mục riêng {YYYYMMDD_HHMMSS}_{tên}.

Bên trong: output.wav (nguyên bytes API trả về — KHÔNG hard-code sample rate),
output.mp3 (tùy chọn), input.txt, ref_used.wav, meta.json.
"""

import io
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_name(name: str, max_len: int = 60) -> str:
    """Làm sạch tên cho thư mục Windows."""
    name = INVALID_WIN_CHARS.sub("_", name).strip(" .")
    name = re.sub(r"\s+", "_", name)
    return (name[:max_len] or "untitled")


def create_output_dir(base: str, source_name: str) -> Path:
    """Tạo thư mục {timestamp}_{tên}; nếu trùng thì thêm hậu tố _2, _3…"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{ts}_{sanitize_name(source_name)}"
    base_path = Path(base)
    base_path.mkdir(parents=True, exist_ok=True)
    out = base_path / stem
    n = 2
    while out.exists():
        out = base_path / f"{stem}_{n}"
        n += 1
    out.mkdir(parents=True)
    return out


def _wav_duration_seconds(wav_bytes: bytes) -> Optional[float]:
    try:
        import soundfile as sf
        info = sf.info(io.BytesIO(wav_bytes))
        return round(info.frames / float(info.samplerate), 3)
    except Exception:
        return None


def _export_mp3(wav_bytes: bytes, mp3_path: Path) -> bool:
    """Xuất MP3 bằng pydub + ffmpeg của imageio-ffmpeg. Trả False nếu không xuất được."""
    try:
        import imageio_ffmpeg
        from pydub import AudioSegment
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = ffmpeg_exe
        AudioSegment.ffmpeg = ffmpeg_exe
        seg = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
        seg.export(str(mp3_path), format="mp3", bitrate="192k")
        return True
    except Exception:
        return False


def write_result(*, output_base: str, source_name: str, wav_bytes: bytes,
                 text: str, ref_audio_path: str, meta: dict,
                 export_mp3: bool = False,
                 srt_text: Optional[str] = None) -> Path:
    """Ghi trọn bộ kết quả cho một đầu vào. Trả về đường dẫn thư mục đã tạo."""
    out_dir = create_output_dir(output_base, source_name)

    # 1. Audio kết quả — ghi nguyên bytes
    (out_dir / "output.wav").write_bytes(wav_bytes)

    # 2. MP3 tùy chọn
    mp3_ok = False
    if export_mp3:
        mp3_ok = _export_mp3(wav_bytes, out_dir / "output.mp3")

    # 2b. Phụ đề SRT tùy chọn
    if srt_text:
        (out_dir / "output.srt").write_text(srt_text, encoding="utf-8")

    # 3. Văn bản nguồn
    (out_dir / "input.txt").write_text(text, encoding="utf-8")

    # 4. Bản sao audio mẫu đã dùng
    ref_copy = None
    try:
        src = Path(ref_audio_path)
        if src.is_file():
            ref_copy = out_dir / f"ref_used{src.suffix.lower() or '.wav'}"
            shutil.copy2(src, ref_copy)
    except Exception:
        ref_copy = None

    # 5. meta.json
    full_meta = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source_name": source_name,
        "output_dir": str(out_dir),
        "duration_seconds": _wav_duration_seconds(wav_bytes),
        "ref_audio_original_path": ref_audio_path,
        "ref_audio_copied": str(ref_copy) if ref_copy else None,
        "mp3_exported": mp3_ok,
        "srt_exported": bool(srt_text),
        **meta,
    }
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(full_meta, f, ensure_ascii=False, indent=2)

    return out_dir
