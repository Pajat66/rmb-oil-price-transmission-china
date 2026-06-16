# Figure 6-1. Mantel correlation network with Pearson correlation bubbles
# Required packages: readxl, dplyr, tidyr, ggplot2, vegan, scales, stringr, grid

suppressPackageStartupMessages({
  library(readxl)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(vegan)
  library(scales)
  library(stringr)
  library(grid)
})

get_script_dir <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- "--file="
  file_idx <- grep(file_arg, cmd_args, fixed = TRUE)
  if (length(file_idx) > 0) {
    return(dirname(normalizePath(sub(file_arg, "", cmd_args[file_idx[1]], fixed = TRUE), winslash = "/")))
  }

  frames <- sys.frames()
  for (idx in rev(seq_along(frames))) {
    if (!is.null(frames[[idx]]$ofile)) {
      return(dirname(normalizePath(frames[[idx]]$ofile, winslash = "/")))
    }
  }

  normalizePath(getwd(), winslash = "/")
}

SCRIPT_DIR <- get_script_dir()
ROOT <- normalizePath(file.path(SCRIPT_DIR, "..", ".."), winslash = "/", mustWork = TRUE)
FIG_DIR <- file.path(ROOT, "04_results", "figures_english")
if (!dir.exists(FIG_DIR)) dir.create(FIG_DIR, recursive = TRUE)

pick_first <- function(paths) {
  for (path in paths) {
    if (file.exists(path)) return(path)
  }
  stop("No short-sample data file was found.")
}

short_file <- pick_first(c(
  file.path(ROOT, "04_results", "chapter2", "master_short_clean_v1.xlsx"),
  file.path(ROOT, "02_clean", "monthly_master", "master_monthly_v1_filled_full_openpyxl.xlsx")
))

df <- read_excel(short_file)

if (!"oil_rmb" %in% names(df) && all(c("brent_usd", "cny_per_usd") %in% names(df))) {
  df$oil_rmb <- as.numeric(df$brent_usd) * as.numeric(df$cny_per_usd)
}

for (nm in setdiff(names(df), "month")) {
  df[[nm]] <- suppressWarnings(as.numeric(df[[nm]]))
}

corr_vars <- c(
  "oil_rmb",
  "import_crude_oil_unit_price_yuan_per_kg",
  "ppi_fuel_power_yoy",
  "ppi_yoy",
  "cpi_yoy",
  "brent_usd",
  "cny_per_usd"
)
corr_vars <- corr_vars[corr_vars %in% names(df)]
if (length(corr_vars) < 5) stop("Fewer than five core variables are available for the Mantel figure.")

pretty_names <- c(
  oil_rmb                                  = "RMB-denominated oil price",
  import_crude_oil_unit_price_yuan_per_kg = "Crude oil import unit price",
  ppi_fuel_power_yoy                      = "Purchase price index for fuel and power",
  ppi_yoy                                 = "Producer price index",
  cpi_yoy                                 = "Consumer price index",
  brent_usd                               = "Brent crude oil price",
  cny_per_usd                             = "CNY/USD exchange rate",
  import_crude_oil_qty_10k_ton            = "Crude oil import volume",
  import_crude_oil_value_100m_rmb         = "Crude oil import value",
  ppi_purchase_yoy                        = "Purchase price index",
  indust_va_yoy                           = "Industrial value added",
  indust_va_cum_yoy                       = "Cumulative industrial value added",
  cpi_transport_comm_yoy                  = "Transport and communication CPI"
)

groups <- list(
  "External shocks" = c("brent_usd", "cny_per_usd", "oil_rmb"),
  "Import costs" = c(
    "import_crude_oil_unit_price_yuan_per_kg",
    "import_crude_oil_qty_10k_ton",
    "import_crude_oil_value_100m_rmb"
  ),
  "Upstream prices" = c("ppi_fuel_power_yoy", "ppi_purchase_yoy", "ppi_yoy"),
  "Consumer prices" = c("cpi_yoy", "cpi_transport_comm_yoy"),
  "Real activity" = c("indust_va_yoy", "indust_va_cum_yoy")
)
groups <- lapply(groups, function(x) x[x %in% names(df)])
groups <- groups[sapply(groups, length) >= 1]

