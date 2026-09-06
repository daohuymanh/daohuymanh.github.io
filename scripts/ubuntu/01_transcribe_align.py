"""
Buoc 1: Transcribe video/audio bang WhisperX + align o muc TU (word-level),
de caption bam sat CHINH XAC theo giong doc thuc te trong file mp4
(khong ep theo script.docx, vi nguoi doc co the da doc lech script).

Cach chay:
    python 01_transcribe_align.py video.mp4 --out ./out --glossary glossary.txt

Ket qua trong thu muc --out:
    - transcript.srt      caption theo cau (chuan de gan phu de)
    - transcript_words.srt caption highlight tung tu (karaoke-style, tuy chon)
    - transcript.vtt      dinh dang WebVTT
    - transcript.json     full timestamps muc tu, dung de doi chieu / debug
"""

import argparse
import json
import os
import subprocess

import whisperx


def extract_audio(video_path: str, out_wav: str):
    """Tach audio 16kHz mono tu video bang ffmpeg (whisperx yeu cau)."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-ar", "16000", "-ac", "1", out_wav,
    ]
    subprocess.run(cmd, check=True)


def build_initial_prompt(glossary_path: str | None) -> str:
    """
    Doc danh sach thuat ngu/ten rieng (moi dong 1 tu/cum tu) tu file glossary,
    ghep thanh 1 cau moi Whisper "nghe" dung chinh ta hon cho cac tu chuyen nganh
    (vd: OUCRU, BSL-2, HTD, LEAF...). Day KHONG phai la ep transcript theo script,
    chi la goi y phat am/chinh ta cho model.
    """
    default_terms = [
        "OUCRU", "BSL-2", "BSL-3", "HTD",
        "Hospital for Tropical Diseases",
        "LEAF", "Laboratory Efficiency Assessment Framework",
        "Wellcome Trust", "Oxford University", "PI",
    ]
    terms = list(default_terms)
    if glossary_path and os.path.exists(glossary_path):
        with open(glossary_path, encoding="utf-8") as f:
            extra = [line.strip() for line in f if line.strip()]
        terms.extend(extra)
    # loai trung, giu thu tu
    seen = set()
    uniq = []
    for t in terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return ", ".join(uniq)


def format_timestamp_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path, word_level=False):
    lines = []
    idx = 1
    if word_level:
        for seg in segments:
            for w in seg.get("words", []):
                if "start" not in w or "end" not in w:
                    continue
                lines.append(str(idx))
                lines.append(
                    f"{format_timestamp_srt(w['start'])} --> {format_timestamp_srt(w['end'])}"
                )
                lines.append(w["word"])
                lines.append("")
                idx += 1
    else:
        for seg in segments:
            lines.append(str(idx))
            lines.append(
                f"{format_timestamp_srt(seg['start'])} --> {format_timestamp_srt(seg['end'])}"
            )
            lines.append(seg["text"].strip())
            lines.append("")
            idx += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_vtt(segments, path):
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp_srt(seg["start"]).replace(",", ".")
        end = format_timestamp_srt(seg["end"]).replace(",", ".")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"].strip())
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="Duong dan file video.mp4 (hoac audio .wav/.mp3)")
    ap.add_argument("--out", default="./out", help="Thu muc ket qua")
    ap.add_argument("--model", default="large-v3", help="Whisper model: large-v3 / medium / small")
    ap.add_argument("--language", default="en", help="Ma ngon ngu (en, vi, ...)")
    ap.add_argument("--device", default="cuda", help="cuda hoac cpu")
    ap.add_argument("--compute_type", default="float16", help="float16 (GPU) / int8 (CPU)")
    ap.add_argument("--glossary", default=None, help="File .txt liet ke them thuat ngu/ten rieng, moi dong 1 muc")
    ap.add_argument("--hf_token", default=None, help="HuggingFace token, chi can neu dung --diarize")
    ap.add_argument("--diarize", action="store_true", help="Bat phan biet nguoi noi (neu video co nhieu nguoi doc)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # 1) Tach audio neu input la video
    audio_path = args.video
    if not audio_path.lower().endswith(".wav"):
        audio_path = os.path.join(args.out, "audio.wav")
        print(f"[1/4] Tach audio -> {audio_path}")
        extract_audio(args.video, audio_path)

    # 2) Transcribe (lay dung loi doc THUC TE trong audio)
    print(f"[2/4] Load model {args.model} ...")
    model = whisperx.load_model(
        args.model, args.device, compute_type=args.compute_type,
        language=args.language,
        asr_options={"initial_prompt": build_initial_prompt(args.glossary)},
    )
    audio = whisperx.load_audio(audio_path)
    print("[2/4] Transcribing ...")
    result = model.transcribe(audio, language=args.language, batch_size=16)

    # 3) Align o muc TU cho khop chinh xac voi giong doc (dung diem quan trong nhat)
    print("[3/4] Word-level alignment ...")
    align_model, metadata = whisperx.load_align_model(language_code=args.language, device=args.device)
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, args.device,
        return_char_alignments=False,
    )

    # 3b) (tuy chon) diarization neu nhieu nguoi doc
    if args.diarize:
        print("[3b] Diarization ...")
        diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=args.hf_token, device=args.device)
        diarize_segments = diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    # 4) Xuat ket qua
    print("[4/4] Xuat file ket qua ...")
    with open(os.path.join(args.out, "transcript.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    write_srt(result["segments"], os.path.join(args.out, "transcript.srt"), word_level=False)
    write_srt(result["segments"], os.path.join(args.out, "transcript_words.srt"), word_level=True)
    write_vtt(result["segments"], os.path.join(args.out, "transcript.vtt"))

    print("\nXong! File caption khop voi giong doc thuc te trong:")
    print(f"  - {args.out}/transcript.srt        (caption theo cau)")
    print(f"  - {args.out}/transcript_words.srt   (caption tung tu / karaoke)")
    print(f"  - {args.out}/transcript.vtt")
    print(f"  - {args.out}/transcript.json        (dung cho buoc doi chieu script)")


if __name__ == "__main__":
    main()
