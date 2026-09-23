#!/usr/bin/env python3
"""
03_build_primer_bed.py
-----------------------
Dựng file .bed mồi CHÍNH XÁC cho iVar/artic minion bằng cách BLAST (blastn-short)
từng trình tự mồi (từ <SEROTYPE>_primers.fasta, sinh ở bước 01) lên chính bản
reference đã chọn ở bước 02 - thay vì tin thẳng cột From/To trong Excel gốc
(có thể lệch nếu Excel được đánh số theo một reference/isolate khác).

YÊU CẦU: blastn (ncbi-blast+) cài sẵn trong PATH. Chạy trên máy có blast+,
KHÔNG chạy trong sandbox chat này.

Cách dùng:
    python3 03_build_primer_bed.py \
        --primers-fasta primers_parsed/D2_primers.fasta \
        --primers-csv   primers_parsed/D2_primers.csv \
        --reference     references/D2_chosen_reference.fasta \
        --out-prefix    final_bed/D2

Sinh ra:
    <out-prefix>.bed              : BED cuối cùng dùng cho --primer_bed
    <out-prefix>.primer_fasta.fa  : copy lại FASTA mồi dùng cho --primer_fasta
    <out-prefix>.mapping_report.tsv : chi tiết % identity / coverage mỗi mồi,
                                       để bạn soát lại các mồi map yếu (<95% identity
                                       hoặc coverage <100%) trước khi dùng.
"""
import argparse
import csv
import subprocess
import sys
import tempfile
import os


def run_blast(primers_fasta, reference_fasta):
    """BLAST ngắn (tối ưu cho mồi 18-25bp) từng mồi lên reference, trả về dict
    name -> best hit (sstart, send, sstrand, pident, qcovs, length)."""
    with tempfile.TemporaryDirectory() as tmp:
        db_prefix = os.path.join(tmp, "ref_db")
        subprocess.run(
            ["makeblastdb", "-in", reference_fasta, "-dbtype", "nucl", "-out", db_prefix],
            check=True, capture_output=True,
        )
        cmd = [
            "blastn", "-task", "blastn-short",
            "-query", primers_fasta, "-db", db_prefix,
            "-outfmt", "6 qseqid sseqid pident length qcovs sstart send sstrand evalue bitscore",
            "-evalue", "1000", "-word_size", "7", "-max_target_seqs", "5",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

    hits = {}
    for line in result.stdout.strip().splitlines():
        f = line.split("\t")
        qseqid, sseqid, pident, length, qcovs, sstart, send, sstrand, evalue, bitscore = f
        pident, length, qcovs, bitscore = float(pident), int(length), float(qcovs), float(bitscore)
        best = hits.get(qseqid)
        if best is None or bitscore > best["bitscore"]:
            hits[qseqid] = dict(
                sseqid=sseqid, pident=pident, length=length, qcovs=qcovs,
                sstart=int(sstart), send=int(send), sstrand=sstrand, bitscore=bitscore,
            )
    return hits


def load_pool_and_direction(primers_csv):
    info = {}
    with open(primers_csv) as f:
        for row in csv.DictReader(f):
            info[row["name"]] = row
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primers-fasta", required=True)
    ap.add_argument("--primers-csv", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--min-pident", type=float, default=90.0,
                     help="Ngưỡng %%identity tối thiểu để chấp nhận mồi map được (default 90)")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)

    hits = run_blast(args.primers_fasta, args.reference)
    pool_info = load_pool_and_direction(args.primers_csv)

    # lấy tên chrom từ header đầu tiên của file reference fasta
    with open(args.reference) as fh:
        header = fh.readline().strip()
    chrom = header.split()[0].lstrip(">") if header.startswith(">") else "REF"

    bed_lines = []
    report_rows = []
    n_missing, n_low_identity = 0, 0

    for name, meta in pool_info.items():
        direction = meta["direction"]  # LEFT / RIGHT
        pool = meta["pool"]
        hit = hits.get(name)

        if hit is None:
            n_missing += 1
            report_rows.append([name, direction, "NO_HIT", "", "", "", ""])
            continue

        if hit["pident"] < args.min_pident or hit["qcovs"] < 90:
            n_low_identity += 1

        s, e = sorted([hit["sstart"], hit["send"]])
        start0, end0 = s - 1, e  # BED 0-based half-open
        # strand chuẩn hoá theo quy ước ARTIC/iVar: LEFT='+' , RIGHT='-'
        strand = "+" if direction == "LEFT" else "-"
        suffix = "_LEFT" if direction == "LEFT" else "_RIGHT"

        bed_lines.append((chrom, start0, end0, f"{name}{suffix}", pool, strand))
        report_rows.append(
            [name, direction, f"{hit['pident']:.1f}", f"{hit['qcovs']:.0f}",
             hit["sstrand"], start0, end0]
        )

    bed_lines.sort(key=lambda x: x[1])  # sắp theo toạ độ tăng dần

    bed_path = f"{args.out_prefix}.bed"
    with open(bed_path, "w") as fbed:
        for chrom_, start0, end0, name_, pool_, strand_ in bed_lines:
            fbed.write(f"{chrom_}\t{start0}\t{end0}\t{name_}\t{pool_}\t{strand_}\n")

    report_path = f"{args.out_prefix}.mapping_report.tsv"
    with open(report_path, "w", newline="") as frep:
        w = csv.writer(frep, delimiter="\t")
        w.writerow(["name", "direction", "pident", "qcovs", "blast_strand", "bed_start0", "bed_end0"])
        w.writerows(report_rows)

    fasta_copy = f"{args.out_prefix}.primer_fasta.fa"
    with open(args.primers_fasta) as src, open(fasta_copy, "w") as dst:
        dst.write(src.read())

    print(f"-> {bed_path}  ({len(bed_lines)} mồi map thành công)")
    print(f"-> {report_path}")
    print(f"-> {fasta_copy}")
    if n_missing:
        print(f"⚠️  {n_missing} mồi KHÔNG map được lên reference này - kiểm tra lại serotype/reference đã chọn.")
    if n_low_identity:
        print(f"⚠️  {n_low_identity} mồi có %identity<{args.min_pident} hoặc coverage<90% - xem report để soát tay.")
    if n_missing or n_low_identity:
        sys.exit(1)


if __name__ == "__main__":
    main()
