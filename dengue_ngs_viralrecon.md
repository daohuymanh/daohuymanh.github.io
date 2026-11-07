title: Pipeline giải trình tự Dengue và các virus RNA khác (multi-primer amplicon) trên nf-core/viralrecon: từ dữ liệu thô đến genotype, cây phát sinh loài và đột biến
slug: dengue_ngs_viralrecon.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.09.23
reading_time: 90 phút đọc
author: Đào Huy Mạnh
excerpt: Hướng dẫn trọn quy trình giải trình tự virus RNA bằng amplicon đa mồi trên nf-core-viralrecon (Dengue 1-4, Zika, Chikungunya, Dại, Enterovirus...): chuẩn bị mồi và reference, chạy trên server qua SSH/Tailscale/tmux, xử lý lỗi, đánh giá chất lượng, phân loại genotype, chọn chuỗi tham chiếu NCBI, dựng và vẽ cây (TIFF 300 dpi), tìm và diễn giải đột biến
scripts: 01_parse_primers.py|02_select_reference.sh|03_build_primer_bed.py|04_run_viralrecon.sh|fastq_dir_to_samplesheet.py
---
# Pipeline giải trình tự Dengue và các virus RNA khác (multi-primer amplicon) trên nf-core/viralrecon

Tài liệu này đi trọn quy trình, từ file mồi và dữ liệu thô đến diễn giải kết quả (genotype, cây phát sinh loài, đột biến).
Các ví dụ số liệu lấy từ một lô thực tế DENV1 (Illumina, 15 mẫu); phần cuối có hướng dẫn điều chỉnh cho
DENV2, DENV3, DENV4, Zika, Chikungunya, virus Dại và Enterovirus.

```
Excel mồi                         dữ liệu NGS (contig/reads)
    │                                      │
    ▼                                      ▼
01_parse_primers.py            02_select_reference.sh   (BLAST -> chọn reference/type)
    │                                      │
    └──────────────┬───────────────────────┘
                   ▼
        03_build_primer_bed.py     (BLAST từng mồi lên reference đã chọn -> BED chuẩn)
                   │
                   ▼
        Bước 4: nf-core/viralrecon (Illumina / Nanopore)
                   │
                   ▼
        Bước 5: đánh giá chất lượng mẫu
                   │
        ┌──────────┴───────────┬────────────────────┐
        ▼                      ▼                    ▼
  Bước 6: phân loại    Bước 7-9: chuỗi tham   Bước 10: đột biến
  (genotype/lineage)   chiếu, cây, vẽ cây     (bảng, ma trận, diễn giải)
                   │
                   ▼
        Bước 11: diễn giải kết quả và kiểm tra trước khi xuất bản
```

**Quan trọng:** các script 02 và 03 cần `blastn`/`makeblastdb` (gói `ncbi-blast+`)
và Internet (để tải genome tham chiếu). Các script 01-03 được viết cho 4 serotype Dengue
(thư mục `D1` đến `D4`); với virus khác, đổi tên nhóm (type) tương ứng và kiểm tra lại vòng lặp trong script.

> **Bài học quan trọng từ lô DENV1:** dùng thẳng reference RefSeq mà bỏ qua Bước 2 có thể làm mẫu cách reference
> khoảng 7% (khoảng 800 SNP trên genome 10,7 kb). Khi đó QUAST không align được, primer có thể bắt cặp kém và
> một số amplicon bị mất. **Chọn reference gần genotype của mẫu (Bước 2) và BED đúng tọa độ reference đó (Bước 3)
> là bước không nên bỏ qua.**

## Bảng tham khảo theo virus

Bảng dưới là điểm xuất phát; hãy xác nhận accession, độ dài và hệ phân loại trên NCBI/ICTV và tài liệu mới nhất
trước khi dùng, vì tên gọi và cách phân loại thay đổi theo thời gian.

| Virus | RefSeq tham khảo | Độ dài genome (xấp xỉ) | Cấu trúc gene | Hệ phân loại thường dùng | Vùng thường dùng để định type |
|---|---|---|---|---|---|
| DENV1 | NC_001477.1 | 10,7 kb | 1 polyprotein | Genotype | Gene E |
| DENV2 | NC_001474.2 | 10,7 kb | 1 polyprotein | Genotype/lineage (có nhiều hệ thống) | Gene E |
| DENV3 | NC_001475.2 | 10,7 kb | 1 polyprotein | Genotype | Gene E |
| DENV4 | NC_002640.1 | 10,6 kb | 1 polyprotein | Genotype | Gene E |
| Zika | NC_012532.1 | 10,8 kb | 1 polyprotein | Lineage Châu Phi và Châu Á (gồm Châu Mỹ) | Toàn CDS hoặc gene E |
| Chikungunya | NC_004162.2 | 11,8 kb | 2 ORF (không cấu trúc và cấu trúc) | Genotype ECSA, West Africa, Asian (và nhánh IOL) | Gene E1 hoặc toàn CDS |
| Dại (RABV) | NC_001542.1 | 11,9 kb | 5 gene riêng (N, P, M, G, L) | Clade/lineage (Cosmopolitan, Asian, Arctic-like...) | Gene N hoặc toàn genome |
| Enterovirus | Theo từng type (xem phụ lục) | 7,4 kb | 1 polyprotein | Type, rồi genogroup/subgenogroup | Gene VP1 |

Hệ quả thực tế của bảng này:
- **Một virus nhiều type** (Dengue 1-4, Enterovirus): mỗi type cần reference, GFF, BED và samplesheet riêng; không trộn type trong một lần chạy.
- **Hai ORF hoặc nhiều gene** (Chikungunya, Dại): GFF có nhiều CDS; tọa độ cắt vùng mã hóa và cách đánh số đột biến khác với trường hợp 1 polyprotein (xem Bước 8 và Bước 10).
- **Virus đa dạng cao** (Enterovirus, Dại): nên chọn reference đúng type/lineage và cân nhắc giữ assembly de novo để so với consensus từ mapping (xem phụ lục).

---

## Bước 0 — Chuẩn bị file primer

Chuẩn bị file excel chứa thông tin mồi. Ví dụ Mồi_NGS_DEN.xlsx. Trong file chứa các cột sau:  Thứ tự, Name, Position (From, To), Sequence of primer (5’-3’), Length of primer, size (bp), Pool để chuẩn bị làm file .BED cho phân tích.

Nếu dùng bộ mồi có sẵn kiểu ARTIC/PrimalScheme (đã có file BED), chỉ cần kiểm tra tên mồi có hậu tố `_LEFT` và
`_RIGHT` và cột đầu của BED trùng tên sequence trong FASTA reference. Với virus chưa có bộ mồi công bố, có thể thiết kế
bằng PrimalScheme (xem tài liệu của công cụ) trên các genome đại diện của virus đó.

---

## Bước 1 — chuẩn hoá bảng mồi

Chạy sau khi có file primer Excel: 
```bash
python3 scripts/01_parse_primers.py Mồi_NGS_DEN.xlsx primers_parsed
```

## Bước 2 — Chọn reference (genotype) phù hợp, TRONG PHẠM VI type đã biết trước

Vì type (serotype) mỗi mẫu **đã biết trước** (RT-PCR định type...), script không còn
BLAST để "đoán type" nữa — chỉ BLAST để chọn đúng **genotype/isolate**
tham chiếu khớp nhất trong chính type đó, nhanh hơn và tránh nhầm chéo.

**Bắt buộc tổ chức contig/consensus theo thư mục con = type đã biết:**
```
contigs_per_sample/
  D1/  DENV1_S001.fasta  DENV1_S007.fasta
  D2/  DENV2_S002.fasta  DENV2_S010.fasta
  D3/  DENV3_S003.fasta
  D4/  DENV4_S004.fasta
```
(chỉ tạo thư mục cho type bạn thực sự có mẫu; xem cách lấy contig từ
Illumina/Nanopore ở mục "Lấy contig/consensus đầu vào cho bước 2" bên dưới)

