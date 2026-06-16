from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from plos_figure_export import save_plos_figure


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx"
FIG_DIR = ROOT / "04_results" / "figures_english"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Arial",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "xtick.color": "#222222",
    "ytick.color": "#222222",
})

vars_used = [
    "brent_usd",
    "cny_per_usd",
    "oil_rmb",
    "cpi_yoy",
    "ppi_yoy",
    "ppi_fuel_power_yoy",
    "import_crude_oil_unit_price_yuan_per_kg",
]

name_map = {
    "brent_usd": "Brent crude oil price",
    "cny_per_usd": "CNY/USD exchange rate",
    "oil_rmb": "RMB-denominated oil price",
    "cpi_yoy": "Consumer price index",
    "ppi_yoy": "Producer price index",
    "ppi_fuel_power_yoy": "Purchase price index for fuel and power",
    "import_crude_oil_unit_price_yuan_per_kg": "Crude oil import unit price",
}


def wrap_label(label, width=26):
    words = label.split()
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) <= width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

for col in vars_used:
    df[col] = pd.to_numeric(df[col], errors="coerce")

corr_df = df[vars_used].corr(method="pearson")
avg_abs_corr = (corr_df.abs().sum(axis=1) - 1) / (len(vars_used) - 1)
labels = [name_map[v] for v in vars_used]
wrapped_labels = [wrap_label(label, width=24) for label in labels]

bar_order = avg_abs_corr.sort_values(ascending=True)
bar_labels = [wrap_label(name_map[v], width=24) for v in bar_order.index]

cmap = LinearSegmentedColormap.from_list(
    "academic_red_blue",
    ["#3B6EA8", "#F7F7F7", "#A50026"],
    N=256,
)

fig = plt.figure(figsize=(21.5, 8.8), facecolor="white")
outer = fig.add_gridspec(
    1,
    2,
    width_ratios=[5.6, 3.25],
    wspace=0.32,
)

left = outer[0, 0].subgridspec(
    1,
    2,
    width_ratios=[5.2, 0.18],
    wspace=0.06,
)

ax_heat = fig.add_subplot(left[0, 0])
ax_cbar = fig.add_subplot(left[0, 1])
ax_bar = fig.add_subplot(outer[0, 1])

im = ax_heat.imshow(corr_df.values, cmap=cmap, vmin=-1, vmax=1, aspect="equal")

ax_heat.set_xticks(np.arange(len(labels)))
ax_heat.set_yticks(np.arange(len(labels)))
ax_heat.set_xticklabels(wrapped_labels, rotation=45, ha="right", fontsize=9)
ax_heat.set_yticklabels(wrapped_labels, fontsize=9)
ax_heat.set_title("Pearson Correlation Matrix", fontsize=14, fontweight="bold", pad=14)

ax_heat.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
ax_heat.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
ax_heat.grid(which="minor", color="white", linestyle="-", linewidth=1.0)
ax_heat.tick_params(which="minor", bottom=False, left=False)
ax_heat.tick_params(axis="both", length=0)
ax_heat.tick_params(axis="x", pad=8)

for i in range(len(labels)):
    for j in range(len(labels)):
        value = corr_df.iloc[i, j]
        text_color = "white" if abs(value) >= 0.65 else "#1A1A1A"
        ax_heat.text(
            j,
            i,
            f"{value:.2f}",
            ha="center",
            va="center",
            fontsize=8.5,
            color=text_color,
        )

cbar = fig.colorbar(im, cax=ax_cbar)
cbar.set_label("Correlation coefficient", fontsize=10, fontweight="bold", labelpad=12)
cbar.ax.tick_params(labelsize=8)
cbar.outline.set_linewidth(0.6)

y_pos = np.arange(len(bar_order))
bar_color = "#2F6F9F"
ax_bar.barh(y_pos, bar_order.values, color=bar_color, height=0.62)
ax_bar.set_yticks(y_pos)
ax_bar.set_yticklabels(bar_labels, fontsize=8.5)
ax_bar.set_xlim(0, 1)
ax_bar.set_xlabel("Mean absolute correlation", fontsize=10, fontweight="bold")
ax_bar.set_title("Average Absolute Correlation", fontsize=14, fontweight="bold", pad=14)
ax_bar.grid(axis="x", alpha=0.25, linestyle="--", linewidth=0.7)
ax_bar.set_axisbelow(True)

for i, value in enumerate(bar_order.values):
    ax_bar.text(
        min(value + 0.025, 0.97),
        i,
        f"{value:.2f}",
        va="center",
        ha="left",
        fontsize=8.5,
        color="#1A1A1A",
    )

for spine in ["top", "right"]:
    ax_bar.spines[spine].set_visible(False)

ax_bar.tick_params(axis="y", pad=8)

fig.suptitle(
    "Correlation Structure of Core Variables",
    fontsize=16,
    fontweight="bold",
    y=0.985,
)

tiff_file = FIG_DIR / "fig3_2_correlation_matrix_bar_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