cor_mat <- suppressWarnings(
  cor(df[, corr_vars], use = "pairwise.complete.obs", method = "pearson")
)
n <- length(corr_vars)

bubble_df <- expand.grid(i = seq_len(n), j = seq_len(n)) %>%
  filter(j >= i) %>%
  mutate(
    x = j,
    y = n - i + 1,
    var_i = corr_vars[i],
    var_j = corr_vars[j],
    corr = mapply(function(a, b) cor_mat[a, b], var_i, var_j),
    label = sprintf("%.2f", corr),
    text_color = ifelse(abs(corr) >= 0.72, "white", "#20242A")
  )

mantel_rows <- list()
for (gname in names(groups)) {
  gvars <- groups[[gname]]
  for (v in corr_vars) {
    use_vars <- unique(c(gvars, v))
    sub <- df[, use_vars, drop = FALSE]
    sub <- sub[complete.cases(sub), , drop = FALSE]
    if (nrow(sub) < 8) next

    gmat <- scale(as.matrix(sub[, gvars, drop = FALSE]))
    if (ncol(gmat) == 1) gmat <- matrix(gmat, ncol = 1)
    vmat <- scale(as.matrix(sub[, v, drop = FALSE]))

    mt <- suppressWarnings(vegan::mantel(dist(gmat), dist(vmat), permutations = 999))
    mantel_rows[[length(mantel_rows) + 1]] <- data.frame(
      group = gname,
      var = v,
      r = as.numeric(mt$statistic),
      p = as.numeric(mt$signif)
    )
  }
}

mantel_df <- bind_rows(mantel_rows)
if (nrow(mantel_df) == 0) stop("The Mantel tests did not return valid results.")

mantel_df <- mantel_df %>%
  mutate(
    p_cat = case_when(
      p < 0.01 ~ "p < 0.01",
      p < 0.05 ~ "0.01 <= p < 0.05",
      TRUE ~ "p >= 0.05"
    ),
    r_cat = case_when(
      abs(r) < 0.20 ~ "|r| < 0.20",
      abs(r) < 0.40 ~ "0.20 <= |r| < 0.40",
      TRUE ~ "|r| >= 0.40"
    )
  )

group_names <- names(groups)
group_pos <- data.frame(
  group = group_names,
  x = rep(-2.55, length(group_names)),
  y = seq(n - 0.7, 1.2, length.out = length(group_names))
)

diag_pos <- data.frame(
  var = corr_vars,
  x = seq_len(n),
  y = n:1
)

mantel_plot_df <- mantel_df %>%
  left_join(group_pos, by = "group") %>%
  left_join(diag_pos, by = "var", suffix = c("_g", "_d"))

top_labels <- data.frame(
  x = seq_len(n),
  y = rep(n + 0.74, n),
  label = str_wrap(unname(pretty_names[corr_vars]), width = 20)
)

right_labels <- data.frame(
  x = rep(n + 0.48, n),
  y = n:1,
  label = str_wrap(unname(pretty_names[corr_vars]), width = 28)
)

