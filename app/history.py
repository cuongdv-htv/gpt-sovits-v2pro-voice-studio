# -*- coding: utf-8 -*-
"""Lịch sử kết quả qua các phiên — lưu danh sách thư mục vào results_history.json."""

import json

from app.settings import config_dir

MAX_ENTRIES = 200


def _path():
    return config_dir() / "results_history.json"


def load_history() -> list:
    """Trả về danh sách đường dẫn thư mục kết quả (cũ → mới)."""
    try:
        with open(_path(), "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return [d for d in data if isinstance(d, str)]
    except Exception:
        return []


def append_history(out_dir: str):
    dirs = load_history()
    if out_dir in dirs:
        dirs.remove(out_dir)
    dirs.append(out_dir)
    dirs = dirs[-MAX_ENTRIES:]
    try:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(dirs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
