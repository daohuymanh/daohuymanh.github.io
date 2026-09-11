"""
08_extract_all_pathogens.py

Pipeline day du:
1. Lay danh sach link tat ca cac trang PSDS tu trang index (bo qua trang template)
2. Voi moi trang PSDS, xoa menu/header/footer, roi tach noi dung theo heading (h2-h5)
3. Luu ket qua thanh:
   - psds_data.json   -> du lieu day du, dang cay, de doc lai bang code
   - psds_search.csv  -> dang phang (pathogen, section, text), de mo bang Excel / grep / tim kiem

So voi ban truoc: da xu ly 2 van de phat hien duoc sau khi thong ke du lieu
    - Loc mot so trang menu/header/footer bi lan vao noi dung (do mot so trang
      khong co div class="mwsgeneric-base-html" nen truoc day fallback ve ca trang)
    - Loai bo trang "Pathogen Safety Data Sheet Template" (khong phai pathogen that)

Chay:
    python3 08_extract_all_pathogens.py
"""

import csv
import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.canada.ca"

INDEX_URL = (
    "https://www.canada.ca/en/public-health/services/"
    "laboratory-biosafety-biosecurity/"
    "pathogen-safety-data-sheets-risk-assessment.html"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (research script; contact: your_email@example.com)"
}

REQUEST_DELAY_SECONDS = 1.0  # lich su voi server, tranh spam request

# Cac id/tag chuan cua khung template canada.ca (WET) chi chua menu/header/footer,
# KHONG phai noi dung PSDS -> loai bo truoc khi tim noi dung, de fallback co an toan.
NAV_IDS_TO_STRIP = ["wb-tphp", "wb-bnr", "wb-sec", "wb-info", "wb-glb-mn", "wb-share"]
NAV_TAGS_TO_STRIP = ["nav", "header", "footer", "script", "style"]

# Cac trang bi loai vi khong phai pathogen that (trang template/huong dan chung)
SKIP_NAME_KEYWORDS = ["template"]
SKIP_URL_KEYWORDS = ["template"]


def get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def strip_navigation(soup):
    """Xoa cac phan menu/header/footer chuan cua canada.ca truoc khi tim noi dung,
    de neu phai fallback ve ca trang thi cung khong bi lan menu vao."""
    for tag_id in NAV_IDS_TO_STRIP:
        el = soup.find(id=tag_id)
        if el:
            el.decompose()

    for tag_name in NAV_TAGS_TO_STRIP:
        for el in soup.find_all(tag_name):
            el.decompose()

    return soup


def is_real_pathogen_page(name, url):
    """Loai cac trang khong phai PSDS that su, vi du trang template/huong dan."""
    name_lower = (name or "").lower()
    url_lower = url.lower()

    if any(keyword in name_lower for keyword in SKIP_NAME_KEYWORDS):
        return False
    if any(keyword in url_lower for keyword in SKIP_URL_KEYWORDS):
        return False
    return True


def find_psds_links(index_url):
    """Lay danh sach (name, url) cua tat ca trang PSDS tu trang index."""
    soup = get_soup(index_url)

    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        name = a.get_text(" ", strip=True)
        href = a["href"]
        full_url = urljoin(BASE_URL, href)

        if "pathogen-safety-data-sheets-risk-assessment/" not in full_url:
            continue
        # Bo qua link trung, link ve chinh trang index, link khong phai .html chi tiet
        if full_url == index_url or full_url in seen:
            continue
        if not full_url.endswith(".html"):
            continue
        # Bo qua trang khong phai pathogen that (vi du trang template)
        if not is_real_pathogen_page(name, full_url):
            continue

        seen.add(full_url)
        links.append({"name": name, "url": full_url})

    return links


