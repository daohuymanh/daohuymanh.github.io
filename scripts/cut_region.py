import sys

def read_fasta(p):
    d, k = {}, None
    for line in open(p):
        line = line.rstrip()
        if line.startswith('>'):
            k = line[1:]; d[k] = []
        elif k:
            d[k].append(line)
    return {a: ''.join(b) for a, b in d.items()}

# Cách dùng: python3 cut_region.py aligned.fasta out.fasta <tiền_tố_tên_reference> <bắt_đầu> <kết_thúc>
inp, out, refprefix = sys.argv[1], sys.argv[2], sys.argv[3]
start, end = int(sys.argv[4]), int(sys.argv[5])      # tọa độ trên reference
aln = read_fasta(inp)
ref = next(v for k, v in aln.items() if k.startswith(refprefix))
pos, cols = 0, []
for i, c in enumerate(ref):
    if c != '-':
        pos += 1
    if start <= pos <= end:
        cols.append(i)
lo, hi = cols[0], cols[-1] + 1
with open(out, 'w') as f:
    for k, v in aln.items():
        f.write('>' + k + '\n' + v[lo:hi] + '\n')
print('Các cột giữ lại:', lo, hi, 'độ dài:', hi - lo)
