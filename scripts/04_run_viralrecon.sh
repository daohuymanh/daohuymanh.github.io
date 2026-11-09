#!/usr/bin/env bash
#
# 04_run_viralrecon.sh  (phiên bản 2)
# ----------------------------------------------------------------------------------
# Chạy nf-core/viralrecon cho MỘT type (serotype/virus) mỗi lần, vì mỗi type có reference, BED, GFF
# và samplesheet riêng.
#
# THAY ĐỔI QUAN TRỌNG SO VỚI PHIÊN BẢN 1
#   * Illumina luôn truyền --protocol amplicon. Mặc định của viralrecon là 'metagenomic': khi đó
#     iVar KHÔNG cắt primer, --primer_bed không được dùng để cắt, và caller mặc định là bcftools.
#     Nếu thiếu cờ này, consensus tại vị trí mồi phản ánh trình tự MỒI chứ không phải trình tự mẫu.
#   * Ghim phiên bản pipeline (-r) và Nextflow (NXF_VER); profile mặc định conda (đã kiểm chứng).
#   * Kiểm tra trước khi chạy: file tồn tại, tên sequence trong BED khớp FASTA, tên mồi có _LEFT/_RIGHT.
#   * Tham số tuỳ chọn qua biến môi trường (GFF, bỏ Pangolin/Nextclade/Freyja, bỏ assembly...).
#   * Nhánh Nanopore cập nhật theo tham số của viralrecon 3.0.0 (CHƯA kiểm chứng trên dữ liệu thật).
#
# CÁCH DÙNG
#   Illumina:
#     ./04_run_viralrecon.sh illumina <TYPE> <samplesheet.csv> <primer.bed> <reference.fasta> <outdir>
#   Nanopore (ARTIC):
#     ./04_run_viralrecon.sh nanopore <TYPE> <samplesheet.csv> <primer.bed> <reference.fasta> <outdir> <fastq_pass_dir>
#
# BIẾN MÔI TRƯỜNG (tất cả tuỳ chọn)
#   VR_VERSION=3.0.0   NXF_VER=25.04.6   PROFILE=conda   CUSTOM_CONFIG=custom.config
#   GFF=duong_dan.gff             (cần cho SnpEff; nên cung cấp)
#   PRIMER_FASTA=mồi.fa           (chỉ cần khi chạy assembly de novo ở chế độ amplicon)
#   VARIANT_CALLER=ivar|bcftools  (trống = mặc định của pipeline: ivar cho amplicon)
#   SKIP_PANGOLIN=1  SKIP_ASSEMBLY=1  SKIP_QUAST=1  SKIP_KRAKEN2=0   (1 = bỏ bước đó)
#   EXTRA_ARGS="--ivar_trim_offset 5"   (tham số bổ sung tuỳ ý)
#   DRY_RUN=1                      (chỉ in lệnh, không chạy)
#   Nanopore: ARTIC_SCHEME, PRIMER_SET, PRIMER_SET_VERSION, ARTIC_MODEL (Clair3)
#
set -euo pipefail

MODE="${1:?illumina | nanopore}"
TYPE="${2:?tên type, ví dụ D1, ZIKV, CHIKV}"
SAMPLESHEET="${3:?samplesheet.csv}"
PRIMER_BED="${4:?primer.bed}"
REF_FASTA="${5:?reference.fasta}"
OUTDIR="${6:?outdir}"

VR_VERSION="${VR_VERSION:-3.0.0}"
export NXF_VER="${NXF_VER:-25.04.6}"
PROFILE="${PROFILE:-conda}"
CUSTOM_CONFIG="${CUSTOM_CONFIG:-custom.config}"

# ---- Kiểm tra trước khi chạy ----
for f in "$SAMPLESHEET" "$PRIMER_BED" "$REF_FASTA"; do
  [ -s "$f" ] || { echo "[LỖI] Không thấy file hoặc file rỗng: $f" >&2; exit 1; }
done
if [ -n "${GFF:-}" ] && [ ! -s "$GFF" ]; then echo "[LỖI] Không thấy GFF: $GFF" >&2; exit 1; fi

chrom_fa=$(head -n 1 "$REF_FASTA" | sed 's/^>//; s/[[:space:]].*//')
bad_chrom=$(cut -f1 "$PRIMER_BED" | sort -u | grep -vx "$chrom_fa" || true)
if [ -n "$bad_chrom" ]; then
  echo "[LỖI] Cột 1 của BED không khớp tên sequence trong FASTA ('$chrom_fa'). Giá trị lạ: $bad_chrom" >&2
  echo "      Dựng lại BED bằng 03_build_primer_bed.py với đúng reference này." >&2
  exit 1
fi
no_suffix=$(cut -f4 "$PRIMER_BED" | grep -v -E '_LEFT|_RIGHT' | wc -l || true)
if [ "$no_suffix" -gt 0 ]; then
  echo "[LỖI] $no_suffix mồi trong BED thiếu hậu tố _LEFT/_RIGHT (đặt --primer_left_suffix/--primer_right_suffix nếu dùng hậu tố khác)." >&2
  exit 1
