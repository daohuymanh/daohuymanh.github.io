title: Vẽ biểu đồ cột số mẫu theo tỉnh với ggplot2
slug: ns1-bar-plot-tinh.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.10
reading_time: 6 phút đọc
author: Mạnh Phượng
excerpt: Hướng dẫn vẽ biểu đồ cột bằng ggplot2 trong R
scripts: ns1_bar_plot.R|Script R vẽ biểu đồ, du-lieu-mau.csv, chuyen-doi.py|Script Python xử lý
---

## Bước 1 — Cài đặt

Chạy lệnh sau để cài thư viện cần thiết, bạn có thể xem thêm tại
[trang chủ WhisperX](https://github.com/m-bain/whisperX).

```
pip install whisperx
```

Sau khi cài xong, kiểm tra lại bằng `pip show whisperx`.

## Bước 2 — Các tuỳ chọn

Có 3 chế độ chính:

1. Chạy nhanh, độ chính xác thấp
2. Chạy vừa, cân bằng
3. Chạy chậm, độ chính xác cao nhất

- Tuỳ chọn **GPU** giúp nhanh hơn nhiều
- Tuỳ chọn *CPU* chỉ nên dùng khi video ngắn

> Lưu ý: bản free của Colab giới hạn thời gian dùng GPU liên tục.

## Bảng so sánh

| Chế độ | Tốc độ | Độ chính xác |
|---|---|---|
| fast | Nhanh | Thấp |
| balanced | Vừa | Trung bình |
| accurate | Chậm | Cao |

Đoạn văn kết bài.
