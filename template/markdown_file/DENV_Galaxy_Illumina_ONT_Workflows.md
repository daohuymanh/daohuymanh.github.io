title: Hướng dẫn phân tích giải trình tự với Galaxy
slug: dengue_NGS_Galaxy.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.11
reading_time: 20 phút đọc
author: Mạnh Phượng
excerpt: Phân tích dữ liệu giải trình tự gen thế hệ mới từ Illumina và ONT trên nền tảng Galaxy
scripts: 
---
# Galaxy workflows for whole-genome Dengue virus sequencing from tiled amplicons

## Mục tiêu

Tài liệu này đề xuất **hai workflow Galaxy độc lập** để phân tích dữ liệu FASTQ từ giải trình tự toàn bộ genome virus Dengue (DENV) bằng phương pháp **tiled amplicon sequencing**:

1. **Illumina workflow** — short, high-accuracy reads.
2. **Oxford Nanopore (ONT) workflow** — long reads, thường cho phép nối các vùng amplicon dài và có thể phát hiện biến thể, nhưng cần kiểm soát chất lượng và primer rất chặt.

Mục tiêu đầu ra là một bộ dữ liệu có thể sử dụng cho nghiên cứu genomics/phylogenetics và chuẩn bị cho công bố quốc tế:

- QC trước và sau trimming.
- FASTQ đã loại adapter/primer và reads chất lượng thấp.
- BAM alignment với reference DENV phù hợp.
- Coverage theo genome và theo amplicon.
- Consensus genome FASTA.
- VCF/BCF và bảng biến thể.
- Kiểm tra biến thể ở các vị trí có coverage đủ.
- QC consensus: % genome được phủ, depth, Ns, chiều dài.
- Phylogenetic dataset và cây phát sinh chủng loại.
- Metadata và workflow version để đảm bảo reproducibility.

> **Quan trọng:** Đây là workflow phân tích dữ liệu đã được giải trình tự. Thiết kế/điều kiện PCR và tối ưu mồi cần được xác định, thẩm định và kiểm soát trong phòng xét nghiệm trước khi chạy sequencing.

---

# 1. Nguyên tắc chung

Với tiled amplicon sequencing, không nên coi dữ liệu như shotgun sequencing thông thường. Mỗi mẫu cần được theo dõi:

**FASTQ → QC → primer/adapter trimming → mapping → primer-aware variant calling → consensus → QC → phylogenetics**

Galaxy có sẵn nhiều workflow pathogen/amplicon tương tự cho Illumina và ONT; các workflow của Galaxy cũng nhấn mạnh việc kết hợp variant calling, consensus construction và reporting. Có thể dùng các workflow này làm khung rồi thay reference, primer scheme và thông số phù hợp với DENV. 

---

# 2. Chuẩn bị dữ liệu

## 2.1. FASTQ Illumina

Nếu paired-end:

```text
Sample01_R1.fastq.gz
Sample01_R2.fastq.gz
```

Nếu single-end:

```text
Sample01.fastq.gz
```

Cần giữ metadata:

```text
sample_id
collection_date
province
patient/sample type
DENV_serotype
sequencing_platform
library/preparation method
run_id
```

## 2.2. FASTQ Nanopore

Thông thường:

```text
Sample01.fastq.gz
```

Nếu chạy multiplex/barcoding, phải demultiplex trước hoặc sử dụng FASTQ đã được phân tách theo sample.

Nên lưu thêm:

```text
basecaller
basecalling_model
flow_cell
kit
barcode kit
sequencing date
primer scheme/version
```

---

# 3. Reference genome và primer scheme

Đây là phần rất quan trọng đối với nghiên cứu DENV.

## 3.1. Reference

Không nên dùng một reference DENV tùy ý.

Nên:

1. xác định serotype;
2. chọn reference gần với serotype/genotype đang nghiên cứu;
3. ghi rõ accession number và version;
4. lưu FASTA trong project;
5. lưu annotation nếu có.

Ví dụ cấu trúc:

```text
reference/
├── DENV1_reference.fasta
├── DENV2_reference.fasta
├── DENV3_reference.fasta
└── DENV4_reference.fasta
```

Nếu nghiên cứu nhiều serotype, nên xây dựng workflow có bước chọn reference theo serotype hoặc chạy từng nhóm serotype.

## 3.2. Primer scheme

Cần lưu primer scheme ở dạng BED hoặc định dạng tương thích với tool được sử dụng.

Ví dụ:

```text
DENV_tiled_amplicon_v1.bed
```

Các thông tin tối thiểu:

```text
chromosome/reference
amplicon_start
amplicon_end
amplicon_id
primer_name
```

Primer scheme phải được version hóa:

```text
DENV_tiled_amplicon_v1.0
DENV_tiled_amplicon_v1.1
```

Không nên thay đổi primer scheme giữa các batch mà không ghi lại version.

## 3.3. Hướng dẫn chi tiết: tạo file .bed cho primer scheme DENV

File BED (Browser Extensible Data) là định dạng toạ độ dạng bảng, tab-separated, dùng để khai báo vị trí mồi (primer) hoặc amplicon trên trục toạ độ của reference genome. Đây là input bắt buộc cho các bước primer trimming (iVar trim, ARTIC, Cutadapt theo toạ độ) và tính coverage theo amplicon.

### 3.3.1. Nguyên tắc toạ độ BED

- File BED dùng hệ toạ độ **0-based, half-open**: vị trí đầu tiên của reference là `0` (không phải `1` như FASTA/VCF), và `end` là vị trí **không bao gồm**.
- Ví dụ: mồi bắt đầu ở base 1 và kết thúc ở base 22 theo FASTA (1-based) → trong BED ghi là `start=0`, `end=22`.
- Sai lệch 1 vị trí (off-by-one) là lỗi rất phổ biến khi tự tạo BED thủ công — cần kiểm tra kỹ trước khi dùng cho trimming.

