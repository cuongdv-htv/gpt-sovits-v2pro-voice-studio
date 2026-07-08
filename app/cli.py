# -*- coding: utf-8 -*-
"""CLI mode — chạy batch TTS không cần mở GUI (tự động hóa được từ script).

Ví dụ:
  # Dùng voice profile đã lưu, đọc 3 file chương, xuất SRT + audiobook
  python -m app.cli --engine D:\\GPT-SoVITS-v2pro-20250604 --profile "MC nu" ^
      --input ch1.txt ch2.txt ch3.txt --lang ja --srt --audiobook --mp3

  # Chỉ định trực tiếp audio mẫu, đọc 1 câu
  python -m app.cli --engine <folder> --ref voice.wav --prompt-text "..." ^
      --prompt-lang ja --text "Hello world" --lang en

  # Liệt kê voice profiles
  python -m app.cli --list-profiles
"""

import argparse
import random
import sys
import time
from pathlib import Path

from app.audio_post import build_chapters, build_srt, concat_with_silence, \
    normalize_loudness, offset_srt_entries, wav_duration
from app.engine_client import EngineError, GptSovitsClient
from app.engine_manager import EngineManager
from app.output_writer import _export_mp3, create_output_dir, write_result
from app.profiles import ProfileStore
from app.settings import Settings
from app.worker import TtsJobConfig, synthesize_one


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="GPT-SoVITS v2Pro Voice Studio — headless batch TTS")
    p.add_argument("--list-profiles", action="store_true",
                   help="list saved voice profiles and exit")
    # engine
    p.add_argument("--engine", help="engine folder (containing api_v2.py)")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--keep-engine", action="store_true",
                   help="do not stop the engine when finished")
    # voice
    p.add_argument("--profile", help="voice profile name (from the GUI)")
    p.add_argument("--ref", help="reference audio path (3-10s)")
    p.add_argument("--prompt-text", default="")
    p.add_argument("--prompt-lang", default="ja",
                   choices=["ja", "en", "zh", "ko", "yue"])
    p.add_argument("--aux", action="append", default=[],
                   help="auxiliary reference audio (repeatable)")
    # input
    p.add_argument("--text", help="direct text to speak")
    p.add_argument("--input", nargs="+", default=[], help=".txt files (UTF-8)")
    p.add_argument("--input-dir", help="folder containing .txt files")
    p.add_argument("--lang", default="auto",
                   choices=["auto", "ja", "en", "zh", "ko", "yue"])
    # output
    p.add_argument("--out", help="output base folder (default: GUI setting)")
    p.add_argument("--mp3", action="store_true")
    p.add_argument("--srt", action="store_true",
                   help="per-sentence synthesis + .srt subtitles")
    p.add_argument("--normalize", action="store_true",
                   help="loudness normalize to -14 LUFS")
    p.add_argument("--audiobook", action="store_true",
                   help="merge all items into one file")
    p.add_argument("--gap", type=float, default=None,
                   help="silence between audiobook items (s)")
    # synthesis params
    p.add_argument("--speed", type=float, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--cut", default=None,
                   choices=["cut0", "cut1", "cut2", "cut3", "cut4", "cut5"])
    return p


