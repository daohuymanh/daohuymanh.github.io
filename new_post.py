#!/usr/bin/env python3
"""
new_post.py — chuyển 1 file .md (Markdown chuẩn, có front matter)
thành bài viết .html đúng style trang, và tự chèn card vào index.html.

Cài thư viện cần thiết (1 lần duy nhất):
    pip install markdown

Cách dùng (trong Termux, đứng tại thư mục repo daohuymanh.github.io):
    python new_post.py bai-moi.md

Sau khi chạy xong, dùng git add / commit / push như bình thường.
"""

import random
import re
import sys
import html
from pathlib import Path

try:
    import markdown as md
except ImportError:
    sys.exit(
        "Lỗi: chưa cài thư viện 'markdown'.\n"
        "Chạy lệnh sau rồi thử lại: pip install markdown"
    )

REPO_DIR = Path(__file__).resolve().parent

# Thư mục chứa các icon .svg tải từ https://bioicons.com (ưu tiên icon
# giấy phép CC0, khỏi phải ghi công tác giả). Mỗi lần tạo bài mới,
# script sẽ chọn ngẫu nhiên 1 icon trong thư mục này để thay cho
# card thumbnail toàn màu xanh mặc định.
ICONS_DIR = REPO_DIR / "assets" / "icons"

VALID_TAGS = {
    "tag--congdong": "Sức khoẻ cộng đồng",
    "tag--tools": "Công cụ phân tích",
    "tag--miendich": "Miễn dịch học",
    "tag--phantu": "Sinh học phân tử",
    "tag--thongtin": "Thông tin y sinh",
}

MD_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]

# pandoc (khi xuất sang markdown) hay ghi kèm kích thước ảnh/bảng gốc
# theo cú pháp riêng, ví dụ: {width="5.72in" height="4.27in"}
# hoặc {#tbl:abc}, {.class}. Thư viện `markdown` không hiểu cú pháp
# này nên để nguyên thành chữ hiển thị ra ngoài — regex dưới đây dọn
# sạch các đoạn đó trước khi chèn vào bài viết.
PANDOC_ATTR_RE = re.compile(
    r'\{[^{}\n]{0,150}(?:width\s*=|height\s*=|#[\w:-]|\.[\w-])[^{}\n]{0,150}\}'
)


def strip_pandoc_attrs(text: str) -> str:
    cleaned = PANDOC_ATTR_RE.sub("", text)
    # dọn khoảng trắng thừa để lại sau khi xoá
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def pick_random_icon() -> str:
    """Chọn ngẫu nhiên 1 file .svg trong assets/icons/ và trả về
    đường dẫn tương đối để chèn vào thẻ <img>. Nếu thư mục chưa
    tồn tại hoặc chưa có icon nào, trả về chuỗi rỗng — card sẽ
    hiển thị nền gradient xanh như trước (không lỗi)."""
    if not ICONS_DIR.exists():
        return ""
    icons = sorted(p.name for p in ICONS_DIR.glob("*.svg"))
    if not icons:
        return ""
    return f"assets/icons/{random.choice(icons)}"


def thumb_icon_html(icon_path: str) -> str:
    if not icon_path:
        return ""
    return f'<div class="thumb-icon"><img src="{icon_path}" alt="" loading="lazy"></div>'


# =========================================================
# 1. Đọc & tách front matter / nội dung markdown
# =========================================================

def parse_input(text: str):
    if "---" not in text:
        sys.exit("Lỗi: không tìm thấy dòng '---' ngăn cách front matter và nội dung.")

    head, body = text.split("---", 1)

    meta = {}
    for line in head.strip().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip().lower()] = val.strip()

    required = ["title", "slug", "tag", "tag_label", "date", "reading_time", "author", "excerpt"]
    missing = [k for k in required if not meta.get(k)]
    if missing:
        sys.exit(f"Lỗi: thiếu trường bắt buộc trong front matter: {', '.join(missing)}")

    if meta["tag"] not in VALID_TAGS:
        sys.exit(
            f"Lỗi: tag '{meta['tag']}' không hợp lệ. "
            f"Chỉ dùng 1 trong: {', '.join(VALID_TAGS)}"
        )

    if not meta["slug"].endswith(".html"):
        meta["slug"] += ".html"

    return meta, body.strip("\n")