### 3.3.2. Hai kiểu file BED thường gặp trong pipeline tiled amplicon

**(a) Amplicon BED (mô tả từng amplicon)** — dùng để tính coverage theo amplicon, phát hiện amplicon dropout:

```text
#chrom       start   end     name          score   strand
DENV2_ref    0       420     Amplicon_01   .       +
DENV2_ref    380     810     Amplicon_02   .       +
DENV2_ref    770     1205    Amplicon_03   .       +
```

**(b) Primer BED (mô tả từng mồi riêng lẻ)** — dùng cho các tool primer-aware trimming như iVar/ARTIC. Đây là định dạng 6 cột, mỗi mồi (forward và reverse) là một dòng riêng:

```text
#chrom       start   end   name                     score   strand
DENV2_ref    30      52    DENV2_1_LEFT             60      +
DENV2_ref    398     420   DENV2_1_RIGHT            60      -
DENV2_ref    380     402   DENV2_2_LEFT             60      +
DENV2_ref    788     810   DENV2_2_RIGHT            60      -
```

Quy ước đặt tên (theo chuẩn ARTIC, được iVar và nhiều tool Galaxy hỗ trợ):

```text
<scheme_name>_<amplicon_number>_LEFT
<scheme_name>_<amplicon_number>_RIGHT
```

Nếu primer scheme có primer pool (2 pool xen kẽ để tránh amplicon liền kề chồng nhau), một số định dạng mở rộng (ARTIC "primer.tsv"/"alt-BED") thêm cột `pool`:

```text
chrom        start  end   name              pool
DENV2_ref    30     52    DENV2_1_LEFT      1
DENV2_ref    398    420   DENV2_1_RIGHT     1
DENV2_ref    380    402   DENV2_2_LEFT      2
DENV2_ref    788    810   DENV2_2_RIGHT     2
```

Cần xác định trước tool nào sẽ dùng BED này (iVar, ARTIC field bioinformatics, hay tool khác trong Galaxy) vì mỗi tool có thể yêu cầu số cột và quy ước tên hơi khác nhau — đọc kỹ tài liệu tool trước khi trimming hàng loạt mẫu.

### 3.3.3. Các bước tạo file BED cho DENV (từ danh sách mồi có sẵn)

1. **Chuẩn bị danh sách mồi**: mỗi mồi cần có `primer_name`, `sequence (5'→3')`, `pool` (nếu có), và biết mồi là forward (LEFT) hay reverse (RIGHT).
2. **Xác định vị trí mồi trên reference** bằng in-silico mapping/alignment thay vì đếm tay:
   - Trong Galaxy: dùng tool **BLAST+ blastn-short** hoặc **map with BWA-MEM/minimap2** để align từng chuỗi mồi vào `reference.fasta`, lấy toạ độ bắt đầu/kết thúc từ kết quả alignment (SAM/BAM hoặc BLAST tabular).
   - Với mồi reverse, chuỗi mồi thường được thiết kế là reverse-complement của reference; toạ độ trên BED vẫn lấy theo chiều của reference (start < end), cột `strand` đánh dấu `-`.
3. **Chuyển kết quả alignment sang BED**:
   - Nếu dùng BLAST tabular output (outfmt 6), có thể dùng tool **Text manipulation / Cut / awk** trong Galaxy để trích cột `qseqid, sstart, send, strand` rồi tính lại `start = min(sstart,send) - 1` (đổi sang 0-based), `end = max(sstart,send)`.
   - Nếu dùng BAM alignment của mồi, dùng tool **bedtools bamtobed** để xuất trực tiếp ra BED, sau đó đổi lại `name` cho đúng quy ước `_LEFT/_RIGHT`.
4. **Sắp xếp và kiểm tra file** bằng **bedtools sort** (sort theo `chrom`, `start`), đảm bảo không có toạ độ âm, không vượt quá chiều dài reference.
5. **Kiểm tra trực quan**: nạp `reference.fasta` + `primer.bed` vào **IGV** (hoặc Trackster/JBrowse trong Galaxy) để xác nhận từng cặp LEFT/RIGHT nằm đúng vị trí, các amplicon có phần chồng lấn (overlap) hợp lý giữa 2 pool.
6. **Version hoá và lưu**: đặt tên file theo quy ước version (`DENV_tiled_amplicon_v1.0.bed`), lưu kèm bảng nguồn gốc mồi (sequence, pool, ngày thiết kế, người thiết kế/tài liệu tham khảo) trong `metadata/`.

### 3.3.4. Nếu dùng thiết kế mồi kiểu PrimalScheme/ARTIC

Nếu primer scheme DENV được thiết kế bằng công cụ dạng PrimalScheme (phổ biến cho ARTIC-style tiled amplicon), công cụ này thường xuất sẵn:

```text
*.primer.bed
*.reference.fasta
*.scheme.bed (amplicon-level)
```

Trong trường hợp này chỉ cần kiểm tra lại: (a) toạ độ có khớp với `reference.fasta` đang dùng trong workflow Galaxy hay không (rất dễ lệch nếu reference version khác), (b) tên chromosome trong cột 1 của BED phải **khớp chính xác** với tên sequence trong file FASTA reference đã import vào Galaxy (kể cả chữ hoa/thường, khoảng trắng).

### 3.3.5. Lỗi thường gặp khi tạo/sử dụng BED

