# -*- coding: utf-8 -*-
"""Thread nền: chạy batch TTS + khởi động engine. UI KHÔNG bao giờ bị đơ."""

import random
import time
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal

from app.audio_post import (build_srt, concat_with_silence, normalize_loudness,
                            split_sentences, wav_duration)
from app.audiobook import write_audiobook
from app.engine_client import EngineError, GptSovitsClient
from app.output_writer import write_result
from app.pronunciation import apply_rules, matching_rules

# Số lần thử lại MỖI CÂU trước khi bỏ qua câu đó (chế độ SRT).
# Engine đôi khi lỗi nhất thời (OOM tạm, hụt hơi khi giải mã) — retry cứu được
# phần lớn, và một câu hỏng không được phép làm mất cả chương.
SENTENCE_RETRIES = 2
RETRY_DELAY_SEC = 1.0


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
    # Hậu xử lý (tùy chọn)
    export_srt: bool = False          # tổng hợp từng câu + sinh .srt
    normalize_loudness: bool = False  # chuẩn -14 LUFS (YouTube)
    audiobook_merge: bool = False     # ghép cả batch thành 1 file
    audiobook_gap: float = 0.8        # khoảng lặng giữa các mục (giây)
    # Từ điển phát âm: chỉ đổi chuỗi GỬI engine, không đổi text gốc/SRT
    pronunciation_rules: list = field(default_factory=list)


class SynthCancelled(Exception):
    """Bị hủy giữa lúc tổng hợp (người dùng bấm Hủy)."""


def tts_once(client: GptSovitsClient, cfg: TtsJobConfig, text: str,
             text_lang: str, seed: int, split_method: str) -> bytes:
    """Một lời gọi /tts với đầy đủ tham số từ cfg."""
    return client.tts(
        text=text,
        text_lang=text_lang,
        ref_audio_path=cfg.ref_audio_path,
        prompt_text=cfg.prompt_text,
        prompt_lang=cfg.prompt_lang,
        aux_ref_audio_paths=cfg.aux_ref_audio_paths,
        speed_factor=cfg.speed_factor,
        text_split_method=split_method,
        batch_size=cfg.batch_size,
        top_k=cfg.top_k,
        top_p=cfg.top_p,
        temperature=cfg.temperature,
        repetition_penalty=cfg.repetition_penalty,
        fragment_interval=cfg.fragment_interval,
        seed=seed,
        media_type="wav",
    )


def _tts_with_retry(client: GptSovitsClient, cfg: TtsJobConfig, text: str,
                    text_lang: str, seed: int, split_method: str,
                    retries: int, cancel_cb, log_cb) -> bytes:
    """tts_once + thử lại `retries` lần. Ném lỗi cuối cùng nếu vẫn hỏng."""
    last_error = None
    for attempt in range(retries + 1):
        if cancel_cb():
            raise SynthCancelled()
        try:
            return tts_once(client, cfg, text, text_lang, seed, split_method)
        except Exception as e:
            last_error = e
            if attempt < retries:
                log_cb(f"⟳ retry {attempt + 1}/{retries}: {e}")
                time.sleep(RETRY_DELAY_SEC)
    raise last_error