# =========================================================
# 2. Markdown -> HTML (dùng thư viện markdown chuẩn)
# =========================================================

def convert_body(body: str, is_html: bool) -> tuple[str, str]:
    """Trả về (lead_paragraph_html, rest_html).

    is_html=False: body là Markdown, chuyển bằng thư viện markdown.
    is_html=True : body đã là HTML sẵn (ví dụ xuất từ
                   `pandoc -t html`) — giữ nguyên, không qua markdown.
    """
    body = strip_pandoc_attrs(body)
    rendered = body if is_html else md.markdown(body, extensions=MD_EXTENSIONS)

    # Tách đoạn <p> đầu tiên ra làm lead (câu mở đầu to hơn)
    m = re.match(r"\s*<p>(.*?)</p>\s*", rendered, re.S)
    if m:
        lead_html = m.group(1).strip()
        rest_html = rendered[m.end():]
    else:
        lead_html = ""
        rest_html = rendered

    # Không thụt lề thủ công ở đây: bên trong <pre><code> mọi khoảng
    # trắng đều hiển thị nguyên văn, nên thêm dấu cách/indent vào sẽ
    # làm sai lệch nội dung code. Giữ nguyên HTML do thư viện sinh ra.
    return lead_html, rest_html.strip("\n")


# =========================================================
# 3. Khung HTML bài viết (giống bai-viet-mau.html)
# =========================================================

ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Mạnh Phượng</title>
<meta name="description" content="{excerpt}">
<meta name="author" content="{author}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a href="index.html" class="logo">
      <img class="logo-mark" src="assets/logo-icon.png" alt="Logo Mạnh Phượng">
      <span class="logo-text">
        <span class="logo-name">Mạnh Phượng</span>
        <span class="logo-tagline">Biomedicine &amp; Bioinformatics</span>
      </span>
    </a>
    <nav class="primary-nav" id="primaryNav">
      <a href="index.html">trang chủ</a>
      <a href="index.html#bai-viet">bài viết</a>
      <a href="index.html#chu-de">chủ đề</a>
      <a href="index.html#gioi-thieu">giới thiệu</a>
      <a href="index.html#lien-he">liên hệ</a>
    </nav>
    <button class="nav-toggle" id="navToggle" aria-label="Mở menu" aria-expanded="false" aria-controls="primaryNav"></button>
  </div>
</header>

<div class="track"></div>

<div class="wrap" style="padding-top:24px;">
  <a href="index.html#bai-viet" class="back-link">← quay lại danh sách bài viết</a>
</div>

<header class="article-header">
  <div class="wrap">
    <span class="tag {tag}">{tag_label}</span>
    <h1>{title}</h1>
    <div class="article-meta">
      <span>{date}</span>
      <span>{reading_time}</span>
    </div>
    <div class="article-author">
      <strong>Tác giả:</strong> {author}
    </div>
  </div>
</header>

<article class="post-body">
  <div class="wrap">

    <p class="lead">
      {lead}
    </p>

{body}

    <div class="article-license">
      <p class="license-title">Bản quyền &amp; giấy phép</p>
      <p>© 2026 {author}.</p>
      <p>
        Bài viết này được cấp phép theo
        <a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="license noopener">
          Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
        </a>.
      </p>
      <p>
        Bạn được phép chia sẻ và điều chỉnh nội dung cho mục đích phi thương mại,
        với điều kiện ghi công tác giả phù hợp và dẫn liên kết tới bài viết gốc.
      </p>
    </div>

  </div>
</article>

<div class="track"></div>