- Tên `chrom` trong BED không khớp tên header FASTA reference → tool trimming sẽ không tìm thấy overlap, primer không bị cắt, gây false variant tại đầu amplicon.
- Toạ độ 1-based bị chép nhầm vào BED (thiếu bước trừ 1) → lệch 1 base ở mọi mồi.
- Thiếu phân biệt LEFT/RIGHT hoặc thiếu cột `strand` → tool không xác định đúng chiều trimming.
- Trộn nhiều version primer scheme trong cùng một file BED mà không ghi chú → gây khó khăn khi truy vết lỗi hàng loạt.
- Không sort file trước khi dùng với `bedtools`/`samtools` → một số tool yêu cầu BED đã sort mới chạy đúng.

---

# 4. Workflow A — Illumina

## Tổng quan

```text
FASTQ R1/R2
   │
   ▼
FastQC
   │
   ▼
MultiQC
   │
   ▼
Adapter + primer trimming
   │
   ▼
FastQC
   │
   ▼
MultiQC
   │
   ▼
BWA-MEM/BWA-MEM2
   │
   ▼
SAM/BAM
   │
   ▼
Sort + Index
   │
   ├──────────────► Mapping QC
   │
   ▼
Primer-aware variant calling
   │
   ▼
VCF
   │
   ▼
Consensus FASTA
   │
   ▼
Consensus QC
   │
   ▼
Coverage + depth
   │
   ▼
IGV/manual inspection
   │
   ▼
Phylogenetic analysis
```

Galaxy có các workflow amplicon Illumina sử dụng chiến lược tương tự cho virus surveillance; workflow SARS-CoV-2 của Galaxy là ví dụ tham khảo về cách tổ chức variant calling + consensus + reporting. 

---

# 5. Illumina — Step 1: FastQC

Tool:

```text
FastQC
```

Input:

```text
R1
R2
```

Kiểm tra:

- Per-base sequence quality
- Per-sequence quality
- Adapter content
- Sequence duplication
- Overrepresented sequences
- N content

Sau đó:

```text
MultiQC
```

Mục tiêu là tạo một báo cáo QC cho toàn bộ batch.

---

# 6. Illumina — Step 2: Adapter và primer trimming

Không chỉ loại adapter.

Đối với tiled amplicon sequencing phải loại **primer sequence** trước khi gọi biến thể, nếu không primer-derived bases có thể tạo false variants.

Có thể sử dụng:

- Cutadapt
- fastp
- iVar trim
- công cụ primer trimming tương thích với primer BED

Nếu primer scheme được sử dụng cho variant calling, cần đảm bảo tool trimming và tool variant calling sử dụng cùng hệ tọa độ/reference.

### Nguyên tắc

```text
Raw reads
     ↓
adapter trimming
     ↓
primer trimming
     ↓
quality filtering
     ↓
clean reads
```

Không nên chỉ chạy:

```text
FastQC → BWA → variant calling
```

cho tiled amplicon data.

---

# 7. Illumina — Step 3: QC sau trimming

Chạy lại:

```text
FastQC
MultiQC
```

So sánh:

```text
Raw QC
vs
Post-trimming QC
```

Các chỉ số nên lưu:

- số reads trước/sau trimming;
- % reads retained;
- mean/median read quality;
- adapter content;
- read length distribution.

---

# 8. Illumina — Step 4: Mapping

Reference:

```text
DENV_reference.fasta
```

Mapper:

```text
BWA-MEM
```

hoặc:

```text
BWA-MEM2
```

Input:

```text
clean_R1.fastq.gz
clean_R2.fastq.gz
```

Output:

```text
sample.bam
```

Sau đó:

```text
Sort BAM
Index BAM
```

Output:

```text
sample.sorted.bam
sample.sorted.bam.bai
```

---

# 9. Illumina — Step 5: Mapping QC

Nên tạo:

```text
samtools flagstat
samtools idxstats
samtools depth
```

Các chỉ số:

- total reads;
- mapped reads;
- mapping percentage;
- properly paired reads;
- mean depth;
- median depth;
- genome breadth;
- positions with zero coverage.

Đặc biệt cần báo cáo:

```text
Genome coverage ≥ 10×
Genome coverage ≥ 20×
Genome coverage ≥ 50×
```

Ngưỡng cuối cùng nên được định nghĩa **trước khi phân tích** và giữ cố định trong toàn bộ dataset.

---

# 10. Illumina — Step 6: Primer-aware variant calling

Đây là bước quan trọng nhất.

Có thể xây dựng pipeline dựa trên:

```text
iVar
```

hoặc một caller phù hợp khác.

Workflow:

```text
BAM
 +
primer BED
      ↓
primer-aware trimming
      ↓
variant calling
      ↓
VCF
```

Cần ghi lại:

- minimum allele frequency;
- minimum depth;
- base quality;
- mapping quality;
- strand support;
- primer overlap handling.

Không nên chỉ báo cáo tất cả các SNP được caller tạo ra.

---

# 11. Illumina — Step 7: Consensus genome

Consensus có thể tạo từ:

```text
reference + VCF
```

hoặc bằng tool consensus phù hợp với workflow.

Output:

```text
Sample01_consensus.fasta
```

Nên đặt quy tắc rõ ràng:

```text
High-confidence position → gọi base
Insufficient coverage → N
Ambiguous position → IUPAC hoặc N tùy protocol
```

Không nên tự động biến mọi vị trí coverage thấp thành reference base.

---

# 12. Illumina — Step 8: Consensus QC

Tạo bảng:

| Sample | Length | %N | Mean depth | Median depth | Genome ≥10× | Genome ≥20× |
|---|---:|---:|---:|---:|---:|---:|
| S01 | ... | ... | ... | ... | ... | ... |
| S02 | ... | ... | ... | ... | ... | ... |

