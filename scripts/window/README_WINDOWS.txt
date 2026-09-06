HUONG DAN CHAY TREN WINDOWS (CMD)
===================================

0) Chuan bi thu muc
--------------------
Tao 1 thu muc, vi du: C:\caption
Copy vao do 6 file:
  - run_all.bat
  - 01_transcribe_align.py
  - 02_compare_with_script.py
  - requirements.txt
  - video.mp4      (video cua ban)
  - script.docx    (kich ban cua ban)

Mo CMD (nhan Win, go "cmd", Enter), roi:
  cd C:\caption


1) Cai Python (neu chua co)
-----------------------------
Tai Python 3.10 hoac 3.11 tai https://www.python.org/downloads/
Khi cai, NHO TICK vao o "Add python.exe to PATH".

Kiem tra:
  python --version


2) Cai ffmpeg (bat buoc, dung de tach audio + gan sub)
---------------------------------------------------------
Cach de nhat: dung winget (co san tren Windows 10/11):
  winget install ffmpeg

Hoac tai thu cong tai https://www.gyan.dev/ffmpeg/builds/ (ban "essentials"),
giai nen, roi them thu muc "bin" ben trong vao PATH (System Properties ->
Environment Variables -> Path -> New -> tro toi ...\ffmpeg\bin).

Kiem tra:
  ffmpeg -version


3) Cai thu vien Python
-------------------------
  pip install -r requirements.txt

Neu ban CO card man hinh NVIDIA va muon dung GPU (nhanh hon nhieu), cai them
PyTorch ban CUDA truoc khi cai whisperx (xem huong dan tai
https://pytorch.org/get-started/locally/ chon: Windows / Pip / Python / CUDA):
  pip install torch --index-url https://download.pytorch.org/whl/cu121
  pip install -r requirements.txt

Neu KHONG co GPU NVIDIA, khong sao — script van chay duoc bang CPU (cham hon),
chi can sua --device cpu --compute_type int8 (xem buoc 4).


4) Chay pipeline
-------------------
Cach 1 - dung file .bat co san (mac dinh dung GPU/cuda):
  run_all.bat video.mp4 script.docx

Cach 2 - neu KHONG co GPU, mo run_all.bat bang Notepad, tim dong:
  --device cuda ^
  --compute_type float16
sua thanh:
  --device cpu ^
  --compute_type int8
roi luu lai va chay lai "run_all.bat video.mp4 script.docx".

Cach 3 - chay tung buoc thu cong (khong dung .bat):
  python 01_transcribe_align.py video.mp4 --out out --model large-v3 --language en --device cpu --compute_type int8
  python 02_compare_with_script.py --script script.docx --transcript out\transcript.json --out out\compare_report.html


5) Ket qua
------------
Trong thu muc "out\":
  - transcript.srt        caption chinh (dung de gan vao video)
  - transcript_words.srt  caption tung tu (karaoke-style)
  - transcript.vtt        dinh dang WebVTT
  - compare_report.html   mo bang trinh duyet, xem cho nao giong doc lech
                           script hoac Whisper co the nghe nham thuat ngu

Gan caption vao video (tuy chon, tao file moi co sub):
  ffmpeg -i video.mp4 -vf subtitles=out/transcript.srt output_with_subs.mp4

(luu y: dung dau / thay vi \ trong duong dan sau "subtitles=" de tranh loi
ffmpeg tren Windows khi duong dan co dau hai cham cua o dia)


LOI THUONG GAP
================
- "python khong duoc nhan dien" -> Python chua duoc them vao PATH, cai lai va
  tick "Add python.exe to PATH", hoac dung "py" thay vi "python".
- "ffmpeg khong duoc nhan dien" -> chua them ffmpeg\bin vao PATH, mo CMD moi
  sau khi sua PATH.
- Loi lien quan CUDA/torch -> may khong co GPU NVIDIA phu hop, chuyen sang
  --device cpu --compute_type int8.
- Lan chay dau tien se tai model (vai GB) tu Hugging Face, can mang on dinh,
  co the mat vai phut.
