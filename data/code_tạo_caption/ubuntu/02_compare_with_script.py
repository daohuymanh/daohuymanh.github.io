"""
Buoc 2: Doi chieu transcript.json (loi doc THUC TE, tu whisperx) voi script.docx
(kich ban goc), de:
  1) Phat hien nhung cho nguoi doc DOC LECH so voi script (giu nguyen theo audio,
     vi caption phai dung voi nhung gi nghe duoc).
  2) Phat hien nhung cho co the la LOI NHAN DIEN cua Whisper doi voi thuat ngu/ten
     rieng (vd nghe nham "OUCRU" thanh "oh crew") de ban xem xet sua lai transcript
     cho dung chinh ta, KHONG doi timestamp.

Cach chay:
    python 02_compare_with_script.py --script script.docx --transcript out/transcript.json --out out/compare_report.html
"""

import argparse
import difflib
import json
import re

from docx import Document


def read_script_text(docx_path: str) -> str:
    doc = Document(docx_path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return " ".join(parts)


def normalize_words(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9'\s-]", " ", text)
    return [w for w in text.split() if w]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, help="script.docx goc")
    ap.add_argument("--transcript", required=True, help="transcript.json tu buoc 1 (whisperx)")
    ap.add_argument("--out", default="compare_report.html", help="File bao cao HTML ket qua")
    args = ap.parse_args()

    script_text = read_script_text(args.script)
    script_words = normalize_words(script_text)

    with open(args.transcript, encoding="utf-8") as f:
        result = json.load(f)

    transcript_words_raw = []  # (word_text, start, end)
    for seg in result["segments"]:
        for w in seg.get("words", []):
            transcript_words_raw.append((w.get("word", ""), w.get("start"), w.get("end")))
    transcript_norm = normalize_words(" ".join(w[0] for w in transcript_words_raw))

    sm = difflib.SequenceMatcher(a=script_words, b=transcript_norm, autojunk=False)
    ops = sm.get_opcodes()

    rows = []
    for tag, i1, i2, j1, j2 in ops:
        script_chunk = " ".join(script_words[i1:i2])
        audio_chunk = " ".join(transcript_norm[j1:j2])
        if tag == "equal":
            continue
        rows.append((tag, script_chunk, audio_chunk))

    html = ["<html><head><meta charset='utf-8'>",
            "<style>",
            "body{font-family:sans-serif;max-width:900px;margin:30px auto;}",
            "table{border-collapse:collapse;width:100%;}",
            "td,th{border:1px solid #ccc;padding:8px;vertical-align:top;text-align:left;}",
            ".replace{background:#fff3cd;} .delete{background:#f8d7da;} .insert{background:#d4edda;}",
            "</style></head><body>",
            "<h2>Doi chieu Script vs Giong doc thuc te (transcript WhisperX)</h2>",
            "<p><b>replace</b> = script noi khac voi audio (uu tien giu ban audio cho caption).<br>",
            "<b>delete</b> = co trong script nhung KHONG doc trong audio.<br>",
            "<b>insert</b> = doc them trong audio nhung KHONG co trong script.<br>",
            "Neu doan 'audio' trong o replace/insert trong vo nghia (vd la ten rieng bi nghe nham), ",
            "rat co the la loi nhan dien cua Whisper — nen nghe lai doan do va sua transcript.json/srt thu cong.</p>",
            "<table><tr><th>Loai</th><th>Script (goc)</th><th>Audio (WhisperX nhan dien)</th></tr>"]

    for tag, script_chunk, audio_chunk in rows:
        html.append(
            f"<tr class='{tag}'><td>{tag}</td><td>{script_chunk}</td><td>{audio_chunk}</td></tr>"
        )
    html.append("</table></body></html>")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"Da tao bao cao doi chieu: {args.out}")
    print(f"Tong so cho khac biet: {len(rows)}")


if __name__ == "__main__":
    main()
