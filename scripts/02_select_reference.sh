#!/usr/bin/env bash
#
# 02_select_reference.sh  (phiên bản 2)
# ------------------------------------------------------------------------
# Chọn reference (genotype/isolate) khớp nhất cho từng mẫu, TRONG PHẠM VI type đã biết trước
# (serotype Dengue, virus, hoặc type Enterovirus...). Không BLAST để "đoán" type.
#
# So với phiên bản 1:
#   - Không cố định D1..D4: mọi thư mục con của <contigs_dir> là một type. Accession RefSeq lấy từ
#     bảng mặc định (Dengue) hoặc từ file TSV (cột 1 = tên type, cột 2 = accession) qua REFSEQ_TSV.
#   - "Best hit" tính theo TỔNG bitscore của từng reference trên mọi đoạn/contig của mẫu, và
#     %identity tính có trọng số theo độ dài căn, thay vì lấy một đoạn căn ngắn có identity cao.
#   - Cảnh báo khi mẫu khác reference quá xa (pident < PIDENT_WARN, mặc định 95): cần bổ sung
#     genotype lưu hành vào <type>_extra.fasta. (Bài học lô DENV1: reference RefSeq cách mẫu ~7%.)
#   - Sinh bảng tóm tắt theo type và (tuỳ chọn AUTO_CHOOSE=1) tự tải reference được chọn nhiều nhất.
#
# YÊU CẦU (chạy trên máy có Internet): blastn, makeblastdb (ncbi-blast+), efetch (NCBI edirect).
#
# TỔ CHỨC THƯ MỤC ĐẦU VÀO:
#   contigs_per_sample/
#     D1/  DENV1_S001.fasta ...
#     D2/  DENV2_S002.fasta ...
#   (contig SPAdes hoặc consensus FASTA của từng mẫu; xem hướng dẫn)
#
# Cách dùng:
#   ./02_select_reference.sh <contigs_per_sample_dir> <output_dir>
#
# Biến môi trường tuỳ chọn:
#   REFSEQ_TSV=refseq.tsv   # type<TAB>accession (bắt buộc với virus ngoài Dengue)
#   PIDENT_WARN=95          # ngưỡng cảnh báo identity
#   AUTO_CHOOSE=1           # tự tải reference chiếm đa số thành <type>_chosen_reference.fasta
#
set -euo pipefail

QUERY_ROOT="${1:?Cần truyền thư mục gốc chứa contig, tổ chức theo thư mục con = type}"
OUTDIR="${2:?Cần truyền thư mục output}"
PIDENT_WARN="${PIDENT_WARN:-95}"
AUTO_CHOOSE="${AUTO_CHOOSE:-0}"
mkdir -p "$OUTDIR"/{db,results,references}