def _collect_inputs(args) -> list:
    items = []
    if args.text:
        items.append(("manual", args.text))
    for f in args.input:
        path = Path(f)
        items.append((path.stem,
                      path.read_text(encoding="utf-8", errors="replace")))
    if args.input_dir:
        for path in sorted(Path(args.input_dir).glob("*.txt")):
            items.append((path.stem,
                          path.read_text(encoding="utf-8", errors="replace")))
    return [(n, t) for n, t in items if t.strip()]


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    settings = Settings()

    if args.list_profiles:
        store = ProfileStore()
        if not store.profiles:
            print("(no profiles)")
        for prof in store.profiles:
            print(f"{prof.name}\t{prof.prompt_lang}\t{prof.ref_audio_path}")
        return 0

    # ---- voice ----
    ref, prompt_text = args.ref, args.prompt_text
    prompt_lang, aux = args.prompt_lang, list(args.aux)
    if args.profile:
        prof = ProfileStore().get(args.profile)
        if not prof:
            print(f"ERROR: profile not found: {args.profile}", file=sys.stderr)
            return 1
        ref = prof.ref_audio_path
        prompt_text = prof.prompt_text
        prompt_lang = prof.prompt_lang
        aux = prof.aux_ref_audio_paths
    if not ref or not Path(ref).is_file():
        print("ERROR: reference audio missing (--ref or --profile)",
              file=sys.stderr)
        return 1

    items = _collect_inputs(args)
    if not items:
        print("ERROR: no input text (--text / --input / --input-dir)",
              file=sys.stderr)
        return 1

    cfg = TtsJobConfig(
        ref_audio_path=ref,
        prompt_text=prompt_text,
        prompt_lang=prompt_lang,
        aux_ref_audio_paths=aux,
        speed_factor=args.speed if args.speed is not None
        else settings.get("speed_factor"),
        text_split_method=args.cut or settings.get("text_split_method"),
        batch_size=settings.get("batch_size"),
        top_k=settings.get("top_k"),
        top_p=settings.get("top_p"),
        temperature=settings.get("temperature"),
        repetition_penalty=settings.get("repetition_penalty"),
        fragment_interval=settings.get("fragment_interval"),
        seed=args.seed if args.seed is not None else settings.get("seed"),
        output_base=args.out or settings.get("output_base"),
        export_mp3=args.mp3,
        export_srt=args.srt,
        normalize_loudness=args.normalize,
        audiobook_merge=args.audiobook,
        audiobook_gap=args.gap if args.gap is not None
        else settings.get("audiobook_gap"),
    )

    # ---- engine ----
    host = args.host or settings.get("host")
    port = args.port or int(settings.get("port"))
    client = GptSovitsClient(host, port)
    mgr = EngineManager(on_log=lambda s: None)
    we_started = False
    if not client.is_alive():
        engine_folder = args.engine or settings.get("engine_folder")
        if not engine_folder or not mgr.find_api_script(engine_folder):
            print("ERROR: engine not running and --engine folder invalid",
                  file=sys.stderr)
            return 1
        print(f"Starting engine: {engine_folder}")
        mgr.start(engine_folder, host, port, settings.get("engine_python"))
        if not client.wait_ready(timeout=600,
                                 should_abort=lambda: not mgr.is_running()):
            print("ERROR: engine failed to start", file=sys.stderr)
            mgr.stop()
            return 1
        we_started = True
    print(f"Engine ready at {host}:{port}")

    # ---- run ----
    ok = fail = 0
    merged_parts = []
    try:
        for i, (name, text) in enumerate(items, 1):
            seed = cfg.seed
            if seed is None or int(seed) < 0:
                seed = random.randint(0, 2**31 - 1)
            t0 = time.time()
            print(f"[{i}/{len(items)}] {name} ({len(text)} chars)…",
                  flush=True)
            try:
                wav, entries, failed = synthesize_one(
                    client, cfg, text, args.lang, seed,
                    log_cb=lambda s: print(f"  {s}", flush=True))
                if cfg.normalize_loudness:
                    try:
                        wav = normalize_loudness(wav)
                    except Exception as e:
                        print(f"  loudnorm skipped: {e}")
                out_dir = write_result(
                    output_base=cfg.output_base, source_name=name,
                    wav_bytes=wav, text=text, ref_audio_path=ref,
                    meta={"text_lang": args.lang, "prompt_lang": prompt_lang,
                          "seed_actual": seed, "cli": True,
                          "failed_sentences": failed},
                    export_mp3=cfg.export_mp3,
                    srt_text=build_srt(entries) if entries else None)
                print(f"  OK {time.time() - t0:.1f}s -> {out_dir}"
                      + (f"  ({len(failed)} sentence(s) skipped)" if failed else ""))
                ok += 1
                if cfg.audiobook_merge:
                    merged_parts.append((name, wav, entries))
            except EngineError as e:
                print(f"  FAILED: {e}", file=sys.stderr)
                fail += 1

        if cfg.audiobook_merge and merged_parts:
            gap = float(cfg.audiobook_gap)
            merged = concat_with_silence([w for _, w, _ in merged_parts], gap)
            out_dir = create_output_dir(cfg.output_base, "audiobook")
            (out_dir / "merged.wav").write_bytes(merged)

            srt_ok = cfg.export_srt and all(e for _, _, e in merged_parts)
            chapters, all_entries, off = [], [], 0.0
            for n, w, e in merged_parts:
                chapters.append((n, off))
                if srt_ok:
                    all_entries.extend(offset_srt_entries(e, off))
                off += wav_duration(w) + gap
            (out_dir / "chapters.txt").write_text(build_chapters(chapters),
                                                  encoding="utf-8")
            if srt_ok:
                (out_dir / "merged.srt").write_text(build_srt(all_entries),
                                                    encoding="utf-8")
            if cfg.export_mp3:
                _export_mp3(merged, out_dir / "merged.mp3")
            print(f"Audiobook -> {out_dir}")
    finally:
        if we_started and not args.keep_engine:
            mgr.stop()
            print("Engine stopped.")

    print(f"Done: {ok} ok, {fail} failed / {len(items)} items")
    return 0 if fail == 0 else (2 if ok else 1)


if __name__ == "__main__":
    sys.exit(main())
