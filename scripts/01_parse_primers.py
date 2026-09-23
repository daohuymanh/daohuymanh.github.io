#!/usr/bin/env python3
"""
01_parse_primers.py
--------------------
Đọc file Excel chứa danh sách mồi Dengue (4 serotype D1-D4, mỗi serotype là một
khối được phân cách bởi dòng trống, mỗi khối có các cột:
  It. | Name | From | To | Sequence (5'-3') | Length | Tm | Size(bp) | PCR1 | Pool

Sinh ra, cho MỖI serotype:
  - <SEROTYPE>_primers.csv     : bảng mồi đã chuẩn hoá (tên, toạ độ, chiều, pool)
  - <SEROTYPE>_primers.fasta   : FASTA mồi (dùng cho --primer_fasta / Cutadapt)
  - <SEROTYPE>_primers.provisional.bed
        BED "tạm" dựng THẲNG từ toạ độ From/To có sẵn trong file Excel.
        LƯU Ý QUAN TRỌNG: toạ độ này chỉ đúng nếu nó đã được đánh số theo ĐÚNG
        bản genome tham chiếu bạn sẽ dùng để chạy viralrecon. Tên sheet gốc là
        "primer seq DEN old (pool)" - chữ "old" cho thấy khả năng cao đây là toạ
        độ theo một reference cũ/khác. => Luôn chạy tiếp 03_build_primer_bed.py
        (BLAST từng mồi lên reference đã chọn ở bước 2) để có BED chính xác,
        không dùng thẳng file .provisional.bed này để phân tích chính thức.

Quy ước sinh BED (theo chuẩn ARTIC/iVar - primal-page spec):
  cột 1 chrom       : id serotype tạm (DENV1/DENV2/DENV3/DENV4) - sẽ thay bằng
                       accession NCBI thật sau bước chọn reference.
  cột 2-3 start/end : BED 0-based, half-open  (start = From-1, end = To)
  cột 4 name        : <TênMồi>_LEFT  hoặc  <TênMồi>_RIGHT
  cột 5 pool        : lấy từ cột "Pool" trong Excel nếu có; nếu trống thì suy
                       luận bằng cách luân phiên 1,2,1,2... theo từng cặp mồi
                       liên tiếp trong khối (F/R) - được đánh dấu inferred=True
                       trong file CSV để bạn xác nhận lại với protocol PCR gốc.
  cột 6 strand      : '+' cho mồi F (LEFT, xuôi chiều reference)
                       '-' cho mồi R (RIGHT, ngược chiều reference)

Cách dùng:
    python3 01_parse_primers.py <file_excel> <thư_mục_output>
"""
import sys
import re
import csv
import os
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("Cần cài openpyxl: pip install openpyxl")


def classify_direction(name: str) -> str:
    """Xác định mồi F (LEFT) hay R (RIGHT) từ tên mồi, vd 'D1,1F' -> F, 'D1.23Rbis' -> R."""
    # bỏ hậu tố 'bis'/'Bis' khi xét ký tự cuối F/R
    core = re.sub(r"(?i)bis$", "", name.strip())
    core = core.rstrip()
    last_alpha = core[-1].upper() if core and core[-1].isalpha() else None
    if last_alpha == "F":
        return "LEFT"
    if last_alpha == "R":
        return "RIGHT"
    raise ValueError(f"Không xác định được chiều mồi từ tên: {name!r}")


def parse_workbook(xlsx_path: str):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    blocks = {}  # serotype -> list[dict]
    current_serotype = None

    for row in ws.iter_rows(min_row=1, values_only=True):
        name = row[1]
        frm = row[2]
        to = row[3]
        seq = row[4]
        pool_raw = row[9] if len(row) > 9 else None

        if not name or not isinstance(name, str):
            continue
        if not seq or not isinstance(seq, str):
            continue

        m = re.match(r"^\s*D(\d)[.,]", name)
        if not m:
            continue
        serotype = f"D{m.group(1)}"
        current_serotype = serotype

        # toạ độ đôi khi bị lưu dạng chuỗi ('12', '-', ...) hoặc thiếu
        def to_int(v):
            try:
                return int(str(v).strip())
            except (ValueError, TypeError):
                return None

        frm_i = to_int(frm)
        to_i = to_int(to)

        pool = None
        if pool_raw and isinstance(pool_raw, str) and pool_raw.strip().upper() in ("P1", "P2", "1", "2"):
            pool = pool_raw.strip().upper().replace("P", "")

        blocks.setdefault(serotype, []).append(
            {
                "name": name.strip(),
                "from": frm_i,
                "to": to_i,
                "seq": seq.strip().upper(),
                "pool_given": pool,
            }
        )
    return blocks