**(Khuyến nghị) trước khi chạy**, bổ sung thêm vài genotype đang lưu hành tại
khu vực lấy mẫu cho từng type (không bắt buộc, nhưng giúp chọn reference
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
Script tự động: với mỗi type có mẫu → build ngân hàng BLAST riêng (RefSeq
+ file `_extra.fasta` nếu có) → BLAST từng mẫu trong đúng type đó.

Kết quả `ref_selection_out/results/best_reference_per_sample.tsv` cho biết
accession NCBI khớp nhất với từng mẫu (kèm cột type để đối chiếu). Trong
từng type, nếu các mẫu đều khớp cùng 1 accession → chọn accession đó làm
reference đại diện; nếu các mẫu lệch rõ rệt sang accession khác nhau → có thể
đang lưu hành >1 genotype, cân nhắc dùng reference riêng cho từng nhóm mẫu.
Tải genome accession đã chọn, lưu thành:
```
ref_selection_out/references/D1_chosen_reference.fasta
ref_selection_out/references/D2_chosen_reference.fasta
ref_selection_out/references/D3_chosen_reference.fasta
ref_selection_out/references/D4_chosen_reference.fasta
```

**Khi chưa biết chắc type của mẫu:** BLAST consensus (hoặc contig dài nhất) lên bộ RefSeq của tất cả type
có thể gặp, hoặc lên toàn bộ nucleotide collection trên web NCBI, để xác định type trước rồi mới tách mẫu theo type.

**Kiểm tra độ gần của reference đã chọn** (khuyến nghị): sau lần chạy viralrecon đầu tiên, đếm số SNP của
từng mẫu so với reference (Bước 5, mục 6). Nếu mẫu khác reference khoảng 5% trở lên, chọn reference gần hơn
rồi chạy lại từ Bước 3.

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

**Từ lần chạy viralrecon đầu tiên (cách nhanh):** nếu đã chạy viralrecon với reference tạm, gom consensus
(đường dẫn ở Bước 4.8) để BLAST ở Bước 2. Consensus ít N (khoảng 1% N) cho kết quả BLAST đáng tin nhất.

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

**Lưu ý về BED:** tên primer phải có hậu tố `_LEFT` và `_RIGHT` (ví dụ `D1,18F_LEFT`,
`D1,17R_RIGHT`). Nếu dùng hậu tố khác, thêm `--primer_left_suffix` và
`--primer_right_suffix` khi chạy viralrecon. Cột đầu của BED phải trùng tên sequence trong file FASTA reference
(ví dụ `NC_001477.1`).

---

## Bước 4 — Chuẩn bị môi trường và chạy nf-core/viralrecon

### 4.0. Đặt biến dùng chung (sửa theo virus và lô)

Đặt biến một lần ở đầu mỗi phiên để các lệnh sau dùng lại cho mọi virus:

```bash
export WD=/mnt/e/Analysis                    # thư mục phân tích
export TAG=D1                                # nhãn lô/type: D1..D4, ZIKV, CHIKV, RABV, EVA71...
export REF=reference/dengue/DENV1.fasta      # reference đã chọn ở Bước 2
export GFF=reference/dengue/DENV1.gff        # annotation của đúng reference đó
export BED=final_bed/D1_DENV1.bed            # BED từ Bước 3
export SAMPLESHEET=samplesheet_D1.csv
export OUT=output/result_illumina_D1
cd $WD
```

Samplesheet Illumina có 3 cột `sample,fastq_1,fastq_2` (xem mẫu ở mục 4.4). Đường dẫn FASTQ phải đọc được từ WSL (`/mnt/e/...`).

### 4.1. Chuẩn bị file GFF của reference (cho SnpEff)

GFF phải lấy từ **đúng accession và đúng phiên bản** của file reference, nếu không tọa độ sẽ lệch.

```bash
head -n 1 $REF                                  # xem accession, ví dụ NC_001477.1
curl -o $GFF \
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=ACCESSION&rettype=gff3&retmode=text"
head $GFF                                       # phải có dòng ##gff-version 3
```
Kiểm tra tên sequence ở cột 1 của GFF trùng với header FASTA:
```bash
grep '>' $REF | cut -d' ' -f1
grep -v '^#' $GFF | cut -f1 | sort -u
```
Xem cấu trúc gene (quyết định cách cắt vùng ở Bước 8 và cách đánh số đột biến ở Bước 10):
```bash
grep -v '^#' $GFF | awk '$3=="CDS"' | cut -f4,5,9 | cut -c1-120
```
- **Một CDS dài** (Dengue, Zika, Enterovirus): một polyprotein duy nhất; SnpEff báo vị trí amino acid theo toàn polyprotein.
- **Nhiều CDS** (Dại: N, P, M, G, L; Chikungunya: hai ORF): SnpEff báo theo từng gene/ORF, thuận tiện hơn.

### 4.2. Cố định phiên bản Nextflow và pipeline

Luôn ghim phiên bản pipeline bằng `-r` và Nextflow bằng `NXF_VER`:

```bash
conda activate nf-core
export NXF_CONDA_CACHEDIR=$HOME/nf_conda_cache   # build env một lần, dùng lại
NXF_VER=25.04.6 nextflow run nf-core/viralrecon -r 3.0.0 ...
```

Lý do: Nextflow mới (ví dụ 26.x) parse file cấu hình chặt hơn và có thể báo lỗi
`Invalid include source ... conf/test_full_sispa.config` khi chạy bản pipeline chưa tương
thích. Ghim `-r 3.0.0` kèm `NXF_VER=25.04.6` đã chạy ổn trong thực tế. Khi cần xoá cache
pipeline: `nextflow drop nf-core/viralrecon`.

### 4.3. File `custom.config` (giới hạn tài nguyên và sửa môi trường conda)

Tạo `custom.config` trong thư mục phân tích:

```groovy
process {
    // Giới hạn theo cấu hình máy thật (kiểm tra bằng nproc, free -h)
    resourceLimits = [
        cpus: 30,
        memory: 42.GB,
        time: 48.h
    ]

    // QUAST với Python 3.13 thiếu module distutils -> ghim Python 3.11
    withName: 'QUAST' {
        conda = 'bioconda::quast=5.3.0 conda-forge::python=3.11 conda-forge::setuptools'
    }
}

executor {
    cpus   = 30
    memory = '42 GB'
}
```

- `resourceLimits` sửa lỗi `Process requirement exceeds available memory -- req: 72 GB; avail: 47 GB`
  (ví dụ bước `BOWTIE2_BUILD`). Đặt RAM thấp hơn RAM thật khoảng 5-10%.
- Dòng `executor` giới hạn tổng tài nguyên chạy đồng thời, tránh OOM khi nhiều tiến trình chạy song song.
- Kiểm tra cấu hình đã được nhận (lưu ý `-c` đứng **trước** từ `config`):
  ```bash
  NXF_VER=25.04.6 nextflow -c custom.config config ~/.nextflow/assets/nf-core/viralrecon -profile conda -flat | grep -i quast
  ```

### 4.4. Lệnh chạy Illumina (đã kiểm chứng với dengue D1)

```bash
NXF_VER=25.04.6 nextflow run nf-core/viralrecon -r 3.0.0 \
  --input $SAMPLESHEET \
  --platform illumina \
  --outdir $OUT \
  --fasta $REF \
  --gff $GFF \
  --primer_bed $BED \
  --skip_pangolin \
  --skip_nextclade \
  --skip_freyja \
  --skip_assembly \
  --skip_variants_quast \
  -profile conda \
  -c custom.config \
  -ansi-log false \
  -resume
```

Giải thích các tham số bỏ qua (Pangolin, Freyja và dataset Nextclade mặc định dành cho SARS-CoV-2):

| Tham số | Lý do |
|---|---|
| `--skip_pangolin` | Pangolin chỉ dành cho SARS-CoV-2; bước `PANGOLIN_UPDATEDATA` còn có thể lỗi khi tạo env conda |
| `--skip_nextclade` | Dataset Nextclade mặc định là SARS-CoV-2 (chạy Nextclade riêng cho virus của bạn ở Bước 6) |
| `--skip_freyja` | Freyja dùng dữ liệu SARS-CoV-2 |
| `--skip_assembly` | Bỏ SPAdes và các bước de novo; với dữ liệu amplicon thường chỉ cần consensus từ mapping. **Với virus đa dạng cao (Enterovirus, Dại) cân nhắc không bỏ** |
| `--skip_variants_quast` | Tránh lỗi MultiQC khi QUAST không align được consensus (xem bảng lỗi, Mục 4.7) |
| `--skip_kraken2` (tuỳ chọn) | Bỏ bước loại reads người nếu không cần, tiết kiệm thời gian và RAM |

`-ansi-log false` giúp log dễ đọc hơn trong tmux và trên màn hình nhỏ (tablet). Caller biến thể trong lô
D1 là bcftools (thư mục `variants/bcftools`); kiểm tra caller thực tế trong `pipeline_info/params_*.json`.

Script `04_run_viralrecon.sh` (Illumina MiSeq, ví dụ type D2):
```bash
bash scripts/04_run_viralrecon.sh illumina D2 \
  samplesheet_illumina_D2.csv \
  final_bed/D2.bed \
  final_bed/D2.primer_fasta.fa \
  ref_selection_out/references/D2_chosen_reference.fasta \
  results_illumina_D2
```
Nên mở script và đảm bảo nó đã gồm các tham số trên (ghim `-r`, `-c custom.config`, các `--skip_*`).

**Nanopore** (Medaka, không cần fast5), ví dụ type D2:
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

Chạy riêng từng type (samplesheet/BED/reference khác nhau) — nếu 1 lô mẫu lẫn nhiều type, tách mẫu theo
type (dựa kết quả BLAST ở bước 2) trước khi tạo samplesheet cho từng lần chạy.

### 4.5. Chạy trên server từ xa (SSH + Tailscale + tmux)

Pipeline kéo dài hàng giờ, nên luôn chạy trong `tmux` trên server để mất kết nối không làm
dừng pipeline.

**Từ PowerShell trên Windows client:**
```powershell
tailscale status                                    # tìm IP 100.x.y.z của server
ssh daohuymanh@<IP-tailscale>                       # kiểm tra đăng nhập
ssh -t daohuymanh@<IP-tailscale> wsl tmux new -As viralrecon
```
- Nếu sshd chạy trong WSL (prompt dạng `user@host:~$`), bỏ chữ `wsl`. Nếu vào Windows của server
  (prompt dạng `C:\...>`), giữ `wsl`.
- Lỗi `Could not resolve hostname server` nghĩa là bạn chưa tạo bí danh. Dùng IP trực tiếp, hoặc tạo
  `C:\Users\<bạn>\.ssh\config`:
  ```
  Host server
      HostName <IP-tailscale>
      User daohuymanh
      ServerAliveInterval 30
      ServerAliveCountMax 6
  ```
- Chạy lệnh tmux từ PowerShell không cần vào hẳn server: `ssh <host> wsl tmux ls`,
  `ssh <host> wsl pgrep -af nextflow`, `ssh <host> wsl tail -n 30 /mnt/e/Analysis/.nextflow.log`.
  Chỉ lệnh tương tác (`tmux attach`, `tmux new`) mới cần `-t`.

**Vì sao dùng `tmux new -As <tên>`:** lệnh chạy trong phiên SSH sẽ chết khi mạng chập chờn hoặc đóng cửa sổ;
tmux giữ phiên trên server. `-s <tên>` đặt tên phiên; `-A` nghĩa là nếu phiên đã có thì vào lại thay vì tạo mới.
Bên trong tmux là shell mới, nên cần `conda activate` lại. Cách khác:
`nohup <lệnh> > run.out 2>&1 &` rồi `tail -f run.out`.

**Thao tác tmux cần nhớ:**
- Thoát mà vẫn để lệnh chạy: `Ctrl+b` rồi `d`.
- Vào lại: `tmux attach -d -t viralrecon` (`-d` đá thiết bị kia ra, hữu ích khi đổi giữa máy tính và tablet).
- Thêm vào `~/.tmux.conf` trên server: `set -g mouse on`, `set -g history-limit 50000`, `set -g window-size latest`.

**WSL tự tắt làm mất tmux:** nếu sau khi SSH rớt mà `tmux ls` báo
`error connecting to /tmp/tmux-.../default`, WSL đã tắt và kéo pipeline theo. Giữ WSL luôn sống bằng
một tiến trình nền (chạy trong PowerShell trên Windows của server; thay `Ubuntu` bằng tên distro
từ `wsl -l -v`):
```powershell
Start-Process wsl -ArgumentList "-d","Ubuntu","-e","sleep","infinity" -WindowStyle Hidden
```
Nên tạo Task Scheduler chạy lệnh này lúc đăng nhập. Tắt chế độ sleep/hibernate của server. Nếu pipeline
bị dừng, chạy lại đúng lệnh cũ với `-resume`: các bước đã xong sẽ hiện `cached`.

Dữ liệu và thư mục `work` nằm trên ổ Windows (`/mnt/e/...`) thì I/O chậm hơn; nếu có chỗ trên ổ Linux,
dùng `-w $HOME/nf_work` (lưu ý đổi thư mục work thì `-resume` không dùng lại kết quả cũ).

### 4.6. Tải file về máy client

Chạy trong **PowerShell trên máy client**, không phải trong WSL của server. Cú pháp là `người_dùng@địa_chỉ:đường_dẫn`
với tên đăng nhập SSH của server (không phải tên tài khoản Windows của client):
```powershell
cd $HOME\Downloads
scp daohuymanh@<IP-tailscale>:/mnt/e/Analysis/output/result_illumina_D1/multiqc/multiqc_report.html .
```
- `hostname contains invalid characters`: sai cú pháp (thiếu `user@` hoặc `:`), hoặc gõ trong WSL thay vì client.
- Báo không tìm thấy đường dẫn: sshd của server có thể là sshd của Windows; thử đường dẫn dạng `/E:/Analysis/...`.
- Dự phòng cho file văn bản nhỏ (ví dụ cây Newick): `cat file` trong WSL, sao chép và dán vào Notepad.

### 4.7. Bảng lỗi thường gặp và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Invalid include source ... test_full_sispa.config` | Nextflow quá mới so với phiên bản pipeline, hoặc cache pipeline không đầy đủ | `NXF_VER=25.04.6` và `-r 3.0.0`; `nextflow drop nf-core/viralrecon` rồi chạy lại |
| `Parameter --platform is required` | Gõ lệnh với `...` thay cho tham số | Truyền đủ các tham số |
| `PANGOLIN_UPDATEDATA` lỗi tạo env conda (status 120) | Pangolin dành cho SARS-CoV-2, không cần với virus khác | `--skip_pangolin --skip_nextclade --skip_freyja` |
| `Process requirement exceeds available memory -- req: 72 GB; avail: 47 GB` | Module yêu cầu nhiều RAM hơn máy có | `resourceLimits` trong `custom.config` (Mục 4.3) |
| QUAST: `No module named 'distutils'` | Env conda dùng Python 3.13 | Ghim `python=3.11` + `setuptools` cho QUAST (Mục 4.3) |
| MultiQC: `TypeError: unsupported operand type(s) for /: 'str' and 'int'` (kèm `rich has no attribute 'panel'`) | Báo cáo QUAST chứa `-` vì consensus không align được với reference (độ tương đồng thấp hơn ngưỡng của QUAST); lỗi `rich` chỉ là lỗi phụ che lỗi gốc | `--skip_variants_quast`; về lâu dài chọn reference gần hơn (Bước 2) |
| `client_loop: send disconnect: Connection reset` | SSH bị ngắt | Chạy trong tmux; vào lại `tmux attach -d -t viralrecon` |
| `error connecting to /tmp/tmux-.../default` sau khi SSH rớt | WSL đã tắt | Giữ WSL sống (Mục 4.5), chạy lại với `-resume` |
| `nextflow config ... -r` hoặc `-c` báo `Unknown option` | Sai vị trí tuỳ chọn | `nextflow -c custom.config config <đường dẫn pipeline> -profile conda -flat` |
| `NullPointerException ... MermaidRenderer` trong `.nextflow.log` | Lỗi vẽ sơ đồ DAG lúc kết thúc | Vô hại, bỏ qua |
| `iqtree2: command not found` | IQ-TREE 3.x dùng lệnh `iqtree` | Dùng `iqtree` (kiểm tra `iqtree --version`) |
| `scp`: `hostname contains invalid characters` | Sai cú pháp hoặc chạy trên server | Chạy từ PowerShell client, dạng `user@IP:/đường/dẫn` |
| `dataformat` báo sai tên trường | Tên trường khác giữa các phiên bản | `dataformat tsv virus-genome --help` |
| Cảnh báo `size` aesthetic lỗi thời, `codetools` khi vẽ cây | Cảnh báo của ggplot2/ggtree/R | Vô hại |

Khi gặp lỗi lạ, xem 30 dòng cuối của `.nextflow.log` và nội dung `.command.err` trong thư mục work của
tiến trình lỗi (đường dẫn in trong thông báo `Work dir:`).

### 4.8. Ý nghĩa các thư mục trong `output/result_illumina_D1/`

| Thư mục | Chứa gì | Mức độ quan trọng |
|---|---|---|
| `multiqc/` | `multiqc_report.html` tổng hợp QC mọi mẫu; `multiqc_data/` là số liệu thô | **Xem đầu tiên** |
| `variants/` | BAM, VCF, consensus, SnpEff, thống kê độ phủ | **Kết quả chính** |
| `fastp/` | Báo cáo cắt adapter và lọc chất lượng reads (`*.fastp.html/json/log`) | Trung bình |
| `fastqc/` | Chất lượng reads thô (`*_fastqc.html/zip`) | Trung bình |
| `kraken2/` | Phân loại reads (`*.kraken2.report.txt`), dùng để loại reads người | Trung bình |
| `pipeline_info/` | Báo cáo thực thi, timeline, phiên bản phần mềm, tham số đã dùng | Dùng để viết Methods |
| `assembly/` | Kết quả SPAdes (chỉ có nếu không dùng `--skip_assembly`) | Thấp, trừ virus đa dạng cao |

Cấu trúc thực tế trong `variants/` (caller bcftools):

```
variants/
├── bowtie2/
│   ├── log/                 # log Bowtie2: có dòng "overall alignment rate"
│   ├── samtools_stats/      # flagstat, stats, idxstats
│   ├── mosdepth/genome/     # *.mosdepth.summary.txt (độ sâu trung bình)
│   └── *.sorted.bam (+ .bai)  # reads đã map (mở bằng IGV)
└── bcftools/
    ├── D1-xxx.vcf.gz (+ .tbi)          # toàn bộ biến thể gọi được
    ├── bcftools_stats/                 # số SNP/indel mỗi mẫu
    ├── snpeff/                         # VCF chú giải amino acid + báo cáo SnpEff
    ├── consensus/bcftools/
    │   ├── D1-xxx.consensus.fa         # CHUỖI CONSENSUS từng mẫu
    │   └── D1-xxx.filtered.vcf.gz      # biến thể sau lọc, nguồn tạo consensus
    └── variants_long_table.csv         # bảng tổng hợp mọi biến thể của mọi mẫu
```

Tên file chính xác có thể khác chút giữa các phiên bản; khi không thấy, dùng
`find $OUT -name '*từ_khóa*'`.

**Cách dùng từng nhóm:**
- `multiqc_report.html`: rà mẫu bất thường (ít reads, map thấp, độ phủ lệch) trước khi dùng kết quả.
- `fastp/`, `fastqc/`: mở file riêng khi mẫu đáng ngờ; ghi lại Q30 hoặc số reads bị loại làm lý do loại mẫu.
- `kraken2/`: ước lượng mức lẫn vật chủ. Tỷ lệ reads virus thật nằm ở log Bowtie2, không phải ở đây.
- `variants/bowtie2/`: tỷ lệ map thật, độ sâu, BAM để xem trực quan bằng IGV.
- `variants/bcftools/consensus/bcftools/*.consensus.fa`: **đầu vào của BLAST, Nextclade, MAFFT và cây phát sinh loài**.
- `variants_long_table.csv` và `snpeff/`: lọc và so sánh đột biến theo mẫu, gene, loại tác động, AF, DP (Bước 10).
- `pipeline_info/`: lấy phiên bản phần mềm và tham số (`params_*.json`) điền vào Methods.

Thư mục `work/` (cùng cấp thư mục chạy) lớn hơn `output/` rất nhiều. Chỉ xoá khi đã xong mọi lần chạy,
vì xoá `work/` làm `-resume` không dùng lại được.

---

## Bước 5 — Đánh giá chất lượng mẫu (và cách diễn giải)

Mở `multiqc/multiqc_report.html` trước, rồi kiểm tra thêm bằng các lệnh dưới đây (chạy trong `$WD`).

**1. Tỷ lệ reads map vào reference.** Chỉ số `100% mapped` trong flagstat **không có ý nghĩa** vì reads không
map đã bị loại; hãy xem log Bowtie2:
```bash
grep -H "overall alignment rate" $(find $OUT -name '*.bowtie2.log')
```
Mẫu có tỷ lệ map quá thấp (ví dụ dưới 1%) hoặc chỉ vài chục reads thì loại khỏi samplesheet
(ví dụ lô D1: một mẫu có 0,96% và chỉ 52 reads map, không tạo được consensus).

**2. Độ sâu trung bình** (cột thứ 4 của dòng `total`):
```bash
grep -H total $(find $OUT -name '*.mosdepth.summary.txt')
```
Độ sâu trung bình chưa đủ để kết luận, vì nó che các vùng có độ sâu bằng 0 (xem mục 4).

**3. Độ dài consensus, tổng số N và N trong vùng mã hóa** (lưu thành `qc_consensus.py` để dùng lại cho mọi virus):
```bash
cat > qc_consensus.py << 'EOF'
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
EOF
python3 qc_consensus.py "$OUT/variants/bcftools/consensus/bcftools/*.consensus.fa" 95 10273 | column -t
```
Thay `95 10273` bằng tọa độ CDS của reference (lấy từ GFF, Mục 4.1). Lưu ý cách tính này giả định consensus giữ
nguyên độ dài và tọa độ của reference (đúng với lô D1: mọi consensus dài 10.735 bp).

**4. Vị trí các đoạn N** (quan trọng hơn tỷ lệ N):
```bash
for f in $OUT/variants/bcftools/consensus/bcftools/*.consensus.fa; do
  echo "== $(basename $f)"
  grep -v '>' $f | tr -d '\n' | grep -ob 'N\+' | awk -F: '{print $1+1 "-" $1+length($2)}' | head -n 20
done
```
- N chỉ ở hai đầu genome (ngoài vùng primer) thường nằm trong UTR. So với CDS trong GFF để biết vùng mã hóa còn đầy đủ không.
- N ở **giữa genome**, bắt đầu cùng một vị trí ở nhiều mẫu, là dấu hiệu **mất amplicon**
  (độ sâu bằng 0 ở đó dù các vùng khác sâu hàng nghìn lần).

**5. Đối chiếu vùng mất với tọa độ primer** để biết amplicon nào bị mất (đổi khoảng tọa độ cho phù hợp):
```bash
awk '$2>7400 && $3<9300' $BED | sort -k2,2n
```
Vùng chỉ một amplicon phủ riêng nằm giữa đầu primer phải của amplicon kề trước và đầu primer trái của amplicon
kề sau. Nhiều mẫu cùng mất một amplicon thường do nguyên nhân chung (ví dụ biến dị ở vị trí gắn primer).
Đó là giả thuyết cần xác nhận bằng độ sâu theo amplicon (thư mục `mosdepth/amplicon` nếu có) và bằng cách so
trình tự consensus ở vị trí primer với trình tự primer.

**6. Số SNP so với reference** (đo độ xa của reference):
```bash
grep -H "number of SNPs:" $(find $OUT -name '*.bcftools_stats.txt' | grep -v snpeff)
```
Ví dụ lô D1: mỗi mẫu có khoảng 710-820 SNP trên 10.735 bp (khoảng 6,6-7,6%). Mức này đủ để QUAST không align được
dù Bowtie2 vẫn map 85-94% reads. Số SNP cao nghĩa là reference nên được thay bằng chuỗi gần genotype hơn (Bước 2).

### Cách phân loại chất lượng mẫu (ví dụ lô D1)

| Nhóm | Đặc điểm | Dùng cho |
|---|---|---|
| A | N chỉ ở hai đầu (khoảng 1% N) | Phân loại, cây toàn CDS, đột biến |
| B | Hai đầu cộng một đoạn N ngắn trong UTR | Tương đương nhóm A sau khi kiểm tra bằng GFF |
| C | Hai đầu cộng khoảng trống giữa genome (3,5% đến 16% N) từ cùng một vị trí | Phân loại qua gene đủ dữ liệu; loại khỏi cây toàn CDS và phân tích đột biến vùng thiếu, hoặc nêu rõ trong Methods |
| Loại | Quá ít reads map | Không dùng |

Ngưỡng cụ thể (độ sâu tối thiểu, tỷ lệ N tối đa) tùy mục đích, loại virus và tạp chí; hãy đặt tiêu chí rõ
ràng, ghi vào Methods và áp dụng thống nhất cho mọi mẫu. Lưu danh sách mẫu đạt chuẩn vào `good_samples.txt`
(mỗi dòng một tên mẫu, ví dụ `D1-4000_S31_L001`) để dùng ở các bước sau.

---

## Bước 6 — Phân loại genotype/lineage

viralrecon **không** phân loại Dengue và các virus khác (Pangolin, Freyja và dataset Nextclade mặc định chỉ dành cho
SARS-CoV-2). Hãy làm riêng sau khi có consensus, trong một môi trường conda riêng (không dùng chung với `nf-core`):

```bash
conda create -n phylo -c conda-forge -c bioconda nextclade mafft iqtree seqkit entrez-direct ncbi-datasets-cli snp-dists -y
conda activate phylo
mkdir -p $WD/downstream && cd $WD/downstream
```

### 6.1. Gom consensus của mẫu đạt chuẩn

```bash
CONS=$WD/$OUT/variants/bcftools/consensus/bcftools
cd $WD/downstream
# good_samples.txt: mỗi dòng một tên mẫu đạt chuẩn (xem Bước 5)
for s in $(cat good_samples.txt); do cat $CONS/${s}.consensus.fa; done > ${TAG}_good.fasta
cat $CONS/*.consensus.fa > ${TAG}_all.fasta           # toàn bộ mẫu, dùng cho BLAST/phân loại
sed -i 's/ .*//' ${TAG}_good.fasta ${TAG}_all.fasta   # bỏ phần sau khoảng trắng trong header
grep -c '>' ${TAG}_good.fasta ${TAG}_all.fasta
```
Header consensus dạng `>D1-4000_S31_L001 NC_001477.1`; sau lệnh `sed` chỉ còn tên mẫu.

### 6.2. Ba cách phân loại, nên dùng ít nhất hai để đối chiếu

**(a) Nextclade với dataset của virus bạn** (nhanh, cho kết quả phân loại, đột biến và chất lượng chuỗi):
```bash
nextclade dataset list | grep -i -E "dengue|denv|zika|chik|rabies|entero"   # xem dataset nào có
nextclade dataset get --name <tên_dataset> --output-dir nc_dataset
nextclade run -D nc_dataset --output-all nextclade_out ${TAG}_all.fasta
```
Không phải virus nào cũng có dataset; nếu danh sách không có, dùng (b) và (c). Kết quả nằm trong `nextclade_out/`
(bảng `nextclade.tsv` gồm clade/lineage được gán, đột biến nucleotide và amino acid, điểm chất lượng).

**(b) BLAST** consensus lên cơ sở dữ liệu NCBI (web: blastn, nucleotide collection) để xem chuỗi giống nhất là
genotype/lineage nào và tương đồng bao nhiêu phần trăm. Mẫu ít N cho kết quả tin cậy nhất.

**(c) Phân loại bằng cây phát sinh loài** (Bước 7-9): đặt mẫu cạnh các chuỗi tham chiếu đã biết genotype/lineage.
Đây là cách chặt chẽ nhất khi cần đưa vào bài báo; (a) và (b) dùng để định hướng chọn chuỗi tham chiếu.

### 6.3. Công cụ phân loại theo virus (xác nhận phiên bản mới nhất khi dùng)

| Virus | Cách thường dùng |
|---|---|
| Dengue 1-4 | Nextclade dataset (nếu có), BLAST, Dengue Genotyping Tool của NCBI, cây với chuỗi đại diện genotype; thường dựa trên gene E |
| Zika | Nextclade dataset (nếu có), cây với chuỗi đại diện lineage Châu Phi và Châu Á |
| Chikungunya | Nextclade dataset (nếu có), cây với chuỗi ECSA/WA/Asian/IOL; gene E1 hoặc toàn CDS |
| Dại | Công cụ gán lineage chuyên biệt như RABV-GLUE (nếu dùng được), BLAST, cây với chuỗi đại diện clade; gene N hoặc toàn genome |
| Enterovirus | Xác định type bằng VP1 (BLAST hoặc Enterovirus Genotyping Tool), sau đó genogroup/subgenogroup bằng cây VP1 |

### 6.4. Kiểm tra nhiễm hỗn hợp và nhầm type

Một mẫu có thể chứa hai type (ví dụ đồng nhiễm 2 serotype dengue). Dấu hiệu: nhiều biến thể có tần số allele trung
gian (không gần 0 hoặc 1) và độ phủ amplicon bất thường. Kiểm tra bằng cách map reads lên tất cả reference của
virus rồi so số reads map:

```bash
# ref_all.fa: gộp reference của mọi type (ví dụ 4 serotype dengue)
minimap2 -ax sr ref_all.fa sample_R1.fastq.gz sample_R2.fastq.gz | samtools view -F 4 | cut -f3 | sort | uniq -c
```
Reads dồn vào một reference là mẫu đơn type; chia đáng kể giữa hai reference nên xem lại (cần minimap2 và samtools
trong môi trường).

---

## Bước 7 — Chọn chuỗi tham chiếu từ NCBI (metadata trước, tải trình tự sau)

Cách này kiểm soát được chuỗi nào vào cây và để lại danh sách accession cho phụ lục bài báo.
Nếu có khoá API NCBI, đặt `export NCBI_API_KEY=<khoá>` để tăng giới hạn tốc độ (đừng dán khoá vào nơi công khai).

Đặt biến cho virus đang làm (tên taxon dùng đúng như NCBI Taxonomy; kiểm tra bằng
`datasets summary taxonomy taxon "<tên>"`):

```bash
cd $WD/downstream
export TAXON="Dengue virus 1"      # ví dụ: "Dengue virus 2", "Zika virus", "Chikungunya virus", "Rabies virus"
export LEN_MIN=10500 LEN_MAX=10800 # khoảng độ dài genome hoàn chỉnh của virus (xem bảng ở đầu tài liệu)
export REF_ACC=NC_001477.1         # accession reference đã dùng trong pipeline
```

**(a) Lấy metadata genome hoàn chỉnh:**
```bash
datasets summary virus genome taxon "$TAXON" --complete-only --as-json-lines \
 | dataformat tsv virus-genome \
     --fields accession,virus-name,length,isolate-collection-date,geo-location,geo-region,host-name,release-date \
 > ${TAG}_metadata.tsv
wc -l ${TAG}_metadata.tsv
head -n 5 ${TAG}_metadata.tsv
```
Tên trường có thể khác giữa các phiên bản; xem `dataformat tsv virus-genome --help` nếu báo lỗi.
Thứ tự cột: 1 accession, 2 tên virus, 3 độ dài, 4 ngày thu mẫu, 5 vị trí, 6 vùng, 7 host, 8 ngày công bố.
Nhiều chuỗi cũ thiếu ngày, vị trí hoặc host. Với Enterovirus, lọc theo type (từ tên virus hoặc tài liệu);
với Dại, host không phải người (chó, dơi...) là bình thường nên đừng lọc theo `Homo sapiens`.

**(b) Xem phân bố trước khi lọc:**
```bash
cut -f5 ${TAG}_metadata.tsv | cut -d: -f1 | sort | uniq -c | sort -nr | head -n 25      # theo nước
cut -f7 ${TAG}_metadata.tsv | sort | uniq -c | sort -nr | head                           # theo host
awk -F'\t' 'NR>1 && $4!="" && $5!="" && $7!=""' ${TAG}_metadata.tsv | wc -l              # đủ ngày+vị trí+host
awk -F'\t' '$5 ~ /Viet/ {print substr($4,1,4)}' ${TAG}_metadata.tsv | sort | uniq -c      # ví dụ: Việt Nam theo năm
```
Ví dụ lô D1 (DENV1, 2.912 genome): Brazil 850, Việt Nam 808, Trung Quốc 246, Singapore 193, Mexico 116,
Campuchia 110, Thái Lan 68, Philippines 62, Indonesia 51... NCBI ghi nước là `Viet Nam`, nên dùng regex `Viet`.

**(c) Lọc và giảm mẫu theo nhóm** (tránh thiên lệch do vài nghiên cứu lớn; có điểm khởi tạo cố định nên chạy lại ra
cùng kết quả). Sửa danh sách nước theo khu vực của bạn: nhóm 1 (khu vực nghiên cứu) lấy nhiều hơn, nhóm 2 (lân cận)
vừa phải, nhóm 3 (các nơi còn lại) chỉ lấy vài đại diện:

```bash
GROUP1='^(Viet Nam)$'
GROUP2='^(Cambodia|Thailand|Singapore|China|Philippines|Indonesia|Malaysia|Laos|Myanmar)$'
GROUP3='^(Brazil|Mexico|Venezuela|Nicaragua|Colombia|Puerto Rico|USA|Argentina|Ecuador|India|Sri Lanka|Bangladesh|Japan|Nigeria|New Caledonia|French Polynesia)$'

(head -n 1 ${TAG}_metadata.tsv; tail -n +2 ${TAG}_metadata.tsv | shuf --random-source=<(yes)) \
| awk -F'\t' -v len_min=$LEN_MIN -v len_max=$LEN_MAX -v g1="$GROUP1" -v g2="$GROUP2" -v g3="$GROUP3" '
  NR==1{print; next}
  $3>=len_min && $3<=len_max && $4 ~ /^[0-9][0-9][0-9][0-9]/ && $5!="" {
    split($5,g,":"); c=g[1]; y=substr($4,1,4)
    if (c ~ g1)      {cap=3; k=c"_"y}
    else if (c ~ g2) {cap=2; k=c"_"y}
    else if (c ~ g3) {cap=3; k=c}
    else next
    if (++n[k] <= cap) print
  }' > ${TAG}_subsampled.tsv

wc -l ${TAG}_subsampled.tsv
cut -f5 ${TAG}_subsampled.tsv | cut -d: -f1 | sort | uniq -c | sort -nr
```
Bộ lọc host (ví dụ chỉ `homo sapiens` cho virus ở người) thêm bằng điều kiện `&& tolower($7) ~ /homo sapiens/` vào
dòng điều kiện. Mục tiêu hợp lý cho cây toàn vùng mã hóa là khoảng 100 đến 300 chuỗi; nhiều quá thì giảm `cap`,
ít quá thì tăng. Nên thêm vài chuỗi đại diện từng genotype/lineage từ bài phân loại đã công bố (hoặc chọn theo kết quả
phân loại ở Bước 6), và các chuỗi lưu hành gần đây ở khu vực.

**(d) Danh sách accession (luôn gồm reference đã dùng trong pipeline):**
```bash
cut -f1 ${TAG}_subsampled.tsv | tail -n +2 > refs_accessions.txt
echo "$REF_ACC" >> refs_accessions.txt
# echo "ACCESSION_đại_diện_genotype" >> refs_accessions.txt
sort -u refs_accessions.txt -o refs_accessions.txt
wc -l refs_accessions.txt
```

**(e) Tải trình tự theo accession và kiểm tra:**
```bash
datasets download virus genome accession --inputfile refs_accessions.txt --filename refs_${TAG}.zip
unzip -o refs_${TAG}.zip -d refs_${TAG}
grep -c '>' refs_${TAG}/ncbi_dataset/data/genomic.fna
grep '>' refs_${TAG}/ncbi_dataset/data/genomic.fna | cut -d' ' -f1 | tr -d '>' | sort > got.txt
sort refs_accessions.txt | comm -23 - got.txt        # accession còn thiếu
```
Danh sách quá dài thì chia nhỏ bằng `split -l 200 refs_accessions.txt` rồi tải từng phần.

**(f) Đặt tên dễ đọc (`accession_nước_năm`) và gộp với mẫu của bạn:**
```bash
awk -F'\t' 'NR>1{split($5,g,":"); gsub(/ /,"",g[1]); y=substr($4,1,4); if(y=="")y="NA"; if(g[1]=="")g[1]="NA"; print $1"\t"$1"_"g[1]"_"y}' ${TAG}_subsampled.tsv > rename.tsv
echo -e "${REF_ACC}\t${REF_ACC}_ref" >> rename.tsv

sed 's/ .*//' refs_${TAG}/ncbi_dataset/data/genomic.fna | seqkit rmdup -s > refs_clean.fasta
seqkit replace -p '^(.+)$' -r '{kv}' -k rename.tsv refs_clean.fasta > refs_named.fasta
grep '>' refs_named.fasta | head -n 5

cat ${TAG}_good.fasta refs_named.fasta > tree_input.fasta
grep -c '>' tree_input.fasta
```
Quy ước tên `accession_nước_năm` được script vẽ cây ở Bước 9 dùng để tô màu theo nước. Ví dụ lô D1: 9 mẫu cộng
khoảng 166 chuỗi tham chiếu thành 175 chuỗi.

---

## Bước 8 — Align, cắt vùng mã hóa, kiểm tra và dựng cây IQ-TREE

### 8.1. Align bằng MAFFT

```bash
mafft --auto --thread 16 tree_input.fasta > aligned.fasta
seqkit stats aligned.fasta
```
Ví dụ lô D1: 175 chuỗi, cùng dài 10.823 cột (genome gốc 10.735 bp, nên có thêm cột gap). Dòng
`ambiguous characters` chỉ là N và mã IUPAC, không phải lỗi. Kiểm tra trước khi cắt:
```bash
grep -c "^>${TAG}-" aligned.fasta          # đúng bằng số mẫu của bạn (nếu tên mẫu bắt đầu bằng ${TAG}-)
grep -c "^>${REF_ACC}" aligned.fasta       # phải bằng 1 (reference dùng để cắt vùng)
grep '>' aligned.fasta | sort | uniq -d    # không được in dòng nào (tên trùng sẽ làm IQ-TREE lỗi)
```

### 8.2. Cắt về vùng mã hóa (bỏ UTR)

Lấy tọa độ vùng mã hóa từ GFF của reference:
```bash
grep -v '^#' $WD/$GFF | awk '$3=="CDS"{print $4"\t"$5}' | sort -n | awk 'NR==1{s=$1} {e=($2>e?$2:e)} END{print "bat dau:", s, " ket thuc:", e}'
```
- Một CDS (Dengue, Zika, Enterovirus): lấy trực tiếp (ví dụ DENV1 `NC_001477.1`: 95-10273).
- Nhiều CDS (Dại, Chikungunya): lấy từ đầu CDS đầu tiên đến cuối CDS cuối cùng (vùng giữa có thể gồm đoạn không mã hóa
  nhỏ, chấp nhận được khi dựng cây toàn vùng). Nếu chỉ cần một gene (ví dụ E1, N, VP1), dùng tọa độ của riêng gene đó.

Lưu script để dùng lại (tên reference và tọa độ là tham số):
```bash
cat > cut_region.py << 'EOF'
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
EOF

python3 cut_region.py aligned.fasta cds_aligned.fasta $REF_ACC 95 10273    # đổi tọa độ theo virus
seqkit stats cds_aligned.fasta
```
Độ dài kỳ vọng xấp xỉ (kết thúc − bắt đầu + 1) cộng thêm các gap chèn trong vùng này.

### 8.3. Kiểm tra chất lượng alignment trước khi dựng cây

Tỷ lệ gap và N của từng chuỗi sau khi cắt, 15 chuỗi cao nhất:
```bash
awk '/^>/{if(n!="")printf "%s\t%d\t%.1f%%\n",n,g,100*g/t; n=substr($0,2); g=0; t=0; next}{x=$0; g+=gsub(/[-Nn]/,"",x); t+=length($0)}END{printf "%s\t%d\t%.1f%%\n",n,g,100*g/t}' cds_aligned.fasta \
  | sort -t$'\t' -k3 -nr | head -n 15
```
Ví dụ lô D1: chuỗi tệ nhất chỉ 2,6% gap/N, còn lại gần 0%; chín mẫu của bạn không nằm trong danh sách đầu, xác nhận
vùng mã hóa đầy đủ. Chuỗi có tỷ lệ cao bất thường thì loại (ngưỡng tự đặt theo yêu cầu bài):
```bash
seqkit grep -v -p "TÊN_THẬT_CỦA_CHUỖI" cds_aligned.fasta > cds_clean.fasta
```
Chỉ chạy lệnh trên khi có chuỗi cần loại, và thay `TÊN_THẬT_CỦA_CHUỖI` bằng tên thật; nếu không `cds_clean.fasta` chỉ là
bản sao của `cds_aligned.fasta`.

Ma trận khác biệt giữa các mẫu (số SNP từng cặp), hữu ích để thấy mẫu nào giống hệt hoặc gần giống nhau:
```bash
snp-dists -m cds_aligned.fasta > snp_matrix.tsv
```

### 8.4. Dựng cây IQ-TREE

**Lưu ý phiên bản:** IQ-TREE 3.x trong conda dùng lệnh `iqtree`, không có `iqtree2`. Kiểm tra bằng `iqtree --version`.

**Cây thử nhanh** (vài phút, chỉ để kiểm tra, không dùng trong bài):
```bash
iqtree -s cds_aligned.fasta -m GTR+G -fast -T 8 --prefix test_fast
```

**Cây chính (chạy trong tmux)**, vì có thể mất từ vài phút đến vài giờ:
```bash
tmux new -As phylo
conda activate phylo
cd $WD/downstream
iqtree -s cds_aligned.fasta -m MFP -B 1000 -T 16 --prefix ${TAG}_cds
```
- `-m MFP`: tự chọn mô hình thay thế nucleotide tốt nhất; `-B 1000`: ultrafast bootstrap 1000 lần;
  `-T 16`: số luồng; `--prefix`: tiền tố tên file kết quả.
- Nếu bị ngắt, chạy lại đúng lệnh (IQ-TREE tự tiếp tục từ checkpoint hoặc báo cần `--redo`).
- Cảnh báo `identical sequences` trong log là bình thường khi nhiều mẫu giống hệt nhau.

### 8.5. Đọc kết quả IQ-TREE

| File | Là gì | Dùng để |
|---|---|---|
| `D1_cds.treefile` | Cây ML tốt nhất, có giá trị UFBoot trên nhánh | **Cây chính để vẽ và đưa vào bài** |
| `D1_cds.contree` | Cây đồng thuận (consensus) của bootstrap | Tham khảo, so sánh |
| `D1_cds.iqtree` | Báo cáo: mô hình, tham số, số vị trí, thống kê | Ghi Methods |
| `D1_cds.log` | Log chạy | Truy lỗi, kiểm tra cảnh báo |
| `D1_cds.splits.nex`, `D1_cds.mldist` | Hỗ trợ split, ma trận khoảng cách | Phân tích bổ sung |

Trích thông tin cần cho Methods từ file báo cáo:
```bash
grep -E "Input data|constant sites|parsimony|Best-fit model|Model of substitution|Log-likelihood of the tree" ${TAG}_cds.iqtree
```
Ghi lại: số chuỗi, số vị trí, mô hình tốt nhất (dòng `Best-fit model`), UFBoot 1000 lần, phiên bản IQ-TREE.

Ví dụ lô D1: 175 chuỗi, tổng thời gian thực khoảng 4 phút 24 giây với 16 luồng, log-likelihood tốt nhất khoảng
-80172,6. Tham số cho thấy chuyển đổi (transition) C-T và A-G lớn hơn nhiều các hoán đổi khác, điển hình của virus RNA.
Log gợi ý mô hình GTR có tỷ lệ vị trí bất biến và tốc độ biến thiên theo FreeRate, nhưng hãy đọc dòng `Best-fit model`
để ghi chính xác.

---

## Bước 9 — Vẽ cây và xuất hình chất lượng xuất bản (TIFF 300 dpi)

Nên xuất **vector (PDF/SVG)** để chỉnh sửa và giữ chất lượng, đồng thời xuất **TIFF 300 dpi** nếu tạp chí yêu cầu ảnh
raster. Làm trên server qua SSH được, vì R xuất file trực tiếp, không cần màn hình đồ họa.

### 9.1. Cài môi trường R (một lần)

Dùng môi trường riêng để không ảnh hưởng `phylo` và `nf-core`:
```bash
conda create -n rtree -c conda-forge -c bioconda \
  r-base r-ggplot2 bioconductor-ggtree r-ape r-phangorn r-ragg -y
conda activate rtree
Rscript -e 'library(ggtree); cat("ggtree", as.character(packageVersion("ggtree")), "\n")'
```
Nếu `conda` báo xung đột gói, thử `mamba` hoặc bỏ `r-ragg` (script có phương án dự phòng ở Mục 9.3).

### 9.2. Script `plot_tree.R` (dùng chung cho mọi virus)

Script nhận tham số dòng lệnh, nên không phải sửa code khi đổi virus. Tên đầu nhánh theo quy ước
`accession_nước_năm` (Bước 7f); mẫu của bạn nhận diện bằng một biểu thức chính quy; chuỗi reference có tên bắt đầu `NC_`.

```bash
cd $WD/downstream
cat > plot_tree.R << 'EOF'
suppressPackageStartupMessages({
  library(ape); library(ggplot2); library(ggtree); library(phangorn)
})

## Cách dùng:
## Rscript plot_tree.R <treefile> <out_prefix> [own_regex] [outgroup_regex] [groups.tsv]
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2)
  stop("Cách dùng: Rscript plot_tree.R <treefile> <out_prefix> [own_regex] [outgroup_regex] [groups.tsv]")
TREE_FILE  <- args[1]
OUT_PREFIX <- args[2]
OWN_REGEX  <- if (length(args) >= 3 && nzchar(args[3])) args[3] else "^D[1-4]-"   # tên mẫu của bạn
OUT_REGEX  <- if (length(args) >= 4 && nzchar(args[4])) args[4] else ""           # outgroup; rỗng = midpoint
GROUPS_TSV <- if (length(args) >= 5 && nzchar(args[5])) args[5] else ""           # ghi đè nhóm: label<TAB>group
WIDTH_MM <- 180; HEIGHT_MM <- 240      # 2 cột ~180 mm; 1 cột ~85 mm (theo yêu cầu tạp chí)
TOP_N <- 7                             # số nước hiển thị riêng, còn lại gộp "Other"
SUPPORT_CUTOFF <- 95                   # chấm xám trên nhánh có UFBoot >= ngưỡng này

## ---- Đọc cây và đặt gốc ----
tr <- read.tree(TREE_FILE)
if (nzchar(OUT_REGEX)) {
  og <- grep(OUT_REGEX, tr$tip.label, value = TRUE)
  if (length(og) == 0) stop("Không tìm thấy outgroup khớp: ", OUT_REGEX)
  tr <- ape::root(tr, outgroup = og, resolve.root = TRUE, edgelabel = TRUE)
} else {
  tr <- phangorn::midpoint(tr, node.labels = "support")      # tạm thời, chỉ để xem sơ bộ
}

## ---- Nhóm cho từng đầu nhánh (tên: accession_nước_năm) ----
tips <- tr$tip.label
parts <- strsplit(tips, "_")
country <- vapply(parts, function(x) if (length(x) >= 3) x[length(x) - 1] else "NA", character(1))
group <- ifelse(grepl(OWN_REGEX, tips), "This study",
         ifelse(grepl("^NC_", tips), "Reference", country))
top <- names(sort(table(group[!group %in% c("This study", "Reference")]), decreasing = TRUE))
top <- head(top, TOP_N)
group <- ifelse(group %in% c("This study", "Reference", top), group, "Other")

if (nzchar(GROUPS_TSV)) {                                    # tuỳ chọn: tự gán nhóm (ví dụ genotype)
  g <- read.delim(GROUPS_TSV, header = FALSE, stringsAsFactors = FALSE, col.names = c("label", "group"))
  m <- match(tips, g$label)
  group[!is.na(m)] <- g$group[m[!is.na(m)]]
}

lv <- c("This study", setdiff(unique(group), c("This study", "Other", "Reference")), "Other", "Reference")
lv <- lv[lv %in% group]
mid <- setdiff(lv, c("This study", "Other", "Reference"))
pal <- c("#0072B2","#E69F00","#009E73","#CC79A7","#56B4E9","#F0E442","#882255","#44AA99","#DDCC77","#117733")
cols <- c("This study" = "#D55E00", setNames(rep(pal, length.out = length(mid)), mid),
          "Other" = "#BBBBBB", "Reference" = "#000000")[lv]
shapes <- setNames(ifelse(lv == "This study", 17, ifelse(lv == "Reference", 15, 16)), lv)
sizes  <- setNames(ifelse(lv == "This study", 2.2, ifelse(lv == "Reference", 1.6, 1.0)), lv)

lab <- sub("_S[0-9]+_L[0-9]+$", "", tips)                    # D1-4000_S31_L001 -> D1-4000
df  <- data.frame(label = tips, group = factor(group, levels = lv), lab = lab, stringsAsFactors = FALSE)

## ---- Vẽ cây ----
p <- ggtree(tr, size = 0.25) %<+% df
p$data$support <- suppressWarnings(as.numeric(p$data$label))   # UFBoot trên nút trong

p2 <- p +
  geom_nodepoint(aes(subset = !isTip & !is.na(support) & support >= SUPPORT_CUTOFF),
                 size = 0.6, color = "grey25") +
  geom_tippoint(aes(color = group, shape = group, size = group), na.rm = TRUE) +
  geom_tiplab(aes(label = lab, subset = group == "This study"),
              size = 1.9, fontface = "bold", offset = 0.002, na.rm = TRUE) +
  scale_color_manual(values = cols,   breaks = lv, name = NULL, drop = FALSE) +
  scale_shape_manual(values = shapes, breaks = lv, name = NULL, drop = FALSE) +
  scale_size_manual(values = sizes,   breaks = lv, name = NULL, drop = FALSE) +
  geom_treescale(width = 0.01, fontsize = 2.5, linesize = 0.3) +
  coord_cartesian(clip = "off") +
  theme(legend.position = "bottom",
        legend.text = element_text(size = 7),
        plot.margin = margin(4, 28, 4, 4),
        plot.background = element_rect(fill = "white", color = NA))

## ---- Xuất file ----
ggsave(paste0(OUT_PREFIX, ".pdf"), p2,
       width = WIDTH_MM, height = HEIGHT_MM, units = "mm")                  # vector (nên giữ)
ggsave(paste0(OUT_PREFIX, "_preview.png"), p2,
       width = WIDTH_MM, height = HEIGHT_MM, units = "mm", dpi = 100)       # xem nhanh
ggsave(paste0(OUT_PREFIX, "_300dpi.tiff"), p2,
       width = WIDTH_MM, height = HEIGHT_MM, units = "mm", dpi = 300,
       device = ragg::agg_tiff, compression = "lzw")                        # TIFF 300 dpi
cat("Xong:", OUT_PREFIX, ".pdf / _preview.png / _300dpi.tiff\n")
EOF
```

Ý nghĩa các phần chính:
- **Rooting:** không truyền `outgroup_regex` thì dùng midpoint, chỉ mang tính tạm thời. Với bài báo, đặt gốc theo outgroup hoặc nhóm gốc có cơ sở từ tài liệu.
- **Nhóm màu:** tên đầu nhánh `accession_nước_năm` được tách để lấy nước; `TOP_N` nước phổ biến nhất được tô riêng, còn lại gộp `Other`.
  Mẫu của bạn tô cam đỏ, hình tam giác lớn, kèm nhãn in đậm.
- **Ghi đè nhóm:** muốn tô màu theo genotype thay vì nước, tạo file `groups.tsv` (hai cột: tên đầu nhánh, nhóm; không có tiêu đề) và truyền làm tham số thứ năm.
- **Chấm xám trên nút:** nhánh có UFBoot từ 95 trở lên. Ghi ngưỡng này trong chú thích hình.
- **Bảng màu** theo Okabe-Ito, phân biệt được với người mù màu.

### 9.3. Chạy script

```bash
conda activate rtree
cd $WD/downstream
Rscript plot_tree.R ${TAG}_cds.treefile tree_${TAG} "^${TAG}-" 2>&1 | tail -n 20
ls -lh tree_${TAG}*
```
Ví dụ với outgroup: `Rscript plot_tree.R ${TAG}_cds.treefile tree_${TAG} "^${TAG}-" "^ACCESSION1|^ACCESSION2"`.
Cảnh báo `codetools` và `size` đã lỗi thời của ggplot2 là vô hại.

**Phương án dự phòng** nếu `ragg` lỗi: thay đoạn `ggsave(... _300dpi.tiff ...)` bằng
```r
tiff(paste0(OUT_PREFIX, "_300dpi.tiff"), width = WIDTH_MM, height = HEIGHT_MM,
     units = "mm", res = 300, compression = "lzw", type = "cairo")
print(p2)
dev.off()
```
Hoặc chuyển từ PDF sang TIFF bằng dòng lệnh (nếu có ImageMagick): `magick -density 300 tree_D1.pdf -compress lzw tree_D1_300dpi.tiff`.

### 9.4. Kiểm tra TIFF đã đúng 300 dpi chưa

Khổ 180 × 240 mm ở 300 dpi tương ứng khoảng 2126 × 2835 điểm ảnh (lệch một điểm do làm tròn là bình thường):
```bash
file tree_${TAG}_300dpi.tiff
tiffinfo tree_${TAG}_300dpi.tiff 2>/dev/null | grep -i -E "resolution|image width|length"
python3 -c "from PIL import Image; im=Image.open('tree_${TAG}_300dpi.tiff'); print(im.size, im.info.get('dpi'))" 2>/dev/null
```
Ví dụ lô D1: 2125 × 2834 điểm ảnh, `Resolution: 300, 300 pixels/inch`, nén LZW, màu RGB. Giá trị `bps` lạ trong
kết quả của lệnh `file` không đáng lo nếu `tiffinfo` đọc đúng; cách xác nhận cuối là mở TIFF bằng Fiji hoặc GIMP.

### 9.5. Tải về và xem

Tải về từ **PowerShell trên máy client** (cú pháp ở Mục 4.6):
```powershell
cd $HOME\Downloads
scp daohuymanh@<IP-tailscale>:/mnt/e/Analysis/downstream/tree_D1_preview.png .
scp daohuymanh@<IP-tailscale>:/mnt/e/Analysis/downstream/tree_D1.pdf .
scp daohuymanh@<IP-tailscale>:/mnt/e/Analysis/downstream/tree_D1_300dpi.tiff .
```
Xem `preview.png` trước để chỉnh nhanh. Mở PDF bằng trình đọc PDF hoặc Inkscape; mở TIFF bằng Windows Photos, GIMP hoặc Fiji.
Cây `.treefile` cũng mở được trực tiếp bằng FigTree hoặc iTOL nếu muốn chỉnh tay.

### 9.6. Chỉnh hình khi chưa đẹp

Sửa giá trị trong `plot_tree.R` rồi chạy lại (vài giây):
- Nhãn bị cắt bên phải: tăng số thứ hai trong `plot.margin = margin(4, 28, 4, 4)` (ví dụ 40).
- Chữ nhãn quá nhỏ hoặc to: sửa `size = 1.9` trong `geom_tiplab`.
- Muốn hình 1 cột: `WIDTH_MM <- 85` (chữ tối thiểu khoảng 6 pt để còn đọc được).
- Hình quá dày đặc: giảm số chuỗi tham chiếu ở Bước 7, hoặc đưa cây đầy đủ vào phụ lục và chỉ hiển thị phiên bản thu gọn trong bài chính.
- Tô màu theo genotype/lineage: dùng file `groups.tsv` (Mục 9.2).

### 9.7. Danh sách kiểm tra hình trước khi nộp

- Tra hướng dẫn tác giả của tạp chí: định dạng, dpi (hình nét vẽ thường yêu cầu cao hơn ảnh thông thường), kích thước, chế độ màu (RGB hay CMYK), kiểu nén.
- Gốc cây được nêu rõ (outgroup hay midpoint) và có cơ sở trong Methods.
- Chú thích hình nêu: số chuỗi, vùng genome, phần mềm và mô hình, ý nghĩa chấm trên nhánh (UFBoot ≥ ngưỡng), thanh tỷ lệ (số thay thế trên vị trí), nghĩa của màu và ký hiệu.
- Màu phân biệt được với người mù màu và đọc được khi in đen trắng nếu tạp chí yêu cầu.
- Font phổ biến (Arial/Helvetica), PDF nhúng font; giữ lại file vector, `.treefile` và script để sửa khi phản biện.

---

## Bước 10 — Tìm và tóm tắt đột biến

### 10.1. Các nguồn dữ liệu đột biến

| Nguồn | Có gì | Dùng khi |
|---|---|---|
| `variants/bcftools/variants_long_table.csv` | Một dòng cho mỗi biến thể của mỗi mẫu, kèm chú giải SnpEff | Lọc, so sánh nhiều mẫu cùng lúc |
| `variants/bcftools/snpeff/` | VCF chú giải amino acid và báo cáo SnpEff từng mẫu | Xem chi tiết một mẫu |
| `variants/bcftools/consensus/bcftools/*.filtered.vcf.gz` | Biến thể thực sự được đưa vào consensus | Biết đột biến nào nằm trong chuỗi consensus |
| `nextclade_out/nextclade.tsv` (Bước 6) | Đột biến nucleotide và amino acid so với reference của dataset, theo gene | Khi virus có dataset Nextclade |
| Alignment `cds_aligned.fasta` | So sánh trực tiếp giữa các mẫu và chuỗi tham chiếu | Tìm vị trí khác biệt giữa các mẫu |

Xem tên các cột trước khi lọc:
```bash
cd $WD/$OUT/variants/bcftools
head -n 1 variants_long_table.csv | tr ',' '\n' | cat -n
wc -l variants_long_table.csv
```
Các cột thường gặp gồm tên mẫu, vị trí, REF, ALT, FILTER, độ sâu (DP), tần số allele (AF), gene, loại tác động và ký hiệu
thay đổi amino acid; tên chính xác có thể khác, nên đối chiếu với kết quả lệnh trên.

### 10.2. Script tóm tắt đột biến theo ngưỡng

Script đọc `variants_long_table.csv`, lọc theo AF và DP, rồi tạo hai bảng: danh sách đột biến kèm số mẫu mang đột biến,
và ma trận có/không theo mẫu. Nếu tên cột của bạn khác, sửa trong hàm `g(...)`.

```bash
cat > summarize_variants.py << 'EOF'
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
EOF

python3 summarize_variants.py variants_long_table.csv 0.75 20 $WD/downstream/${TAG}_mut
head $WD/downstream/${TAG}_mut_list.tsv
```
Kết quả: `*_mut_list.tsv` (mỗi đột biến, số mẫu mang, danh sách mẫu) và `*_mut_matrix.tsv` (ma trận 0/1 để vẽ bản đồ nhiệt
hoặc lọc bằng Excel/R). Ngưỡng 0,75 và 20 chỉ là ví dụ; hãy tự đặt theo chất lượng dữ liệu và mục tiêu (xem 10.4).

### 10.3. Cách đánh số vị trí amino acid

- **Polyprotein đơn (Dengue, Zika, Enterovirus):** SnpEff báo vị trí theo toàn polyprotein. Để ghi theo từng protein
  (ví dụ E:D390N), lấy tọa độ protein trưởng thành từ GFF rồi trừ vị trí bắt đầu của protein, hoặc dùng Nextclade (báo theo từng gene).
  ```bash
  grep -v '^#' $WD/$GFF | cut -f3 | sort | uniq -c
  awk -F'\t' '$3 ~ /mature/ {match($9,/product=[^;]*/); print $4"\t"$5"\t"substr($9,RSTART+8,RLENGTH-8)}' $WD/$GFF
  ```
  Nếu GFF không có feature `mature_peptide`, lấy ranh giới protein từ ghi chú của accession trên NCBI hoặc từ tài liệu.
- **Nhiều CDS (Dại, Chikungunya):** SnpEff báo theo từng gene hoặc ORF; ghi rõ đánh số tính theo gene/ORF hay theo polyprotein.
- Luôn ghi **reference và accession** dùng để đánh số trong Methods, vì số vị trí phụ thuộc vào reference.

### 10.4. Chọn ngưỡng và loại biến thể không đáng tin

| Mục tiêu | Gợi ý cách lọc |
|---|---|
| Đột biến mức consensus (cho cây, so sánh genotype) | AF cao (ví dụ từ 0,75 trở lên), DP đủ lớn, FILTER đạt |
| Biến thể tần số thấp (quần thể, nhiễm hỗn hợp, thích ứng) | Hạ AF, nhưng cần DP cao, kiểm tra trùng lặp giữa các lần chạy và loại vị trí gần primer; cần caller phù hợp (iVar thường dùng cho việc này) |
| Đột biến mới của riêng mẫu | Loại các vị trí chung của cả nhóm (khác biệt cố định so với reference) |

Cần loại hoặc kiểm tra kỹ:
- **Biến thể nằm ở vị trí gắn primer:** primer có thể làm sai lệch trình tự ở đó; pipeline cắt primer, nhưng vị trí sát primer vẫn cần thận trọng.
- **Vùng độ sâu thấp** hoặc ngay sát khoảng trống mất amplicon.
- **Indel trong vùng lặp** (dễ sai ở dữ liệu Illumina và rất dễ sai ở Nanopore).
- **Vùng bị mất amplicon:** không được kết luận có hay không có đột biến ở đó.

### 10.5. Phân biệt khác biệt do genotype và đột biến thật sự

Mẫu của bạn so với reference có thể khác hàng trăm vị trí (lô D1: khoảng 800 SNP). Phần lớn là **khác biệt cố định giữa
genotype**, không phải đột biến mới. Để tách:
1. Đếm số mẫu mang mỗi đột biến (`*_mut_list.tsv`): đột biến có ở hầu hết mẫu thường là khác biệt genotype so với reference.
2. Đột biến chỉ có ở một hai mẫu hoặc một cụm mẫu mới đáng chú ý, và cần kiểm tra thêm (độ sâu, AF, vị trí gần primer).
3. Dùng reference gần genotype của mẫu (Bước 2) để giảm số khác biệt "nền", hoặc so sánh trực tiếp giữa các mẫu và với chuỗi tham chiếu cùng genotype trong alignment.
4. Với đột biến có ý nghĩa sinh học, đối chiếu tài liệu về vị trí đó (kháng nguyên, thích ứng vector, kháng thuốc...) thay vì suy diễn từ việc nó là missense.

---

## Bước 11 — Diễn giải kết quả và kiểm tra trước khi xuất bản

### 11.1. Cách đọc cây phát sinh loài

1. **Đặt gốc trước khi diễn giải.** Midpoint chỉ để xem sơ bộ. Cây chưa có gốc đúng có thể cho thấy quan hệ họ hàng sai chiều. Dùng outgroup (chuỗi thuộc type/lineage khác nhưng cùng virus, được tài liệu ủng hộ).
2. **Gán genotype/lineage cho mẫu:** tìm cụm (clade) chứa chuỗi tham chiếu đã biết genotype/lineage và có UFBoot từ khoảng 95 trở lên; nếu mẫu nằm trong cụm đó và cụm đơn nguồn (monophyletic) thì gán theo. Đối chiếu với kết quả BLAST và Nextclade (Bước 6).
3. **UFBoot** (chấm xám trên nhánh): ngưỡng khoảng 95 trở lên thường được coi là hỗ trợ tốt, nhưng hãy theo quy ước của tạp chí và nhớ rằng UFBoot khác bootstrap thường (diễn giải khác nhau).
4. **Nhánh dài bất thường** của một chuỗi: nghi ngờ lỗi (chuỗi kém chất lượng, nhiều N, lỗi alignment, nhiễm chéo, hoặc là chuỗi lai/tái tổ hợp). Kiểm tra lại chuỗi đó trước khi đưa vào bài.
5. **Mẫu gom thành cụm riêng của bạn:** các mẫu giống hệt hoặc gần giống nhau (xem `snp_matrix.tsv`) cho thấy có thể cùng nguồn lây, nhưng **kết luận về chuỗi lây truyền chỉ có giá trị khi kết hợp dữ liệu dịch tễ** (thời gian, địa điểm, tiếp xúc), vì chuỗi giống nhau cũng có thể là tình cờ khi virus ít biến đổi.
6. **Mẫu nằm cạnh chuỗi từ nước khác:** gợi ý mối liên hệ về nguồn gốc hoặc nhập khẩu, nhưng bị ảnh hưởng mạnh bởi **thiên lệch lấy mẫu** (nước có nhiều chuỗi công bố, như Brazil hay Việt Nam, dễ xuất hiện nhiều hơn). Đừng kết luận hướng lây truyền chỉ từ vị trí trên cây.
7. **Thời gian tiến hóa** (ước tính ngày tổ tiên chung gần nhất, tốc độ tiến hóa) cần phân tích riêng bằng phần mềm có mô hình đồng hồ phân tử (ví dụ TreeTime hoặc BEAST) và dữ liệu có ngày thu mẫu đầy đủ; cây ML không cho thông tin này.

### 11.2. Cách đọc kết quả phân loại

- Hai phương pháp độc lập (BLAST/Nextclade và cây) cùng cho một kết quả thì đáng tin; nếu khác nhau, xem lại chất lượng mẫu và chuỗi tham chiếu.
- Độ tương đồng thấp với chuỗi gần nhất (ví dụ dưới khoảng 95% đối với virus có genotype gần nhau) gợi ý genotype/lineage chưa có đại diện trong cơ sở dữ liệu hoặc nhầm type.
- Với virus có hệ phân loại đang thay đổi (ví dụ Dengue, Chikungunya, Dại), ghi rõ **hệ thống phân loại và phiên bản dataset/tài liệu** đã dùng.

### 11.3. Cách đọc kết quả đột biến

- Phân biệt đột biến **đồng nghĩa** (synonymous) và **sai nghĩa** (missense); đột biến sai nghĩa không tự động có ý nghĩa chức năng.
- Báo cáo kèm tần số allele, độ sâu và vị trí tương đối so với primer; với biến thể tần số thấp, nói rõ giới hạn của phương pháp.
- Đối chiếu với tài liệu trước khi gắn ý nghĩa sinh học; tránh suy diễn từ một vị trí duy nhất.
- Đột biến chỉ thấy ở một mẫu có thể là lỗi kỹ thuật (PCR, giải trình tự, nhiễm chéo); nên xác nhận bằng mẫu lặp hoặc phương pháp khác khi kết luận quan trọng.

### 11.4. Danh sách kiểm tra trước khi xuất bản

1. Xác nhận type và genotype/lineage bằng ít nhất hai phương pháp; loại trừ nhầm type và nhiễm hỗn hợp.
2. Dùng reference gần genotype của mẫu và BED đúng tọa độ reference đó.
3. Đặt tiêu chí lọc mẫu rõ ràng (độ sâu tối thiểu, tỷ lệ N tối đa, vùng mã hóa đầy đủ) và áp dụng thống nhất.
4. Báo cáo độ sâu trung bình, tỷ lệ genome đạt ngưỡng độ sâu và vị trí các khoảng trống từng mẫu.
5. Kiểm tra mẫu đối chứng âm của lô giải trình tự để loại trừ nhiễm chéo.
6. Với phân tích đột biến, nêu rõ ngưỡng DP, AF, caller và reference dùng để so sánh và đánh số.
7. Nộp reads lên SRA và chuỗi lên GenBank nếu tạp chí yêu cầu; mô tả đúng loại chuỗi (đủ vùng mã hóa hay toàn bộ genome) theo hướng dẫn của GenBank.
8. Phần Methods ghi rõ phiên bản và tham số:
   - nf-core/viralrecon 3.0.0, Nextflow 25.04.6, reference (accession), bộ primer, các tham số `--skip_*`, `custom.config` (lấy từ `pipeline_info/`);
   - cách chọn chuỗi tham chiếu cho cây: nguồn (NCBI Virus/datasets), tiêu chí lọc (genome hoàn chỉnh, host, vùng địa lý), cách giảm mẫu, ngày tải dữ liệu, và **danh sách accession** (`refs_accessions.txt`, `*_subsampled.tsv`) ở phụ lục;
   - MAFFT (phiên bản, chế độ `--auto`), vùng cắt (CDS, bỏ UTR), IQ-TREE (phiên bản, mô hình từ dòng `Best-fit model`, số chuỗi, số vị trí, UFBoot 1000 lần), phần mềm vẽ cây và cách đặt gốc.
9. Lưu các file trung gian để tái lập: `tree_input.fasta`, `aligned.fasta`, `cds_aligned.fasta`, `*_cds.*`, các script (`cut_region.py`, `plot_tree.R`, `summarize_variants.py`, `qc_consensus.py`) và các lệnh đã chạy.

---

## Phụ lục A — Điều chỉnh cho từng virus

Các ghi chú dưới đây là hướng dẫn thực hành, không thay thế tài liệu chuyên ngành. Trước khi dùng, hãy xác nhận
accession, hệ phân loại và công cụ phân loại hiện hành.

### A.1. Dengue 1, 2, 3, 4

- **Quy trình giống lô DENV1:** mỗi serotype một reference, GFF, BED và samplesheet riêng; không trộn serotype trong cùng lần chạy.
  Thay `TAXON` ở Bước 7 bằng `"Dengue virus 2"`, `"Dengue virus 3"`, `"Dengue virus 4"` và đổi `REF_ACC`
  (ví dụ DENV2 NC_001474.2, DENV3 NC_001475.2, DENV4 NC_002640.1; xác nhận lại trên NCBI).
- **Tọa độ CDS khác nhau giữa serotype:** luôn lấy lại từ GFF (Bước 8.2), không dùng lại tọa độ 95-10273 của DENV1.
- **Phân loại:** thường dựa trên gene E; với DENV2 có nhiều hệ thống đặt tên genotype/lineage (cũ và mới), nên nêu rõ hệ thống bạn dùng.
- **Đồng nhiễm nhiều serotype** có thể gặp trong vùng dịch; dùng cách kiểm tra ở Bước 6.4 (map lên 4 reference).
- **Reference nên gần genotype lưu hành:** bài học lô D1 cho thấy reference RefSeq có thể cách mẫu khoảng 7% và làm mất amplicon.

### A.2. Zika

- Reference tham khảo NC_012532.1, một polyprotein; quy trình giống Dengue.
- Phân loại chủ yếu giữa lineage Châu Phi và Châu Á (nhánh Châu Á gồm các chuỗi Châu Mỹ); kiểm tra Nextclade dataset (`nextclade dataset list`) hoặc dùng cây với chuỗi đại diện.
- Mẫu thường có tải lượng virus thấp, nên **mất amplicon (dropout)** hay gặp; đọc kỹ Bước 5, mục 4 và 5.
- Số chuỗi công bố ít hơn Dengue; bộ chuỗi tham chiếu cho cây có thể lấy gần như toàn bộ genome hoàn chỉnh thay vì giảm mẫu mạnh.
- Bộ mồi amplicon có thể dùng bộ đã công bố cho Zika (kiểu PrimalSeq) hoặc thiết kế mới bằng PrimalScheme.

### A.3. Chikungunya

- Reference tham khảo NC_004162.2. Genome có **hai ORF** (polyprotein không cấu trúc nsP1-4 và polyprotein cấu trúc), nên GFF có hai CDS chính.
  - Vùng dùng cho cây toàn vùng mã hóa: từ đầu CDS đầu tiên đến cuối CDS cuối cùng, hoặc chỉ gene E1 nếu so sánh với dữ liệu E1 công bố.
  - SnpEff báo vị trí theo từng ORF; ghi rõ cách đánh số khi báo cáo.
- Phân loại: genotype ECSA, West Africa, Asian, cùng nhánh IOL (Indian Ocean Lineage) trong ECSA. Dùng gene E1 hoặc toàn CDS; kiểm tra Nextclade dataset nếu có.
- Một số đột biến ở protein E1 và E2 được nêu trong tài liệu liên quan đến thích ứng với muỗi vector; khi báo cáo, đối chiếu tài liệu và ghi rõ vị trí tính theo protein và reference.
- Lọc tải về từ NCBI theo `"Chikungunya virus"`; độ dài genome hoàn chỉnh khoảng 11,6-12,0 kb (đặt `LEN_MIN`, `LEN_MAX` tương ứng).

### A.4. Virus Dại (RABV)

- Reference tham khảo NC_001542.1. Genome có **5 gene riêng** (N, P, M, G, L), nên GFF có 5 CDS; SnpEff báo theo từng gene, rất thuận tiện cho diễn giải.
- **Host rất đa dạng** (chó, dơi, động vật hoang dã...): đừng lọc theo `Homo sapiens` ở Bước 7; lọc theo host phù hợp với nghiên cứu (ví dụ chó nhà) và nêu rõ.
- Phân loại theo clade/lineage (ví dụ Cosmopolitan, Asian, Arctic-like, các nhánh Châu Phi); có công cụ gán lineage chuyên biệt như RABV-GLUE (xác nhận hiện còn dùng được và phiên bản). Phân loại thường dựa trên gene N hoặc toàn genome.
- Mẫu thường là mô não; tải lượng có thể biến động, và chất lượng RNA phụ thuộc bảo quản; kiểm tra Bước 5 kỹ.
- Cấu trúc lineage phụ thuộc mạnh vào địa lý và vật chủ; khi chọn chuỗi tham chiếu, thêm chuỗi từ nhiều lineage để không áp đặt kết quả phân loại.
- Dữ liệu công bố lệch theo nước và loài; lưu ý trong diễn giải.
- Cân nhắc **không bỏ assembly** (`--skip_assembly`) để so consensus mapping với contig de novo khi mẫu khác reference nhiều.

### A.5. Enterovirus

- **Không dùng một reference chung cho nhiều type:** Enterovirus gồm rất nhiều type (ví dụ EV-A71, CV-A16, CV-A6, EV-D68, các echovirus), khác nhau lớn đến mức mapping lên reference sai type cho kết quả kém.
  Quy trình:
  1. Xác định type bằng **gene VP1** (BLAST hoặc công cụ Enterovirus Genotyping Tool); tiêu chí tương đồng VP1 để định type có trong tài liệu phân loại (tra cứu ngưỡng hiện hành).
  2. Chọn một reference **đúng type** (bằng Bước 2), tạo GFF, BED và samplesheet riêng cho từng type.
- Genome ngắn hơn (khoảng 7,4 kb) với một polyprotein; vùng dùng cho cây là toàn CDS (từ GFF) hoặc VP1.
- Phân loại tiếp ở mức **genogroup/subgenogroup** bằng cây VP1 với chuỗi đại diện đã công bố (ví dụ EV-A71 có các genogroup A, B, C và các nhánh con).
- **Tái tổ hợp thường gặp:** dựng thêm cây theo vùng khác (ví dụ VP1 so với vùng 3D hoặc 5'UTR); cây khác nhau gợi ý tái tổ hợp, cần công cụ phát hiện tái tổ hợp (ví dụ RDP, GARD, 3SEQ).
- Đa dạng cao nên mapping lên reference có thể thiên lệch; nên **giữ assembly de novo** (bỏ `--skip_assembly`) và so sánh với consensus.
- Lọc tải về từ NCBI theo đúng type (tên taxon dùng trong NCBI Taxonomy; xác nhận bằng `datasets summary taxonomy taxon "<tên>"`), và đặt `LEN_MIN`, `LEN_MAX` quanh 7,2-7,6 kb.

### A.6. Các virus RNA khác

Quy trình áp dụng được cho virus RNA có thể sinh khuếch đại đa mồi. Cần xác định trước:
reference và GFF đúng, bộ mồi và BED, khoảng độ dài genome hoàn chỉnh, vùng thường dùng để phân loại,
hệ phân loại (genotype/lineage) và công cụ phân loại hiện hành, và cấu trúc gene (polyprotein đơn hay nhiều gene).

---

## Phụ lục B — Danh sách việc cần làm khi chuyển sang virus mới

1. Chọn reference (RefSeq hoặc chuỗi gần nhất) và tải GFF **cùng accession** (Bước 4.1).
2. Chuẩn bị bảng mồi và dựng BED đúng tọa độ reference đó (Bước 0-3); kiểm tra hậu tố `_LEFT`/`_RIGHT`.
3. Đặt biến dùng chung (`TAG`, `REF`, `GFF`, `BED`, `OUT`; Bước 4.0).
4. Chạy viralrecon với `--skip_pangolin --skip_nextclade --skip_freyja`; cân nhắc `--skip_assembly` hay giữ tùy độ đa dạng của virus (Bước 4.4).
5. Đánh giá chất lượng bằng `qc_consensus.py` (đổi tọa độ CDS) và các lệnh ở Bước 5; lập `good_samples.txt`.
6. Phân loại (Bước 6): kiểm tra `nextclade dataset list` cho virus; nếu không có thì BLAST và cây.
7. Đặt `TAXON`, `LEN_MIN`, `LEN_MAX`, danh sách nước, bộ lọc host phù hợp rồi chọn chuỗi tham chiếu (Bước 7).
8. Lấy tọa độ vùng cắt từ GFF (một hay nhiều CDS) rồi chạy `cut_region.py` (Bước 8.2).
9. Dựng cây với IQ-TREE (`iqtree`), ghi lại mô hình (Bước 8.4-8.5).
10. Vẽ cây bằng `plot_tree.R`, đổi biểu thức chính quy cho tên mẫu và outgroup (Bước 9).
11. Tóm tắt đột biến bằng `summarize_variants.py` với ngưỡng phù hợp mục tiêu (Bước 10).
12. Diễn giải và kiểm tra theo Bước 11, rồi ghi Methods đầy đủ phiên bản và tham số.

---

## Phụ lục C — Tóm tắt lệnh theo thứ tự (cho lô mới)

```bash
# 0. Môi trường và biến
conda activate nf-core
export WD=/mnt/e/Analysis TAG=... REF=... GFF=... BED=... SAMPLESHEET=... OUT=...
cd $WD && export NXF_CONDA_CACHEDIR=$HOME/nf_conda_cache

# 1. Chạy viralrecon trong tmux (Bước 4.4)
tmux new -As viralrecon
NXF_VER=25.04.6 nextflow run nf-core/viralrecon -r 3.0.0 --input $SAMPLESHEET --platform illumina \
  --outdir $OUT --fasta $REF --gff $GFF --primer_bed $BED \
  --skip_pangolin --skip_nextclade --skip_freyja --skip_assembly --skip_variants_quast \
  -profile conda -c custom.config -ansi-log false -resume

# 2. Đánh giá chất lượng (Bước 5)
python3 qc_consensus.py "$OUT/variants/bcftools/consensus/bcftools/*.consensus.fa" <bắt_đầu_CDS> <kết_thúc_CDS> | column -t

# 3. Phân loại, chuỗi tham chiếu, cây (Bước 6-8)
conda activate phylo && cd $WD/downstream
#   gom consensus -> Nextclade/BLAST -> metadata NCBI -> tải chuỗi -> mafft -> cut_region.py -> iqtree

# 4. Vẽ cây (Bước 9)
conda activate rtree
Rscript plot_tree.R ${TAG}_cds.treefile tree_${TAG} "^${TAG}-"

# 5. Đột biến (Bước 10)
python3 summarize_variants.py $WD/$OUT/variants/bcftools/variants_long_table.csv 0.75 20 ${TAG}_mut
```

---

## Yêu cầu công cụ

| Bước | Công cụ cần cài |
|---|---|
| 01 | Python 3 + `openpyxl` |
| 02 | `ncbi-blast+` (blastn, makeblastdb), NCBI `edirect` (efetch/esearch), Internet |
| 03 | `ncbi-blast+`, Python 3 |
| 04 | Nextflow (ghim `NXF_VER`), conda hoặc Docker/Singularity (profile conda đã kiểm chứng), Internet (kéo pipeline), `tmux` trên server |
| 05 | Python 3 (script `qc_consensus.py`), IGV (xem BAM, tuỳ chọn) |
| 06-08 | Môi trường conda `phylo`: `nextclade`, `mafft`, `iqtree` (lệnh `iqtree`), `seqkit`, `entrez-direct`, `ncbi-datasets-cli` (gồm `datasets`, `dataformat`), `snp-dists`; Python 3; `minimap2` và `samtools` nếu kiểm tra đồng nhiễm |
| 09 | Môi trường conda `rtree`: `r-base`, `r-ggplot2`, `bioconductor-ggtree`, `r-ape`, `r-phangorn`, `r-ragg`; FigTree hoặc iTOL và Inkscape/GIMP/Fiji trên máy client (tuỳ chọn) |
| 10 | Python 3 (script `summarize_variants.py`); Excel hoặc R để vẽ ma trận đột biến (tuỳ chọn) |
