# -*- coding: utf-8 -*-
"""Đọc/ghi settings.json — ghi nhớ toàn bộ cấu hình người dùng."""

import json
import os
from pathlib import Path

APP_DIR_NAME = "GPT-SoVITS-VoiceStudio"


def config_dir() -> Path:
    """Thư mục cấu hình ghi được kể cả khi đóng gói exe (dùng %APPDATA%)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


DEFAULTS = {
    "ui_lang": "vi",                    # vi | ja
    # Engine
    "engine_folder": "",
    "engine_python": "",                # để trống = tự dò runtime\python.exe
    "host": "127.0.0.1",
    "port": 9880,
    # Model
    "model_variant": "v2Pro",           # v2Pro | v2ProPlus
    "gpt_weights": "",
    "sovits_weights": "",
    # Voice
    "ref_audio_path": "",
    "prompt_text": "",
    "prompt_lang": "ja",
    "aux_ref_audio_paths": [],
    # Synthesis
    "text_lang": "auto",
    "speed_factor": 1.0,
    "text_split_method": "cut5",
    "batch_size": 1,
    "top_k": 15,
    "top_p": 1.0,
    "temperature": 1.0,
    "repetition_penalty": 1.35,
    "fragment_interval": 0.3,
    "seed": -1,
    # Output
    "output_base": str(Path.home() / "Documents" / "VoiceStudioOutput"),
    "export_mp3": False,
}


class Settings:
    def __init__(self):
        self.path = config_dir() / "settings.json"
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            if self.path.exists():
                # utf-8-sig: chịu được BOM nếu file bị công cụ khác ghi kèm BOM
                with open(self.path, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                for k, v in loaded.items():
                    if k in DEFAULTS:
                        self.data[k] = v
        except Exception:
            # File hỏng → dùng mặc định, không làm sập app
            self.data = dict(DEFAULTS)

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        self.data[key] = value

    def update(self, **kwargs):
        self.data.update(kwargs)