Nên bổ sung:

```text
number of variants
number of SNPs
number of indels
transition/transversion nếu phù hợp
```

---

# 13. Illumina — Step 9: IGV validation

Đây là bước rất nên có trước khi công bố.

Mở:

```text
reference.fasta
sample.sorted.bam
VCF
```

trong:

```text
IGV
```

Kiểm tra các biến thể quan trọng:

- SNP có depth đủ không?
- có strand bias không?
- có nằm tại vị trí primer không?
- có chỉ xuất hiện ở một vài reads không?
- có soft clipping bất thường không?
- có pattern cho thấy contamination/index hopping không?

Các biến thể quan trọng nên được kiểm tra thủ công.

---

# 14. Workflow B — Oxford Nanopore

## Tổng quan

```text
FASTQ
  │
  ▼
NanoPlot / NanoQC
  │
  ▼
Quality filtering
  │
  ▼
Primer trimming
  │
  ▼
Minimap2
  │
  ▼
BAM
  │
  ▼
Sort + Index
  │
  ▼
Mapping QC
  │
  ▼
Primer-aware variant calling
  │
  ▼
Medaka / appropriate consensus
  │
  ▼
Consensus FASTA
  │
  ▼
Consensus QC
  │
  ▼
IGV
  │
  ▼
Phylogenetics
```

Galaxy có các workflow và training materials cho Nanopore pathogen analysis; Galaxy cũng sử dụng minimap2 cho long-read mapping và Medaka trong các workflow Nanopore consensus/polishing. 

---

# 15. ONT — Step 1: Read QC

Tool:

```text
NanoPlot
```

Kiểm tra:

- read length;
- mean read quality;
- N50;
- total bases;
- number of reads;
- quality distribution.

Output:

```text
NanoPlot_report.html
```

---

# 16. ONT — Step 2: Quality filtering

Có thể sử dụng:

```text
Filtlong
```

hoặc công cụ tương đương trong Galaxy.

Mục tiêu:

```text
raw ONT reads
      ↓
quality filtering
      ↓
high-quality reads
```

Không nên đặt ngưỡng quá cao một cách máy móc vì viral amplicon data thường có read length phụ thuộc thiết kế amplicon.

Quan trọng hơn là đánh giá:

- coverage;
- uniformity;
- read quality;
- amplicon dropout.

---

# 17. ONT — Step 3: Primer trimming

Primer trimming đặc biệt quan trọng đối với ONT tiled amplicon data.

Sử dụng:

```text
primer BED
```

và tool tương thích với workflow.

Mục tiêu:

```text
ONT reads
     ↓
primer removal
     ↓
clean reads
```

Phải kiểm tra xem primer sequence có còn ở đầu reads hay không.

---

# 18. ONT — Step 4: Mapping bằng minimap2

Tool:

```text
minimap2
```

Reference:

```text
DENV_reference.fasta
```

Input:

```text
clean_ONT.fastq.gz
```

Output:

```text
sample.sorted.bam
sample.sorted.bam.bai
```

Sau đó dùng:

```text
samtools flagstat
samtools depth
```

để đánh giá mapping.

---

# 19. ONT — Step 5: Coverage analysis

Tạo coverage plot theo genome.

Nên đánh giá:

```text
mean depth
median depth
breadth ≥10×
breadth ≥20×
breadth ≥50×
minimum depth
maximum depth
```

Ngoài genome-wide coverage, nên kiểm tra từng amplicon.

Ví dụ:

```text
Amplicon 01 → 1250×
Amplicon 02 → 1100×
Amplicon 03 → 15×
Amplicon 04 → 980×
```

Amplicon dropout phải được báo cáo, không nên chỉ nhìn mean coverage.

---

# 20. ONT — Step 6: Variant calling

Có thể sử dụng caller phù hợp với ONT, ví dụ workflow dựa trên:

```text
Medaka
```

hoặc một caller đã được validation cho ONT viral sequencing.

Nguyên tắc:

```text
ONT BAM
   ↓
variant calling
   ↓
VCF
   ↓
consensus
```

Không nên áp dụng trực tiếp các ngưỡng allele frequency của Illumina cho ONT mà không validation.

---

# 21. ONT — Step 7: Consensus

Có thể sử dụng:

```text
Medaka
```

để tạo/polish consensus.

Galaxy Training Network có workflow polishing sử dụng Medaka cho Nanopore và nhấn mạnh việc chọn model phù hợp với dữ liệu; model phải tương ứng với chemistry/basecaller của dataset. 

Output:

```text
Sample01_ONT_consensus.fasta
```

---

# 22. So sánh Illumina và ONT

Nên phân tích song song:

```text
                    Illumina              ONT
-------------------------------------------------------
Read                 Short                 Long
Accuracy             Cao                   Thấp hơn
Mapping               BWA-MEM              minimap2
QC                     FastQC/MultiQC       NanoPlot
Primer handling       iVar/Cutadapt/...     primer-aware tool
Variant calling       iVar/...              Medaka/validated caller
Consensus              VCF + reference      Medaka/validated consensus
Main strength         SNP accuracy          long reads
Main concern           PCR/amplicon bias     sequencing error
```

Nếu có điều kiện, **hybrid validation** rất mạnh:

```text
ONT consensus
       +
Illumina reads
       ↓
independent validation
       ↓
high-confidence consensus
```

Tuy nhiên, nếu Illumina và ONT được tạo từ các mẫu khác nhau thì không nên gọi đây là technical validation trực tiếp.

---

# 23. Phylogenetic workflow

Sau khi có consensus:

```text
*.fasta
```

lọc các sequence không đạt QC.

## 23.1. Multiple sequence alignment

Có thể sử dụng:

