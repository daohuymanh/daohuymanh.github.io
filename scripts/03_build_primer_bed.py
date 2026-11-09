#!/usr/bin/env python3
"""
03_build_primer_bed.py  (phiên bản 2)
-------------------------------------
Dựng file .bed mồi CHÍNH XÁC cho iVar/viralrecon bằng cách BLAST (blastn-short) từng trình tự mồi
(<nhóm>_primers.fasta từ bước 01) lên CHÍNH reference đã chọn ở bước 02, thay vì tin cột From/To
trong Excel (có thể được đánh số theo reference khác).

So với phiên bản 1:
  - Toạ độ BED bao trọn TOÀN BỘ chiều dài mồi (kể cả khi 1-2 base ở đầu mồi không khớp reference
    nên BLAST chỉ căn một phần), vì iVar cắt primer theo toạ độ này.
  - Kiểm tra chiều: mồi LEFT phải khớp chiều xuôi (plus), mồi RIGHT phải khớp chiều ngược (minus).
  - Kiểm tra amplicon: mỗi amplicon phải có cả mồi trái và phải, độ dài hợp lý (--min-amplicon / --max-amplicon).
  - Tên mồi trong BED là tên ARTIC (<nhóm>_<số>_LEFT / _RIGHT / _RIGHT_alt) để viralrecon ghép cặp amplicon.
  - Mặc định thoát với mã 0 kể cả khi có cảnh báo (an toàn trong vòng lặp shell); dùng --strict để thoát 1.

YÊU CẦU: blastn và makeblastdb (ncbi-blast+) trong PATH.

Cách dùng:
    python3 03_build_primer_bed.py \
        --primers-fasta primers_parsed/D1_primers.fasta \
        --primers-csv   primers_parsed/D1_primers.csv \
        --reference     ref_selection_out/references/D1_chosen_reference.fasta \
        --out-prefix    final_bed/D1

Sinh ra:
    <out-prefix>.bed                 : BED dùng cho --primer_bed
    <out-prefix>.primer_fasta.fa     : FASTA mồi dùng cho --primer_fasta
    <out-prefix>.mapping_report.tsv  : %identity, coverage, chiều, toạ độ từng mồi
    <out-prefix>.amplicons.tsv       : toạ độ và độ dài từng amplicon
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile
from collections import defaultdict

BLAST_FIELDS = ("qseqid sseqid pident length qcovs qstart qend qlen "
                "sstart send sstrand evalue bitscore").split()


def read_ref_length(reference_fasta):
    """Độ dài bản ghi đầu tiên của FASTA reference và tên sequence (token đầu của header)."""
    name, length = None, 0
    with open(reference_fasta) as fh:
        for line in fh:
            if line.startswith(">"):
                if name is not None:
                    break
                name = line[1:].split()[0]
            else:
                length += len(line.strip())
    return name or "REF", length


def run_blast(primers_fasta, reference_fasta):
    """BLAST ngắn từng mồi lên reference; trả về dict tên mồi -> hit tốt nhất (theo bitscore)."""
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "ref_db")
        subprocess.run(["makeblastdb", "-in", reference_fasta, "-dbtype", "nucl", "-out", db],
                       check=True, capture_output=True)
        cmd = ["blastn", "-task", "blastn-short", "-query", primers_fasta, "-db", db,
               "-outfmt", "6 " + " ".join(BLAST_FIELDS),
               "-evalue", "1000", "-word_size", "7", "-max_target_seqs", "5"]
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return parse_blast(res.stdout)


def parse_blast(text):
    hits = {}
    for line in text.strip().splitlines():
        f = dict(zip(BLAST_FIELDS, line.split("\t")))
        h = {
            "pident": float(f["pident"]), "qcovs": float(f["qcovs"]),
            "qstart": int(f["qstart"]), "qend": int(f["qend"]), "qlen": int(f["qlen"]),
            "sstart": int(f["sstart"]), "send": int(f["send"]),
            "sstrand": f["sstrand"], "bitscore": float(f["bitscore"]),
        }
        best = hits.get(f["qseqid"])
        if best is None or h["bitscore"] > best["bitscore"]:
            hits[f["qseqid"]] = h
    return hits


def footprint(hit, ref_len):
    """Toạ độ BED (0-based, half-open) bao trọn toàn bộ mồi trên reference."""
    qs, qe, ql = hit["qstart"], hit["qend"], hit["qlen"]
    ss, se = hit["sstart"], hit["send"]
    if ss <= se:                      # mồi khớp chiều xuôi
        low, high = ss - (qs - 1), se + (ql - qe)
    else:                             # mồi khớp chiều ngược
        low, high = se - (ql - qe), ss + (qs - 1)
    low, high = max(low, 1), min(high, ref_len)
    return low - 1, high


def amplicon_id(artic_name):
    """'D1_18_RIGHT_alt2' -> ('D1_18', 'RIGHT'); trả (None, None) nếu không nhận ra."""
    for tag in ("_LEFT", "_RIGHT"):
        if tag in artic_name:
            return artic_name.split(tag)[0], tag[1:]
    return None, None


def check_amplicons(bed_rows, min_len, max_len):
    amps = defaultdict(lambda: {"LEFT": [], "RIGHT": [], "pool": ""})
    for chrom, start0, end0, name, pool, strand in bed_rows:
        aid, side = amplicon_id(name)
        if aid is None:
            continue
        amps[aid][side].append((start0, end0))
        amps[aid]["pool"] = pool
    rows, warnings = [], []
    for aid in sorted(amps, key=lambda a: min([s for s, _ in amps[a]["LEFT"] + amps[a]["RIGHT"]] or [0])):
        L, R = amps[aid]["LEFT"], amps[aid]["RIGHT"]
        if not L or not R:
            warnings.append(f"Amplicon {aid} thiếu mồi {'trái' if not L else 'phải'}")
            rows.append([aid, "", "", "", amps[aid]["pool"], "THIEU_MOI"])
            continue
        start = min(s for s, _ in L)
        end = max(e for _, e in R)
        length = end - start
        flag = "ok"
        if length < min_len or length > max_len:
            flag = "DO_DAI_BAT_THUONG"
            warnings.append(f"Amplicon {aid}: độ dài {length} bp nằm ngoài [{min_len}, {max_len}] "
                            f"(kiểm tra mồi map nhầm vị trí hoặc đánh số amplicon)")
        rows.append([aid, start, end, length, amps[aid]["pool"], flag])
    return rows, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--primers-fasta", required=True)
    ap.add_argument("--primers-csv", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--min-pident", type=float, default=90.0, help="%%identity tối thiểu (mặc định 90)")
    ap.add_argument("--min-qcov", type=float, default=90.0, help="coverage tối thiểu của mồi (mặc định 90)")
    ap.add_argument("--min-amplicon", type=int, default=100)
    ap.add_argument("--max-amplicon", type=int, default=3000)
    ap.add_argument("--strict", action="store_true", help="Thoát mã 1 nếu có cảnh báo")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)
    chrom, ref_len = read_ref_length(args.reference)
    hits = run_blast(args.primers_fasta, args.reference)

    meta = {}
    with open(args.primers_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[row.get("artic_name") or row["name"]] = row

    bed_rows, report, warnings = [], [], []
    n_missing = n_weak = n_strand = n_partial = 0

    for name, m in meta.items():
        direction, pool = m["direction"], m["pool"]
        hit = hits.get(name)
        if hit is None:
            n_missing += 1
            report.append([name, direction, "NO_HIT", "", "", "", "", "", ""])
            continue
        if hit["pident"] < args.min_pident or hit["qcovs"] < args.min_qcov:
            n_weak += 1
        expect = "plus" if direction == "LEFT" else "minus"
        strand_ok = hit["sstrand"] == expect
        if not strand_ok:
            n_strand += 1
        partial = hit["qend"] - hit["qstart"] + 1 < hit["qlen"]
        if partial:
            n_partial += 1
        start0, end0 = footprint(hit, ref_len)
        strand = "+" if direction == "LEFT" else "-"
        bed_rows.append((chrom, start0, end0, name, pool, strand))
        report.append([name, direction, f"{hit['pident']:.1f}", f"{hit['qcovs']:.0f}", hit["sstrand"],
                       "ok" if strand_ok else "SAI_CHIEU", "partial" if partial else "full", start0, end0])

    bed_rows.sort(key=lambda x: (x[1], x[2]))
    amp_rows, amp_warn = check_amplicons(bed_rows, args.min_amplicon, args.max_amplicon)
    warnings.extend(amp_warn)

    with open(f"{args.out_prefix}.bed", "w") as fbed:
        for r in bed_rows:
            fbed.write("\t".join(str(x) for x in r) + "\n")
    with open(f"{args.out_prefix}.mapping_report.tsv", "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["name", "direction", "pident", "qcovs", "blast_strand", "strand_check",
                    "alignment", "bed_start0", "bed_end0"])
        w.writerows(report)
    with open(f"{args.out_prefix}.amplicons.tsv", "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["amplicon", "start0", "end0", "length", "pool", "check"])
        w.writerows(amp_rows)
    with open(args.primers_fasta) as src, open(f"{args.out_prefix}.primer_fasta.fa", "w") as dst:
        dst.write(src.read())

    print(f"-> {args.out_prefix}.bed  ({len(bed_rows)} mồi map; reference {chrom}, {ref_len} bp)")
    print(f"-> {args.out_prefix}.mapping_report.tsv, {args.out_prefix}.amplicons.tsv, "
          f"{args.out_prefix}.primer_fasta.fa")
    if n_missing:
        warnings.append(f"{n_missing} mồi KHÔNG map được lên reference này (sai type/reference?)")
    if n_weak:
        warnings.append(f"{n_weak} mồi có %identity<{args.min_pident} hoặc coverage<{args.min_qcov}% (xem report)")
    if n_strand:
        warnings.append(f"{n_strand} mồi khớp SAI CHIỀU (LEFT phải plus, RIGHT phải minus): kiểm tra tên/chiều mồi")
    if n_partial:
        print(f"[i] {n_partial} mồi chỉ căn một phần; toạ độ BED đã được mở rộng ra đủ chiều dài mồi.")
    for w_ in warnings:
        print(f"[!] {w_}")
    if warnings and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
