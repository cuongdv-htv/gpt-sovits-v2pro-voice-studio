# -*- coding: utf-8 -*-
"""Thread nền: chạy batch TTS + khởi động engine. UI KHÔNG bao giờ bị đơ."""

import random
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal

from app.engine_client import EngineError, GptSovitsClient
from app.output_writer import write_result


@dataclass
class QueueItem:
    """Một mục trong hàng đợi."""
    name: str                 # tên nguồn (tên file .txt hoặc "manual")
    text: str
    text_lang: str = "auto"
    status: str = "pending"   # pending | running | done | error | skipped
    error: str = ""
    output_dir: str = ""

    @property
    def chars(self) -> int:
        return len(self.text)


@dataclass
class TtsJobConfig:
    """Toàn bộ tham số dùng chung cho một lượt batch."""
    ref_audio_path: str = ""
    prompt_text: str = ""
    prompt_lang: str = "ja"
    aux_ref_audio_paths: list = field(default_factory=list)
    speed_factor: float = 1.0
    text_split_method: str = "cut5"
    batch_size: int = 1
    top_k: int = 15
    top_p: float = 1.0
    temperature: float = 1.0
    repetition_penalty: float = 1.35
    fragment_interval: float = 0.3
    seed: int = -1
    output_base: str = ""
    export_mp3: bool = False
    model_variant: str = "v2Pro"
    gpt_weights: str = ""
    sovits_weights: str = ""


class BatchWorker(QThread):
    """Xử lý tuần tự hàng đợi; 1 mục lỗi KHÔNG làm sập batch."""

    sig_item_started = Signal(int)              # index
    sig_item_finished = Signal(int, str, str)   # index, status, output_dir/error
    sig_item_progress = Signal(int)             # 0-100 cho mục hiện tại
    sig_total_progress = Signal(int, int)       # done, total
    sig_log = Signal(str)
    sig_batch_finished = Signal(int, int, bool) # ok, fail, cancelled

    def __init__(self, client: GptSovitsClient, items: list, cfg: TtsJobConfig,
                 parent=None):
        super().__init__(parent)
        self.client = client
        self.items: list[QueueItem] = items
        self.cfg = cfg
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        ok = fail = 0
        total = len(self.items)
        for i, item in enumerate(self.items):
            if self._cancel:
                break
            self.sig_item_started.emit(i)
            self.sig_item_progress.emit(0)

            if not item.text.strip():
                item.status = "skipped"
                self.sig_log.emit(f"⚠ skip (empty): {item.name}")
                self.sig_item_finished.emit(i, "skipped", "")
                self.sig_total_progress.emit(i + 1, total)
                continue

            # Seed thực tế: -1 → sinh ngẫu nhiên để tái lập được (ghi vào meta)
            actual_seed = self.cfg.seed
            if actual_seed is None or int(actual_seed) < 0:
                actual_seed = random.randint(0, 2**31 - 1)

            try:
                self.sig_item_progress.emit(15)
                self.sig_log.emit(f"▶ TTS [{item.text_lang}] {item.name} ({item.chars} chars)")
                wav = self.client.tts(
                    text=item.text,
                    text_lang=item.text_lang,
                    ref_audio_path=self.cfg.ref_audio_path,
                    prompt_text=self.cfg.prompt_text,
                    prompt_lang=self.cfg.prompt_lang,
                    aux_ref_audio_paths=self.cfg.aux_ref_audio_paths,
                    speed_factor=self.cfg.speed_factor,
                    text_split_method=self.cfg.text_split_method,
                    batch_size=self.cfg.batch_size,
                    top_k=self.cfg.top_k,
                    top_p=self.cfg.top_p,
                    temperature=self.cfg.temperature,
                    repetition_penalty=self.cfg.repetition_penalty,
                    fragment_interval=self.cfg.fragment_interval,
                    seed=actual_seed,
                    media_type="wav",
                )
                self.sig_item_progress.emit(80)

                meta = {
                    "text_lang": item.text_lang,
                    "prompt_text": self.cfg.prompt_text,
                    "prompt_lang": self.cfg.prompt_lang,
                    "aux_ref_audio_paths": self.cfg.aux_ref_audio_paths,
                    "model_variant": self.cfg.model_variant,
                    "gpt_weights": self.cfg.gpt_weights,
                    "sovits_weights": self.cfg.sovits_weights,
                    "speed_factor": self.cfg.speed_factor,
                    "text_split_method": self.cfg.text_split_method,
                    "batch_size": self.cfg.batch_size,
                    "top_k": self.cfg.top_k,
                    "top_p": self.cfg.top_p,
                    "temperature": self.cfg.temperature,
                    "repetition_penalty": self.cfg.repetition_penalty,
                    "fragment_interval": self.cfg.fragment_interval,
                    "seed_requested": self.cfg.seed,
                    "seed_actual": actual_seed,
                }
                out_dir = write_result(
                    output_base=self.cfg.output_base,
                    source_name=item.name,
                    wav_bytes=wav,
                    text=item.text,
                    ref_audio_path=self.cfg.ref_audio_path,
                    meta=meta,
                    export_mp3=self.cfg.export_mp3,
                )
                item.status = "done"
                item.output_dir = str(out_dir)
                ok += 1
                self.sig_item_progress.emit(100)
                self.sig_log.emit(f"✓ saved: {out_dir}")
                self.sig_item_finished.emit(i, "done", str(out_dir))
            except EngineError as e:
                item.status, item.error = "error", str(e)
                fail += 1
                self.sig_log.emit(f"✗ {item.name}: {e}")
                self.sig_item_finished.emit(i, "error", str(e))
            except Exception as e:  # lỗi bất kỳ khác cũng không sập batch
                item.status, item.error = "error", str(e)
                fail += 1
                self.sig_log.emit(f"✗ {item.name}: {e}")
                self.sig_item_finished.emit(i, "error", str(e))

            self.sig_total_progress.emit(i + 1, total)

        self.sig_batch_finished.emit(ok, fail, self._cancel)


