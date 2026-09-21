# ==========================================
# Figure 7-1: Sankey-style transmission chain for imported inflation in China, readability-fix version
# Main changes:
#   1. Use white or very light node backgrounds with dark text to avoid clipping and invisibility
#   2. Add a thin colored strip to policy-implication nodes instead of using dark backgrounds
#   3. Widen the canvas and add right-side margin to prevent right-column text clipping
#   4. Adjust flow-band transparency to match the light node design
# ==========================================

suppressPackageStartupMessages({
  library(ggplot2)
  library(ggalluvial)
  library(dplyr)
  library(scales)
})

base_family_use <- "sans"

# 1. Data
flow_df <- tibble::tribble(
  ~冲击来源,         ~进口成本层,    ~中上游价格层,      ~终端价格层,       ~政策含义,           ~权重, ~层级标签,
  "国际油价波动",   "原油进口单价", "燃料动力购进价格", "CPI弱滞后响应",   "加强能源价格监测",  40,   "强传导",
  "国际油价波动",   "原油进口单价", "PPI生产价格",      "CPI弱滞后响应",   "强化中上游疏导",    28,   "中强传导",
  "人民币汇率变动", "原油进口单价", "燃料动力购进价格", "CPI弱滞后响应",   "提升进口成本缓冲",  26,   "中等传导",
  "人民币汇率变动", "原油进口单价", "PPI生产价格",      "CPI弱滞后响应",   "优化汇率风险管理",  20,   "中等传导",
  "国际油价波动",   "原油进口单价", "燃料动力购进价格", "中上游先行释放",  "提高产业链韧性",    18,   "强传导",
  "人民币汇率变动", "原油进口单价", "PPI生产价格",      "中上游先行释放",  "精准终端稳价",      14,   "中等传导"
)

flow_df <- flow_df %>%
  mutate(
    冲击来源     = factor(冲击来源,     levels = c("国际油价波动", "人民币汇率变动")),
    进口成本层   = factor(进口成本层,   levels = c("原油进口单价")),
    中上游价格层 = factor(中上游价格层, levels = c("燃料动力购进价格", "PPI生产价格")),
    终端价格层   = factor(终端价格层,   levels = c("中上游先行释放", "CPI弱滞后响应")),
    政策含义     = factor(政策含义,     levels = c("加强能源价格监测", "强化中上游疏导",
                                           "提升进口成本缓冲", "优化汇率风险管理",
                                           "提高产业链韧性",   "精准终端稳价")),
    层级标签     = factor(层级标签,     levels = c("强传导", "中强传导", "中等传导"))
  )

axis_labels <- c("冲击来源", "进口成本层", "中上游价格层", "终端价格层", "政策含义")

# 2. Color palette
# Flow bands: three low-saturation colors
fill_pal <- c(
  "强传导"   = "#C2773A",   # Warm amber
  "中强传导" = "#4A7FC1",   # Steel blue
  "中等传导" = "#3A9E8F"    # Cyan green
)

# Nodes: very light warm-gray fills, thin borders, and dark text
# Columns use subtle color differences while remaining light enough for readable text
stratum_fills <- c(
  # Shock source layer: warm off-white
  "国际油价波动"     = "#FEF3E2",
  "人民币汇率变动"   = "#FEF3E2",
  # Import-cost layer: cool gray-white
  "原油进口单价"     = "#EFF6FF",
  # Midstream and upstream price layer: pale cyan-white
  "燃料动力购进价格" = "#F0FDF9",
  "PPI生产价格"      = "#F0FDF9",
  # Final-price layer: pale purple-white
  "中上游先行释放"   = "#F5F3FF",
  "CPI弱滞后响应"    = "#F5F3FF",
  # Policy implications: colored by transmission type while remaining light
  "加强能源价格监测" = "#FFF7ED",
  "强化中上游疏导"   = "#EFF6FF",
  "提升进口成本缓冲" = "#F0FDF9",
  "优化汇率风险管理" = "#F0FDF9",
  "提高产业链韧性"   = "#FFF7ED",
  "精准终端稳价"     = "#F0FDF9"
)

