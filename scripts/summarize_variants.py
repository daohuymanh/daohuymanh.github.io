import csv, sys, collections

# Cách dùng: python3 summarize_variants.py variants_long_table.csv [min_AF] [min_DP] [tiền_tố_đầu_ra]
path = sys.argv[1]
min_af = float(sys.argv[2]) if len(sys.argv) > 2 else 0.75
min_dp = float(sys.argv[3]) if len(sys.argv) > 3 else 20
prefix = sys.argv[4] if len(sys.argv) > 4 else "mutations"

rows = list(csv.DictReader(open(path, newline='')))
if not rows:
    sys.exit("File rỗng")
print("Các cột:", ", ".join(rows[0].keys()), file=sys.stderr)

def g(r, *names):
    for n in names:
        if n in r and r[n] not in ("", None):
            return r[n]
    return ""

mut = collections.defaultdict(set)      # (khóa đột biến, tác động) -> tập mẫu
per_sample = collections.Counter()
samples = set()
for r in rows:
    flt = g(r, "FILTER")
    if flt and flt not in ("PASS", "."):
        continue
    try:
        af = float(g(r, "AF")); dp = float(g(r, "DP"))
    except ValueError:
        continue
    s = g(r, "SAMPLE")
    samples.add(s)
    if af < min_af or dp < min_dp:
        continue
    gene = g(r, "GENE")
    prot = g(r, "HGVS_P_1LETTER", "HGVS_P")
    eff = g(r, "EFFECT")
    key = f"{gene}:{prot}" if prot else f"{g(r,'CHROM')}:{g(r,'POS')}{g(r,'REF')}>{g(r,'ALT')}"
    mut[(key, eff)].add(s)
    per_sample[s] += 1

samples = sorted(samples)
with open(prefix + "_list.tsv", "w") as f:
    f.write("dot_bien\ttac_dong\tso_mau\tcac_mau\n")
    for (k, e), ss in sorted(mut.items(), key=lambda x: -len(x[1])):
        f.write(f"{k}\t{e}\t{len(ss)}\t{','.join(sorted(ss))}\n")
with open(prefix + "_matrix.tsv", "w") as f:
    f.write("dot_bien\t" + "\t".join(samples) + "\n")
    for (k, e), ss in sorted(mut.items(), key=lambda x: -len(x[1])):
        f.write(k + "\t" + "\t".join("1" if s in ss else "0" for s in samples) + "\n")
print(f"Số mẫu: {len(samples)}; số đột biến sau lọc: {len(mut)}", file=sys.stderr)
for s in samples:
    print(f"{s}\t{per_sample[s]}", file=sys.stderr)
