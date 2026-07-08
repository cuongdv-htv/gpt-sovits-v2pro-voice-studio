# -*- coding: utf-8 -*-
"""Ghép nhiều mục thành một audiobook: merged.wav + chapters.txt (+ srt/mp3).

Dùng chung cho GUI (BatchWorker) và CLI — trước đây hai nơi có bản sao riêng
và đã lệch nhau (CLI không ghi meta.json).

Nhận ĐƯỜNG DẪN wav của từng mục (mỗi mục đã được ghi ra đĩa trước đó), không
nhận bytes: audiobook dài hàng giờ không được phép nằm hết trong RAM.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple

from app.audio_post import (build_chapters, build_srt, concat_files_to_wav,
                            offset_srt_entries, wav_duration_file)
from app.output_writer import create_output_dir, export_mp3_file

# Một phần của audiobook: (tên mục, đường dẫn wav, srt entries | None)
AudiobookPart = Tuple[str, str, Optional[list]]


def write_audiobook(*, output_base: str, parts: List[AudiobookPart],
                    gap: float, export_srt: bool = False,
                    export_mp3: bool = False,
                    loudness_normalized: bool = False) -> Tuple[Path, dict]:
    """Ghép `parts` theo thứ tự, ghi ra thư mục `{timestamp}_audiobook`.

    `chapters.txt` LUÔN được ghi (mốc thời gian từng mục, dán vào mô tả
    YouTube). `merged.srt` chỉ khi bật SRT và MỌI mục đều có entries —
    thiếu một mục thì phụ đề gộp sẽ lệch, thà không ghi còn hơn ghi sai.

    Trả về (thư mục kết quả, meta đã ghi)."""
    if not parts:
        raise ValueError("empty parts")
    gap = float(gap)

    out_dir = create_output_dir(output_base, "audiobook")
    merged_path = out_dir / "merged.wav"
    total = concat_files_to_wav([p for _, p, _ in parts], gap, merged_path)

    srt_ok = bool(export_srt) and all(e is not None for _, _, e in parts)
    chapters: list = []
    all_entries: list = []
    offset = 0.0
    for name, wav_path, entries in parts:
        chapters.append((name, offset))
        if srt_ok:
            all_entries.extend(offset_srt_entries(entries, offset))
        offset += wav_duration_file(wav_path) + gap

    (out_dir / "chapters.txt").write_text(build_chapters(chapters),
                                          encoding="utf-8")
    if srt_ok:
        (out_dir / "merged.srt").write_text(build_srt(all_entries),
                                            encoding="utf-8")
    if export_mp3:
        export_mp3_file(merged_path, out_dir / "merged.mp3")

    meta = {
        "type": "audiobook",
        "parts": [name for name, _, _ in parts],
        "chapters": [{"name": n, "start_seconds": round(s, 3)}
                     for n, s in chapters],
        "gap_seconds": gap,
        "duration_seconds": round(total, 3),
        "loudness_normalized": loudness_normalized,
        "srt_included": srt_ok,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return out_dir, meta