def get_clean_text(element):
    """
    Lay text cua 1 the (p/li), loai bo cac chu thich dang "Footnote N"
    (canada.ca gan chung bang <sup><a class="fn-lnk">...<span class="wb-inv">
    Footnote</span> N</a></sup> ngay trong doan van, get_text() binh thuong
    se lay ca chu "Footnote" an va so do vao text).

    Dung ban sao (parse lai tu string) thay vi decompose truc tiep tren cay
    goc, de khong lam hong vong lap find_all_next() dang duyet cay chinh.
    """
    clone = BeautifulSoup(str(element), "html.parser")
    for sup in clone.find_all("sup"):
        sup.decompose()
    text = clone.get_text(" ", strip=True)
    # Xoa khoang trang thua truoc dau cau, con lai sau khi bo <sup> (vd "ZIKV ." -> "ZIKV.")
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return text


def extract_sections(soup):
    """
    Duyet toan bo heading h2..h5 trong noi dung chinh va gom cac doan <p>/<li>
    ngay sau moi heading (cho toi khi gap heading cung cap hoac cao hon).

    Tra ve list cac dict:
        {"level": 2, "path": "Section I - Infectious agent", "text": "..."}
        {"level": 3, "path": "Section I - Infectious agent > Name", "text": "..."}
        ...
    """
    # Xoa menu/header/footer truoc, de neu phai fallback thi van an toan
    soup = strip_navigation(soup)

    # Thu nhieu cach tim vung noi dung chinh, uu tien tu cu the -> chung chung.
    # Chi khi khong tim duoc gi moi fallback ve ca trang (da duoc lam sach o tren).
    container = (
        soup.find("div", class_="mwsgeneric-base-html")
        or soup.find("main", attrs={"property": "mainContentOfPage"})
        or soup.find("main")
        or soup.find(id="wb-cont")
        or soup
    )

    headings = container.find_all(["h2", "h3", "h4", "h5"])
    sections = []

    # stack luu (level, text) de dung path dang "Cha > Con"
    path_stack = []

    for heading in headings:
        level = int(heading.name[1])
        heading_text = heading.get_text(" ", strip=True)

        # cap nhat stack: bo cac muc co level >= level hien tai
        path_stack = [item for item in path_stack if item[0] < level]
        path_stack.append((level, heading_text))
        current_path = " > ".join(item[1] for item in path_stack)

        # gom text cho toi khi gap heading tiep theo
        texts = []
        for sibling in heading.find_all_next():
            if sibling.name and re.fullmatch(r"h[2-5]", sibling.name):
                break
            if sibling.name == "p":
                text = get_clean_text(sibling)
                if text:
                    texts.append(text)
            elif sibling.name == "li":
                text = get_clean_text(sibling)
                if text:
                    texts.append("- " + text)

        combined_text = "\n".join(texts).strip()

        sections.append(
            {
                "level": level,
                "path": current_path,
                "text": combined_text,
            }
        )

    return sections


def extract_pathogen_name(soup, fallback_name):
    """Uu tien lay ten pathogen tu h1, neu khong co thi dung title link tu trang index."""
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(" ", strip=True)
        if text:
            return text
    return fallback_name


def main():
    print("Dang lay danh sach cac trang PSDS...")
    psds_links = find_psds_links(INDEX_URL)
    print(f"Tim thay {len(psds_links)} trang PSDS.\n")

    all_data = []

    for i, item in enumerate(psds_links, start=1):
        url = item["url"]
        print(f"[{i}/{len(psds_links)}] Dang xu ly: {url}")

        try:
            soup = get_soup(url)
        except requests.RequestException as e:
            print(f"  -> Loi khi tai trang: {e}")
            continue

        pathogen_name = extract_pathogen_name(soup, item["name"])
        sections = extract_sections(soup)

        all_data.append(
            {
                "pathogen": pathogen_name,
                "url": url,
                "sections": sections,
            }
        )

        time.sleep(REQUEST_DELAY_SECONDS)

    # 1) Luu ban day du dang JSON (giu cau truc, de doc lai bang code)
    with open("psds_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\nDa luu psds_data.json")

    # 2) Luu ban phang dang CSV (de tim kiem bang Excel / grep / pandas)
    with open("psds_search.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pathogen", "url", "section_path", "text"])
        for page in all_data:
            for section in page["sections"]:
                if section["text"]:
                    writer.writerow(
                        [page["pathogen"], page["url"], section["path"], section["text"]]
                    )
    print("Da luu psds_search.csv")


if __name__ == "__main__":
    main()
