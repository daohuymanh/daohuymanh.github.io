"""
10_crawl_diseases.py

Crawl phan "Diseases and conditions" cua canada.ca (khac voi phan PSDS
o script 08_extract_all_pathogens.py).

Cau truc trang o day khac PSDS:
    - Trang index: https://www.canada.ca/en/public-health/services/diseases.html
      la 1 bang ten benh -> link. Nhieu link tro RA NGOAI canada.ca (bi bo qua).
    - Nhieu benh (vd Malaria) co 1 trang "hub" liet ke cac trang con:
      Causes, Symptoms, Risks, Treatment, Prevention, Surveillance,
      For health professionals... Script se tu phat hien hub va crawl tung
      trang con (vi du trang "Symptoms" cua Malaria).
    - Neu benh khong co cau truc hub (trang don), script tach noi dung
      truc tiep tu trang do.

Xuat ra:
    - diseases_data.json   -> du lieu day du, dang cay
    - diseases_search.csv  -> dang phang: disease, page_title, url, section_path, text

Chay:
    python3 10_crawl_diseases.py
"""

import csv
import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.canada.ca"

INDEX_URL = "https://www.canada.ca/en/public-health/services/diseases.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (research script; contact: your_email@example.com)"
}

REQUEST_DELAY_SECONDS = 1.0

NAV_IDS_TO_STRIP = ["wb-tphp", "wb-bnr", "wb-sec", "wb-info", "wb-glb-mn", "wb-share"]
NAV_TAGS_TO_STRIP = ["nav", "header", "footer", "script", "style"]


def get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def strip_navigation(soup):
    for tag_id in NAV_IDS_TO_STRIP:
        el = soup.find(id=tag_id)
        if el:
            el.decompose()
    for tag_name in NAV_TAGS_TO_STRIP:
        for el in soup.find_all(tag_name):
            el.decompose()
    return soup


def is_canada_ca(url):
    """Chi giu link thuoc canada.ca, bo qua link ra ngoai (veterans.gc.ca, camh.ca...)."""
    netloc = urlparse(url).netloc.lower()
    return netloc.endswith("canada.ca")


def find_disease_links(index_url):
    """Doc bang benh tren trang index, tra ve list (name, url), chi giu link canada.ca."""
    soup = get_soup(index_url)

    links = []
    seen = set()

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            a = row.find("a", href=True)
            if not a:
                continue
            name = a.get_text(" ", strip=True)
            full_url = urljoin(BASE_URL, a["href"])

            if not is_canada_ca(full_url):
                continue
            if full_url in seen:
                continue

            seen.add(full_url)
            links.append({"name": name, "url": full_url})

    return links


def find_main_container(soup):
    return (
        soup.find("div", class_="mwsgeneric-base-html")
        or soup.find("main", attrs={"property": "mainContentOfPage"})
        or soup.find("main")
        or soup.find(id="wb-cont")
        or soup
    )


def find_hub_subpages(container):
    """
    Tim khoi 'Services and information' (kieu trang hub nhu trang Malaria):
    cac h3 chua link con (Causes/Symptoms/Risks/...). Tra ve list dict
    {"title":..., "url":...} hoac [] neu khong phai trang hub.
    """
    heading = None
    for tag in container.find_all(["h2", "h3"]):
        if tag.get_text(" ", strip=True).lower() == "services and information":
            heading = tag
            break

    if heading is None:
        return []

    subpages = []
    for element in heading.find_all_next():
        if element.name == "h2":
            break
        if element.name == "h3":
            a = element.find("a", href=True)
            if a:
                title = a.get_text(" ", strip=True)
                url = urljoin(BASE_URL, a["href"])
                if is_canada_ca(url):
                    subpages.append({"title": title, "url": url})

    return subpages


def get_clean_text(element):
    """Lay text cua 1 the, loai bo chu thich 'Footnote N' (xem giai thich
    chi tiet trong 08_extract_all_pathogens.py)."""
    clone = BeautifulSoup(str(element), "html.parser")
    for sup in clone.find_all("sup"):
        sup.decompose()
    text = clone.get_text(" ", strip=True)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return text


def extract_sections(container):
    """Giong extract_sections trong 08_extract_all_pathogens.py: tach noi dung
    theo cau truc heading h2..h5, tra ve list {"level","path","text"}."""
    headings = container.find_all(["h2", "h3", "h4", "h5"])
    sections = []
    path_stack = []

    for heading in headings:
        level = int(heading.name[1])
        heading_text = heading.get_text(" ", strip=True)

        path_stack = [item for item in path_stack if item[0] < level]
        path_stack.append((level, heading_text))
        current_path = " > ".join(item[1] for item in path_stack)

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
        sections.append({"level": level, "path": current_path, "text": combined_text})

    return sections


def crawl_page(url):
    """Tai 1 trang, xoa nav, tra ve (container_da_lam_sach, sections)."""
    soup = get_soup(url)
    soup = strip_navigation(soup)
    container = find_main_container(soup)
    sections = extract_sections(container)
    return container, sections


def main():
    print("Dang lay danh sach benh tu trang index...")
    disease_links = find_disease_links(INDEX_URL)
    print(f"Tim thay {len(disease_links)} benh thuoc canada.ca.\n")

    all_data = []

    for i, item in enumerate(disease_links, start=1):
        disease_name = item["name"]
        disease_url = item["url"]
        print(f"[{i}/{len(disease_links)}] {disease_name} -> {disease_url}")

        try:
            container, sections = crawl_page(disease_url)
        except requests.RequestException as e:
            print(f"  -> Loi khi tai trang: {e}")
            continue

        subpages_meta = find_hub_subpages(container)
        time.sleep(REQUEST_DELAY_SECONDS)

        pages = []

        if subpages_meta:
            # Trang hub: crawl tung trang con (Causes, Symptoms, Risks, ...)
            print(f"  -> La trang hub, co {len(subpages_meta)} trang con")
            for sub in subpages_meta:
                print(f"     - {sub['title']}: {sub['url']}")
                try:
                    _, sub_sections = crawl_page(sub["url"])
                except requests.RequestException as e:
                    print(f"       Loi khi tai trang con: {e}")
                    continue
                pages.append(
                    {"title": sub["title"], "url": sub["url"], "sections": sub_sections}
                )
                time.sleep(REQUEST_DELAY_SECONDS)
        else:
            # Trang don: dung luon noi dung da lay o tren
            pages.append({"title": disease_name, "url": disease_url, "sections": sections})

        all_data.append({"disease": disease_name, "url": disease_url, "pages": pages})

    # 1) JSON day du
    with open("diseases_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print("\nDa luu diseases_data.json")

    # 2) CSV phang de tim kiem
    with open("diseases_search.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["disease", "page_title", "url", "section_path", "text"])
        for disease in all_data:
            for page in disease["pages"]:
                for section in page["sections"]:
                    if section["text"]:
                        writer.writerow(
                            [
                                disease["disease"],
                                page["title"],
                                page["url"],
                                section["path"],
                                section["text"],
                            ]
                        )
    print("Da luu diseases_search.csv")


if __name__ == "__main__":
    main()
