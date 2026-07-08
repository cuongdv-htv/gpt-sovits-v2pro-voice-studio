# -*- coding: utf-8 -*-
"""Từ điển phát âm — thay thế văn bản TRƯỚC khi gửi engine đọc.

Engine đọc sai/bỏ qua các từ viết tắt và số liệu (`TSMC`, `EUV`, `5G`,
`1,200億円`). Từ điển cho phép ép cách đọc mà KHÔNG đụng tới văn bản gốc:
phụ đề `.srt`, `input.txt` và bản kịch vẫn giữ nguyên chữ bạn viết —
chỉ chuỗi gửi tới `/tts` là đã được thay thế.

Quy tắc lưu ở `%APPDATA%\\GPT-SoVITS-VoiceStudio\\pronunciation.json`:
    [{"pattern": "TSMC", "replace": "ティーエスエムシー",
      "regex": false, "enabled": true}, ...]

Áp dụng TUẦN TỰ theo thứ tự trong danh sách — quy tắc trước ảnh hưởng đầu vào
của quy tắc sau. Vì vậy quy tắc cụ thể phải đặt TRƯỚC quy tắc tổng quát
(`EUV` trước `EU`, nếu không `EU` sẽ ăn mất phần đầu của `EUV`).
"""

import json
import re
from typing import List, Optional, Tuple

from app.settings import config_dir


def _path():
    return config_dir() / "pronunciation.json"


def valid_regex(pattern: str) -> Optional[str]:
    """None nếu regex hợp lệ; ngược lại trả về thông báo lỗi."""
    try:
        re.compile(pattern)
        return None
    except re.error as e:
        return str(e)


def _sub_once(text: str, rule: dict) -> str:
    """Áp một quy tắc. Regex hỏng → bỏ qua quy tắc đó (không làm sập batch)."""
    pattern = rule.get("pattern") or ""
    if not pattern:
        return text
    replace = rule.get("replace", "")
    if not rule.get("regex"):
        return text.replace(pattern, replace)
    try:
        return re.sub(pattern, replace, text)
    except re.error:
        return text


def apply_rules(text: str, rules: List[dict]) -> str:
    """Văn bản sau khi áp mọi quy tắc đang bật (dùng để GỬI engine)."""
    for rule in rules or []:
        if rule.get("enabled", True):
            text = _sub_once(text, rule)
    return text


def matching_rules(text: str, rules: List[dict]) -> List[str]:
    """Danh sách `pattern` của các quy tắc THỰC SỰ đổi được văn bản.

    Dùng để ghi vào meta.json — biết chính xác quy tắc nào đã tác động."""
    hits = []
    for rule in rules or []:
        if not rule.get("enabled", True):
            continue
        after = _sub_once(text, rule)
        if after != text:
            hits.append(rule.get("pattern", ""))
        text = after
    return hits


def preview(text: str, rules: List[dict]) -> Tuple[str, List[str]]:
    """(văn bản sau thay thế, danh sách pattern đã khớp) — cho ô thử trong UI."""
    return apply_rules(text, rules), matching_rules(text, rules)


class PronunciationStore:
    def __init__(self):
        self.path = _path()
        self.rules: List[dict] = []
        self.load()

    def load(self):
        self.rules = []
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                for d in data:
                    if isinstance(d, dict) and d.get("pattern"):
                        self.rules.append({
                            "pattern": str(d.get("pattern", "")),
                            "replace": str(d.get("replace", "")),
                            "regex": bool(d.get("regex", False)),
                            "enabled": bool(d.get("enabled", True)),
                        })
        except Exception:
            # File hỏng → chạy không từ điển, không làm sập app
            self.rules = []

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def enabled_rules(self) -> List[dict]:
        return [r for r in self.rules if r.get("enabled", True)]
