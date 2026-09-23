#!/usr/bin/env bash
#
# 02_select_reference.sh  (bản cập nhật: ĐÃ BIẾT TRƯỚC SEROTYPE mỗi mẫu)
# ------------------------------------------------------------------------
# Vì serotype của từng mẫu đã biết (vd. bằng RT-PCR định type trước đó),
# script này KHÔNG còn BLAST vào cả 4 serotype để "đoán" nữa. Nó chỉ dùng
# BLAST để chọn ĐÚNG GENOTYPE/ISOLATE tham chiếu phù hợp nhất TRONG PHẠM VI
# serotype đã biết của từng mẫu -> nhanh hơn, tránh nguy cơ nhầm chéo serotype
# do contig ngắn/nhiễu.
#
# YÊU CẦU (chạy trên máy/server CÓ INTERNET, không phải trong sandbox chat):
#   - blastn, makeblastdb (gói ncbi-blast+)
#   - NCBI edirect (efetch/esearch) để tải genome tham chiếu
#   - dữ liệu đầu vào: contig/consensus FASTA sơ bộ của từng mẫu (xem hướng
#     dẫn lấy contig từ Illumina/Nanopore trong README)
#
# TỔ CHỨC THƯ MỤC ĐẦU VÀO (bắt buộc theo serotype đã biết):
#   contigs_per_sample/
#     D1/  DENV1_S001.fasta  DENV1_S007.fasta ...
#     D2/  DENV2_S002.fasta  DENV2_S010.fasta ...
#     D3/  DENV3_S003.fasta ...
#     D4/  DENV4_S004.fasta ...
#   (chỉ cần tạo các thư mục serotype bạn thực sự có mẫu, không bắt buộc đủ 4)
#
# Cách dùng:
#   ./02_select_reference.sh <contigs_per_sample_dir> <output_dir>
#
set -euo pipefail

QUERY_ROOT="${1:?Cần truyền thư mục gốc chứa contig, tổ chức theo D1/D2/D3/D4/}"
OUTDIR="${2:?Cần truyền thư mục output}"
mkdir -p "$OUTDIR"/{db,results,references}

# RefSeq làm khung tối thiểu cho mỗi serotype. NÊN bổ sung thêm các genotype/
# isolate lưu hành phổ biến tại địa bàn lấy mẫu của bạn (xem ghi chú dưới)
# vào file "$OUTDIR/references/<SEROTYPE>_extra.fasta" TRƯỚC khi chạy script -
# script sẽ tự gộp file đó vào ngân hàng BLAST của đúng serotype tương ứng.
declare -A REFSEQ=(
  [D1]="NC_001477.1"
  [D2]="NC_001474.2"
  [D3]="NC_001475.2"
  [D4]="NC_002640.1"
)

summary="$OUTDIR/results/best_reference_per_sample.tsv"
echo -e "sample\tserotype\tbest_hit_accession\tbest_hit_title\tpident\tqcovs\tlength" > "$summary"

for SEROTYPE in D1 D2 D3 D4; do
  QUERY_DIR="$QUERY_ROOT/$SEROTYPE"
  [ -d "$QUERY_DIR" ] || continue   # bỏ qua serotype không có mẫu

  echo "== $SEROTYPE: chuẩn bị ngân hàng reference (chỉ trong phạm vi $SEROTYPE) =="
  acc="${REFSEQ[$SEROTYPE]}"
  bank="$OUTDIR/references/${SEROTYPE}_bank.fasta"
  refseq_file="$OUTDIR/references/${SEROTYPE}_${acc}.fasta"

  if [ ! -s "$refseq_file" ]; then
    echo "  Tải RefSeq $SEROTYPE ($acc) ..."
    efetch -db nuccore -id "$acc" -format fasta > "$refseq_file"
  fi

  : > "$bank"
  cat "$refseq_file" >> "$bank"

  extra="$OUTDIR/references/${SEROTYPE}_extra.fasta"
  if [ -s "$extra" ]; then
    echo "  + gộp thêm genotype bổ sung từ $extra"
    cat "$extra" >> "$bank"
  else
    echo "  (chưa có $extra - chỉ dùng RefSeq đơn lẻ $acc. Khuyến nghị bổ sung"
    echo "   thêm vài genotype $SEROTYPE lưu hành tại khu vực lấy mẫu để BLAST"
    echo "   chọn được genotype khớp nhất, không chỉ khớp RefSeq mặc định."
    echo "   Tìm/tải qua NCBI Virus, lọc theo serotype:"
    echo "   https://www.ncbi.nlm.nih.gov/labs/virus/vssi/#/virus?SeqType_s=Nucleotide&VirusLineage_ss=Dengue%20virus,%20taxid:12637"
  fi

  echo "== $SEROTYPE: tạo BLAST database =="
  makeblastdb -in "$bank" -dbtype nucl -out "$OUTDIR/db/${SEROTYPE}_bank" >/dev/null

  echo "== $SEROTYPE: BLAST từng mẫu trong $QUERY_DIR =="
  for qf in "$QUERY_DIR"/*.fa "$QUERY_DIR"/*.fasta; do
    [ -e "$qf" ] || continue
    sample=$(basename "$qf"); sample="${sample%.*}"
    out_tsv="$OUTDIR/results/${sample}.blast.tsv"

    blastn -query "$qf" -db "$OUTDIR/db/${SEROTYPE}_bank" \
      -outfmt "6 qseqid sseqid stitle pident length qcovs evalue bitscore" \
      -max_target_seqs 5 -evalue 1e-10 > "$out_tsv"

    best=$(sort -t$'\t' -k4,4nr -k6,6nr "$out_tsv" | head -n1)
    if [ -z "$best" ]; then
      echo "  [!] $sample ($SEROTYPE): KHÔNG có hit -> kiểm tra lại chất lượng contig/mẫu"
      continue
    fi
    accn=$(echo "$best" | cut -f2); title=$(echo "$best" | cut -f3)
    pident=$(echo "$best" | cut -f4); length=$(echo "$best" | cut -f5); qcovs=$(echo "$best" | cut -f6)
    echo -e "${sample}\t${SEROTYPE}\t${accn}\t${title}\t${pident}\t${qcovs}\t${length}" >> "$summary"
    echo "  [$sample] -> $accn ($title) pident=${pident}% qcov=${qcovs}%"
  done
done

echo ""
echo "== Xong. Xem tổng hợp tại: $summary =="
echo "Với mỗi serotype, xem accession trùng lặp/chiếm đa số giữa các mẫu -> chọn"
echo "làm reference đại diện chính thức cho serotype đó (nếu các mẫu cùng"
echo "serotype nhưng khớp accession khác nhau rõ rệt, có thể có >1 genotype"
echo "đang lưu hành -> cân nhắc chạy riêng theo từng genotype)."
echo "Tải genome accession đã chọn, lưu thành:"
echo "  $OUTDIR/references/<SEROTYPE>_chosen_reference.fasta"
echo "rồi chạy tiếp: 03_build_primer_bed.py"
