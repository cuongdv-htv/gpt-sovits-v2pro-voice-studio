@echo off
rem ============================================================
rem  GPT-SoVITS v2Pro Voice Studio - chay nhanh khong can build
rem  Tao venv GUI + cai requirements + chay app
rem ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Tao virtual env .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo LOI: Khong tao duoc venv. Kiem tra Python 3.10-3.12 da cai chua.
        pause
        exit /b 1
    )
)

echo [2/3] Cai dat thu vien GUI (PySide6, requests, ...) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo LOI: Cai thu vien that bai.
    pause
    exit /b 1
)

echo [3/3] Khoi dong GPT-SoVITS v2Pro Voice Studio ...
".venv\Scripts\python.exe" -m app.main
if errorlevel 1 pause