def synthesize_one(client: GptSovitsClient, cfg: TtsJobConfig, text: str,
                   text_lang: str, seed: int,
                   progress_cb=None, cancel_cb=None, log_cb=None,
                   retries: int = SENTENCE_RETRIES):
    """Lõi tổng hợp một văn bản — dùng chung cho GUI batch, hội thoại và CLI.

    cfg.export_srt=True → tổng hợp TỪNG CÂU lấy timestamp chính xác. Câu nào
    hỏng sau khi retry thì BỎ QUA (không làm hỏng cả văn bản) và được liệt kê
    trong giá trị trả về.

    Trả về (wav_bytes, srt_entries | None, failed_sentences);
    entries: [(start, end, text), ...] tính cả khoảng lặng fragment_interval."""
    progress_cb = progress_cb or (lambda p: None)
    cancel_cb = cancel_cb or (lambda: False)
    log_cb = log_cb or (lambda s: None)

    rules = cfg.pronunciation_rules

    if not cfg.export_srt:
        wav = _tts_with_retry(client, cfg, apply_rules(text, rules), text_lang,
                              seed, cfg.text_split_method, retries, cancel_cb,
                              log_cb)
        return wav, None, []

    sentences = split_sentences(text) or [text.strip()]
    gap = float(cfg.fragment_interval)
    segments, entries, failed = [], [], []
    last_error = None
    t = 0.0
    for k, sent in enumerate(sentences):
        if cancel_cb():
            raise SynthCancelled()
        try:
            # Engine đọc bản đã thay thế; SRT bên dưới giữ nguyên `sent` gốc
            wav = _tts_with_retry(client, cfg, apply_rules(sent, rules),
                                  text_lang, seed, "cut0",
                                  retries, cancel_cb, log_cb)
        except SynthCancelled:
            raise
        except Exception as e:
            last_error = e
            failed.append(sent)
            log_cb(f"✗ bỏ qua câu {k + 1}/{len(sentences)}: {e}")
            progress_cb(int(10 + 70 * (k + 1) / len(sentences)))
            continue
        dur = wav_duration(wav)
        entries.append((t, t + dur, sent))
        segments.append(wav)
        t += dur + gap
        progress_cb(int(10 + 70 * (k + 1) / len(sentences)))

    if not segments:
        # Không cứu được câu nào → coi như cả văn bản hỏng
        raise last_error or EngineError("no sentence could be synthesized")
    if failed:
        log_cb(f"⚠ {len(failed)}/{len(sentences)} câu bị bỏ qua")
    return concat_with_silence(segments, gap), entries, failed


class BatchWorker(QThread):
    """Xử lý tuần tự hàng đợi; 1 mục lỗi KHÔNG làm sập batch."""

    sig_item_started = Signal(int)              # index
    sig_item_finished = Signal(int, str, str)   # index, status, output_dir/error
    sig_item_progress = Signal(int)             # 0-100 cho mục hiện tại
    sig_total_progress = Signal(int, int)       # done, total
    sig_log = Signal(str)
    sig_audiobook_done = Signal(str)            # thư mục audiobook đã ghép
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
        # Chỉ xử lý các mục "pending" — cho phép "Chạy lại mục lỗi" mà không
        # đụng tới các mục đã xong.
        targets = [i for i, it in enumerate(self.items) if it.status == "pending"]
        total = len(targets)
        done_count = 0
        # (item, srt_entries) của các mục thành công — cho chế độ audiobook
        merged_parts: list = []

        for i in targets:
            item = self.items[i]
            if self._cancel:
                break
            self.sig_item_started.emit(i)
            self.sig_item_progress.emit(0)

            if not item.text.strip():
                item.status = "skipped"
                self.sig_log.emit(f"⚠ skip (empty): {item.name}")
                self.sig_item_finished.emit(i, "skipped", "")
                done_count += 1
                self.sig_total_progress.emit(done_count, total)
                continue

            # Seed thực tế: -1 → sinh ngẫu nhiên để tái lập được (ghi vào meta)
            actual_seed = self.cfg.seed
            if actual_seed is None or int(actual_seed) < 0:
                actual_seed = random.randint(0, 2**31 - 1)

            try:
                self.sig_item_progress.emit(5)
                self.sig_log.emit(f"▶ TTS [{item.text_lang}] {item.name} ({item.chars} chars)")

                wav, srt_entries, failed = synthesize_one(
                    self.client, self.cfg, item.text, item.text_lang,
                    actual_seed,
                    progress_cb=self.sig_item_progress.emit,
                    cancel_cb=lambda: self._cancel,
                    log_cb=self.sig_log.emit)
                self.sig_item_progress.emit(80)

                if self.cfg.normalize_loudness:
                    try:
                        wav = normalize_loudness(wav)  # giữ nguyên thời lượng → SRT vẫn khớp
                    except Exception as e:
                        self.sig_log.emit(f"⚠ loudnorm skipped ({item.name}): {e}")
                self.sig_item_progress.emit(88)

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
                    "loudness_normalized": self.cfg.normalize_loudness,
                    "failed_sentences": failed,
                    "pronunciation_applied": matching_rules(
                        item.text, self.cfg.pronunciation_rules),
                }
                out_dir = write_result(
                    output_base=self.cfg.output_base,
                    source_name=item.name,
                    wav_bytes=wav,
                    text=item.text,
                    ref_audio_path=self.cfg.ref_audio_path,
                    meta=meta,
                    export_mp3=self.cfg.export_mp3,
                    srt_text=build_srt(srt_entries) if srt_entries else None,
                )
                item.status = "done"
                item.output_dir = str(out_dir)
                ok += 1
                if self.cfg.audiobook_merge:
                    merged_parts.append((item.name, wav, srt_entries))
                self.sig_item_progress.emit(100)
                self.sig_log.emit(f"✓ saved: {out_dir}")
                self.sig_item_finished.emit(i, "done", str(out_dir))
            except SynthCancelled:
                item.status = "skipped"
                self.sig_log.emit(f"⚠ cancelled mid-item: {item.name}")
                self.sig_item_finished.emit(i, "skipped", "")
                break
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

            done_count += 1
            self.sig_total_progress.emit(done_count, total)

        # ---- Audiobook: ghép các mục thành công thành 1 file ----
        if self.cfg.audiobook_merge and merged_parts and not self._cancel:
            try:
                self._write_audiobook(merged_parts)
            except Exception as e:
                self.sig_log.emit(f"✗ audiobook merge failed: {e}")

        self.sig_batch_finished.emit(ok, fail, self._cancel)

    def _write_audiobook(self, parts):
        """parts: [(name, wav_bytes, srt_entries|None), ...] theo thứ tự batch."""
        out_dir, meta = write_audiobook(
            output_base=self.cfg.output_base,
            parts=parts,
            gap=self.cfg.audiobook_gap,
            export_srt=self.cfg.export_srt,
            export_mp3=self.cfg.export_mp3,
            loudness_normalized=self.cfg.normalize_loudness,
        )
        self.sig_log.emit(f"📚 audiobook: {out_dir} ({len(parts)} parts, "
                          f"{meta['duration_seconds']}s)")
        self.sig_audiobook_done.emit(str(out_dir))


