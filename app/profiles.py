# -*- coding: utf-8 -*-
"""Voice profiles — lưu/nạp hồ sơ giọng (ref audio + prompt) vào profiles.json."""

import json
from typing import Optional

from app.settings import config_dir


class VoiceProfile:
    def __init__(self, name: str, ref_audio_path: str, prompt_text: str,
                 prompt_lang: str, aux_ref_audio_paths: Optional[list] = None):
        self.name = name
        self.ref_audio_path = ref_audio_path
        self.prompt_text = prompt_text
        self.prompt_lang = prompt_lang
        self.aux_ref_audio_paths = aux_ref_audio_paths or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ref_audio_path": self.ref_audio_path,
            "prompt_text": self.prompt_text,
            "prompt_lang": self.prompt_lang,
            "aux_ref_audio_paths": self.aux_ref_audio_paths,
        }

    @staticmethod
    def from_dict(d: dict) -> "VoiceProfile":
        return VoiceProfile(
            name=d.get("name", ""),
            ref_audio_path=d.get("ref_audio_path", ""),
            prompt_text=d.get("prompt_text", ""),
            prompt_lang=d.get("prompt_lang", "ja"),
            aux_ref_audio_paths=d.get("aux_ref_audio_paths", []),
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
