# Hướng dẫn: cấu trúc site mới (posts/, scripts/, js/) và file mẫu đính kèm bài viết

Tài liệu này gộp lại toàn bộ thay đổi về cấu trúc thư mục của site và
cách dùng tính năng "tải file mẫu" trong bài viết.

---

## 1. Cấu trúc thư mục mới

```
daohuymanh.github.io/
├── index.html            ← trang chủ, giữ nguyên vị trí gốc
├── copyright.html        ← giữ nguyên vị trí gốc
├── style.css              ← giữ nguyên vị trí gốc
├── js/
│   └── main.js             ← JS xử lý menu, dùng chung mọi trang
├── assets/
│   ├── logo-icon.png
│   ├── icons/                ← icon Bioicons cho thumbnail ngẫu nhiên
│   └── (ảnh khác chèn trong bài, ví dụ ảnh trích từ .docx)
├── posts/
│   └── *.html                ← TOÀN BỘ bài viết, phẳng (không thư mục con)
├── scripts/
│   └── *                     ← file mẫu/script ví dụ nhắc trong bài (.R, .py, .csv, .ipynb...)
├── new_post.py             ← tạo bài mới (đã cập nhật cho cấu trúc này)
├── retrofit_thumbs.py      ← gắn icon ngẫu nhiên cho bài cũ (không đổi)
└── migrate.py              ← script dời file 1 LẦN DUY NHẤT sang cấu trúc mới
```

**Vì sao đổi:** trước đây mọi bài viết nằm chung 1 cấp với
`index.html`, càng viết nhiều càng rối. Giờ tách riêng:
- `posts/` — nội dung bài viết.
- `scripts/` — file dùng để minh hoạ/cho tải trong các bài hướng dẫn công cụ.
- `js/main.js` — gộp đoạn `<script>` xử lý menu đang bị lặp lại ở mọi trang.

## 2. Chạy `migrate.py` (chỉ 1 lần)

Nếu bạn còn bài viết cũ đang nằm ở gốc repo (cùng cấp `index.html`),
chạy 1 lần duy nhất để dời hết vào `posts/` và tự sửa link:

```bash
python migrate.py
```

Script sẽ tự động:
- Tạo 3 thư mục `posts/`, `scripts/`, `js/` nếu chưa có.
- Dời mọi file `.html` ở gốc (trừ `index.html`, `copyright.html`,
  `bai-viet-mau.html`) vào `posts/`.
- Tự sửa lại toàn bộ đường dẫn tương đối bên trong mỗi bài vừa dời
  (`style.css` → `../style.css`, `index.html` → `../index.html`,
  `assets/...` → `../assets/...`, kể cả ảnh chèn trong bài từ file
  Word/docx).
- Gộp đoạn `<script>` xử lý menu ở mọi trang thành 1 dòng
  `<script src="js/main.js">` (hoặc `../js/main.js` với bài trong
  `posts/`).
- Cập nhật link các card trong `index.html` để trỏ sang `posts/...`.

An toàn khi chạy lại nhiều lần — bài nào đã dời rồi sẽ không bị sửa
lần 2.

Chạy xong, mở lại `index.html` và vài bài trong `posts/` để kiểm tra
trước khi `git add / commit / push`.

## 3. Tạo bài viết mới — không đổi thao tác

Vẫn dùng đúng lệnh cũ:

```bash
python new_post.py bai-moi.md
```

`new_post.py` giờ tự tạo file trong `posts/` và tự chèn card vào
`index.html` với link đúng — không cần làm gì thêm.

## 4. Đính kèm file mẫu cho bài hướng dẫn công cụ

Nếu bài viết có nhắc tới 1 hoặc nhiều script/file mẫu (ví dụ file
`.R` vẽ biểu đồ, file `.csv` dữ liệu mẫu, file `.py` xử lý dữ liệu),
làm theo 2 bước:

**Bước 1:** bỏ file đó vào thư mục `scripts/` ở gốc repo (đặt tên
gọn, không dấu, không khoảng trắng).

**Bước 2:** khai báo trong front matter của file `.md`, dùng trường
`scripts:` — liệt kê tên file, ngăn cách bằng dấu phẩy. Muốn hiện
nhãn riêng cho từng file (thay vì hiện luôn tên file) thì thêm dấu
`|` sau tên file:

```
title: Vẽ biểu đồ cột số mẫu theo tỉnh với ggplot2
slug: ns1-bar-plot-tinh.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.10
reading_time: 6 phút đọc
author: Mạnh Phượng
excerpt: Hướng dẫn vẽ biểu đồ cột bằng ggplot2 trong R
scripts: ns1_bar_plot.R|Script R vẽ biểu đồ, du-lieu-mau.csv
---
Nội dung bài viết...
```

Kết quả: đầu bài viết tự hiện 1 khối liệt kê từng file kèm nút tải
về (📎 icon + link `download`), không cần viết tay HTML.

- File nào không ghi nhãn sau dấu `|` (như `du-lieu-mau.csv` ở ví dụ
  trên) sẽ hiển thị luôn tên file làm nhãn.
- Không khai báo `scripts:` thì bài viết không có gì thay đổi.
- Vẫn hỗ trợ cú pháp cũ (1 file) từ trước, không cần sửa lại bài đã
  viết theo kiểu này:
  ```
  script: ten-file.py
  script_label: Tải script
  ```

**Muốn cho tải nhiều loại file khác ngoài khối này** (ví dụ chèn
link ngay giữa đoạn văn thay vì đầu bài), viết tay trong nội dung
Markdown:

```markdown
[Tải dữ liệu mẫu (.csv)](../scripts/du-lieu-mau.csv)
```

Nhớ luôn có `../scripts/...` (lùi 1 cấp) vì bài viết nằm trong
`posts/`.

## 5. Icon ngẫu nhiên cho thumbnail — không đổi

Phần này vẫn hoạt động y như trước (xem `HUONG-DAN-ICON.md`): thả
icon `.svg` vào `assets/icons/`, `new_post.py` tự chọn ngẫu nhiên khi
tạo bài mới; `retrofit_thumbs.py` gắn icon cho bài cũ đã có sẵn
trong `index.html`.

## 6. Tóm tắt việc cần làm

1. Ghi đè `index.html`, `style.css`, `new_post.py` bằng bản mới.
2. Tạo `js/main.js`.
3. Copy `migrate.py` vào gốc repo, chạy `python migrate.py` một lần.
4. Từ giờ viết bài như cũ; muốn đính kèm file mẫu thì bỏ vào
   `scripts/` + khai báo `scripts:` trong front matter.
