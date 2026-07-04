# -*- coding: utf-8 -*-
"""Nhận diện các lỗi engine phổ biến → khóa i18n để hiện thông báo dễ hiểu.

Engine (GPT-SoVITS) hay trả lỗi nguyên văn tiếng Trung hoặc traceback;
map các mẫu thường gặp về thông báo song ngữ thân thiện. Không khớp mẫu
nào → trả None, UI hiển thị nguyên văn."""

import re
from typing import Optional

# (pattern, khóa i18n) — xét theo thứ tự, mẫu cụ thể đặt trước
_PATTERNS = [
    # Audio mẫu ngoài 3–10 giây (lỗi phổ biến nhất)
    (re.compile(r"3~10|3-10|范围外|参考音频"), "err_ref_duration"),
    # Hết VRAM
    (re.compile(r"out of memory|OutOfMemory|CUDA error", re.IGNORECASE), "msg_vram"),
    # Engine chết / không kết nối được
    (re.compile(r"Engine không phản hồi|応答なし|Connection(Error| refused)|"
                r"RemoteDisconnected|Max retries", re.IGNORECASE), "engine_not_ready_msg"),
    # Ngôn ngữ không hỗ trợ
    (re.compile(r"text_lang|prompt_lang.*(not|不支持|unsupported)|"
                r"(not|不支持|unsupported).*(text_lang|prompt_lang)",
                re.IGNORECASE), "msg_lang_unsupported"),
]


def classify_error(raw: str) -> Optional[str]:
    """Trả về khóa i18n cho lỗi quen thuộc, hoặc None nếu không nhận ra."""
    if not raw:
        return None
    for pattern, key in _PATTERNS:
        if pattern.search(raw):
            return key
    return None
