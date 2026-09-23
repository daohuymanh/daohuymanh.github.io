#!/usr/bin/env bash
#
# 04_run_viralrecon.sh
# ----------------------
# Chạy nf-core/viralrecon CHO TỪNG SEROTYPE riêng (vì mỗi serotype có
# reference + primer BED/FASTA khác nhau). Gọi 1 trong 2 mode:
#
#   ./04_run_viralrecon.sh illumina D2 \
#       samplesheet_illumina_D2.csv \
#       final_bed/D2.bed final_bed/D2.primer_fasta.fa \
#       references/D2_chosen_reference.fasta \
#       results_illumina_D2
#
#   ./04_run_viralrecon.sh nanopore D2 \
#       samplesheet_nanopore_D2.csv \
#       final_bed/D2.bed \
#       references/D2_chosen_reference.fasta \
#       results_nanopore_D2 \
#       fastq_pass_D2/ \
#       medaka <ten_model_medaka>
#
set -euo pipefail
MODE="${1:?illumina | nanopore}"
SEROTYPE="${2:?vd D1/D2/D3/D4}"

case "$MODE" in
  illumina)
    SAMPLESHEET="${3:?samplesheet.csv}"
    PRIMER_BED="${4:?primer.bed}"
    PRIMER_FASTA="${5:?primer.fasta}"
    REF_FASTA="${6:?reference.fasta}"
    OUTDIR="${7:?outdir}"

    nextflow run nf-core/viralrecon \
      --input "$SAMPLESHEET" \
      --outdir "$OUTDIR" \
      --platform illumina \
      --protocol amplicon \
      --fasta "$REF_FASTA" \
      --primer_bed "$PRIMER_BED" \
      --primer_fasta "$PRIMER_FASTA" \
      -profile docker \
      -resume
    ;;

  nanopore)
    SAMPLESHEET="${3:?samplesheet.csv}"
    PRIMER_BED="${4:?primer.bed}"
    REF_FASTA="${5:?reference.fasta}"
    OUTDIR="${6:?outdir}"
    FASTQ_DIR="${7:?fastq_pass dir}"
    CALLER="${8:-medaka}"           # medaka (mặc định, không cần fast5) hoặc nanopolish
    MEDAKA_MODEL="${9:-}"

    EXTRA_ARGS=()
    if [ "$CALLER" = "medaka" ]; then
      : "${MEDAKA_MODEL:?Cần truyền tên medaka model khi dùng --artic_minion_caller medaka}"
      EXTRA_ARGS+=(--artic_minion_medaka_model "$MEDAKA_MODEL")
    fi

    nextflow run nf-core/viralrecon \
      --input "$SAMPLESHEET" \
      --outdir "$OUTDIR" \
      --platform nanopore \
      --fasta "$REF_FASTA" \
      --primer_bed "$PRIMER_BED" \
      --fastq_dir "$FASTQ_DIR" \
      --artic_minion_caller "$CALLER" \
      "${EXTRA_ARGS[@]}" \
      -profile docker \
      -resume
    ;;

  *)
    echo "MODE phải là 'illumina' hoặc 'nanopore'"; exit 1 ;;
esac

echo "== Hoàn tất $MODE / $SEROTYPE. Kết quả tại: $OUTDIR =="
echo "   Xem báo cáo tổng hợp: $OUTDIR/multiqc/"
