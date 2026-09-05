title: Hướng dẫn: dùng icon ngẫu nhiên cho thumbnail bài viết
slug: huong-dan-icon.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.05
reading_time: 10 phút đọc
author: Đào Huy Mạnh
excerpt: Thêm một icon tròn đặt giữa nền gradient đó, được
chọn ngẫu nhiên từ một kho icon khoa học miễn phí như bioincons
để mỗi bài trông sinh động hơn.
---
# Hướng dẫn: dùng icon Bioicons ngẫu nhiên cho thumbnail bài viết

Mặc định, mỗi card bài viết trên trang chủ có ô ảnh đại diện (thumbnail)
chỉ là nền gradient xanh (navy → xanh lá đậm). Với thiết lập dưới đây,
mỗi bài sẽ có thêm một **icon tròn** đặt giữa nền gradient đó, được
chọn **ngẫu nhiên** từ một kho icon khoa học miễn phí như ([bioicons.com](https://bioicons.com)),
để mỗi bài trông đỡ giống nhau hơn.

Card nào đã có ảnh minh hoạ SVG riêng (kiểu vẽ tay, không phải icon
đơn) thì không bị ảnh hưởng.

---

## 1. Tải icon từ Bioicons

1. Vào **https://bioicons.com**
2. Tìm icon phù hợp chủ đề của trang: virus, DNA, kính hiển vi, tế bào,
   ống nghiệm, máy tính/tin sinh học, biểu đồ, v.v.
3. **Ưu tiên lọc theo giấy phép `CC0`** (Public Domain) — dùng thoải
   mái, không cần ghi công tác giả.
   - Nếu thích một icon giấy phép `CC-BY`, vẫn dùng được, nhưng phải
     ghi công tác giả + nguồn (xem mục 4 bên dưới).
4. Bấm vào icon để tải file `.svg` về máy.
5. Đặt tên file gọn, không dấu, không khoảng trắng — ví dụ:
   `virus.svg`, `dna-helix.svg`, `microscope.svg`, `lab-flask.svg`.

Nên tải khoảng **10–20 icon** trở lên để độ "ngẫu nhiên" rõ rệt (tải
càng nhiều, xác suất trùng icon giữa 2 bài liền kề càng thấp).

## 2. Đặt icon vào đúng thư mục

Trong thư mục gốc của repo (cùng cấp với `index.html`), tạo thư mục:

```
assets/icons/
```

rồi copy toàn bộ các file `.svg` vừa tải vào đó. Cấu trúc cuối cùng
sẽ giống:

```
daohuymanh.github.io/
├── index.html
├── style.css
├── new_post.py
├── retrofit_thumbs.py
└── assets/
    ├── logo-icon.png
    └── icons/
        ├── virus.svg
        ├── dna-helix.svg
        ├── microscope.svg
        └── ...
```

## 3. Cập nhật 2 file đã sửa sẵn

Ghi đè 2 file sau bằng bản đã chỉnh (đã gửi ở tin nhắn trước):

- `style.css` — thêm style cho huy hiệu tròn `.thumb-icon` chứa icon.
- `new_post.py` — thêm hàm `pick_random_icon()`, tự chọn icon ngẫu
  nhiên mỗi khi tạo bài mới.

> Nếu `assets/icons/` chưa có icon nào, `new_post.py` vẫn chạy bình
> thường — thumbnail sẽ chỉ là gradient xanh như trước, không lỗi.

## 4. Gắn icon cho các bài viết ĐÃ CÓ SẴN (chạy 1 lần)

Các bài viết cũ trong `index.html` đang có thumb trống. Chạy script
`retrofit_thumbs.py` (đứng tại thư mục gốc repo, sau khi đã có icon
trong `assets/icons/`):

```bash
python retrofit_thumbs.py
```

Script sẽ:
- Quét toàn bộ `index.html`, tìm các `<div class="thumb"></div>` đang
  trống.
- Gắn ngẫu nhiên 1 icon trong `assets/icons/` cho mỗi card.
- Bỏ qua card đã có icon hoặc ảnh minh hoạ riêng.

Chạy xong thì mở `index.html` bằng trình duyệt kiểm tra lại, rồi
`git add / commit / push` như thường.

> Có thể chạy lại `retrofit_thumbs.py` nhiều lần nếu muốn xáo lại icon
> cho các bài — script chỉ động vào thumb đang trống nên không phá gì
> đã có.

## 5. Từ giờ mỗi bài mới tự có icon

Từ lúc này, quy trình tạo bài mới **không đổi gì cả** — vẫn gõ:

```bash
python new_post.py bai-moi.md
```

`new_post.py` sẽ tự chọn 1 icon ngẫu nhiên trong `assets/icons/` và
chèn vào card mới, không cần làm thêm bước nào.

## 6. Muốn thêm/bớt icon sau này

- Muốn có thêm icon mới: tải thêm file `.svg` bỏ vào `assets/icons/`
  — không cần sửa code, `new_post.py` tự nhận diện toàn bộ file trong
  thư mục này mỗi lần chạy.
- Muốn bỏ 1 icon không ưng: xoá file `.svg` tương ứng khỏi
  `assets/icons/`.
- Muốn tắt hẳn tính năng icon, quay lại gradient xanh thuần: xoá hết
  file trong `assets/icons/` (hoặc xoá cả thư mục) — code tự rơi về
  hành vi cũ, không cần sửa gì thêm.

## 7. Lưu ý bản quyền

- Icon giấy phép **CC0**: dùng tự do, không bắt buộc ghi công.
- Icon giấy phép **CC-BY**: bắt buộc ghi công tác giả + nguồn ở đâu đó
  công khai trên trang (ví dụ thêm vào trang `copyright.html`), theo
  mẫu:

  ```
  Tên-icon icon by Tên-tác-giả (link tác giả), licensed under
  CC BY 4.0 (link giấy phép)
  ```

  Cách đơn giản nhất để tránh việc này: chỉ tải icon `CC0`.
