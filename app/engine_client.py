# -*- coding: utf-8 -*-
"""HTTP client gọi api_v2.py của GPT-SoVITS (POST /tts, /set_*_weights, /control)."""

import time
from typing import Optional

import requests


class EngineError(RuntimeError):
    """Lỗi từ engine, message đã ở dạng đọc được."""


class GptSovitsClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9880):
        self.host = host
        self.port = int(port)

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_alive(self) -> bool:
        """Server sống là đủ; /tts thiếu tham số trả 400 nhưng chứng tỏ đã chạy."""
        try:
            requests.get(f"{self.base}/tts", timeout=3)
            return True
        except requests.exceptions.RequestException:
            return False

    def wait_ready(self, timeout: float = 300, poll: float = 2.0,
                   should_abort=None) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout:
            if should_abort is not None and should_abort():
                return False
            if self.is_alive():
                return True
            time.sleep(poll)
        return False

    def set_gpt_weights(self, ckpt_path: str):
        r = requests.get(f"{self.base}/set_gpt_weights",
                         params={"weights_path": ckpt_path}, timeout=300)
        if r.status_code != 200:
            raise EngineError(self._err_msg(r, "set_gpt_weights failed"))

    def set_sovits_weights(self, pth_path: str):
        r = requests.get(f"{self.base}/set_sovits_weights",
                         params={"weights_path": pth_path}, timeout=300)
        if r.status_code != 200:
            raise EngineError(self._err_msg(r, "set_sovits_weights failed"))

    def control(self, command: str):
        """command: restart | exit"""
        try:
            requests.get(f"{self.base}/control",
                         params={"command": command}, timeout=5)
        except requests.exceptions.RequestException:
            pass  # server thoát ngay nên connection có thể đứt — bình thường

    def tts(self, *, text: str, text_lang: str, ref_audio_path: str,
            prompt_text: str = "", prompt_lang: str = "ja",
            aux_ref_audio_paths: Optional[list] = None,
            speed_factor: float = 1.0, text_split_method: str = "cut5",
            batch_size: int = 1, top_k: int = 15, top_p: float = 1.0,
            temperature: float = 1.0, repetition_penalty: float = 1.35,
            fragment_interval: float = 0.3, seed: int = -1,
            media_type: str = "wav", timeout: float = 600) -> bytes:
        """Trả về audio bytes (wav) nếu thành công; ném EngineError nếu thất bại."""
        payload = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "aux_ref_audio_paths": aux_ref_audio_paths or [],
            "speed_factor": float(speed_factor),
            "text_split_method": text_split_method,
            "batch_size": int(batch_size),
            "top_k": int(top_k),
            "top_p": float(top_p),
            "temperature": float(temperature),
            "repetition_penalty": float(repetition_penalty),
            "fragment_interval": float(fragment_interval),
            "seed": int(seed),
            "media_type": media_type,
            "streaming_mode": False,
        }
        try:
            r = requests.post(f"{self.base}/tts", json=payload, timeout=timeout)
        except requests.exceptions.ConnectionError as e:
            raise EngineError(f"Engine không phản hồi / エンジン応答なし ({e.__class__.__name__})")
        except requests.exceptions.Timeout:
            raise EngineError("Engine timeout (văn bản quá dài hoặc máy quá chậm / テキストが長すぎるか処理が遅すぎます)")

        if r.status_code != 200:
            raise EngineError(self._err_msg(r, "TTS failed"))
        return r.content  # audio bytes — GHI NGUYÊN, không hard-code sample rate

    @staticmethod
    def _err_msg(r, fallback: str) -> str:
        try:
            j = r.json()
            parts = [str(j[k]) for k in ("message", "Exception", "exception")
                     if j.get(k)]
            return " | ".join(parts) or str(j) or fallback
        except Exception:
            return f"{fallback} (HTTP {r.status_code})"
