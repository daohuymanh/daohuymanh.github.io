@echo off
REM Chay toan bo pipeline tren Windows CMD:
REM   run_all.bat video.mp4 script.docx
REM
REM Yeu cau da cai truoc (xem README_WINDOWS.txt):
REM   - Python 3.10/3.11 (them vao PATH khi cai)
REM   - ffmpeg (them vao PATH)
REM   - pip install -r requirements.txt
REM
REM Neu KHONG co GPU (card man hinh NVIDIA + CUDA), sua 2 dong --device / --compute_type
REM trong lenh python 01_transcribe_align.py ben duoi: --device cpu --compute_type int8

setlocal

set VIDEO=%1
set SCRIPT_DOCX=%2
set OUT_DIR=out

if "%VIDEO%"=="" (
  echo Cach dung: run_all.bat video.mp4 script.docx
  exit /b 1
)
if "%SCRIPT_DOCX%"=="" (
  echo Cach dung: run_all.bat video.mp4 script.docx
  exit /b 1
)

echo == Buoc 1: Transcribe + word-level align bang WhisperX ==
python 01_transcribe_align.py "%VIDEO%" ^
  --out "%OUT_DIR%" ^
  --model large-v3 ^
  --language en ^
  --device cuda ^
  --compute_type float16

if errorlevel 1 (
  echo.
  echo [Loi] Buoc transcribe that bai. Neu ban KHONG co GPU NVIDIA/CUDA,
  echo mo file run_all.bat va doi dong --device cuda / --compute_type float16
  echo thanh --device cpu / --compute_type int8 roi chay lai.
  exit /b 1
)

echo.
echo == Buoc 2: Doi chieu voi script.docx de phat hien loi/doan doc lech ==
python 02_compare_with_script.py ^
  --script "%SCRIPT_DOCX%" ^
  --transcript "%OUT_DIR%\transcript.json" ^
  --out "%OUT_DIR%\compare_report.html"

echo.
echo Hoan tat. Xem ket qua:
echo   - %OUT_DIR%\transcript.srt        ^<- caption chinh, dung de gan vao video
echo   - %OUT_DIR%\compare_report.html   ^<- mo bang trinh duyet de kiem tra cho lech/loi
echo.
echo Gan caption vao video (tuy chon):
echo   ffmpeg -i "%VIDEO%" -vf subtitles="%OUT_DIR%\transcript.srt" output_with_subs.mp4

endlocal
