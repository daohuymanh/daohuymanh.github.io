# Hướng dẫn tạo caption chính xác cho video bằng WhisperX

> Bài viết này hướng dẫn cách dùng **WhisperX** để tự động tạo phụ đề (caption/subtitle) bám sát **chính xác theo giọng đọc thực tế** trong file video — kể cả khi người đọc lệch khỏi kịch bản (script) gốc. Kèm theo là bộ code sẵn dùng, chạy được trên cả **Windows** và **macOS/Linux**.

## Vì sao dùng WhisperX thay vì Whisper thường?

Whisper (OpenAI) cho timestamp theo **từng câu/đoạn**, đôi khi bị lệch vài trăm mili-giây đến vài giây so với giọng nói thật — không đủ chính xác để làm phụ đề khớp khẩu hình hay caption karaoke. **WhisperX** thêm một bước **forced alignment** (dùng model wav2vec2) để tính lại timestamp ở **mức từng từ**, cho kết quả khớp âm thanh gần như tuyệt đối. Đây cũng là lựa chọn phù hợp khi bạn có sẵn kịch bản đọc (script) nhưng người đọc **ứng khẩu / đọc lệch script** — vì lúc này bạn cần transcript bám theo audio thật, không phải ép theo văn bản gốc.

## Tổng quan pipeline

1. **Tách audio** từ video (ffmpeg).
2. **Transcribe** audio bằng Whisper (qua WhisperX) — lấy đúng lời đọc thật.
3. **Align mức từ** (word-level alignment) — tính timestamp chính xác cho từng từ.
4. **Xuất phụ đề**: `.srt`, `.vtt`, và bản karaoke từng từ.
5. *(Tùy chọn)* Đối chiếu với script gốc (nếu có) để phát hiện chỗ đọc lệch hoặc lỗi nhận dạng thuật ngữ.
6. *(Tùy chọn)* Gắn phụ đề trực tiếp vào video bằng ffmpeg.

---

## 1. Cài đặt

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install whisperx python-docx
sudo apt install ffmpeg      # Ubuntu/Debian
# brew install ffmpeg        # macOS (Homebrew)
```

### Windows (CMD)

```bat
:: 1) Cài Python 3.10/3.11 tại python.org — nhớ tick "Add python.exe to PATH"
:: 2) Cài ffmpeg
winget install ffmpeg
:: 3) Cài thư viện Python
pip install whisperx python-docx
```

> **Có GPU NVIDIA?** Cài thêm PyTorch bản CUDA trước để chạy nhanh hơn nhiều lần:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```
> Không có GPU vẫn chạy được bằng CPU, chỉ chậm hơn — xem cờ `--device cpu` bên dưới.

---

## 2. Code chính: transcribe + align theo giọng đọc thật

Lưu đoạn code dưới thành file **`transcribe_align.py`**:

```python
"""
Transcribe video/audio bang WhisperX + align o muc TU (word-level),
de caption bam sat CHINH XAC theo giong doc thuc te trong file video.

Cach chay:
    python transcribe_align.py video.mp4 --out ./out
    python transcribe_align.py video.mp4 --out ./out --language vi
    python transcribe_align.py video.mp4 --out ./out --device cpu --compute_type int8
"""

import argparse
import json
import os
import subprocess

import whisperx


def extract_audio(video_path: str, out_wav: str):
    """Tach audio 16kHz mono tu video bang ffmpeg (whisperx yeu cau)."""
    cmd = ["ffmpeg", "-y", "-i", video_path, "-ar", "16000", "-ac", "1", out_wav]
    subprocess.run(cmd, check=True)


def build_initial_prompt(glossary_path: str | None) -> str:
    """
    Doc danh sach thuat ngu / ten rieng tu file glossary (moi dong 1 muc),
    ghep thanh 1 cau "goi y" giup Whisper nhan dung chinh ta cac tu chuyen
    nganh / ten rieng hay bi nghe nham.
    """
    if not glossary_path or not os.path.exists(glossary_path):
        return ""
    with open(glossary_path, encoding="utf-8") as f:
        terms = [line.strip() for line in f if line.strip()]
    return ", ".join(terms)


def format_timestamp_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path, word_level=False):
    lines, idx = [], 1
    if word_level:
        for seg in segments:
            for w in seg.get("words", []):
                if "start" not in w or "end" not in w:
                    continue
                lines += [str(idx),
                          f"{format_timestamp_srt(w['start'])} --> {format_timestamp_srt(w['end'])}",
                          w["word"], ""]
                idx += 1
    else:
        for seg in segments:
            lines += [str(idx),
                      f"{format_timestamp_srt(seg['start'])} --> {format_timestamp_srt(seg['end'])}",
                      seg["text"].strip(), ""]
            idx += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_vtt(segments, path):
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp_srt(seg["start"]).replace(",", ".")
        end = format_timestamp_srt(seg["end"]).replace(",", ".")
        lines += [f"{start} --> {end}", seg["text"].strip(), ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="Duong dan file video (hoac audio .wav/.mp3)")
    ap.add_argument("--out", default="./out", help="Thu muc ket qua")
    ap.add_argument("--model", default="large-v3", help="Whisper model: large-v3 / medium / small")
    ap.add_argument("--language", default="en", help="Ma ngon ngu: en, vi, ...")
    ap.add_argument("--device", default="cuda", help="cuda hoac cpu")
    ap.add_argument("--compute_type", default="float16", help="float16 (GPU) / int8 (CPU)")
    ap.add_argument("--glossary", default=None, help="File .txt liet ke thuat ngu/ten rieng, moi dong 1 muc")
    ap.add_argument("--hf_token", default=None, help="HuggingFace token, chi can khi dung --diarize")
    ap.add_argument("--diarize", action="store_true", help="Phan biet nguoi noi (video co nhieu nguoi)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    audio_path = args.video
    if not audio_path.lower().endswith(".wav"):
        audio_path = os.path.join(args.out, "audio.wav")
        print(f"[1/4] Tach audio -> {audio_path}")
        extract_audio(args.video, audio_path)

    print(f"[2/4] Load model {args.model} ...")
    asr_options = {}
    prompt = build_initial_prompt(args.glossary)
    if prompt:
        asr_options["initial_prompt"] = prompt
    model = whisperx.load_model(
        args.model, args.device, compute_type=args.compute_type,
        language=args.language, asr_options=asr_options or None,
    )
    audio = whisperx.load_audio(audio_path)
    print("[2/4] Transcribing ...")
    result = model.transcribe(audio, language=args.language, batch_size=16)

    print("[3/4] Word-level alignment ...")
    align_model, metadata = whisperx.load_align_model(language_code=args.language, device=args.device)
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, args.device,
        return_char_alignments=False,
    )

    if args.diarize:
        print("[3b] Diarization ...")
        diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=args.hf_token, device=args.device)
        diarize_segments = diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    print("[4/4] Xuat file ket qua ...")
    with open(os.path.join(args.out, "transcript.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    write_srt(result["segments"], os.path.join(args.out, "transcript.srt"), word_level=False)
    write_srt(result["segments"], os.path.join(args.out, "transcript_words.srt"), word_level=True)
    write_vtt(result["segments"], os.path.join(args.out, "transcript.vtt"))

    print("\nXong! Ket qua trong:", args.out)


if __name__ == "__main__":
    main()
```

### Chạy

```bash
python transcribe_align.py video.mp4 --out ./out
```

Kết quả trong thư mục `out/`:

| File | Nội dung |
|---|---|
| `transcript.srt` | Caption theo câu — dùng gắn phụ đề thông thường |
| `transcript_words.srt` | Caption từng từ — kiểu karaoke, highlight theo từ |
| `transcript.vtt` | Định dạng WebVTT (dùng cho web/HTML5 video) |
| `transcript.json` | Timestamp đầy đủ mức từ, dùng để xử lý/đối chiếu thêm |

**Các cờ hữu ích:**
- `--language vi` — nếu video tiếng Việt (đổi theo ngôn ngữ audio)
- `--device cpu --compute_type int8` — nếu máy không có GPU NVIDIA
- `--model medium` — model nhẹ hơn, nhanh hơn nếu máy yếu (đánh đổi độ chính xác)
- `--glossary terms.txt` — file `.txt` liệt kê tên riêng/thuật ngữ chuyên ngành (mỗi dòng 1 mục), giúp Whisper nhận dạng đúng chính tả các từ hay bị nghe nhầm
- `--diarize --hf_token <token>` — nếu video có nhiều người nói và cần phân biệt ai nói câu nào (cần token HuggingFace, xin miễn phí tại huggingface.co)