def infer_pools(records):
    """Điền pool còn thiếu: lan truyền pool đã biết cho cặp mồi liền kề (F,R cùng amplicon),
    nếu cả cặp đều thiếu thì luân phiên 1,2,1,2... theo thứ tự amplicon xuất hiện."""
    n = len(records)
    i = 0
    next_alt_pool = 1
    while i < n:
        pair = records[i : i + 2]
        given = {p["pool_given"] for p in pair if p["pool_given"]}
        if given:
            pool = sorted(given)[0]
            inferred = len(given) == 0
        else:
            pool = str(next_alt_pool)
            next_alt_pool = 2 if next_alt_pool == 1 else 1
            inferred = True
        for p in pair:
            p["pool"] = p["pool_given"] or pool
            p["pool_inferred"] = p["pool_given"] is None
        i += 2
    return records


def main():
    if len(sys.argv) != 3:
        sys.exit(f"Dùng: python3 {sys.argv[0]} <file_excel> <thư_mục_output>")

    xlsx_path, outdir = sys.argv[1], sys.argv[2]
    Path(outdir).mkdir(parents=True, exist_ok=True)

    blocks = parse_workbook(xlsx_path)
    if not blocks:
        sys.exit("Không tìm thấy dòng mồi nào hợp lệ trong file Excel.")

    for serotype, records in sorted(blocks.items()):
        records = infer_pools(records)

        csv_path = os.path.join(outdir, f"{serotype}_primers.csv")
        fasta_path = os.path.join(outdir, f"{serotype}_primers.fasta")
        bed_path = os.path.join(outdir, f"{serotype}_primers.provisional.bed")

        with open(csv_path, "w", newline="") as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow(
                ["name", "direction", "from_1based", "to_1based", "length",
                 "sequence", "pool", "pool_inferred"]
            )
            for r in records:
                direction = classify_direction(r["name"])
                writer.writerow(
                    [
                        r["name"],
                        direction,
                        r["from"],
                        r["to"],
                        len(r["seq"]),
                        r["seq"],
                        r["pool"],
                        r["pool_inferred"],
                    ]
                )

        with open(fasta_path, "w") as ffa:
            for r in records:
                ffa.write(f">{r['name']}\n{r['seq']}\n")

        chrom_placeholder = f"{serotype.replace('D', 'DENV')}_REPLACE_WITH_ACCESSION"
        n_missing_coords = 0
        with open(bed_path, "w") as fbed:
            for r in records:
                direction = classify_direction(r["name"])
                suffix = "_LEFT" if direction == "LEFT" else "_RIGHT"
                strand = "+" if direction == "LEFT" else "-"
                if r["from"] is None or r["to"] is None:
                    n_missing_coords += 1
                    continue
                start0 = r["from"] - 1
                end0 = r["to"]
                fbed.write(
                    f"{chrom_placeholder}\t{start0}\t{end0}\t{r['name']}{suffix}\t{r['pool']}\t{strand}\n"
                )

        n_inferred = sum(1 for r in records if r["pool_inferred"])
        print(
            f"[{serotype}] {len(records)} mồi -> {csv_path}, {fasta_path}, {bed_path}"
            f" | pool tự suy luận: {n_inferred}/{len(records)}"
            + (f" | THIẾU TOẠ ĐỘ: {n_missing_coords} mồi (xem CSV, cột from/to trống)" if n_missing_coords else "")
        )

    print(
        "\n⚠️  BED trên là PROVISIONAL (dựa thẳng vào cột From/To trong Excel).\n"
        "    Bắt buộc chạy 02_select_reference.sh rồi 03_build_primer_bed.py để BLAST\n"
        "    lại từng mồi lên đúng reference đã chọn trước khi dùng cho viralrecon."
    )


if __name__ == "__main__":
    main()
