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
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    app\main.py

if errorlevel 1 (
    echo BUILD THAT BAI.
    pause
    exit /b 1
)

echo Tinh gon: xoa cac module Qt khong dung (WebEngine, QML, Designer...) ~465 MB
powershell -NoProfile -Command ^
  "$base = 'dist\VoiceStudio\_internal\PySide6';" ^
  "$pats = 'Qt6WebEngine*','QtWebEngine*','Qt6Quick*','QtQuick*','Qt6Qml*','QtQml*','Qt6Designer*','QtDesigner*','Qt6Pdf*','QtPdf*','Qt63D*','Qt3D*','Qt6Charts*','QtCharts*','Qt6DataVis*','QtDataVis*','Qt6Location*','QtLocation*','Qt6WebChannel*','QtWebChannel*','Qt6WebSockets*','QtWebSockets*','Qt6VirtualKeyboard*','Qt6Test*','QtTest*','Qt6Sensors*','QtSensors*','Qt6Nfc*','QtNfc*','Qt6Bluetooth*','QtBluetooth*','Qt6SerialPort*','QtSerialPort*','Qt6RemoteObjects*','QtRemoteObjects*','Qt6Scxml*','QtScxml*','Qt6StateMachine*','QtStateMachine*','Qt6Help*','QtHelp*','QtUiTools*','Qt6UiTools*','lupdate*','lrelease*','qmlformat*','assistant*','designer*','linguist*','QtWebEngineProcess*';" ^
  "foreach ($p in $pats) { Get-ChildItem $base -Filter $p -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force };" ^
  "foreach ($d in @(\"$base\resources\", \"$base\translations\", \"$base\qml\")) { if (Test-Path $d) { Remove-Item $d -Recurse -Force } };" ^
  "'Kich thuoc sau tinh gon: {0:N0} MB' -f ((Get-ChildItem dist\VoiceStudio -Recurse -File | Measure-Object Length -Sum).Sum/1MB)"

echo.
echo BUILD XONG: dist\VoiceStudio\VoiceStudio.exe
pause