# RefSeq mặc định cho Dengue (xác nhận lại trên NCBI trước khi dùng).
declare -A REFSEQ=(
  [D1]="NC_001477.1"
  [D2]="NC_001474.2"
  [D3]="NC_001475.2"
  [D4]="NC_002640.1"
)
if [ -n "${REFSEQ_TSV:-}" ]; then
  [ -s "$REFSEQ_TSV" ] || { echo "Không đọc được $REFSEQ_TSV"; exit 1; }
  while IFS=$'\t' read -r t a _; do
    [ -z "${t:-}" ] || [[ "$t" == \#* ]] || REFSEQ[$t]="$a"
  done < "$REFSEQ_TSV"
fi

summary="$OUTDIR/results/best_reference_per_sample.tsv"
echo -e "sample\ttype\tbest_hit_accession\tbest_hit_title\tpident_weighted\tqcovs\taligned_length" > "$summary"

shopt -s nullglob
for QUERY_DIR in "$QUERY_ROOT"/*/; do
  TYPE=$(basename "$QUERY_DIR")
  acc="${REFSEQ[$TYPE]:-}"
  if [ -z "$acc" ]; then
    echo "[!] Type '$TYPE': chưa có accession RefSeq. Thêm vào REFSEQ_TSV (type<TAB>accession). Bỏ qua." >&2
    continue
  fi

  echo "== $TYPE: chuẩn bị ngân hàng reference (RefSeq $acc + extra nếu có) =="
  bank="$OUTDIR/references/${TYPE}_bank.fasta"
  refseq_file="$OUTDIR/references/${TYPE}_${acc}.fasta"
  if [ ! -s "$refseq_file" ]; then
    echo "  Tải RefSeq $TYPE ($acc) ..."
    efetch -db nuccore -id "$acc" -format fasta > "$refseq_file"
  fi
  : > "$bank"
  cat "$refseq_file" >> "$bank"
  extra="$OUTDIR/references/${TYPE}_extra.fasta"
  if [ -s "$extra" ]; then
    echo "  + gộp thêm genotype bổ sung từ $extra"
    cat "$extra" >> "$bank"
  else
    echo "  (chưa có $extra: chỉ dùng RefSeq $acc. Nên thêm vài genome hoàn chỉnh của cùng type lưu hành"
    echo "   tại khu vực lấy mẫu, tải từ NCBI Virus, để chọn được reference gần mẫu hơn.)"
  fi
  makeblastdb -in "$bank" -dbtype nucl -out "$OUTDIR/db/${TYPE}_bank" >/dev/null

  echo "== $TYPE: BLAST từng mẫu =="
  for qf in "$QUERY_DIR"*.fa "$QUERY_DIR"*.fasta; do
    sample=$(basename "$qf"); sample="${sample%.*}"
    out_tsv="$OUTDIR/results/${sample}.blast.tsv"
    blastn -query "$qf" -db "$OUTDIR/db/${TYPE}_bank" \
      -outfmt "6 qseqid sseqid stitle pident length qcovs evalue bitscore" \
      -max_target_seqs 50 -evalue 1e-10 > "$out_tsv"

    # Gộp mọi đoạn căn theo reference: tổng bitscore, identity trọng số theo độ dài căn
    best=$(awk -F'\t' '
      { s=$2; L[s]+=$5; P[s]+=$4*$5; B[s]+=$8; T[s]=$3; if ($6>C[s]) C[s]=$6 }
      END { bs=""
            for (s in B) if (bs=="" || B[s]>B[bs]) bs=s
            if (bs!="") printf "%s\t%s\t%.2f\t%d\t%d\n", bs, T[bs], P[bs]/L[bs], C[bs], L[bs] }' "$out_tsv")

    if [ -z "$best" ]; then
      echo "  [!] $sample ($TYPE): KHÔNG có hit -> kiểm tra lại chất lượng contig hoặc type"
      continue
    fi
    accn=$(echo "$best" | cut -f1); title=$(echo "$best" | cut -f2)
    pident=$(echo "$best" | cut -f3); qcovs=$(echo "$best" | cut -f4); alen=$(echo "$best" | cut -f5)
    echo -e "${sample}\t${TYPE}\t${accn}\t${title}\t${pident}\t${qcovs}\t${alen}" >> "$summary"
    echo "  [$sample] -> $accn  pident=${pident}% qcov=${qcovs}% (độ dài căn ${alen})"
    if awk -v p="$pident" -v t="$PIDENT_WARN" 'BEGIN{exit !(p<t)}'; then
      echo "  [!] $sample khác reference ${pident}% (< ${PIDENT_WARN}%): bổ sung genome cùng genotype vào ${TYPE}_extra.fasta rồi chạy lại"
    fi
  done
done

echo ""
echo "== Tóm tắt theo type (accession được chọn nhiều nhất) =="
type_summary="$OUTDIR/results/reference_choice_per_type.tsv"
{
  echo -e "type\taccession\tso_mau\tpident_trung_binh"
  awk -F'\t' 'NR>1 { k=$2 FS $3; n[k]++; s[k]+=$5 }
    END { for (k in n) { split(k,a,FS); printf "%s\t%s\t%d\t%.2f\n", a[1], a[2], n[k], s[k]/n[k] } }' "$summary" \
    | sort -t$'\t' -k1,1 -k3,3nr
} > "$type_summary"
column -t -s$'\t' "$type_summary" 2>/dev/null || cat "$type_summary"

if [ "$AUTO_CHOOSE" = "1" ]; then
  tail -n +2 "$type_summary" | awk -F'\t' '!seen[$1]++ {print $1"\t"$2}' | while IFS=$'\t' read -r t a; do
    f="$OUTDIR/references/${t}_chosen_reference.fasta"
    if [ -s "$f" ]; then echo "  (giữ nguyên $f đã có)"; continue; fi
    echo "  Tải $a làm reference cho $t -> $f"
    efetch -db nuccore -id "$a" -format fasta > "$f"
  done
fi

echo ""
echo "== Xong. Chi tiết: $summary ; tóm tắt: $type_summary =="
echo "Mỗi type: chọn accession chiếm đa số làm reference đại diện; nếu các mẫu lệch rõ rệt sang nhiều"
echo "accession khác nhau thì có thể có >1 genotype -> chạy riêng theo từng nhóm. Lưu reference đã chọn thành:"
echo "  $OUTDIR/references/<type>_chosen_reference.fasta   (hoặc đặt AUTO_CHOOSE=1)"
echo "Rồi chạy tiếp: 03_build_primer_bed.py"
