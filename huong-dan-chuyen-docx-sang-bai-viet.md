title: Chuyển file Word (.docx) có hình và bảng thành bài viết trên web
slug: huong-dan-chuyen-docx-sang-bai-viet.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.04
reading_time: 7 phút đọc
author: Đào Huy Mạnh
excerpt: Dùng pandoc để chuyển file Word có hình và bảng sang Markdown, rồi qua script new_post.py để ra bài viết đúng style — không cần gõ lại tay.
---
Nếu bạn đã có sẵn nội dung trong file Word (`.docx`) — kể cả có hình ảnh và bảng — không cần gõ lại từ đầu bằng Markdown. Chỉ cần thêm một bước trung gian: dùng `pandoc` chuyển `.docx` sang `.md`, rồi vẫn chạy qua `new_post.py` như bình thường.

## Cài pandoc (chỉ 1 lần)

Trong Termux, chạy:

```
pkg install pandoc
```

Gói này khá nặng (khoảng 150–200MB) vì `pandoc` là chương trình chuyển đổi định dạng văn bản rất lớn, nên tải qua wifi cho nhanh. Sau khi cài xong, không cần cài lại cho những lần sau.

## Đặt tên slug trước khi chuyển

Trước khi chạy lệnh, nghĩ sẵn tên `slug` cho bài viết (không dấu, không khoảng trắng) — ví dụ bài về xét nghiệm miễn dịch sẽ dùng `xet-nghiem-mien-dich`. Tên này sẽ dùng ở cả 2 chỗ: tên thư mục chứa ảnh và tên file `.html` cuối cùng.

## Chuyển docx sang markdown, tách ảnh riêng

Đặt file `.docx` vào thư mục repo, rồi chạy:

```
pandoc bai.docx -t markdown --extract-media=assets/xet-nghiem-mien-dich -o noidung-tho.md
```

Lệnh này làm 2 việc cùng lúc:

- Chuyển toàn bộ nội dung sang Markdown, **giữ nguyên bảng** dưới dạng bảng chữ (pipe table)
- **Tách hết ảnh** trong file Word ra thư mục `assets/xet-nghiem-mien-dich/media/`

> Nhớ đổi `xet-nghiem-mien-dich` thành đúng slug bài của bạn ở cả tên thư mục `--extract-media` lẫn phần `slug` trong front matter ở bước sau — 2 chỗ này phải khớp nhau.

## Thêm front matter vào đầu file

`pandoc` chỉ xuất phần nội dung, không tự thêm phần thông tin bài viết. Mở `noidung-tho.md` bằng app soạn thảo bất kỳ, dán đoạn front matter quen thuộc vào đầu file:

```
title: Tiêu đề bài viết
slug: xet-nghiem-mien-dich.html
tag: tag--miendich
tag_label: Miễn dịch học
date: 2026.09.04
reading_time: 7 phút đọc
author: Đào Huy Mạnh
excerpt: Mô tả ngắn hiện trên card.
---
```

Phần nội dung `pandoc` sinh ra giữ nguyên bên dưới dòng `---`, không cần sửa gì thêm ở bước này.

## Kiểm tra lại đường dẫn ảnh

Đường dẫn ảnh `pandoc` sinh ra thường có dạng `assets/xet-nghiem-mien-dich/media/image1.png` — đã đúng định dạng dùng thẳng trên web, miễn thư mục `assets/xet-nghiem-mien-dich/` nằm cùng cấp với `index.html` trong repo.

Kiểm tra nhanh toàn bộ dòng ảnh bằng lệnh:

```
grep '!\[' noidung-tho.md
```

## Chạy script như bình thường

```
python3 new_post.py noidung-tho.md
```

Script sẽ sinh file `.html` đúng tên `slug`, giữ nguyên bảng và ảnh, rồi tự chèn card vào đầu danh sách trong `index.html` — giống hệt quy trình dùng cho bài viết gõ tay bằng Markdown.

## Kiểm tra kết quả rồi đẩy lên GitHub

Mở file `.html` vừa tạo lên xem thử (hoặc push lên rồi xem trên trình duyệt) để chắc ảnh hiển thị đúng, không vỡ bố cục. Nếu ổn:

```
git add .
git commit -m "thêm bài có hình và bảng"
git push
```

## Vài lưu ý

- Bảng đơn giản (không ô gộp, không nhiều dòng trong 1 ô) thì `pandoc` xuất đúng định dạng ngay. Bảng phức tạp hơn đôi khi `pandoc` xuất ra dạng khác (grid table) — lúc đó cần mở file `.md` sửa lại bảng theo mẫu `| Cột 1 | Cột 2 |`.
- Nếu ảnh trong Word có độ phân giải rất lớn (ảnh chụp màn hình full HD, ảnh máy ảnh), file bài viết sẽ nặng và tải chậm — nên cân nhắc nén ảnh trước khi đưa lên.
- Nội dung dạng bảng/công thức được **chụp màn hình** dán vào Word sẽ chuyển thành ảnh bình thường khi qua `pandoc` — không thể chọn/copy chữ được, vì bản chất Word đã lưu nó như ảnh chứ không phải bảng thật.