<footer class="site-footer">
  <div class="wrap">
    <div class="foot-brand">
      <strong>© 2026 Mạnh Phượng</strong>
      <span>· Ghi chép Y Sinh &amp; Bioinformatics</span>
    </div>
    <ul class="foot-links">
      <li><a href="copyright.html">Copyright &amp; License</a></li>
      <li><a href="https://github.com/daohuymanh" target="_blank" rel="noopener">GitHub</a></li>
      <li><a href="https://orcid.org/0000-0003-3874-5051" target="_blank" rel="noopener">ORCID</a></li>
      <li><a href="mailto:daohuymanh@gmail.com">daohuymanh@gmail.com</a></li>
    </ul>
  </div>
</footer>

<script>
const navToggle = document.getElementById("navToggle");
const primaryNav = document.getElementById("primaryNav");
navToggle.addEventListener("click", () => {{
  const isOpen = primaryNav.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", isOpen);
}});
</script>

</body>
</html>
"""

CARD_TEMPLATE = """      <!-- {title} -->
      <a href="{slug}" class="post-card">
        <div class="thumb">{thumb_icon}</div>
        <div class="body">
          <span class="tag {tag}">
            {tag_label}
          </span>
          <h3>
            {title}
          </h3>
          <p class="excerpt">
            {excerpt}
          </p>
          <div class="post-meta">
            <span>
              {date}
            </span>
            <span>
              {reading_time}
            </span>
          </div>
        </div>
      </a>

"""


# =========================================================
# 4. Chèn card vào index.html
# =========================================================

def insert_card_into_index(index_path: Path, card_html: str):
    if not index_path.exists():
        print(f"⚠️  Không tìm thấy {index_path.name} — bỏ qua bước chèn card. Bạn tự thêm thủ công nhé.")
        return

    text = index_path.read_text(encoding="utf-8")
    marker = '<div class="post-grid featured-grid">'
    idx = text.find(marker)
    if idx == -1:
        print("⚠️  Không tìm thấy vị trí lưới bài viết trong index.html — bạn tự chèn card thủ công.")
        return

    insert_at = idx + len(marker) + 1  # ngay sau dòng mở thẻ
    new_text = text[:insert_at] + "\n" + card_html + text[insert_at:]
    index_path.write_text(new_text, encoding="utf-8")
    print(f"✔ Đã chèn card bài viết vào đầu danh sách trong {index_path.name}")


# =========================================================
# main
# =========================================================

def main():
    if len(sys.argv) != 2:
        sys.exit("Cách dùng: python new_post.py duong-dan-file.md  (hoặc .html)")

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        sys.exit(f"Không tìm thấy file: {input_path}")

    is_html = input_path.suffix.lower() in (".html", ".htm")

    meta, body = parse_input(input_path.read_text(encoding="utf-8"))
    lead_html, rest_html = convert_body(body, is_html)

    article_html = ARTICLE_TEMPLATE.format(
        title=esc(meta["title"]),
        excerpt=esc(meta["excerpt"]),
        author=esc(meta["author"]),
        tag=meta["tag"],
        tag_label=esc(meta["tag_label"]),
        date=esc(meta["date"]),
        reading_time=esc(meta["reading_time"]),
        lead=lead_html,
        body=rest_html.rstrip("\n"),
    )

    out_path = REPO_DIR / meta["slug"]
    out_path.write_text(article_html, encoding="utf-8")
    print(f"✔ Đã tạo bài viết: {out_path.name}")

    icon_path = pick_random_icon()
    card_html = CARD_TEMPLATE.format(
        title=esc(meta["title"]),
        slug=meta["slug"],
        tag=meta["tag"],
        tag_label=esc(meta["tag_label"]),
        excerpt=esc(meta["excerpt"]),
        date=esc(meta["date"]),
        reading_time=esc(meta["reading_time"]),
        thumb_icon=thumb_icon_html(icon_path),
    )
    insert_card_into_index(REPO_DIR / "index.html", card_html)

    print("\nXong! Kiểm tra lại 2 file rồi git add / commit / push như bình thường.")


if __name__ == "__main__":
    main()
