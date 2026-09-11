title: Hướng dẫn trích xuất dữ liệu từ website và tổng hợp
slug: web_scraping_to_appscript.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.11
reading_time: 10 phút đọc
author: Mạnh Phượng
excerpt: Tài liệu này tổng hợp toàn bộ quy trình lấy dữ liệu từ một website, tổng hợp thành file csv sau đó tạo appscript để truy xuất từ csv đó
scripts: 08_extract_all_pathogens.py, 09_list_sections.py, 10_crawl_diseases.py, Code.gs, Index.html
---
# Hướng dẫn tổng hợp: Web Scraping → Google Sheet → Web App tra cứu

Tài liệu này tổng hợp toàn bộ quy trình trích xuất dữ liệu từ website. Bài viết này lấy dữ liệu cụ thể Pathogen Safety Data
Sheets (PSDS) và trang "Diseases and conditions" từ canada.ca, lưu thành file
để tìm kiếm, và dựng một web app tra cứu bằng Google Apps Script.

---

## Tổng quan các file

| File | Vai trò |
|---|---|
| 
| `08_extract_all_pathogens.py` | **Crawl toàn bộ PSDS** → `psds_data.json`, `psds_search.csv` |
| `09_list_sections.py` | Thống kê mỗi pathogen có những mục nào |
| `10_crawl_diseases.py` | **Crawl phần "Diseases and conditions"** (Causes/Symptoms/Risks/...) → `diseases_data.json`, `diseases_search.csv` |
| `Code.gs` + `Index.html` | Web app Google Apps Script để tra cứu theo tên tác nhân |

Chỉ cần 2 thư viện Python:

```bash
pip install requests beautifulsoup4
```

---

## Phần 1 — Crawl dữ liệu PSDS

### 1.1. Chạy script chính

```bash
python3 08_extract_all_pathogens.py
```

Script sẽ:
1. Vào trang index PSDS, lấy danh sách link tất cả các pathogen (bỏ qua trang
   template không phải pathogen thật).
2. Với mỗi trang, **xóa phần menu/header/footer** của khung web (banner, menu
   phụ, footer chuẩn của canada.ca) trước khi tìm nội dung — tránh bị lẫn chữ
   "Menu", "Language selection"... vào dữ liệu.
3. Tách nội dung theo cấu trúc heading (`h2` → `h5`), tạo đường dẫn dạng
   `Section I – Infectious agent > Characteristics > Brief description`.
4. **Loại bỏ chú thích "Footnote N"** — canada.ca gắn số tham khảo bằng chữ ẩn
   (`<span class="wb-inv">Footnote</span>`) ngay trong đoạn văn, nếu không xử
   lý sẽ bị lẫn chữ "Footnote 1", "Footnote 2"... vào text.
5. Lưu ra 2 file:
   - **`psds_data.json`** — dữ liệu đầy đủ, giữ cấu trúc cây theo heading.
   - **`psds_search.csv`** — dạng phẳng: `pathogen, url, section_path, text`
     — 1 dòng = 1 mục nội dung, dễ lọc/tìm kiếm.

Có ~230 pathogen, script chờ 1 giây giữa mỗi request nên mất vài phút. Muốn
test nhanh, sửa tạm trong file:

```python
psds_links = psds_links[:5]   # chỉ lấy 5 trang đầu để test
```

### 1.2. Xem mỗi pathogen có những mục nào

```bash
python3 09_list_sections.py
```

Xuất thêm 2 file:
- `sections_by_pathogen.csv` — liệt kê mục theo từng pathogen.
- `section_inventory.csv` — thống kê mục nào phổ biến (xuất hiện ở bao nhiêu %
  pathogen), giúp biết nên lọc theo tên mục nào khi tìm kiếm.

### 1.3. Lọc/tìm kiếm nhanh bằng pandas hoặc grep

```python
import pandas as pd
df = pd.read_csv("psds_search.csv")

# Theo tên pathogen
df[df["pathogen"].str.contains("Zika", case=False, na=False)]

# Theo tên mục
df[df["section_path"].str.contains("Pathogenicity", case=False, na=False)]

# Theo từ khóa trong nội dung
df[df["text"].str.contains("Guillain", case=False, na=False)]
```

```bash
grep -i "malaria" psds_search.csv | grep -i "pathogenicity"
```

---

## Phần 2 — Crawl phần "Diseases and conditions" (Causes/Symptoms/Risks...)

Lưu ý: đây là **phần khác** với PSDS — PSDS thiên về an toàn sinh học
(`pathogen-safety-data-sheets-risk-assessment/...`), còn phần này là trang
thông tin bệnh cho công chúng (`diseases/...`), ví dụ trang
`symptoms-malaria.html`. PSDS **không có** mục "Symptoms" riêng; thông tin
triệu chứng trong PSDS nằm lồng trong mục `Pathogenicity and toxicity`.

