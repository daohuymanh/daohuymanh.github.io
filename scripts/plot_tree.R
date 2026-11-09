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