```text
MAFFT
```

Input:

```text
DENV_consensus_sequences.fasta
```

Output:

```text
DENV_alignment.fasta
```

Nên bao gồm:

- sequence của nghiên cứu;
- reference sequences;
- representative sequences từ các quốc gia;
- sequences gần về thời gian/địa lý;
- sequences phù hợp với câu hỏi nghiên cứu.

---

# 24. Kiểm tra alignment

Dùng:

```text
AliView
```

hoặc:

```text
Jalview
```

Kiểm tra:

- abnormal gaps;
- sequence quá ngắn;
- alignment sai;
- vùng terminal;
- vùng có nhiều Ns.

Có thể dùng:

```text
IQ-TREE
```

để chọn model và xây dựng ML tree.

Ví dụ:

```text
IQ-TREE
Model selection: ModelFinder
Bootstrap: ultrafast bootstrap
```

Số bootstrap nên được xác định trước và báo cáo trong Methods.

---

# 25. Phân tích genotype/serotype

Không nên suy luận genotype chỉ từ tên sample.

Nên thực hiện:

```text
Consensus
   ↓
alignment
   ↓
reference/reference dataset
   ↓
phylogenetic tree
   ↓
genotype assignment
```

Có thể kết hợp các công cụ/database chuyên biệt cho DENV nếu phù hợp với mục tiêu nghiên cứu.

---

# 26. Phân tích biến thể

Tạo bảng:

```text
Sample
Position
Reference
Alternative
Depth
Alt depth
Allele frequency
Gene
Codon
Nucleotide change
Amino-acid change
```

Ví dụ:

| Sample | Position | Ref | Alt | Depth | Alt depth | AF | Gene | AA change |
|---|---:|---|---|---:|---:|---:|---|---|
| S01 | 1234 | A | G | 850 | 823 | 0.968 | NS1 | ... |

Các biến thể cần được lọc theo tiêu chí đã xác định trước.

---

# 27. QC cần có cho một nghiên cứu xuất bản

Không nên chỉ cung cấp:

```text
Consensus FASTA
```

Nên tạo một **Master QC table**:

| Sample | Platform | Reads | Mapped % | Mean depth | Median depth | ≥10× | ≥20× | ≥50× | %N | SNPs | Indels | QC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| S01 | Illumina | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | PASS |
| S02 | ONT | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | PASS |

---

# 28. Tiêu chí QC nên định nghĩa trước

Ví dụ framework:

```text
PASS nếu:

Genome breadth ≥ predefined threshold
AND
median/mean depth ≥ predefined threshold
AND
%N ≤ predefined threshold
AND
no major contamination detected
AND
no major amplicon dropout
```

**Không nên lấy các ngưỡng trên làm giá trị mặc định cho mọi nghiên cứu.**

Ngưỡng phải dựa trên:

- sequencing platform;
- primer scheme;
- validation data;
- intended use;
- journal/database requirements.

## 28.1. Bộ ngưỡng khởi điểm tham khảo (không phải giá trị cố định)

Bảng dưới đưa ra các mốc **thường thấy** trong các nghiên cứu virus tiled-amplicon công bố (ví dụ ARTIC/SARS-CoV-2, các nghiên cứu DENV WGS) để làm điểm khởi đầu khi xây validation dataset — nhóm nghiên cứu vẫn cần tự xác nhận lại bằng dữ liệu của mình trước khi cố định:

| Chỉ số | Mốc khởi điểm thường gặp | Ghi chú |
|---|---|---|
| Depth tối thiểu để gọi base | 10×–20× | Illumina thường dùng 10–20×; ONT thường yêu cầu cao hơn (≥20–30×) do error rate cao hơn |
| Genome breadth để "PASS" | ≥ 70–90% genome có depth đạt ngưỡng | Tuỳ mục đích: submission GenBank/GISAID-tương-tự thường đòi hỏi cao hơn phân tích nội bộ |
| %N tối đa cho phép | ≤ 10–30% | Càng thấp càng tốt cho phân tích phát sinh chủng loại; ngưỡng cao hơn có thể chấp nhận cho khảo sát dịch tễ sơ bộ |
| Minimum allele frequency để gọi biến thể (consensus) | 0.5 (majority consensus) hoặc 0.75 tuỳ protocol | 0.5 = consensus theo đa số; ngưỡng cao hơn giảm nhiễu nhưng có thể bỏ sót biến thể thật |
| Minimum allele frequency để báo cáo minor variant | 0.03–0.05 (chỉ với Illumina, depth cao) | Không khuyến nghị áp dụng cho ONT nếu chưa validation riêng vì error profile khác |
| Mapping quality tối thiểu | ≥ 20–30 | Áp dụng khi lọc reads trước variant calling |
| Base quality tối thiểu | ≥ 20 (Phred) | Áp dụng khi lọc trước variant calling |

**Đây là các con số "thường thấy trong y văn/thực hành cộng đồng", không phải quy chuẩn bắt buộc.** Nhóm nghiên cứu cần chạy validation dataset (mục 33) để xác nhận các ngưỡng này phù hợp với primer scheme, độ sâu đọc thực tế và mục tiêu công bố của chính mình, rồi mới cố định trong protocol.

---

# 29. Contamination và mixed infection

Đây là phần rất quan trọng nếu muốn công bố chất lượng cao.

Nên kiểm tra:

### 29.1. Contamination

- mapping ngoài reference;
- taxonomic classification nếu cần;
- unexpected genotype;
- unexpected serotype;
- sample-to-sample cross contamination.

### 29.2. Mixed infection

Nếu một vị trí có:

```text
REF = 52%
ALT = 48%
```

không nên ngay lập tức gọi đó là true minority variant.

