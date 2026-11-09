#!/usr/bin/env python3
"""
01_parse_primers.py  (phiên bản 2)
----------------------------------
Đọc file Excel chứa danh sách mồi amplicon đa mồi (ví dụ Dengue D1-D4, hoặc Zika, Chikungunya...).
Mỗi hàng là một mồi, các cột (đếm từ 0, có thể đổi bằng tham số --col-*):
  0 It. | 1 Name | 2 From | 3 To | 4 Sequence (5'-3') | 5 Length | 6 Tm | 7 Size(bp) | 8 PCR1 | 9 Pool

Tên mồi phải có dạng  <nhóm><dấu phân cách><số amplicon><F|R>[bis|alt...]
  ví dụ: D1,1F   D1,17R   D1.23Rbis   ZIKV_12F
  - <nhóm>  : serotype/virus/bộ mồi (D1, D2, ZIKV...). Mỗi nhóm sinh ra bộ file riêng.
  - <số amplicon>: số thứ tự amplicon; mồi F và R cùng số thuộc CÙNG một amplicon.
  - hậu tố bis/alt: mồi thay thế (alternative) cho cùng amplicon.

Với MỖI nhóm sinh ra:
  <nhóm>_primers.csv                : bảng mồi chuẩn hoá (cả tên gốc và tên ARTIC)
  <nhóm>_primers.fasta              : FASTA mồi (header = tên ARTIC), dùng cho --primer_fasta
  <nhóm>_primers.provisional.bed    : BED "tạm" dựng từ toạ độ From/To trong Excel

TÊN ARTIC (quan trọng cho viralrecon):
  viralrecon/iVar/ARTIC ghép mồi trái-phải thành amplicon dựa trên tên có dạng
  <tên_amplicon>_LEFT và <tên_amplicon>_RIGHT (cùng <tên_amplicon>). Vì vậy script đổi
  'D1,18F' -> 'D1_18_LEFT', 'D1,18R' -> 'D1_18_RIGHT', mồi thay thế -> 'D1_18_RIGHT_alt'.
  Tên gốc vẫn được giữ trong cột `name` của CSV để đối chiếu.

BED "tạm" chỉ đúng nếu toạ độ trong Excel đã đánh số theo ĐÚNG reference sẽ dùng. Luôn chạy tiếp
02_select_reference.sh và 03_build_primer_bed.py để BLAST lại từng mồi lên reference đã chọn.

Pool: nếu cột Pool trống, suy luận theo amplicon (amplicon liền kề luân phiên pool 1,2,1,2...) và
đánh dấu pool_inferred=True trong CSV; hãy đối chiếu lại với protocol PCR gốc.

Cách dùng:
    python3 01_parse_primers.py <file_excel> <thư_mục_output> [--sheet TÊN_SHEET]
        [--name-regex REGEX] [--col-name 1 --col-from 2 --col-to 3 --col-seq 4 --col-pool 9]
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("Cần cài openpyxl: pip install openpyxl")

DEFAULT_NAME_REGEX = (
    r"^\s*(?P<group>[A-Za-z0-9]+?)[.,_\-\s]+(?P<num>\d+)\s*(?P<dir>[FfRr])\s*"
    r"(?P<alt>(?i:bis)|(?i:alt)\w*)?\s*$"
)


def to_int(v):
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return None


def parse_workbook(path, sheet, name_re, cols):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    groups = defaultdict(list)
    skipped = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        if len(row) <= max(cols.values()):
            row = tuple(row) + (None,) * (max(cols.values()) + 1 - len(row))
        name, frm, to = row[cols["name"]], row[cols["from"]], row[cols["to"]]
        seq, pool_raw = row[cols["seq"]], row[cols["pool"]]
        if not isinstance(name, str) or not isinstance(seq, str) or not seq.strip():
            continue
        if name.strip().lower() in ("name", "primer", "primer name", "tên mồi"):   # dòng tiêu đề
            continue
        m = name_re.match(name)
        if not m:
            skipped.append(name.strip())
            continue
        direction = "LEFT" if m.group("dir").upper() == "F" else "RIGHT"
        pool = None
        if pool_raw is not None and str(pool_raw).strip().upper() in ("P1", "P2", "1", "2", "1.0", "2.0"):
            pool = str(pool_raw).strip().upper().replace("P", "").replace(".0", "")
        groups[m.group("group")].append(
            {
                "name": name.strip(),
                "group": m.group("group"),
                "amplicon": int(m.group("num")),
                "direction": direction,
                "alt": bool(m.group("alt")),
                "from": to_int(frm),
                "to": to_int(to),
                "seq": re.sub(r"\s+", "", seq).upper(),
                "pool_given": pool,
            }
        )
    return groups, skipped


def assign_names_and_pools(records):
    """Gán tên ARTIC duy nhất và pool (theo amplicon)."""
    # pool theo amplicon: lấy pool đã cho (nếu có) của bất kỳ mồi nào trong amplicon
    by_amp = defaultdict(list)
    for r in records:
        by_amp[r["amplicon"]].append(r)
    for rank, amp in enumerate(sorted(by_amp)):
        given = sorted({p["pool_given"] for p in by_amp[amp] if p["pool_given"]})
        pool = given[0] if given else str(rank % 2 + 1)
        for p in by_amp[amp]:
            p["pool"] = p["pool_given"] or pool
            p["pool_inferred"] = p["pool_given"] is None
    # tên ARTIC duy nhất
    seen = defaultdict(int)
    for r in records:
        base = f"{r['group']}_{r['amplicon']}_{r['direction']}"
        if r["alt"]:
            base += "_alt"
        seen[base] += 1
        r["artic_name"] = base if seen[base] == 1 else f"{base}{seen[base]}"
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("excel")
    ap.add_argument("outdir")
    ap.add_argument("--sheet", default=None, help="Tên sheet (mặc định: sheet đang hoạt động)")
    ap.add_argument("--name-regex", default=DEFAULT_NAME_REGEX,
                    help="Regex có nhóm group, num, dir, alt để phân tích tên mồi")
    ap.add_argument("--col-name", type=int, default=1)
    ap.add_argument("--col-from", type=int, default=2)
    ap.add_argument("--col-to", type=int, default=3)
    ap.add_argument("--col-seq", type=int, default=4)
    ap.add_argument("--col-pool", type=int, default=9)
    args = ap.parse_args()

    cols = {"name": args.col_name, "from": args.col_from, "to": args.col_to,
            "seq": args.col_seq, "pool": args.col_pool}
    name_re = re.compile(args.name_regex)
    Path(args.outdir).mkdir(parents=True, exist_ok=True)

    groups, skipped = parse_workbook(args.excel, args.sheet, name_re, cols)
    if not groups:
        sys.exit("Không tìm thấy dòng mồi hợp lệ. Kiểm tra --name-regex và chỉ số cột (--col-*).")
    if skipped:
        print(f"[!] Bỏ qua {len(skipped)} dòng có tên không khớp quy ước: {', '.join(skipped[:10])}"
              + (" ..." if len(skipped) > 10 else ""))

    for group, records in sorted(groups.items()):
        records = assign_names_and_pools(records)
        records.sort(key=lambda r: (r["amplicon"], r["direction"] != "LEFT", r["alt"]))

        csv_path = os.path.join(args.outdir, f"{group}_primers.csv")
        fasta_path = os.path.join(args.outdir, f"{group}_primers.fasta")
        bed_path = os.path.join(args.outdir, f"{group}_primers.provisional.bed")

        with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
            w = csv.writer(fcsv)
            w.writerow(["name", "artic_name", "group", "amplicon", "direction", "alt",
                        "from_1based", "to_1based", "length", "sequence", "pool", "pool_inferred"])
            for r in records:
                w.writerow([r["name"], r["artic_name"], r["group"], r["amplicon"], r["direction"],
                            r["alt"], r["from"], r["to"], len(r["seq"]), r["seq"], r["pool"],
                            r["pool_inferred"]])

        with open(fasta_path, "w", encoding="utf-8") as ffa:
            for r in records:
                ffa.write(f">{r['artic_name']}\n{r['seq']}\n")

        n_missing = 0
        chrom = f"{group}_REPLACE_WITH_ACCESSION"
        with open(bed_path, "w", encoding="utf-8") as fbed:
            for r in records:
                if r["from"] is None or r["to"] is None:
                    n_missing += 1
                    continue
                lo, hi = sorted((r["from"], r["to"]))
                strand = "+" if r["direction"] == "LEFT" else "-"
                fbed.write(f"{chrom}\t{lo - 1}\t{hi}\t{r['artic_name']}\t{r['pool']}\t{strand}\n")

        n_inf = sum(1 for r in records if r["pool_inferred"])
        amps = {r["amplicon"] for r in records}
        incomplete = [a for a in sorted(amps)
                      if not ({"LEFT", "RIGHT"} <= {r["direction"] for r in records if r["amplicon"] == a})]
        print(f"[{group}] {len(records)} mồi, {len(amps)} amplicon -> {csv_path}, {fasta_path}, {bed_path}"
              f" | pool tự suy luận: {n_inf}/{len(records)}"
              + (f" | THIẾU TOẠ ĐỘ: {n_missing}" if n_missing else ""))
        if incomplete:
            print(f"    [!] Amplicon thiếu mồi trái hoặc phải: {incomplete}")

    print("\n[!] BED trên là PROVISIONAL (dựa vào cột From/To trong Excel). Hãy chạy 02_select_reference.sh\n"
          "    rồi 03_build_primer_bed.py để BLAST lại từng mồi lên đúng reference trước khi chạy viralrecon.")


if __name__ == "__main__":
    main()
