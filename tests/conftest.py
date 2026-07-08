# -*- coding: utf-8 -*-
"""Fixture dùng chung. Không test nào được chạm vào %APPDATA% thật."""

import io
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Chuyển %APPDATA% sang thư mục tạm cho MỌI test.

    `settings.config_dir()` đọc biến môi trường mỗi lần gọi, nên mọi store
    (settings/profiles/pronunciation/history) tự động trỏ vào tmp_path.
    Thiếu fixture này, một test lỡ gọi save() sẽ ghi đè cấu hình người dùng."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return tmp_path


def make_wav(seconds: float = 1.0, sr: int = 32000, channels: int = 1,
             freq: float = 0.05) -> bytes:
    """WAV bytes hợp lệ để đẩy qua các hàm xử lý audio."""
    n = int(seconds * sr)
    data = (np.sin(np.arange(n) * freq) * 0.3).astype("float32")
    if channels > 1:
        data = np.repeat(data[:, None], channels, axis=1)
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class FakeClient:
    """Engine giả. Câu chứa BOOM luôn hỏng; FLAKY hỏng `flaky_fails` lần đầu.

    `seen` giữ đúng chuỗi đã gửi tới engine — dùng để khẳng định từ điển
    phát âm chỉ tác động lên chuỗi gửi đi, không lên văn bản gốc."""

    def __init__(self, flaky_fails: int = 2, wav_seconds: float = 1.0):
        self.seen: list[str] = []
        self.flaky_fails = flaky_fails
        self._flaky_seen = 0
        self.wav_seconds = wav_seconds

    def tts(self, *, text, **_kwargs):
        from app.engine_client import EngineError
        self.seen.append(text)
        if "BOOM" in text:
            raise EngineError("simulated permanent failure")
        if "FLAKY" in text:
            self._flaky_seen += 1
            if self._flaky_seen <= self.flaky_fails:
                raise EngineError("simulated transient failure")
        return make_wav(self.wav_seconds)


@pytest.fixture
def fake_client():
    return FakeClient()


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch):
    """Bỏ `time.sleep` giữa các lần retry — 14 lần retry × 1s làm test ì ạch."""
    monkeypatch.setattr("app.worker.RETRY_DELAY_SEC", 0)


def rule(pattern, replace, regex=False, enabled=True) -> dict:
    return {"pattern": pattern, "replace": replace,
            "regex": regex, "enabled": enabled}
