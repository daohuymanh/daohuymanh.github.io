# Khung website — Ghi chép Y Sinh & Bioinformatics

## Cấu trúc file
- `index.html` — trang chủ (hero, bài viết nổi bật, chủ đề, giới thiệu, liên hệ)
- `bai-viet-mau.html` — trang mẫu cho 1 bài viết, copy file này để tạo bài mới
- `style.css` — toàn bộ style dùng chung cho cả site

## Cách deploy lên GitHub Pages (dùng repo đã có: daohuymanh)
1. Tạo repo mới tên `daohuymanh.github.io` (đúng tên này để dùng làm domain gốc),
   hoặc dùng repo bất kỳ rồi bật Pages cho nhánh đó.
2. Copy 3 file trên vào repo.
3. Vào **Settings → Pages**, chọn branch `main`, thư mục `/root`, bấm Save.
4. Sau 1-2 phút, site sẽ có ở `https://daohuymanh.github.io`.

## Cách thêm bài viết mới
1. Copy `bai-viet-mau.html`, đổi tên (ví dụ `docker-nextflow.html`).
2. Sửa `<title>`, tiêu đề `<h1>`, tag chủ đề, ngày tháng, và nội dung trong `<article>`.
3. Ở `index.html`, thêm một thẻ `<a class="post-card">` mới trong phần
   `post-grid` (copy 1 card có sẵn), trỏ `href` sang file bài viết vừa tạo.

## Video
Mỗi trang bài viết đã có sẵn khối `.video-embed` — chỉ cần thay `VIDEO_ID`
bằng mã video YouTube thật (để chế độ "Unlisted" nếu chưa muốn công khai
trên kênh).

## Màu sắc & font (nếu muốn đổi)
Toàn bộ màu và font khai báo ở đầu `style.css` trong khối `:root { ... }` —
đổi giá trị hex ở đó sẽ đổi màu toàn site. Font đang dùng là bộ IBM Plex
(Serif cho tiêu đề, Sans cho nội dung, Mono cho nhãn/dữ liệu) — tải qua
Google Fonts, không cần cài gì thêm.
