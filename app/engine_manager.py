# -*- coding: utf-8 -*-
"""Quản lý subprocess api_v2.py của GPT-SoVITS: dò python, start/stop, đọc log.

KHÔNG viết lại inference — chỉ khởi động server chính thức:
    <python_cua_engine> api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
"""

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

from app.engine_client import GptSovitsClient

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# Tên file weights v2Pro/v2ProPlus phổ biến trong pretrained_models
KNOWN_SOVITS = {
    "v2Pro": ["s2Gv2Pro.pth"],
    "v2ProPlus": ["s2Gv2ProPlus.pth"],
}
KNOWN_GPT = [
    "s1v3.ckpt",
    "s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
    "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
]


class EngineManager:
    def __init__(self, on_log: Optional[Callable[[str], None]] = None):
        self.proc: Optional[subprocess.Popen] = None
        self.on_log = on_log or (lambda s: None)
        self._reader_thread: Optional[threading.Thread] = None
        self.engine_folder = ""
        self.host = "127.0.0.1"
        self.port = 9880

    # ---------- Dò tìm ----------
    def find_api_script(self, engine_folder: str) -> Optional[Path]:
        root = Path(engine_folder)
        for cand in (root / "api_v2.py", root / "GPT-SoVITS" / "api_v2.py"):
            if cand.is_file():
                return cand
        return None

    def find_python(self, engine_folder: str, custom_python: str = "") -> Optional[str]:
        """Ưu tiên: python chỉ định thủ công → runtime\\python.exe (gói tích hợp)
        → venv thường gặp → python trên PATH (khi cài từ source)."""
        if custom_python and Path(custom_python).is_file():
            return custom_python
        root = Path(engine_folder)
        candidates = [
            root / "runtime" / "python.exe",
            root / "runtime" / "python" / "python.exe",
            root / "venv" / "Scripts" / "python.exe",
            root / ".venv" / "Scripts" / "python.exe",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
        return shutil.which("python")

    def find_config(self, api_script: Path) -> Optional[str]:
        base = api_script.parent
        cfg = base / "GPT_SoVITS" / "configs" / "tts_infer.yaml"
        return str(cfg) if cfg.is_file() else None

    def find_pretrained_weights(self, engine_folder: str, variant: str):
        """Tự dò GPT ckpt + SoVITS pth cho v2Pro/v2ProPlus trong pretrained_models.
        Trả về (gpt_path | None, sovits_path | None)."""
        api = self.find_api_script(engine_folder)
        if not api:
            return None, None
        pm = api.parent / "GPT_SoVITS" / "pretrained_models"
        if not pm.is_dir():
            return None, None

        sovits = None
        for name in KNOWN_SOVITS.get(variant, []):
            hits = list(pm.rglob(name))
            if hits:
                sovits = str(hits[0])
                break
        gpt = None
        for name in KNOWN_GPT:
            hits = list(pm.rglob(name))
            if hits:
                gpt = str(hits[0])
                break
        return gpt, sovits

    @staticmethod
    def has_nvidia_gpu() -> bool:
        return shutil.which("nvidia-smi") is not None

    # ---------- Vòng đời ----------
    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, engine_folder: str, host: str = "127.0.0.1", port: int = 9880,
              custom_python: str = "") -> None:
        """Khởi động api_v2.py. Ném RuntimeError với mã lỗi ngắn nếu thiếu thành phần."""
        if self.is_running():
            return
        api_script = self.find_api_script(engine_folder)
        if not api_script:
            raise RuntimeError("api_not_found")
        python = self.find_python(engine_folder, custom_python)
        if not python:
            raise RuntimeError("python_not_found")

        self.engine_folder = engine_folder
        self.host, self.port = host, int(port)

        cmd = [python, str(api_script.name), "-a", host, "-p", str(port)]
        cfg = self.find_config(api_script)
        if cfg:
            cmd += ["-c", cfg]

        self.on_log(f"[engine] {' '.join(cmd)}")
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        self.proc = subprocess.Popen(
            cmd,
            cwd=str(api_script.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
            env=env,
        )
        self._reader_thread = threading.Thread(target=self._pump_output, daemon=True)
        self._reader_thread.start()

    def _pump_output(self):
        proc = self.proc
        if not proc or not proc.stdout:
            return
        try:
            for raw in iter(proc.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip()
                if line:
                    self.on_log(f"[engine] {line}")
        except Exception:
            pass
        finally:
            code = proc.poll()
            self.on_log(f"[engine] process exited (code={code})")

    def stop(self):
        """Dừng êm qua /control?command=exit, sau đó kill cả cây tiến trình."""
        if self.proc is None:
            return
        try:
            GptSovitsClient(self.host, self.port).control("exit")
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            pass
        if self.is_running():
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                        capture_output=True, creationflags=CREATE_NO_WINDOW,
                    )
                else:
                    self.proc.kill()
            except Exception:
                pass
        self.proc = None
