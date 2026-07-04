@echo off
rem ============================================================
rem  Build GUI thanh .exe bang PyInstaller --onedir
rem  Chi dong goi GUI — KHONG dong goi GPT-SoVITS/torch/model.
rem  Ket qua: dist\VoiceStudio\VoiceStudio.exe
rem ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua co venv. Chay run.bat mot lan truoc de tao venv.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install pyinstaller -q

".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm --clean --onedir --windowed ^
    --name VoiceStudio ^
    --collect-submodules PySide6 ^
    --collect-binaries PySide6 ^
    --hidden-import soundfile ^
    --hidden-import imageio_ffmpeg ^
    --collect-data imageio_ffmpeg ^
    app\main.py

if errorlevel 1 (
    echo BUILD THAT BAI.
    pause
    exit /b 1
)

echo.
echo BUILD XONG: dist\VoiceStudio\VoiceStudio.exe
pause
