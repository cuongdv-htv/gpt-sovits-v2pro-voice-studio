# -*- coding: utf-8 -*-
"""Tự nhận dạng lời thoại audio mẫu bằng faster-whisper (tùy chọn, chạy CPU).

- Dependency tùy chọn: thiếu faster-whisper → báo 'missing', app vẫn chạy bình thường.
- Ưu tiên model đã tải sẵn tại <config>/whisper-small (tránh lỗi SSL khi
  hf-hub tự tải); không có thì để faster-whisper tự tải model "small".
"""

from PySide6.QtCore import QThread, Signal

from app.settings import config_dir

_MODEL = None  # cache model giữa các lần nhận dạng trong một phiên

# Whisper trả mã ngôn ngữ ISO — chỉ map các mã engine hỗ trợ làm prompt_lang
WHISPER_TO_PROMPT_LANG = {"ja": "ja", "en": "en", "zh": "zh", "ko": "ko", "yue": "yue"}


def _model_source() -> str:
    local = config_dir() / "whisper-small"
    if (local / "model.bin").is_file():
        return str(local)
    return "small"


class TranscribeWorker(QThread):
    """Nhận dạng ở thread nền. sig_done(ok, text, lang_hoặc_mã_lỗi).

    ok=False: lang_hoặc_mã_lỗi = "missing" (chưa cài faster-whisper)
              hoặc thông báo lỗi thực tế."""

    sig_done = Signal(bool, str, str)

    def __init__(self, audio_path: str, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path

    def run(self):
        global _MODEL
        try:
            from faster_whisper import WhisperModel
        except Exception:
            self.sig_done.emit(False, "", "missing")
            return
        try:
            if _MODEL is None:
                _MODEL = WhisperModel(_model_source(), device="cpu",
                                      compute_type="int8")
            segments, info = _MODEL.transcribe(self.audio_path, beam_size=5)
            text = "".join(seg.text for seg in segments).strip()
            lang = getattr(info, "language", "") or ""
            self.sig_done.emit(True, text, lang)
        except Exception as e:
            self.sig_done.emit(False, "", str(e))
