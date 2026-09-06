#!/usr/bin/env bash
# Chay toan bo pipeline: transcribe + align (theo giong doc thuc te) -> doi chieu script.docx
#
# Cach dung:
#   ./run_all.sh video.mp4 script.docx
#
# Yeu cau da cai: pip install -r requirements.txt ; ffmpeg co san trong PATH
# Neu chay CPU (khong co GPU CUDA): sua --device cpu --compute_type int8 trong lenh ben duoi

set -e

VIDEO="$1"
SCRIPT_DOCX="$2"
OUT_DIR="./out"

if [ -z "$VIDEO" ] || [ -z "$SCRIPT_DOCX" ]; then
  echo "Cach dung: ./run_all.sh video.mp4 script.docx"
  exit 1
fi

echo "== Buoc 1: Transcribe + word-level align bang WhisperX =="
python 01_transcribe_align.py "$VIDEO" \
  --out "$OUT_DIR" \
  --model large-v3 \
  --language en \
  --device cuda \
  --compute_type float16

echo ""
echo "== Buoc 2: Doi chieu voi script.docx de phat hien loi/doan doc lech =="
python 02_compare_with_script.py \
  --script "$SCRIPT_DOCX" \
  --transcript "$OUT_DIR/transcript.json" \
  --out "$OUT_DIR/compare_report.html"

echo ""
echo "Hoan tat. Xem ket qua:"
echo "  - $OUT_DIR/transcript.srt        <- caption chinh, dung de gan vao video"
echo "  - $OUT_DIR/compare_report.html   <- mo file nay bang trinh duyet de kiem tra cho lech/loi"
echo ""
echo "Gan caption vao video (tuy chon):"
echo "  ffmpeg -i \"$VIDEO\" -vf subtitles=\"$OUT_DIR/transcript.srt\" output_with_subs.mp4"