class EngineStartWorker(QThread):
    """Khởi động engine + chờ sẵn sàng ở thread nền."""

    sig_state = Signal(str)   # starting | ready | error:<code>
    sig_log = Signal(str)

    def __init__(self, manager, client: GptSovitsClient, engine_folder: str,
                 host: str, port: int, custom_python: str = "", parent=None):
        super().__init__(parent)
        self.manager = manager
        self.client = client
        self.engine_folder = engine_folder
        self.host = host
        self.port = port
        self.custom_python = custom_python
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        self.sig_state.emit("starting")
        try:
            self.manager.start(self.engine_folder, self.host, self.port,
                               self.custom_python)
        except RuntimeError as e:
            self.sig_state.emit(f"error:{e}")
            return
        except Exception as e:
            self.sig_log.emit(f"engine start exception: {e}")
            self.sig_state.emit("error:start_failed")
            return

        ready = self.client.wait_ready(
            timeout=600,
            should_abort=lambda: self._abort or not self.manager.is_running(),
        )
        if self._abort:
            self.sig_state.emit("error:aborted")
        elif ready:
            self.sig_state.emit("ready")
        else:
            self.sig_state.emit("error:start_failed")


class ModelApplyWorker(QThread):
    """Gọi /set_gpt_weights + /set_sovits_weights ở thread nền."""

    sig_done = Signal(bool, str)  # success, message

    def __init__(self, client: GptSovitsClient, gpt: str, sovits: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.gpt = gpt
        self.sovits = sovits

    def run(self):
        try:
            if self.gpt:
                self.client.set_gpt_weights(self.gpt)
            if self.sovits:
                self.client.set_sovits_weights(self.sovits)
            self.sig_done.emit(True, "")
        except Exception as e:
            self.sig_done.emit(False, str(e))
