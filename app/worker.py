# -*- coding: utf-8 -*-
"""Thread nền: chạy batch TTS + khởi động engine. UI KHÔNG bao giờ bị đơ."""

import random
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal

from app.audio_post import (build_srt, concat_with_silence, normalize_loudness,
                            offset_srt_entries, split_sentences, wav_duration)
from app.engine_client import EngineError, GptSovitsClient
from app.output_writer import create_output_dir, write_result


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

    def _tts_once(self, text: str, text_lang: str, seed: int,
                  split_method: str) -> bytes:
        return self.client.tts(
            text=text,
            text_lang=text_lang,
            ref_audio_path=self.cfg.ref_audio_path,
            prompt_text=self.cfg.prompt_text,
            prompt_lang=self.cfg.prompt_lang,
            aux_ref_audio_paths=self.cfg.aux_ref_audio_paths,
            speed_factor=self.cfg.speed_factor,
            text_split_method=split_method,
            batch_size=self.cfg.batch_size,
            top_k=self.cfg.top_k,
            top_p=self.cfg.top_p,
            temperature=self.cfg.temperature,
            repetition_penalty=self.cfg.repetition_penalty,
            fragment_interval=self.cfg.fragment_interval,
            seed=seed,
            media_type="wav",
        )

    def _synthesize_with_srt(self, item: QueueItem, seed: int):
        """Tổng hợp TỪNG CÂU để lấy timestamp chính xác → (wav_bytes, entries).
        entries: [(start, end, text), ...] tính cả khoảng lặng fragment_interval."""
        sentences = split_sentences(item.text)
        if not sentences:
            sentences = [item.text.strip()]
        gap = float(self.cfg.fragment_interval)
        segments, entries = [], []
        t = 0.0
        for k, sent in enumerate(sentences):
            if self._cancel:
                raise _CancelledMidItem()
            wav = self._tts_once(sent, item.text_lang, seed, "cut0")
            dur = wav_duration(wav)
            entries.append((t, t + dur, sent))
            segments.append(wav)
            t += dur + gap
            self.sig_item_progress.emit(int(10 + 70 * (k + 1) / len(sentences)))
        return concat_with_silence(segments, gap), entries

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

                srt_entries = None
                if self.cfg.export_srt:
                    wav, srt_entries = self._synthesize_with_srt(item, actual_seed)
                else:
                    wav = self._tts_once(item.text, item.text_lang, actual_seed,
                                         self.cfg.text_split_method)
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
            except _CancelledMidItem:
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
        gap = float(self.cfg.audiobook_gap)
        merged_wav = concat_with_silence([w for _, w, _ in parts], gap)

        out_dir = create_output_dir(self.cfg.output_base, "audiobook")
        (out_dir / "merged.wav").write_bytes(merged_wav)

        # SRT gộp (nếu chế độ SRT bật): dịch timestamp theo vị trí từng phần
        if self.cfg.export_srt and all(e is not None for _, _, e in parts):
            all_entries, offset = [], 0.0
            for name, wav, entries in parts:
                all_entries.extend(offset_srt_entries(entries, offset))
                offset += wav_duration(wav) + gap
            (out_dir / "merged.srt").write_text(build_srt(all_entries),
                                                encoding="utf-8")

        if self.cfg.export_mp3:
            from app.output_writer import _export_mp3
            _export_mp3(merged_wav, out_dir / "merged.mp3")

        import json
        meta = {
            "type": "audiobook",
            "parts": [name for name, _, _ in parts],
            "gap_seconds": gap,
            "duration_seconds": round(wav_duration(merged_wav), 3),
            "loudness_normalized": self.cfg.normalize_loudness,
            "srt_included": self.cfg.export_srt,
        }
        (out_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        self.sig_log.emit(f"📚 audiobook: {out_dir} ({len(parts)} parts, "
                          f"{meta['duration_seconds']}s)")
        self.sig_audiobook_done.emit(str(out_dir))


class _CancelledMidItem(Exception):
    """Người dùng bấm Hủy giữa lúc đang tổng hợp từng câu."""


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
                text=sent,
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
