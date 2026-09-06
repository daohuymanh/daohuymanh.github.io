#!/usr/bin/env python3
"""
migrate.py — chạy MỘT LẦN DUY NHẤT để tổ chức lại cấu trúc file của
site theo layout mới:

    posts/      ← toàn bộ bài viết (phẳng, không thư mục con)
    scripts/    ← chỗ để bạn tự bỏ file mẫu/script ví dụ dùng trong bài
    js/main.js  ← JS tách ra từ <script> lặp lại ở mỗi trang

Cách dùng:
    Đứng tại thư mục gốc repo (cùng cấp với index.html), chạy:
        python migrate.py
    rồi chạy thử site (mở index.html, click vài bài viết) trước khi
    git add / commit / push.

Script này AN TOÀN ĐỂ CHẠY LẠI NHIỀU LẦN — nếu 1 bài đã ở trong
posts/ hoặc đã có link "../..." thì sẽ không bị sửa/di chuyển lần 2.
"""

import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
POSTS_DIR = REPO_DIR / "posts"
SCRIPTS_DIR = REPO_DIR / "scripts"
JS_DIR = REPO_DIR / "js"

# Các file KHÔNG di chuyển vào posts/ vì là hạ tầng site, không phải
# bài viết. Thêm tên file vào đây nếu bạn có file đặc biệt khác.
KEEP_AT_ROOT = {
    "index.html",
    "copyright.html",
    "bai-viet-mau.html",  # file mẫu để copy, không phải bài viết thật
}

MAIN_JS = """const navToggle = document.getElementById("navToggle");
const primaryNav = document.getElementById("primaryNav");
navToggle.addEventListener("click", () => {
  const isOpen = primaryNav.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", isOpen);
});
"""


def fix_links_for_moved_file(html: str) -> str:
    """Sửa các đường dẫn tương đối bên trong 1 file bài viết, để dùng
    được từ vị trí mới posts/<file>.html (lùi ra 1 cấp bằng '../')."""
    # index.html (có kèm #fragment hoặc không)
    html = re.sub(r'href="index\.html(#[^"]*)?"', r'href="../index.html\1"', html)
    html = html.replace('href="copyright.html"', 'href="../copyright.html"')
    html = html.replace('href="style.css"', 'href="../style.css"')
    # bất kỳ ảnh/asset nào trong bài (logo, icon, ảnh chèn từ docx...)
    html = re.sub(r'(src|href)="assets/', r'\1="../assets/', html)
    # nếu bài có nhúng script mẫu qua thẻ script_download (thêm sau này)
    html = re.sub(r'(src|href)="scripts/', r'\1="../scripts/', html)
    # gọn JS dùng chung: thay khối <script> nav-toggle bằng 1 dòng include
    html = re.sub(
        r'<script>\s*const navToggle[\s\S]*?</script>',
        '<script src="../js/main.js"></script>',
        html,
    )
    return html


def fix_index_and_root_files():
    """index.html/copyright.html ở lại gốc: chỉ cần gộp <script> lặp
    lại thành 1 dòng include tới js/main.js, không đổi path khác."""
    for name in ("index.html", "copyright.html"):
        path = REPO_DIR / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        new_text = re.sub(
            r'<script>\s*const navToggle[\s\S]*?</script>',
            '<script src="js/main.js"></script>',
            text,
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            print(f"✔ Đã gộp <script> trong {name} thành include js/main.js")


def update_index_card_links(moved_names: set[str]):
    index_path = REPO_DIR / "index.html"
    if not index_path.exists():
        return
    text = index_path.read_text(encoding="utf-8")
    changed = 0
    for name in moved_names:
        pattern = f'href="{name}"'
        replacement = f'href="posts/{name}"'
        if pattern in text:
            text = text.replace(pattern, replacement)
            changed += 1
    if changed:
        index_path.write_text(text, encoding="utf-8")
        print(f"✔ Đã cập nhật {changed} link bài viết trong index.html sang posts/")


def main():
    POSTS_DIR.mkdir(exist_ok=True)
    SCRIPTS_DIR.mkdir(exist_ok=True)
    JS_DIR.mkdir(exist_ok=True)

    js_path = JS_DIR / "main.js"
    if not js_path.exists():
        js_path.write_text(MAIN_JS, encoding="utf-8")
        print(f"✔ Đã tạo {js_path.relative_to(REPO_DIR)}")

    html_files = sorted(
        p for p in REPO_DIR.glob("*.html") if p.name not in KEEP_AT_ROOT
    )

    if not html_files:
        print("Không tìm thấy bài viết nào ở gốc cần di chuyển (có thể đã dời hết rồi).")
    moved_names = set()

    for post_path in html_files:
        text = post_path.read_text(encoding="utf-8")
        fixed = fix_links_for_moved_file(text)
        dest = POSTS_DIR / post_path.name
        dest.write_text(fixed, encoding="utf-8")
        post_path.unlink()
        moved_names.add(post_path.name)
        print(f"✔ Đã dời {post_path.name} → posts/{post_path.name}")

    fix_index_and_root_files()
    update_index_card_links(moved_names)

    print("\nXong! Hãy mở lại index.html và vài bài viết trong posts/ để kiểm tra")
    print("trước khi git add / commit / push.")


if __name__ == "__main__":
    main()
