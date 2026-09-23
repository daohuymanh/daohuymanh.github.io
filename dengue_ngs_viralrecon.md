title: Pipeline giải trình tự Dengue (multi-primer amplicon) trên nf-core/viralrecon
slug: dengue_ngs_viralrecon.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.23
reading_time: 20 phút đọc
author: Đào Huy Mạnh
excerpt: Pipeline giải trình tự Dengue (multi-primer amplicon) trên nf-core-viralrecon
scripts: 01_parse_primers.py|02_select_reference.sh|03_build_primer_bed.py|04_run_viralrecon.sh|fastq_dir_to_samplesheet.py
---
# Pipeline giải trình tự Dengue (multi-primer amplicon) trên nf-core/viralrecon

Bộ script này tự động hoá 3 bước bạn yêu cầu, nối tiếp nhau:

```
Excel mồi (4 serotype)          dữ liệu NGS (contig/reads)
        │                                │
        ▼                                ▼
01_parse_primers.py          02_select_reference.sh   (BLAST -> chọn reference/serotype)
        │                                │
        └───────────────┬────────────────┘
                         ▼
              03_build_primer_bed.py   (BLAST từng mồi lên reference đã chọn -> BED chuẩn)
                         │
                         ▼
              04_run_viralrecon.sh     (chạy nf-core/viralrecon: Illumina MiSeq / Nanopore)
```

**Quan trọng:** các script 02 và 03 cần `blastn`/`makeblastdb` (gói `ncbi-blast+`)
và Internet (để tải genome tham chiếu).

---

## Bước 0 — Chuẩn bị file primer

Chuẩn bị file excel chứa thông tin mồi. Ví dụ Mồi_NGS_DEN.xlsx. Trong file chứa các cột sau:  Thứ tự, Name, Position (From, To), Sequence of primer (5’-3’), Length of primer, size (bp), Pool để chuẩn bị làm file .BED cho phân tích.

---

## Bước 1 — chuẩn hoá bảng mồi

Chạy sau khi có file primer Excel: 
```bash
python3 scripts/01_parse_primers.py Mồi_NGS_DEN.xlsx primers_parsed
```

## Bước 2 — Chọn reference (genotype) phù hợp, TRONG PHẠM VI serotype đã biết trước

Vì serotype mỗi mẫu **đã biết trước** (RT-PCR định type...), script không còn
BLAST để "đoán serotype" nữa — chỉ BLAST để chọn đúng **genotype/isolate**
tham chiếu khớp nhất trong chính serotype đó, nhanh hơn và tránh nhầm chéo.

**Bắt buộc tổ chức contig/consensus theo thư mục con = serotype đã biết:**
```
contigs_per_sample/
  D1/  DENV1_S001.fasta  DENV1_S007.fasta
  D2/  DENV2_S002.fasta  DENV2_S010.fasta
  D3/  DENV3_S003.fasta
  D4/  DENV4_S004.fasta
```
(chỉ tạo thư mục cho serotype bạn thực sự có mẫu; xem cách lấy contig từ
Illumina/Nanopore ở mục "Lấy contig/consensus đầu vào cho bước 2" bên dưới)

**(Khuyến nghị) trước khi chạy**, bổ sung thêm vài genotype đang lưu hành tại
khu vực lấy mẫu cho từng serotype (không bắt buộc, nhưng giúp chọn reference
sát thực tế hơn RefSeq đơn lẻ):
```
ref_selection_out/references/D1_extra.fasta   # tự tải từ NCBI Virus, gộp thêm
ref_selection_out/references/D2_extra.fasta
...
```

Chạy:
```bash
bash scripts/02_select_reference.sh contigs_per_sample/ ref_selection_out/
```
Script tự động: với mỗi serotype có mẫu → build ngân hàng BLAST riêng (RefSeq
+ file `_extra.fasta` nếu có) → BLAST từng mẫu trong đúng serotype đó.

Kết quả `ref_selection_out/results/best_reference_per_sample.tsv` cho biết
accession NCBI khớp nhất với từng mẫu (kèm cột serotype để đối chiếu). Trong
từng serotype, nếu các mẫu đều khớp cùng 1 accession → chọn accession đó làm
reference đại diện; nếu các mẫu lệch rõ rệt sang accession khác nhau → có thể
đang lưu hành >1 genotype, cân nhắc dùng reference riêng cho từng nhóm mẫu.
Tải genome accession đã chọn, lưu thành:
```
ref_selection_out/references/D1_chosen_reference.fasta
ref_selection_out/references/D2_chosen_reference.fasta
ref_selection_out/references/D3_chosen_reference.fasta
ref_selection_out/references/D4_chosen_reference.fasta
```