# Node border colors: aligned with each layer but slightly darker
stratum_colors <- c(
  "国际油价波动"     = "#D97706",
  "人民币汇率变动"   = "#D97706",
  "原油进口单价"     = "#3B82F6",
  "燃料动力购进价格" = "#0D9488",
  "PPI生产价格"      = "#0D9488",
  "中上游先行释放"   = "#7C3AED",
  "CPI弱滞后响应"    = "#7C3AED",
  "加强能源价格监测" = "#D97706",
  "强化中上游疏导"   = "#3B82F6",
  "提升进口成本缓冲" = "#0D9488",
  "优化汇率风险管理" = "#0D9488",
  "提高产业链韧性"   = "#D97706",
  "精准终端稳价"     = "#0D9488"
)

# 3. Plot
p <- ggplot(
  flow_df,
  aes(axis1 = 冲击来源,
      axis2 = 进口成本层,
      axis3 = 中上游价格层,
      axis4 = 终端价格层,
      axis5 = 政策含义,
      y     = 权重)
) +
  
  # Flow bands
  geom_alluvium(
    aes(fill = 层级标签),
    width      = 0.18,
    alpha      = 0.68,
    knot.pos   = 0.40,
    curve_type = "cubic",
    color      = "white",
    linewidth  = 0.20
  ) +
  
# Node rectangles: light fill with colored thin borders
  geom_stratum(
    aes(fill  = after_stat(stratum),
        color = after_stat(stratum)),
    width     = 0.20,
    linewidth = 0.9,
    alpha     = 0.95
  ) +
  
# Node text: dark charcoal for readability
  geom_text(
    stat       = "stratum",
    aes(label  = after_stat(stratum)),
    family     = base_family_use,
    size       = 3.6,
    fontface   = "bold",
    color      = "#1e293b",
    lineheight = 0.90
  ) +
  
  scale_x_discrete(
    limits = axis_labels,
    # Key setting: increase right-side expansion to leave space for policy-implication text
    expand = c(0.10, 0.10)
  ) +
  
  # Use a unified fill/color scale for node fills, borders, and flow-band fills
  scale_fill_manual(
    values = c(stratum_fills, fill_pal),
    breaks = names(fill_pal),
    name   = "传导强度",
    guide  = guide_legend(
      override.aes = list(alpha = 0.85, color = NA),
      nrow = 1
    )
  ) +
  scale_color_manual(
    values = c(stratum_colors,
               setNames(rep(NA, 3), names(fill_pal))),
    guide  = "none"
  ) +
  
  labs(x = NULL, y = NULL) +
  
  theme_void(base_family = base_family_use) +
  theme(
    axis.text.x = element_text(
      size   = 12,
      face   = "bold",
      color  = "#1e293b",
      margin = margin(t = 12)
    ),
    legend.position  = "bottom",
    legend.title     = element_text(size = 11, face = "bold", color = "#1e293b"),
    legend.text      = element_text(size = 10.5, color = "#374151"),
    legend.key.size  = unit(0.6, "cm"),
    legend.spacing.x = unit(0.4, "cm"),
    legend.margin    = margin(t = 16),
    # Widen the right-side margin to prevent right-column text clipping
    plot.margin     = margin(24, 60, 18, 36),
    plot.background = element_rect(fill = "white", color = NA)
  )

# 4. Resolve the repository root from this script's location and save output.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script_dir <- if (length(file_arg) > 0) {
  dirname(normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/"))
} else {
  normalizePath(getwd(), winslash = "/")
}
root    <- normalizePath(file.path(script_dir, "..", ".."), winslash = "/", mustWork = TRUE)
fig_dir <- file.path(root, "04_results", "figures")
if (!dir.exists(fig_dir)) dir.create(fig_dir, recursive = TRUE)

outfile <- file.path(fig_dir, "fig7_1_summary_alluvial_v3.png")
tiff_file <- file.path(fig_dir, "fig7_1_summary_alluvial_v3.tif")
ggsave(outfile, p, width = 16, height = 8.5, dpi = 300, bg = "white")
ggsave(tiff_file, p, width = 16, height = 8.5, dpi = 300, bg = "white", compression = "lzw")

print(p)
cat("已保存：", outfile, "\n")