```bash
python3 10_crawl_diseases.py
```

Script sẽ:
1. Đọc bảng danh sách bệnh ở trang index, **chỉ giữ link thuộc canada.ca**
   (bỏ link ra ngoài như veterans.gc.ca, camh.ca...).
2. Với mỗi bệnh, tự phát hiện xem đó là **trang hub** (có heading "Services
   and information" dẫn tới các trang con Causes/Symptoms/Risks/Treatment/
   Prevention/...) hay **trang đơn**. Nếu là hub, crawl luôn từng trang con.
3. Áp dụng cùng cách xử lý sạch dữ liệu như Phần 1 (xóa menu/footer, xóa
   "Footnote N").
4. Lưu ra `diseases_data.json` và `diseases_search.csv` (thêm cột
   `page_title` để biết dòng đó thuộc trang con nào, ví dụ "Symptoms").

Tra cứu tương tự:
```python
df = pd.read_csv("diseases_search.csv")
df[(df["disease"].str.contains("Malaria", case=False))
   & (df["page_title"].str.contains("Symptoms", case=False))]
```

---

## Phần 3 — Đưa dữ liệu lên Google Sheet

1. Mở **Google Sheets** → tạo sheet mới.
2. **File > Import** → **Upload** → chọn `psds_search.csv`.
3. Ở bước import, chọn **"Replace current sheet"** (hoặc "Insert new sheet"
   nếu muốn giữ nhiều bộ dữ liệu trong cùng file, ví dụ thêm cả
   `diseases_search.csv` vào 1 sheet khác).
4. Kiểm tra dòng đầu tiên là header đúng 4 cột: `pathogen, url, section_path, text`.

> Nếu bạn đặt tên sheet khác `Sheet1`, nhớ sửa lại ở bước 4.2 bên dưới.

---

## Phần 4 — Dựng web app tra cứu bằng Google Apps Script

### 4.1. Mở Apps Script

Trong Google Sheet vừa tạo: **Extensions > Apps Script**.

### 4.2. Dán code backend

Xóa nội dung `Code.gs` mặc định, dán toàn bộ nội dung file **`Code.gs`** đã
cung cấp. File này gồm:
- `doGet()` — phục vụ trang web.
- `getPathogenList()` — trả về danh sách tên tác nhân (không trùng, A-Z).
- `getPathogenData(pathogenName)` — trả về toàn bộ mục PSDS của 1 tác nhân.

Nếu sheet của bạn không tên `Sheet1`, sửa dòng:
```javascript
const SHEET_NAME = "Sheet1";
```

### 4.3. Dán giao diện web

**File > New > HTML**, đặt tên chính xác là **`Index`**, dán nội dung file
**`Index.html`** đã cung cấp. Giao diện này có:
- Ô nhập liệu với gợi ý tự động (`<datalist>`) — gõ vài chữ là hiện gợi ý tên
  tác nhân.
- Tự khớp gần đúng nếu gõ không chính xác 100%.
- Hiển thị từng mục PSDS kèm link về trang gốc trên canada.ca.

### 4.4. Deploy

**Deploy > New deployment**:
- Chọn loại: **Web app**
- Execute as: **Me**
- Who has access: **Anyone** (hoặc giới hạn trong tổ chức nếu muốn riêng tư)

Bấm **Deploy**, copy URL được cấp — đó là địa chỉ web app tra cứu.

### 4.5. Sử dụng

Mở URL → gõ hoặc chọn tên tác nhân → toàn bộ mục PSDS (Characteristics,
Pathogenicity and toxicity, Epidemiology...) hiện ra ngay, kèm link gốc.

---

## Tổng kết luồng xử lý

```
canada.ca (PSDS + Diseases)
        │  (08_extract_all_pathogens.py / 10_crawl_diseases.py)
        ▼
psds_data.json / psds_search.csv
diseases_data.json / diseases_search.csv
        │  (Google Sheets > File > Import)
        ▼
Google Sheet
        │  (Code.gs + Index.html qua Apps Script)
        ▼
Web app tra cứu theo tên tác nhân
```

## Ghi chú chung

- Luôn tôn trọng server: giữ nguyên `time.sleep(1)` giữa các request khi crawl.
- Nếu chạy lại script crawl, file cũ sẽ bị ghi đè — đổi tên bản cũ nếu muốn
  giữ lịch sử.
- Cấu trúc heading giữa các trang không hoàn toàn giống nhau 100% (trang cũ
  vs mới), nên khi lọc theo `section_path` nên dùng khớp một phần
  (`str.contains`) thay vì so khớp tuyệt đối.
- Dữ liệu ~5.000 dòng nên Apps Script đọc Sheet vẫn đủ nhanh; nếu sau này dữ
  liệu lớn hơn nhiều, có thể cần thêm `CacheService` trong `Code.gs`.