p <- ggplot() +
  geom_tile(
    data = bubble_df,
    aes(x = x, y = y),
    width = 0.94,
    height = 0.94,
    fill = "#FAFAFA",
    color = "#E5E7EB",
    linewidth = 0.28
  ) +
  geom_curve(
    data = mantel_plot_df,
    aes(x = x_g, y = y_g, xend = x_d, yend = y_d, color = p_cat, linewidth = r_cat),
    curvature = 0.14,
    alpha = 0.74,
    lineend = "round"
  ) +
  geom_point(
    data = group_pos,
    aes(x = x, y = y),
    size = 3.9,
    shape = 21,
    fill = "#111827",
    color = "white",
    stroke = 0.55
  ) +
  geom_text(
    data = group_pos,
    aes(x = x - 0.15, y = y, label = group),
    hjust = 1,
    size = 4.1,
    fontface = "bold",
    color = "#111827"
  ) +
  geom_point(
    data = diag_pos,
    aes(x = x, y = y),
    size = 2.5,
    shape = 21,
    fill = "#111827",
    color = "white",
    stroke = 0.45
  ) +
  geom_point(
    data = bubble_df,
    aes(x = x, y = y, fill = corr, size = abs(corr)),
    shape = 21,
    color = "white",
    stroke = 0.42,
    alpha = 0.96
  ) +
  geom_text(
    data = bubble_df,
    aes(x = x, y = y, label = label, color = text_color),
    size = 2.65,
    fontface = "bold",
    show.legend = FALSE
  ) +
  geom_text(
    data = top_labels,
    aes(x = x, y = y, label = label),
    angle = 43,
    hjust = 0,
    vjust = 0,
    lineheight = 0.9,
    size = 3.4,
    color = "#1F2937"
  ) +
  geom_text(
    data = right_labels,
    aes(x = x, y = y, label = label),
    hjust = 0,
    lineheight = 0.92,
    size = 3.25,
    color = "#4B5563"
  ) +
  scale_fill_gradient2(
    low = "#2F6FA9",
    mid = "#F7F7F7",
    high = "#B94132",
    midpoint = 0,
    limits = c(-1, 1),
    name = "Pearson r",
    guide = guide_colorbar(
      barheight = unit(46, "mm"),
      barwidth = unit(4.8, "mm"),
      title.position = "top",
      title.hjust = 0.5,
      frame.colour = "#D1D5DB",
      ticks.colour = "#6B7280"
    )
  ) +
  scale_size_area(max_size = 31, limits = c(0, 1), name = "|Pearson r|") +
  scale_linewidth_manual(
    values = c("|r| < 0.20" = 0.35, "0.20 <= |r| < 0.40" = 1.05, "|r| >= 0.40" = 2.25),
    name = "Mantel r"
  ) +
  scale_color_manual(
    values = c(
      "p < 0.01" = "#009E73",
      "0.01 <= p < 0.05" = "#4C78A8",
      "p >= 0.05" = "#C5CBD3",
      "white" = "white",
      "#20242A" = "#20242A"
    ),
    breaks = c("p < 0.01", "0.01 <= p < 0.05", "p >= 0.05"),
    name = "Mantel p"
  ) +
  guides(
    fill = guide_colorbar(order = 1),
    color = guide_legend(order = 2, override.aes = list(linewidth = 2.5, alpha = 0.95)),
    linewidth = guide_legend(order = 3),
    size = "none"
  ) +
  coord_fixed(
    ratio = 1,
    xlim = c(-4.45, n + 2.75),
    ylim = c(0.15, n + 1.95),
    clip = "off"
  ) +
  labs(x = NULL, y = NULL) +
  theme_void(base_family = "Arial") +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    legend.position = "right",
    legend.box = "vertical",
    legend.box.spacing = unit(4, "mm"),
    legend.title = element_text(size = 10.5, face = "bold", color = "#111827"),
    legend.text = element_text(size = 9.2, color = "#374151"),
    legend.key.height = unit(5.5, "mm"),
    legend.key.width = unit(12, "mm"),
    plot.margin = margin(28, 24, 22, 34)
  )

png_file <- file.path(FIG_DIR, "fig6_1_mantel_network_bubble_english.png")
tiff_file <- file.path(FIG_DIR, "fig6_1_mantel_network_bubble_english.tif")

ggsave(png_file, plot = p, width = 14.4, height = 8.7, dpi = 300, bg = "white")
ggsave(tiff_file, plot = p, width = 14.4, height = 8.7, dpi = 300, bg = "white", compression = "lzw")

print(p)
cat("Figure saved to:", png_file, "\n")
cat("Figure saved to:", tiff_file, "\n")
