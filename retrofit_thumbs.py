#!/usr/bin/env python3
"""
retrofit_thumbs.py — chạy MỘT LẦN để rải icon ngẫu nhiên (từ
assets/icons/) vào các card ĐÃ CÓ SẴN trong index.html, tức là
những card mà lúc tạo bài chưa có icon (thumb vẫn còn trống,
chỉ hiện gradient xanh).

Cách dùng:
    1. Tải một số icon .svg (ưu tiên giấy phép CC0) từ
       https://bioicons.com/ , bỏ vào thư mục assets/icons/
       (đứng cùng cấp với index.html).
    2. Chạy:  python retrofit_thumbs.py
    3. Kiểm tra lại index.html rồi git add / commit / push.

Script CHỈ đụng vào những <div class="thumb"></div> đang trống
(không có gì bên trong) — card nào đã có icon hoặc có SVG minh
hoạ riêng (như card "subtitle_shift_guide") sẽ được giữ nguyên,
không bị ghi đè.

Có thể chạy lại nhiều lần: mỗi lần chạy sẽ xáo lại icon cho các
card đang trống, không ảnh hưởng card đã có icon.
"""

import random
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
ICONS_DIR = REPO_DIR / "assets" / "icons"
INDEX_PATH = REPO_DIR / "index.html"

EMPTY_THUMB_RE = re.compile(r'<div class="thumb">\s*</div>')


def pick_random_icon(icons: list[str]) -> str:
    return f"assets/icons/{random.choice(icons)}"


def main():
    if not ICONS_DIR.exists():
        sys.exit(
            f"Lỗi: không tìm thấy thư mục {ICONS_DIR}.\n"
            "Hãy tải icon .svg từ bioicons.com và bỏ vào assets/icons/ trước."
        )
    icons = sorted(p.name for p in ICONS_DIR.glob("*.svg"))
    if not icons:
        sys.exit(f"Lỗi: thư mục {ICONS_DIR} chưa có file .svg nào.")

    if not INDEX_PATH.exists():
        sys.exit(f"Lỗi: không tìm thấy {INDEX_PATH}.")

    text = INDEX_PATH.read_text(encoding="utf-8")

    count = 0

    def replace(match):
        nonlocal count
        count += 1
        icon = pick_random_icon(icons)
        return (
            '<div class="thumb">'
            f'<div class="thumb-icon"><img src="{icon}" alt="" loading="lazy"></div>'
            "</div>"
        )

    new_text = EMPTY_THUMB_RE.sub(replace, text)

    if count == 0:
        print("Không tìm thấy card nào có thumb trống — không có gì để đổi.")
        return

    INDEX_PATH.write_text(new_text, encoding="utf-8")
    print(f"✔ Đã gắn icon ngẫu nhiên cho {count} card trong {INDEX_PATH.name}.")


if __name__ == "__main__":
    main()