Cần kiểm tra:

- depth;
- strand;
- base quality;
- mapping quality;
- primer position;
- neighboring variants;
- read-level support;
- possible contamination.

---

# 30. Reproducibility

Một bài báo quốc tế tốt nên có khả năng tái lập.

Cần lưu:

```text
Galaxy instance
Galaxy workflow
Workflow version
Tool name
Tool version
Reference accession/version
Primer scheme/version
Parameters
QC thresholds
Database versions
Date of analysis
```

Nên export workflow:

```text
workflow.ga
```

và lưu trong GitHub/Zenodo hoặc repository phù hợp.

Galaxy hỗ trợ workflow có thể chia sẻ và tái sử dụng; Galaxy Training Network cũng có tài liệu về quản lý, kiểm thử và công bố workflow. 

---

# 30bis. Phụ lục: Gợi ý tool Galaxy cụ thể cho từng bước

Bảng dưới liệt kê tên tool thường thấy trên Galaxy Toolshed/usegalaxy.* tương ứng với từng bước ở trên. Đây là **gợi ý khởi điểm** — cần kiểm tra tool nào thực sự có trên Galaxy server sẽ sử dụng (public hay riêng), và luôn ghi lại version cụ thể khi đã chọn.

## Illumina

| Bước | Tool Galaxy gợi ý |
|---|---|
| QC thô | `FastQC`, `MultiQC` |
| Adapter trimming | `fastp` hoặc `Cutadapt` |
| Primer trimming (theo BED) | `ivar trim` (trong bộ `iVar`), hoặc `Cutadapt` với toạ độ chuyển từ BED |
| Mapping | `Map with BWA-MEM` (hoặc `BWA-MEM2`) |
| Sort/Index/QC BAM | `Samtools sort`, `Samtools index`, `Samtools flagstat`, `Samtools idxstats`, `Samtools depth`, `Samtools coverage` |
| Coverage theo amplicon | `bedtools coverage` (BAM × amplicon BED) |
| Primer-aware variant calling | `ivar variants` (yêu cầu BAM đã trim bằng `ivar trim`) hoặc `LoFreq` |
| Consensus | `ivar consensus`, hoặc `bcftools consensus` (reference + VCF đã lọc) |
| Kiểm tra alignment | `IGV` (desktop, kết nối trực tiếp với Galaxy qua "display at IGV") |

## Oxford Nanopore (ONT)

| Bước | Tool Galaxy gợi ý |
|---|---|
| QC thô | `NanoPlot`, `NanoQC` |
| Lọc chất lượng | `Filtlong`, hoặc `Chopper`/`NanoFilt` |
| Loại adapter (nếu chưa loại lúc basecalling) | `Porechop` |
| Primer trimming | công cụ tương thích primer BED (ví dụ workflow dựa trên `ivar trim` áp dụng cho BAM long-read, hoặc bộ công cụ ARTIC field-bioinformatics nếu có trên server) |
| Mapping | `minimap2` (preset `map-ont`) |
| Sort/Index/QC BAM | `Samtools sort`, `Samtools index`, `Samtools flagstat`, `Samtools depth`, `Samtools coverage` |
| Coverage theo amplicon | `bedtools coverage` |
| Variant calling + consensus | `Medaka consensus` / `medaka_variant` (chọn đúng model theo basecaller/chemistry) |
| Kiểm tra alignment | `IGV` |

## Chung cho cả hai nhánh (sau khi có consensus)

| Bước | Tool Galaxy gợi ý |
|---|---|
| Gộp & lọc các consensus đạt QC | `Concatenate datasets`, kết hợp thao tác lọc theo bảng QC |
| Multiple sequence alignment | `MAFFT` |
| Kiểm tra alignment | `AliView`/`Jalview` (thường chạy ngoài Galaxy, tải file alignment về) |
| Cây phát sinh chủng loại | `IQ-TREE` (kèm `ModelFinder` + `ultrafast bootstrap`) |
| Trực quan hoá cây | `iTOL` (web, ngoài Galaxy) hoặc `ggtree` nếu chạy trong Galaxy Jupyter/RStudio interactive tool |

> Ghi chú: tên hiển thị và version của tool có thể khác nhau giữa các Galaxy server (usegalaxy.org, usegalaxy.eu, server nội bộ). Trước khi xây `.ga` chính thức, nên vào Galaxy, tìm từng tool trong ô "Tools" và ghi lại chính xác tên + version sẽ dùng, sau đó cập nhật bảng này cho project.

---

# 31. Cấu trúc Galaxy History đề nghị

Mỗi project có thể tổ chức:

```text
DENV_WGS_2026
│
├── 01_raw_fastq
├── 02_raw_QC
├── 03_trimmed_reads
├── 04_posttrim_QC
├── 05_mapping
├── 06_BAM_QC
├── 07_variants
├── 08_consensus
├── 09_consensus_QC
├── 10_alignment
├── 11_phylogeny
├── 12_figures
└── 13_final_results
```

---

# 32. Hai workflow nên xây dựng trong Galaxy

## Workflow 1

Tên:

```text
DENV_TiledAmplicon_Illumina_WGS_v1
```

Inputs:

```text
R1
R2
reference.fasta
primer.bed
```

Outputs:

```text
raw_QC
trimmed_R1
trimmed_R2
posttrim_QC
BAM
BAM_index
mapping_QC
coverage
VCF
consensus.fasta
consensus_QC
```

## Workflow 2

Tên:

```text
DENV_TiledAmplicon_ONT_WGS_v1
```

Inputs:

```text
ONT_FASTQ
reference.fasta
primer.bed
```

Outputs:

