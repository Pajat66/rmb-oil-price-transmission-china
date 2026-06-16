import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.nonparametric.smoothers_lowess import lowess
from plos_figure_export import save_plos_figure

# =========================
# 1. Path configuration
# =========================
ROOT = Path(r"D:\Anew_file\统计建模\Mainfiles")
DATA_FILE = ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx"
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# 2. Matplotlib font configuration
# =========================
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# =========================
# 3. Read data
# =========================
df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

# =========================
# 4. Variable configuration
# =========================
vars_all = {
    "oil_rmb": "人民币计价油价",
    "import_crude_oil_unit_price_yuan_per_kg": "原油进口单价",
    "ppi_fuel_power_yoy": "燃料动力购进价格指数",
    "ppi_yoy": "PPI同比",
    "cpi_yoy": "CPI同比"
}

for col in vars_all.keys():
    df[col] = pd.to_numeric(df[col], errors="coerce")
    mean_ = df[col].mean()
    std_ = df[col].std()
    df[col + "_z"] = (df[col] - mean_) / std_ if std_ != 0 else np.nan

# =========================
# 5. Color configuration; warm colors for external shocks and cool colors for domestic prices
# =========================
color_map = {
    "oil_rmb": {"raw": "#f4a6a6", "smooth": "#b23a48"},
    "import_crude_oil_unit_price_yuan_per_kg": {"raw": "#f6c28b", "smooth": "#d97706"},
    "ppi_fuel_power_yoy": {"raw": "#9bd3dd", "smooth": "#0f766e"},
    "ppi_yoy": {"raw": "#a8c7fa", "smooth": "#1d4ed8"},
    "cpi_yoy": {"raw": "#b7e4c7", "smooth": "#2f855a"},
}

# =========================
# 6. Phase shading
# =========================
phase_spans = [
    ("2020-01-01", "2020-12-01", "疫情冲击"),
    ("2021-01-01", "2023-12-01", "外部冲击集中释放")
]

# =========================
# 7. Plot layout: one upper panel and three lower panels
# =========================
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 6, height_ratios=[1.2, 1], hspace=0.32, wspace=0.28)

# Upper main panel for external shocks
ax_top = fig.add_subplot(gs[0, :])

x_num = np.arange(len(df))

# Plot the two external variables
for col in ["oil_rmb", "import_crude_oil_unit_price_yuan_per_kg"]:
    y = df[col + "_z"]
    valid = y.notna()

    # Raw series line
    ax_top.plot(
        df["month"], y,
        color=color_map[col]["raw"],
        linewidth=1.4,
        alpha=0.9,
        label=vars_all[col] + "（原始）"
    )

    # LOWESS smoothed line
    if valid.sum() > 5:
        smooth = lowess(y[valid], x_num[valid], frac=0.18, return_sorted=False)
        ax_top.plot(
            df["month"][valid], smooth,
            color=color_map[col]["smooth"],
            linewidth=3,
            label=vars_all[col] + "（平滑）"
        )

# Main-panel styling
for start, end, _ in phase_spans:
    ax_top.axvspan(pd.to_datetime(start), pd.to_datetime(end), color="#94a3b8", alpha=0.10)

ax_top.axhline(0, linestyle="--", linewidth=0.9, color="gray")
ax_top.set_title("外部冲击层：人民币计价油价与原油进口单价", fontsize=15)
ax_top.set_ylabel("标准化值")
ax_top.grid(alpha=0.22, linestyle="--")
ax_top.legend(frameon=False, ncol=2, loc="upper left")
ax_top.tick_params(axis="x", rotation=40)

# Annotate phases in the main panel
for start, end, label in phase_spans:
    mid = pd.to_datetime(start) + (pd.to_datetime(end) - pd.to_datetime(start)) / 2
    ax_top.text(mid, ax_top.get_ylim()[1] * 0.9, label, ha="center", va="center", fontsize=10, color="#475569")

# Three lower panels for domestic price layers
bottom_vars = ["ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]
axes_bottom = [
    fig.add_subplot(gs[1, 0:2]),
    fig.add_subplot(gs[1, 2:4]),
    fig.add_subplot(gs[1, 4:6]),
]

for ax, col in zip(axes_bottom, bottom_vars):
    y = df[col + "_z"]
    valid = y.notna()

    # Raw series line
    ax.plot(
        df["month"], y,
        color=color_map[col]["raw"],
        linewidth=1.3,
        alpha=0.95
    )

    # LOWESS smoothed line
    if valid.sum() > 5:
        smooth = lowess(y[valid], x_num[valid], frac=0.18, return_sorted=False)
        ax.plot(
            df["month"][valid], smooth,
            color=color_map[col]["smooth"],
            linewidth=3
        )

    for start, end, _ in phase_spans:
        ax.axvspan(pd.to_datetime(start), pd.to_datetime(end), color="#94a3b8", alpha=0.10)

    ax.axhline(0, linestyle="--", linewidth=0.9, color="gray")
    ax.set_title(vars_all[col], fontsize=13)
    ax.grid(alpha=0.22, linestyle="--")
    ax.tick_params(axis="x", rotation=40)

# Main title
fig.suptitle("图3-1 核心变量时间演化与阶段特征组图", fontsize=18, y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.96])

out_file = FIG_DIR / "fig3_1_trend_group_alt.tif"
save_plos_figure(fig, out_file, dpi=300, preview_png=True)
plt.show()

print("已保存：", out_file)
