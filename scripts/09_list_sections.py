"""
09_list_sections.py

Doc file psds_data.json (da crawl tu 08_extract_all_pathogens.py) va tra loi
cau hoi: "Moi pathogen gom nhung muc (section) nao?"

Xuat ra 2 file:
    - sections_by_pathogen.csv : pathogen, url, section_path  (1 dong = 1 muc)
    - section_inventory.csv    : section_path, so_luong_pathogen_co_muc_nay
                                  (giup thay muc nao pho bien / muc nao hiem)
"""

import csv
import json
from collections import Counter, defaultdict

INPUT_JSON = "psds_data.json"

# Cac ten muc khong phai noi dung PSDS that su (menu, header, footer cua trang web)
# -> bi lan vao do mot so trang khong co div noi dung rieng, script fallback ve ca trang
NOISE_HEADINGS = {
    "language selection",
    "menu",
    "you are here:",
    "public health agency of canada",
    "government of canada",
    "themes and topics",
    "government of canada corporate",
    "search",
    "footer",
}


def is_noise(section_path):
    leaf = section_path.split(" > ")[-1].strip().lower()
    return leaf in NOISE_HEADINGS


def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Tong so trang trong file: {len(data)}\n")

    # 1) Xuat danh sach muc theo tung pathogen
    with open("sections_by_pathogen.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pathogen", "url", "section_path"])

        for page in data:
            for section in page["sections"]:
                if section["text"] and not is_noise(section["path"]):
                    writer.writerow([page["pathogen"], page["url"], section["path"]])

    print("Da luu sections_by_pathogen.csv")

    # 2) Thong ke: moi muc xuat hien trong bao nhieu pathogen
    #    (dung ten muc cuoi cung trong path, vi du "Epidemiology")
    section_counter = Counter()
    pathogens_by_section = defaultdict(set)

    for page in data:
        for section in page["sections"]:
            if not section["text"] or is_noise(section["path"]):
                continue
            leaf_name = section["path"].split(" > ")[-1]
            section_counter[leaf_name] += 1
            pathogens_by_section[leaf_name].add(page["pathogen"])

    with open("section_inventory.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["section_name", "so_pathogen_co_muc_nay", "ti_le_phan_tram"])
        total_pathogens = len(data)
        for name, count in section_counter.most_common():
            pct = round(100 * count / total_pathogens, 1)
            writer.writerow([name, count, pct])

    print("Da luu section_inventory.csv")

    # 3) In nhanh ra man hinh: cau truc muc cua 1 pathogen lam vi du
    example = data[1] if len(data) > 1 else data[0]
    print(f"\nVi du cau truc muc cua '{example['pathogen']}':")
    for section in example["sections"]:
        if section["text"]:
            print(f"  [{section['level']}] {section['path']}")


if __name__ == "__main__":
    main()