```text
NanoPlot
filtered_FASTQ
trimmed_FASTQ
BAM
BAM_index
mapping_QC
coverage
VCF
consensus.fasta
consensus_QC
```

---

# 32bis. Các bước thực hành để dựng workflow trong Galaxy Workflow Editor

Phần này mô tả thao tác cụ thể trên giao diện Galaxy để biến sơ đồ ở trên thành một workflow chạy được (`.ga`).

1. **Tạo workflow mới**: vào menu `Workflow` → `Create new workflow`, đặt tên đúng theo quy ước version, ví dụ `DENV_TiledAmplicon_Illumina_WGS_v1`.
2. **Thêm input node**: dùng khối `Input dataset` (hoặc `Input dataset collection` nếu chạy nhiều mẫu cùng lúc theo batch) cho từng input: `R1`, `R2` (hoặc collection paired R1/R2), `reference.fasta`, `primer.bed`.
   - Với nhiều mẫu, nên gói `R1`/`R2` thành một **dataset collection** (paired list) để một workflow chạy được cho cả batch thay vì từng mẫu một.
3. **Thêm từng tool bằng thanh tìm kiếm bên trái** (gõ đúng tên tool ở bảng phụ lục mục 30bis), kéo vào canvas theo đúng thứ tự sơ đồ ở mục 4 (Illumina) hoặc mục 14 (ONT).
4. **Nối các cổng (ports)**: kéo dây từ output của tool trước sang input tương ứng của tool sau (ví dụ: output `FASTQ` của `fastp` → input `Reads` của `ivar trim`). Với các tool cần cả BAM và BED (ví dụ `ivar trim`, `bedtools coverage`), nhớ nối cả hai input.
5. **Cấu hình tham số mặc định của từng tool** trong khung bên phải (mapping quality, base quality, minimum depth, minimum allele frequency…) theo giá trị đã thống nhất (mục 28.1); các tham số có thể để dạng "runtime parameter" nếu muốn thay đổi linh hoạt mỗi lần chạy.
6. **Đánh dấu output cần giữ lại**: click vào từng output quan trọng (BAM, VCF, consensus FASTA, các báo cáo QC) → bật `Mark output for dataset collection` hoặc gắn nhãn rõ ràng để dễ nhận diện trong history sau khi chạy.
7. **Lưu workflow** (`Save`), sau đó chạy thử (`Run workflow`) trên 1–2 mẫu để kiểm tra toàn bộ chuỗi không lỗi trước khi chạy hàng loạt.
8. **Export workflow**: `Workflow` → chọn workflow → `Download` để lấy file `.ga`, lưu vào `workflows/` theo cấu trúc ở mục 38 và đưa lên repository (GitHub/Zenodo) để đảm bảo reproducibility.
9. Lặp lại quy trình tương tự cho `DENV_TiledAmplicon_ONT_WGS_v1`.

> Ghi chú: Galaxy cũng hỗ trợ tạo workflow tự động bằng cách "trích xuất" (extract) từ một history đã chạy tay thành công (`History options` → `Extract workflow`) — cách này phù hợp nếu muốn thử nghiệm thủ công từng bước trước, sau đó mới đóng gói thành workflow chuẩn.

---

# 33. Workflow validation

Trước khi chạy hàng trăm mẫu, nên tạo một **validation dataset** gồm:

```text
Known positive samples
Known negative/control samples
High-quality samples
Low-quality samples
Samples with expected variants
```

Sau đó chạy cả workflow.

So sánh:

```text
Galaxy workflow
vs
validated reference analysis
```

Đánh giá:

- consensus identity;
- SNP concordance;
- indel concordance;
- coverage;
- consensus Ns;
- genotype;
- phylogenetic placement.

Chỉ sau khi validation đạt yêu cầu mới chạy toàn bộ dataset.

---

# 34. Publication-ready outputs

Tối thiểu nên có:

### Supplementary Table 1

Sample metadata.

### Supplementary Table 2

Sequencing/QC metrics.

### Supplementary Table 3

Variant table.

### Supplementary Table 4

Consensus genome statistics.

### Supplementary Figure 1

Read QC.

### Supplementary Figure 2

Coverage plots.

### Figure 1

Study design / sequencing workflow.

### Figure 2

Phylogenetic tree.

### Figure 3

Geographical/temporal distribution.

### Figure 4

Genetic diversity / mutation profile nếu phù hợp.

---

# 35. Những gì Methods của bài báo phải mô tả

Ví dụ cấu trúc:

```text
Sample collection
        ↓
RNA extraction
        ↓
DENV detection/serotyping
        ↓
Whole-genome tiled amplicon PCR
        ↓
Library preparation
        ↓
Illumina / ONT sequencing
        ↓
FASTQ
        ↓
Galaxy analysis
        ↓
QC
        ↓
Primer trimming
        ↓
Reference mapping
        ↓
Variant calling
        ↓
Consensus generation
        ↓
Phylogenetic analysis
```

Trong Methods phải ghi rõ:

1. sequencing platform;
2. library preparation;
3. primer scheme;
4. reference accession;
5. trimming software/version;
6. mapper/version;
7. variant caller/version;
8. consensus software/version;
9. QC thresholds;
10. phylogenetic software/version;
11. database/accession selection;
12. Galaxy workflow/version;
13. workflow DOI/repository nếu có.

---

# 36. Một điểm rất quan trọng: không dùng một workflow cho cả Illumina và ONT

Không nên làm:

```text
FASTQ
 ↓
một pipeline chung
 ↓
consensus
```

Mà nên:

