# -*- coding: utf-8 -*-
"""Hội thoại đa giọng: kịch bản gắn tag [Vai] → mỗi vai một voice profile,
ghép thành một file audio hoàn chỉnh (+ SRT có tên vai nếu bật).

Định dạng kịch bản:
    [A] こんにちは、田中さん。
    [B] ああ、佐藤さん！お久しぶりです。
    [A] 最近どうですか？
Dòng không có tag → nối tiếp lời thoại của vai ngay trên nó.
"""

import json
import random
import re
from dataclasses import dataclass, field, replace

from PySide6.QtCore import QThread, Signal

from app.audio_post import (build_srt, concat_with_silence, normalize_loudness,
                            offset_srt_entries, wav_duration)
from app.engine_client import EngineError, GptSovitsClient
from app.output_writer import _export_mp3, create_output_dir
from app.pronunciation import matching_rules
from app.worker import SynthCancelled, TtsJobConfig, synthesize_one

_TAG_RE = re.compile(r"^\s*\[([^\[\]]{1,50})\]\s*(.*)$")


def parse_dialogue(text: str):
    """Trả về danh sách [(tag, lời_thoại), ...] theo thứ tự kịch bản.
    Ném ValueError nếu có nội dung trước tag đầu tiên."""
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = _TAG_RE.match(raw)
        if m:
            lines.append([m.group(1).strip(), m.group(2).strip()])
        elif lines:
            lines[-1][1] = (lines[-1][1] + "\n" + raw.strip()).strip()
        else:
            raise ValueError("text before first [tag]")
    return [(tag, t) for tag, t in lines if t]


def dialogue_tags(lines) -> list:
    """Danh sách tag duy nhất, giữ thứ tự xuất hiện."""
    seen, out = set(), []
    for tag, _ in lines:
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


@dataclass
class SpeakerVoice:
    """Giọng của một vai (lấy từ voice profile)."""
    ref_audio_path: str
    prompt_text: str = ""
    prompt_lang: str = "ja"
    aux_ref_audio_paths: list = field(default_factory=list)


class DialogueWorker(QThread):
    """Tổng hợp từng lời thoại bằng giọng của vai tương ứng rồi ghép lại."""

    sig_progress = Signal(int, int)   # done_lines, total_lines
    sig_log = Signal(str)
    sig_done = Signal(bool, str)      # ok, output_dir | error

    def __init__(self, client: GptSovitsClient, base_cfg: TtsJobConfig,
                 lines: list, speakers: dict, text_lang: str = "auto",
                 script_text: str = "", parent=None):
        super().__init__(parent)
        self.client = client
        self.base_cfg = base_cfg
        self.lines = lines            # [(tag, text), ...]
        self.speakers = speakers      # {tag: SpeakerVoice}
        self.text_lang = text_lang
        self.script_text = script_text
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        cfg = self.base_cfg
        seed = cfg.seed
        if seed is None or int(seed) < 0:
            seed = random.randint(0, 2**31 - 1)
        gap = float(cfg.fragment_interval)

        parts, all_entries, failed = [], [], []
        offset = 0.0
        try:
            for i, (tag, text) in enumerate(self.lines):
                if self._cancel:
                    raise SynthCancelled()
                voice = self.speakers[tag]
                cfg_line = replace(
                    cfg,
                    ref_audio_path=voice.ref_audio_path,
                    prompt_text=voice.prompt_text,
                    prompt_lang=voice.prompt_lang,
                    aux_ref_audio_paths=voice.aux_ref_audio_paths,
                )
                self.sig_log.emit(f"🎭 [{tag}] {text[:50]}…"
                                  if len(text) > 50 else f"🎭 [{tag}] {text}")
                wav, entries, line_failed = synthesize_one(
                    self.client, cfg_line, text, self.text_lang, seed,
                    cancel_cb=lambda: self._cancel,
                    log_cb=self.sig_log.emit)
                failed.extend(f"[{tag}] {s}" for s in line_failed)
                parts.append(wav)
                if cfg.export_srt and entries:
                    all_entries.extend(
                        (s, e, f"{tag}: {t}")
                        for s, e, t in offset_srt_entries(entries, offset))
                offset += wav_duration(wav) + gap
                self.sig_progress.emit(i + 1, len(self.lines))

            merged = concat_with_silence(parts, gap)
            if cfg.normalize_loudness:
                try:
                    merged = normalize_loudness(merged)
                except Exception as e:
                    self.sig_log.emit(f"⚠ loudnorm skipped: {e}")

            out_dir = create_output_dir(cfg.output_base, "dialogue")
            (out_dir / "output.wav").write_bytes(merged)
            (out_dir / "script.txt").write_text(self.script_text,
                                                encoding="utf-8")
            if cfg.export_srt and all_entries:
                (out_dir / "output.srt").write_text(build_srt(all_entries),
                                                    encoding="utf-8")
            if cfg.export_mp3:
                _export_mp3(merged, out_dir / "output.mp3")
            meta = {
                "type": "dialogue",
                "lines": len(self.lines),
                "speakers": {tag: v.ref_audio_path
                             for tag, v in self.speakers.items()},
                "text_lang": self.text_lang,
                "gap_seconds": gap,
                "seed_actual": seed,
                "duration_seconds": round(wav_duration(merged), 3),
                "loudness_normalized": cfg.normalize_loudness,
                "srt_included": bool(cfg.export_srt and all_entries),
                "failed_sentences": failed,
                "pronunciation_applied": matching_rules(
                    self.script_text, cfg.pronunciation_rules),
            }
            (out_dir / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8")
            self.sig_done.emit(True, str(out_dir))
        except SynthCancelled:
            self.sig_done.emit(False, "cancelled")
        except EngineError as e:
            self.sig_done.emit(False, str(e))
        except Exception as e:
            self.sig_done.emit(False, str(e))