class PreviewWorker(QThread):
    """'Thử 1 câu': tổng hợp CÂU ĐẦU TIÊN của văn bản và lưu ra file tạm."""

    sig_done = Signal(bool, str)  # ok, wav_path | error_message

    def __init__(self, client: GptSovitsClient, cfg: TtsJobConfig,
                 text: str, text_lang: str, out_path: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.cfg = cfg
        self.text = text
        self.text_lang = text_lang
        self.out_path = out_path

    def run(self):
        try:
            sentences = split_sentences(self.text)
            sent = sentences[0] if sentences else self.text.strip()[:200]
            seed = self.cfg.seed
            if seed is None or int(seed) < 0:
                seed = random.randint(0, 2**31 - 1)
            wav = self.client.tts(
                text=apply_rules(sent, self.cfg.pronunciation_rules),
                text_lang=self.text_lang,
                ref_audio_path=self.cfg.ref_audio_path,
                prompt_text=self.cfg.prompt_text,
                prompt_lang=self.cfg.prompt_lang,
                aux_ref_audio_paths=self.cfg.aux_ref_audio_paths,
                speed_factor=self.cfg.speed_factor,
                text_split_method="cut0",
                batch_size=self.cfg.batch_size,
                top_k=self.cfg.top_k,
                top_p=self.cfg.top_p,
                temperature=self.cfg.temperature,
                repetition_penalty=self.cfg.repetition_penalty,
                fragment_interval=self.cfg.fragment_interval,
                seed=seed,
                media_type="wav",
            )
            with open(self.out_path, "wb") as f:
                f.write(wav)
            self.sig_done.emit(True, self.out_path)
        except Exception as e:
            self.sig_done.emit(False, str(e))


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