fi
if [ -n "${GFF:-}" ]; then
  gff_chrom=$(grep -v '^#' "$GFF" | cut -f1 | sort -u | head -n 5)
  echo "$gff_chrom" | grep -qx "$chrom_fa" || \
    echo "[CẢNH BÁO] Tên sequence trong GFF (${gff_chrom//$'\n'/, }) khác FASTA ('$chrom_fa'): SnpEff có thể không chú giải được." >&2
fi
if [ -z "${TMUX:-}" ] && [ -z "${STY:-}" ]; then
  echo "[GỢI Ý] Bạn chưa ở trong tmux/screen; pipeline dài nên chạy trong tmux để không mất khi SSH rớt." >&2
fi

# ---- Dựng lệnh ----
COMMON=( -r "$VR_VERSION" -profile "$PROFILE" -ansi-log false -resume )
if [ -s "$CUSTOM_CONFIG" ]; then COMMON+=( -c "$CUSTOM_CONFIG" ); fi

ARGS=( --input "$SAMPLESHEET" --outdir "$OUTDIR" --fasta "$REF_FASTA" --primer_bed "$PRIMER_BED" )
if [ -n "${GFF:-}" ]; then ARGS+=( --gff "$GFF" ); fi

case "$MODE" in
  illumina)
    ARGS+=( --platform illumina --protocol amplicon )
    if [ -n "${PRIMER_FASTA:-}" ]; then ARGS+=( --primer_fasta "$PRIMER_FASTA" ); fi
    if [ -n "${VARIANT_CALLER:-}" ]; then ARGS+=( --variant_caller "$VARIANT_CALLER" ); fi
    if [ "${SKIP_PANGOLIN:-1}" = 1 ]; then ARGS+=( --skip_pangolin --skip_nextclade --skip_freyja ); fi
    if [ "${SKIP_ASSEMBLY:-1}" = 1 ]; then ARGS+=( --skip_assembly ); fi
    if [ "${SKIP_QUAST:-1}" = 1 ]; then ARGS+=( --skip_variants_quast ); fi
    if [ "${SKIP_KRAKEN2:-0}" = 1 ]; then ARGS+=( --skip_kraken2 ); fi
    ;;
  nanopore)
    FASTQ_DIR="${7:?thư mục fastq_pass}"
    ARGS+=( --platform nanopore --fastq_dir "$FASTQ_DIR" )
    if [ -n "${ARTIC_SCHEME:-}" ]; then ARGS+=( --artic_scheme "$ARTIC_SCHEME" ); fi
    if [ -n "${PRIMER_SET:-}" ]; then ARGS+=( --primer_set "$PRIMER_SET" ); fi
    if [ -n "${PRIMER_SET_VERSION:-}" ]; then ARGS+=( --primer_set_version "$PRIMER_SET_VERSION" ); fi
    if [ -n "${ARTIC_MODEL:-}" ]; then ARGS+=( --artic_minion_model "$ARTIC_MODEL" ); fi
    if [ "${SKIP_PANGOLIN:-1}" = 1 ]; then ARGS+=( --skip_pangolin --skip_nextclade --skip_freyja ); fi
    if [ "${SKIP_QUAST:-1}" = 1 ]; then ARGS+=( --skip_variants_quast ); fi
    echo "[LƯU Ý] Nhánh Nanopore của viralrecon 3.0.0 dùng ARTIC (Clair3), tham số khác phiên bản 2.x" >&2
    echo "        (không còn --artic_minion_caller/medaka). Kiểm tra bằng: nextflow run nf-core/viralrecon -r $VR_VERSION --help" >&2
    ;;
  *)
    echo "MODE phải là 'illumina' hoặc 'nanopore'" >&2; exit 1 ;;
esac

if [ -n "${EXTRA_ARGS:-}" ]; then
  read -r -a EXTRA <<< "$EXTRA_ARGS"
  ARGS+=( "${EXTRA[@]}" )
fi

CMD=( nextflow run nf-core/viralrecon "${COMMON[@]}" "${ARGS[@]}" )
echo "== $MODE / $TYPE (NXF_VER=$NXF_VER) =="
printf '%q ' "${CMD[@]}"; echo
if [ "${DRY_RUN:-0}" = 1 ]; then echo "(DRY_RUN: không chạy)"; exit 0; fi

"${CMD[@]}"

echo "== Hoàn tất $MODE / $TYPE. Kết quả: $OUTDIR =="
echo "   Báo cáo tổng hợp: $OUTDIR/multiqc/multiqc_report.html"
echo "   Kiểm tra iVar đã chạy: grep -c -i ivar_trim $OUTDIR/pipeline_info/execution_trace_*.txt   (phải > 0 ở chế độ amplicon)"
