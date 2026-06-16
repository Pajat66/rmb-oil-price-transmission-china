library(tidyverse)
library(readxl)
library(ragg)
library(scales)
library(grid)

script_path <- tryCatch(normalizePath(sys.frame(1)$ofile), error = function(e) NA)
project_root <- if (!is.na(script_path)) {
  normalizePath(file.path(dirname(script_path), "..", ".."))
} else if (dir.exists("02_clean")) {
  normalizePath(".")
} else {
  normalizePath(file.path("..", ".."))
}

source_file <- file.path(
  project_root, "02_clean", "monthly_master", "master_monthly_long_1998_2026.xlsx"
)
output_dir <- file.path(project_root, "04_results", "figures_english")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

if (!exists("df", inherits = FALSE) || !inherits(df, "data.frame")) {
  df <- read_excel(source_file)
}

parse_month <- function(x) {
  if (inherits(x, "Date")) {
    return(x)
  }
  if (is.numeric(x)) {
    return(as.Date(x, origin = "1899-12-30"))
  }
  x <- as.character(x)
  as.Date(ifelse(grepl("^\\d{4}-\\d{2}$", x), paste0(x, "-01"), x))
}

df <- df %>%
  mutate(month = parse_month(month))

variable_lookup <- tibble::tribble(
  ~Variable, ~Variable_EN, ~Group,
  "brent_usd", "Brent crude oil (USD)", "International market",
  "cny_per_usd", "CNY/USD exchange rate", "International market",
  "oil_rmb", "RMB-denominated oil price", "International market",
  "cpi_yoy", "Consumer price index", "Domestic macroeconomy",
  "cpi_transport_comm_yoy", "CPI: transportation and communication", "Domestic macroeconomy",
  "core_cpi_proxy_yoy", "Core CPI proxy", "Domestic macroeconomy",
  "ppi_yoy", "Producer price index", "Price indices",
  "ppi_purchase_yoy", "Industrial purchase price index", "Price indices",
  "ppi_fuel_power_yoy", "Purchase price index for fuel and power", "Price indices",
  "indust_va_yoy", "Industrial value added", "Real economy",
  "indust_va_cum_yoy", "Cumulative industrial value added", "Real economy"
)

ordered_variables <- variable_lookup$Variable
ordered_labels <- variable_lookup$Variable_EN

df_plot <- df %>%
  select(month, all_of(ordered_variables)) %>%
  pivot_longer(cols = -month, names_to = "Variable", values_to = "Value") %>%
  left_join(variable_lookup, by = "Variable") %>%
  mutate(
    Variable_EN = factor(Variable_EN, levels = rev(ordered_labels)),
    Group = factor(
      Group,
      levels = c(
        "International market",
        "Domestic macroeconomy",
        "Price indices",
        "Real economy"
      )
    ),
    Status = if_else(is.na(Value), "Data missing", "Sample coverage")
  )

p <- ggplot(df_plot, aes(x = month, y = Variable_EN, fill = Status)) +
  facet_grid(Group ~ ., scales = "free_y", space = "free_y") +
  geom_tile(color = "white", linewidth = 0.15) +
  scale_fill_manual(
    values = c("Data missing" = "#F7DCE1", "Sample coverage" = "#355C91"),
    breaks = c("Data missing", "Sample coverage"),
    name = "Status"
  ) +
  scale_x_date(
    date_breaks = "4 years",
    date_labels = "%Y",
    expand = c(0, 0)
  ) +
  scale_y_discrete(labels = function(x) stringr::str_wrap(x, width = 34)) +
  labs(x = "Year", y = NULL) +
  theme_minimal(base_family = "Arial", base_size = 11) +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid = element_blank(),
    axis.title.x = element_text(size = 12, face = "bold", margin = margin(t = 8)),
    axis.text.x = element_text(size = 10, color = "black"),
    axis.text.y = element_text(size = 8.8, color = "black", margin = margin(r = 5)),
    axis.ticks.x = element_line(color = "black", linewidth = 0.25),
    axis.ticks.length = unit(2, "pt"),
    strip.text.y = element_text(
      angle = 0,
      size = 10,
      face = "bold",
      color = "black",
      margin = margin(l = 8)
    ),
    strip.background = element_blank(),
    legend.position = "bottom",
    legend.title = element_text(size = 11, face = "bold"),
    legend.text = element_text(size = 10),
    legend.key.size = unit(0.35, "cm"),
    panel.spacing.y = unit(0.45, "lines"),
    plot.margin = margin(12, 14, 10, 12)
  )

ggsave(
  filename = file.path(output_dir, "fig2_1_sample_coverage_english.png"),
  plot = p,
  device = ragg::agg_png,
  width = 12.5,
  height = 6.2,
  units = "in",
  dpi = 300,
  bg = "white"
)

ggsave(
  filename = file.path(output_dir, "fig2_1_sample_coverage_english.tif"),
  plot = p,
  device = ragg::agg_tiff,
  width = 12.5,
  height = 6.2,
  units = "in",
  dpi = 300,
  compression = "lzw",
  bg = "white"
)
