# Tạo caption (.srt) từ video .mp4 bằng Google Colab (WhisperX)

> Hướng dẫn này giúp bạn tạo phụ đề **khớp chính xác theo giọng đọc thực tế** trong video, chạy hoàn toàn trên **Google Colab** — không cần máy mạnh, không cần cài gì trên máy tính cá nhân, có GPU miễn phí.

## Bạn cần gì

- Một tài khoản Google (để dùng Colab)
- File video `.mp4` cần tạo caption
- Vài phút chờ (tuỳ độ dài video, thường 3–8 phút xử lý cho mỗi 20–30 phút audio khi dùng GPU)

---

## Bước 1 — Mở Google Colab và bật GPU

1. Vào **https://colab.research.google.com** → **New notebook**
2. Vào menu **Runtime → Change runtime type**
3. Chọn **T4 GPU** → **Save**

---

## Bước 2 — Cài đặt WhisperX

Dán vào ô đầu tiên và chạy (nhấn Shift+Enter):

```python
# Cell 1: cài đặt
!pip install -q "numpy<2.3" whisperx
```

> Có thể xuất hiện vài dòng cảnh báo màu vàng/trắng kiểu `ERROR: pip's dependency resolver...` — đây chỉ là **warning xung đột phiên bản** giữa whisperx và các package có sẵn khác trong Colab (gradio, diffusers...), **không phải lỗi chặn cài đặt**, có thể bỏ qua.

Sau khi cell này chạy xong: vào **Runtime → Restart session** (không phải Disconnect), rồi chạy tiếp các cell bên dưới — **không cần chạy lại Cell 1**.

---

## Bước 3 — Upload video

```python
# Cell 2: upload file mp4
from google.colab import files
uploaded = files.upload()   # chọn file .mp4 từ máy bạn
```

Chạy xong, kiểm tra tên file chính xác đã upload (nếu không chắc tên):

```python
!ls
```

---

## Bước 4 — Tách audio từ video (dùng ffmpeg có sẵn trong Colab)

```python
# Cell 3: tách audio
!ffmpeg -y -i video.mp4 -ar 16000 -ac 1 audio.wav
```

> Đổi `video.mp4` thành đúng tên file bạn vừa upload nếu khác.

---

## Bước 5 — Transcribe + align theo giọng đọc thật (tiếng Anh)

```python
# Cell 4: transcribe + word-level alignment
import whisperx

audio_file = "audio.wav"
device = "cuda"

model = whisperx.load_model("large-v3", device, compute_type="float16", language="en")
audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, language="en", batch_size=16)

align_model, metadata = whisperx.load_align_model(language_code="en", device=device)
result = whisperx.align(result["segments"], align_model, metadata, audio, device)
```

**Vì sao có bước align riêng?** Whisper gốc chỉ cho timestamp theo câu, có thể lệch vài trăm mili-giây đến vài giây so với giọng nói thật. Bước `align` dùng model wav2vec2 để tính lại timestamp ở **mức từng từ**, cho caption khớp âm thanh chính xác hơn nhiều.

---

## Bước 6 — Xuất file .srt và tải về máy

```python
# Cell 5: xuất srt
def fmt(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

lines = []
for i, seg in enumerate(result["segments"], 1):
    lines += [str(i), f"{fmt(seg['start'])} --> {fmt(seg['end'])}", seg["text"].strip(), ""]

with open("video.srt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

files.download("video.srt")
```

File `video.srt` sẽ tự động tải về máy bạn khi chạy xong.

---

## (Tuỳ chọn) Gắn caption thẳng vào video

Nếu muốn xuất luôn video có sẵn phụ đề (thay vì file `.srt` rời), chạy thêm:

```python
# Cell 6 (tuỳ chọn): gắn caption vào video rồi tải về
!ffmpeg -y -i video.mp4 -vf subtitles=video.srt output_with_subs.mp4
files.download("output_with_subs.mp4")
```

---

## Mẹo & lưu ý

| Tình huống | Cách xử lý |
|---|---|
| Video dài (>30–40 phút) | Đổi `"large-v3"` thành `"medium"` ở Cell 4 để tránh dùng hết GPU quota của Colab free tier |
| Video/audio không phải tiếng Anh | Đổi cả 2 chỗ `language="en"` và `language_code="en"` sang mã ngôn ngữ tương ứng (vd `"vi"` cho tiếng Việt) |
| Muốn caption từng từ kiểu karaoke | Lặp qua `seg["words"]` thay vì `seg["text"]` khi ghi file srt |
| Colab bị ngắt kết nối giữa chừng | Free tier giới hạn thời lượng dùng GPU liên tục — thử lại vào giờ khác, hoặc rút ngắn video, hoặc nâng cấp Colab Pro |
| Có nhiều người nói, cần tách theo người | Dùng thêm `whisperx.diarize.DiarizationPipeline` với `--hf_token` (cần đăng ký free tại huggingface.co) |

---

## Tóm tắt toàn bộ code (copy nhanh)

```python
# ==== Cell 1 ====
!pip install -q "numpy<2.3" whisperx
# -> Runtime > Restart session, rồi chạy tiếp từ đây, KHÔNG chạy lại cell này

# ==== Cell 2 ====
from google.colab import files
uploaded = files.upload()

# ==== Cell 3 ====
!ffmpeg -y -i video.mp4 -ar 16000 -ac 1 audio.wav

# ==== Cell 4 ====
import whisperx
device = "cuda"
model = whisperx.load_model("large-v3", device, compute_type="float16", language="en")
audio = whisperx.load_audio("audio.wav")
result = model.transcribe(audio, language="en", batch_size=16)
align_model, metadata = whisperx.load_align_model(language_code="en", device=device)
result = whisperx.align(result["segments"], align_model, metadata, audio, device)

# ==== Cell 5 ====
def fmt(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

lines = []
for i, seg in enumerate(result["segments"], 1):
    lines += [str(i), f"{fmt(seg['start'])} --> {fmt(seg['end'])}", seg["text"].strip(), ""]

with open("video.srt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

files.download("video.srt")
```