### Lấy contig/consensus đầu vào cho bước 2

**Từ Illumina MiSeq:**
```bash
fastp -i sample_R1.fastq.gz -I sample_R2.fastq.gz \
      -o sample_R1.trim.fastq.gz -O sample_R2.trim.fastq.gz
spades.py -1 sample_R1.trim.fastq.gz -2 sample_R2.trim.fastq.gz \
          -o sample_spades_out --only-assembler
cp sample_spades_out/contigs.fasta contigs_per_sample/D2/DENV2_S001.fasta
```

**Từ Nanopore:**
```bash
NanoFilt -q 10 -l 500 < sample.fastq > sample.filt.fastq
# cách nhanh: lấy trực tiếp một số read dài/tốt làm "pseudo-contig"
seqtk seq -A sample.filt.fastq | head -400 > contigs_per_sample/D2/DENV2_S001.fasta
# hoặc assembly gọn bằng Flye nếu muốn 1 contig/mẫu
flye --nano-raw sample.filt.fastq --out-dir sample_flye_out --meta
cp sample_flye_out/assembly.fasta contigs_per_sample/D2/DENV2_S001.fasta
```

## Bước 3 — Dựng BED mồi chính xác (BLAST mồi lên reference đã chọn)

```bash
mkdir -p final_bed
for D in D1 D2 D3 D4; do
  python3 scripts/03_build_primer_bed.py \
    --primers-fasta primers_parsed/${D}_primers.fasta \
    --primers-csv   primers_parsed/${D}_primers.csv \
    --reference     ref_selection_out/references/${D}_chosen_reference.fasta \
    --out-prefix    final_bed/${D}
done
```
Kiểm tra `final_bed/D*.mapping_report.tsv` — mồi nào có `pident<90` hoặc
`qcovs<90` cần xem lại (thiết kế mồi lệch reference, hoặc reference chọn sai
genotype).

## Bước 4 — Chạy nf-core/viralrecon (giống pipeline gốc đã phân tích ở trên)

**Illumina MiSeq**, ví dụ serotype D2:
```bash
bash scripts/04_run_viralrecon.sh illumina D2 \
  samplesheet_illumina_D2.csv \
  final_bed/D2.bed \
  final_bed/D2.primer_fasta.fa \
  ref_selection_out/references/D2_chosen_reference.fasta \
  results_illumina_D2
```

**Nanopore** (Medaka, không cần fast5), ví dụ serotype D2:
```bash
bash scripts/04_run_viralrecon.sh nanopore D2 \
  samplesheet_nanopore_D2.csv \
  final_bed/D2.bed \
  ref_selection_out/references/D2_chosen_reference.fasta \
  results_nanopore_D2 \
  fastq_pass_D2/ \
  medaka <tên_model_medaka_theo_kit/flowcell>
```

Samplesheet mẫu:
```csv
# Illumina
sample,fastq_1,fastq_2
DENV2_S001,DENV2_S001_R1.fastq.gz,DENV2_S001_R2.fastq.gz

# Nanopore
sample,barcode
DENV2_S001,1
```

Chạy riêng từng serotype (samplesheet/BED/reference khác nhau) — nếu 1 lô
mẫu lẫn nhiều serotype, tách mẫu theo serotype (dựa kết quả BLAST ở bước 2)
trước khi tạo samplesheet cho từng lần chạy.

Sau khi chạy xong, các bước phân tích downstream (QC iVar/artic, consensus,
SnpEff annotation, coverage mosdepth, MultiQC...) giữ nguyên như phần pipeline
viralrecon đã trình bày trước đó — không có gì khác biệt thêm ngoài việc mỗi
serotype dùng bộ `--fasta`/`--primer_bed`/`--primer_fasta` riêng.

---

## Yêu cầu công cụ

| Bước | Công cụ cần cài |
|---|---|
| 01 | Python 3 + `openpyxl` |
| 02 | `ncbi-blast+` (blastn, makeblastdb), NCBI `edirect` (efetch/esearch), Internet |
| 03 | `ncbi-blast+`, Python 3 |
| 04 | Nextflow, Docker/Singularity, Internet (kéo pipeline + container nf-core/viralrecon) |