```text
                  DENV FASTQ
                      │
          ┌───────────┴───────────┐
          │                       │
      Illumina                   ONT
          │                       │
       FastQC                   NanoPlot
          │                       │
   adapter/primer             primer trim
       trim                      │
          │                   minimap2
       BWA-MEM                    │
          │                     BAM
        BAM                       │
          │                   ONT caller
      iVar/...                    │
          │                    Medaka
      consensus                   │
          │                   consensus
          └───────────┬───────────┘
                      │
              Consensus QC
                      │
                   MAFFT
                      │
                  IQ-TREE
                      │
              Epidemiological
                 analysis
```

Điều này giúp phân biệt rõ **platform-specific errors** và tăng tính minh bạch của nghiên cứu.

---

# 37. Có thể dùng Galaxy public hay Galaxy server riêng?

Đối với nghiên cứu thật:

### Galaxy public

Phù hợp cho:

- thử nghiệm;
- pilot;
- học workflow;
- dataset không nhạy cảm.

Galaxy có các public instances và workflow pathogen surveillance có thể dùng làm nền tảng tham khảo. 

### Galaxy server riêng

Phù hợp hơn nếu:

- dữ liệu bệnh nhân;
- dữ liệu chưa công bố;
- số lượng mẫu lớn;
- cần reproducibility lâu dài;
- cần kiểm soát phiên bản tool/database;
- cần tích hợp HPC.

---

# 38. Bộ file nên lưu sau khi hoàn thành

```text
DENV_WGS_project/
│
├── raw_data/
│
├── metadata/
│   └── sample_metadata.tsv
│
├── reference/
│   ├── DENV_reference.fasta
│   └── reference_metadata.tsv
│
├── primers/
│   └── DENV_primer_scheme_v1.bed
│
├── workflows/
│   ├── DENV_TiledAmplicon_Illumina_WGS_v1.ga
│   └── DENV_TiledAmplicon_ONT_WGS_v1.ga
│
├── consensus/
│
├── variants/
│
├── QC/
│
├── phylogeny/
│
├── figures/
│
└── README.md
```

---

# 39. Checklist trước khi submit bài

## Sequencing

- [ ] Raw FASTQ được lưu.
- [ ] Metadata đầy đủ.
- [ ] Primer scheme có version.
- [ ] Reference có accession/version.
- [ ] Sequencing platform được ghi rõ.

## Bioinformatics

- [ ] Raw QC.
- [ ] Adapter trimming.
- [ ] Primer trimming.
- [ ] Post-trimming QC.
- [ ] Mapping QC.
- [ ] Coverage analysis.
- [ ] Variant calling.
- [ ] Consensus QC.
- [ ] Manual inspection các variant quan trọng.
- [ ] Phylogenetic analysis.
- [ ] Contamination assessment.

## Reproducibility

- [ ] Galaxy workflow được export.
- [ ] Tool versions được lưu.
- [ ] Parameters được lưu.
- [ ] Reference được lưu.
- [ ] Primer BED được lưu.
- [ ] QC thresholds được ghi.
- [ ] Code/scripts được lưu.
- [ ] Workflow được chia sẻ qua repository/DOI nếu phù hợp.

---

# 40. Khuyến nghị thiết kế nghiên cứu

Nếu mục tiêu là một bài báo quốc tế có chất lượng tốt, tôi khuyến nghị kiến trúc:

```text
                 DENV samples
                       │
             ┌─────────┴─────────┐
             │                   │
         Illumina               ONT
             │                   │
       Platform QC          Platform QC
             │                   │
       Primer trim          Primer trim
             │                   │
       Reference map        Reference map
             │                   │
      Variant calling      Variant calling
             │                   │
         Consensus           Consensus
             │                   │
             └─────────┬─────────┘
                       │
                Consensus QC
                       │
                 High-quality
                DENV genomes
                       │
            ┌──────────┴──────────┐
            │                     │
       Variant analysis      Phylogenetics
            │                     │
      mutation profile       MAFFT + IQ-TREE
            │                     │
            └──────────┬──────────┘
                       │
              Epidemiological
                  analysis
```

Đây là cấu trúc tốt hơn nhiều so với chỉ tạo FASTA rồi xây cây phát sinh chủng loại.

---

## Tài liệu Galaxy nên tham khảo

- Galaxy Public Health Genomics: https://galaxyproject.org/community/sig/public-health/
- Galaxy viral surveillance workflows: https://galaxyproject.org/projects/covid19/workflows/
- Galaxy Training Network: https://training.galaxyproject.org/
- Galaxy Nanopore pathogen analysis training: https://artifact.galaxyproject.org/news/2023-03-21-foodborne-training/


Galaxy hiện có các workflow pathogen surveillance cho cả Illumina và ONT, và các workflow này có thể được dùng làm khung để xây dựng workflow DENV chuyên biệt.

---

## Bước tiếp theo để biến tài liệu này thành workflow Galaxy thực sự

Tài liệu trên là **kiến trúc phân tích publication-ready**, nhưng để tạo `.ga` có thể import trực tiếp vào Galaxy, cần cố định:

1. **DENV serotype**: DENV-1, DENV-2, DENV-3, DENV-4 hay cả 4.
2. **Primer scheme**: tên/version và file BED.
3. **Reference genome**: accession/version.
4. **Illumina**: single-end hay paired-end.
5. **ONT**: chemistry/basecaller và loại library.
6. **Ngưỡng QC** dự kiến.
7. Có hay không **technical validation Illumina ↔ ONT** trên cùng mẫu.

Sau khi các thông số này được cố định, có thể xây dựng tiếp thành **2 workflow Galaxy cụ thể theo từng tool, từng parameter và từng output**, thay vì chỉ là sơ đồ tổng quát. Galaxy cũng hỗ trợ workflow có thể export/chia sẻ để tăng khả năng tái lập.
