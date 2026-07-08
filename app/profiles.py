# -*- coding: utf-8 -*-
"""Voice profiles — lưu/nạp hồ sơ giọng (ref audio + prompt) vào profiles.json."""

import json
import re
import shutil
from pathlib import Path
from typing import Optional

from app.settings import config_dir

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Tham số tổng hợp lưu kèm profile: giọng kể chuyện (chậm, temperature thấp)
# và giọng documentary (nhanh, dứt khoát) cần bộ số khác nhau.
#
# KHÔNG lưu `seed` (mỗi lần chạy nên khác) và `batch_size` (thuộc về phần cứng
# máy đang chạy, không thuộc về giọng).
PROFILE_PARAM_KEYS = {
    "speed_factor": float,
    "text_split_method": str,
    "top_k": int,
    "top_p": float,
    "temperature": float,
    "repetition_penalty": float,
    "fragment_interval": float,
}


def sanitize_params(raw) -> dict:
    """Chỉ giữ khóa hợp lệ, ép đúng kiểu. Giá trị rác → bỏ khóa đó."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, cast in PROFILE_PARAM_KEYS.items():
        if key in raw:
            try:
                out[key] = cast(raw[key])
            except (TypeError, ValueError):
                pass
    return out


def _voices_dir() -> Path:
    d = config_dir() / "voices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(name: str) -> str:
    return (_INVALID.sub("_", name).strip(" .") or "voice")[:60]


def store_voice_files(profile_name: str, ref_audio_path: str,
                      aux_paths: list) -> tuple:
    """Copy audio mẫu (+ audio phụ) vào thư mục app để profile không chết
    khi người dùng di chuyển/xóa file gốc.

    Trả về (ref_mới, [aux_mới]); file nào copy lỗi thì giữ đường dẫn cũ."""
    dest = _voices_dir() / _safe_name(profile_name)
    dest.mkdir(parents=True, exist_ok=True)

    def _copy(src_str: str, stem: str) -> str:
        try:
            src = Path(src_str)
            if not src.is_file():
                return src_str
            if dest in src.parents:      # đã nằm trong kho app → khỏi copy
                return src_str
            target = dest / f"{stem}{src.suffix.lower() or '.wav'}"
            shutil.copy2(src, target)
            return str(target)
        except Exception:
            return src_str

    new_ref = _copy(ref_audio_path, "ref") if ref_audio_path else ""
    new_aux = [_copy(p, f"aux{i + 1}") for i, p in enumerate(aux_paths or [])]
    return new_ref, new_aux


def delete_voice_files(profile_name: str):
    """Xóa thư mục audio đã copy của profile (nếu có)."""
    try:
        d = _voices_dir() / _safe_name(profile_name)
        if d.is_dir():
            shutil.rmtree(d)
    except Exception:
        pass


class VoiceProfile:
    def __init__(self, name: str, ref_audio_path: str, prompt_text: str,
                 prompt_lang: str, aux_ref_audio_paths: Optional[list] = None,
                 params: Optional[dict] = None):
        self.name = name
        self.ref_audio_path = ref_audio_path
        self.prompt_text = prompt_text
        self.prompt_lang = prompt_lang
        self.aux_ref_audio_paths = aux_ref_audio_paths or []
        # {} = profile cũ, không có tham số → giữ nguyên cài đặt hiện tại
        self.params = sanitize_params(params)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "ref_audio_path": self.ref_audio_path,
            "prompt_text": self.prompt_text,
            "prompt_lang": self.prompt_lang,
            "aux_ref_audio_paths": self.aux_ref_audio_paths,
        }
        if self.params:            # profile không có tham số thì khỏi ghi khóa
            d["params"] = self.params
        return d

    @staticmethod
    def from_dict(d: dict) -> "VoiceProfile":
        return VoiceProfile(
            name=d.get("name", ""),
            ref_audio_path=d.get("ref_audio_path", ""),
            prompt_text=d.get("prompt_text", ""),
            prompt_lang=d.get("prompt_lang", "ja"),
            aux_ref_audio_paths=d.get("aux_ref_audio_paths", []),
            params=d.get("params"),
        )


class ProfileStore:
    def __init__(self):
        self.path = config_dir() / "profiles.json"
        self.profiles: list[VoiceProfile] = []
        self.load()

    def load(self):
        self.profiles = []
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as f:
                    for d in json.load(f):
                        p = VoiceProfile.from_dict(d)
                        if p.name:
                            self.profiles.append(p)
        except Exception:
            self.profiles = []

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump([p.to_dict() for p in self.profiles], f,
                          ensure_ascii=False, indent=2)
        except Exception:
            pass

    def names(self) -> list:
        return [p.name for p in self.profiles]

    def get(self, name: str) -> Optional[VoiceProfile]:
        for p in self.profiles:
            if p.name == name:
                return p
        return None

    def upsert(self, profile: VoiceProfile):
        for i, p in enumerate(self.profiles):
            if p.name == profile.name:
                self.profiles[i] = profile
                self.save()
                return
        self.profiles.append(profile)
        self.save()

    def delete(self, name: str):
        self.profiles = [p for p in self.profiles if p.name != name]
        self.save()
