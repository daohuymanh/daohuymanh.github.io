import sys, re, glob
# Cách dùng: python3 qc_consensus.py "<glob consensus>" <start_CDS> <end_CDS>
files = sorted(glob.glob(sys.argv[1]))
start, end = int(sys.argv[2]), int(sys.argv[3])
print("mau\tdo_dai\ttong_N\t%N\tN_trong_CDS\t%N_CDS\tdoan_N_dai_nhat_trong_CDS")
for f in files:
    seq = ''.join(l.strip() for l in open(f) if not l.startswith('>')).upper()
    n = seq.count('N')
    w = seq[start-1:end]
    nw = w.count('N')
    longest = max([len(m.group()) for m in re.finditer(r'N+', w)] or [0])
    name = f.split('/')[-1].replace('.consensus.fa', '')
    print(f"{name}\t{len(seq)}\t{n}\t{100*n/len(seq):.1f}\t{nw}\t{100*nw/max(len(w),1):.1f}\t{longest}")