---

## 3. (Tùy chọn) Đối chiếu với kịch bản gốc

Nếu bạn có sẵn **script gốc** (Word `.docx`) và người đọc **đọc lệch** so với script, dùng đoạn code sau để so sánh transcript thực tế (từ WhisperX) với script — giúp phát hiện nhanh chỗ đọc khác kịch bản và chỗ nghi ngờ Whisper nghe nhầm thuật ngữ.

Lưu thành **`compare_with_script.py`**:

```python
"""
So sanh transcript.json (WhisperX) voi script.docx goc.
Cach chay:
    python compare_with_script.py --script script.docx --transcript out/transcript.json --out out/compare_report.html
"""

import argparse
import difflib
import json
import re

from docx import Document


def read_script_text(docx_path: str) -> str:
    doc = Document(docx_path)
    return " ".join(p.text for p in doc.paragraphs if p.text.strip())


def normalize_words(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9'\s-]", " ", text)
    return [w for w in text.split() if w]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--out", default="compare_report.html")
    args = ap.parse_args()

    script_words = normalize_words(read_script_text(args.script))

    with open(args.transcript, encoding="utf-8") as f:
        result = json.load(f)
    audio_text = " ".join(
        w.get("word", "") for seg in result["segments"] for w in seg.get("words", [])
    )
    audio_words = normalize_words(audio_text)

    sm = difflib.SequenceMatcher(a=script_words, b=audio_words, autojunk=False)
    rows = [
        (tag, " ".join(script_words[i1:i2]), " ".join(audio_words[j1:j2]))
        for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"
    ]

    html = [
        "<html><head><meta charset='utf-8'><style>",
        "body{font-family:sans-serif;max-width:900px;margin:30px auto}",
        "table{border-collapse:collapse;width:100%}",
        "td,th{border:1px solid #ccc;padding:8px;text-align:left}",
        ".replace{background:#fff3cd}.delete{background:#f8d7da}.insert{background:#d4edda}",
        "</style></head><body>",
        "<h2>Doi chieu Script vs Giong doc thuc te</h2>",
        "<table><tr><th>Loai</th><th>Script</th><th>Audio (WhisperX)</th></tr>",
    ]
    for tag, s, a in rows:
        html.append(f"<tr class='{tag}'><td>{tag}</td><td>{s}</td><td>{a}</td></tr>")
    html.append("</table></body></html>")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"Da tao bao cao: {args.out} ({len(rows)} cho khac biet)")


if __name__ == "__main__":
    main()
```

Chạy:

```bash
pip install python-docx
python compare_with_script.py --script script.docx --transcript out/transcript.json --out out/compare_report.html
```

Mở `compare_report.html` bằng trình duyệt: dòng **replace/delete** = chỗ script và audio khác nhau (ưu tiên giữ theo audio cho caption); dòng có nội dung vô nghĩa ở cột audio thường là Whisper nghe nhầm thuật ngữ — nên nghe lại và sửa tay trong file `.srt`.

---

## 4. Gắn caption vào video

```bash
ffmpeg -i video.mp4 -vf subtitles=out/transcript.srt output_with_subs.mp4
```

> Trên Windows, nếu đường dẫn chứa ký tự `:` (ổ đĩa) hãy dùng dấu `/` thay vì `\` sau `subtitles=` để tránh lỗi escape của ffmpeg.

---

## Câu hỏi thường gặp

**Không có GPU thì có chạy được không?**
Có — thêm `--device cpu --compute_type int8`. Sẽ chậm hơn đáng kể, nên cân nhắc dùng `--model medium` hoặc `small` để bù tốc độ.

**Video tiếng Việt thì sao?**
Thêm `--language vi`. Độ chính xác alignment tiếng Việt hiện chưa tốt bằng tiếng Anh do model align công khai còn hạn chế, nhưng transcribe vẫn dùng được.

**Video có nhiều người đọc, làm sao tách theo từng người?**
Dùng cờ `--diarize` kèm `--hf_token <HuggingFace access token>` (đăng ký miễn phí tại huggingface.co và chấp nhận điều khoản model pyannote/speaker-diarization).

**Lần chạy đầu rất chậm?**
Bình thường — lần đầu WhisperX tải model (vài GB) từ Hugging Face về máy, các lần sau sẽ nhanh hơn nhiều vì đã có cache.
