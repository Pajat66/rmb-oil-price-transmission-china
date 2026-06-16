from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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

df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

cols = [
    "oil_rmb",
    "ppi_fuel_power_yoy",
    "ppi_yoy",
    "cpi_yoy",
]

for col in cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

oil_mean = df["oil_rmb"].mean()
oil_std = df["oil_rmb"].std()
df["oil_rmb_z"] = (df["oil_rmb"] - oil_mean) / oil_std if oil_std != 0 else np.nan

window = 12
df["corr_oil_ppi_fuel"] = df["oil_rmb"].rolling(window).corr(df["ppi_fuel_power_yoy"])
df["corr_oil_ppi"] = df["oil_rmb"].rolling(window).corr(df["ppi_yoy"])
df["corr_oil_cpi"] = df["oil_rmb"].rolling(window).corr(df["cpi_yoy"])

series = [
    (
        "corr_oil_ppi_fuel",
        "Oil price vs. purchase price index for fuel and power",
        "#1F77B4",
    ),
    ("corr_oil_ppi", "Oil price vs. producer price index", "#D55E00"),
    ("corr_oil_cpi", "Oil price vs. consumer price index", "#009E73"),
]

fig = plt.figure(figsize=(15.8, 8.8), facecolor="white")
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 3.2], hspace=0.10)

ax_top = fig.add_subplot(gs[0, 0])
ax_main = fig.add_subplot(gs[1, 0], sharex=ax_top)

bar_colors = np.where(df["oil_rmb_z"] >= 0, "#4C78A8", "#9EC1DC")
ax_top.bar(
    df["month"],
    df["oil_rmb_z"],
    width=20,
    color=bar_colors,
    alpha=0.85,
    edgecolor="none",
)
ax_top.axhline(0, linestyle="--", linewidth=0.9, color="#777777")
ax_top.set_ylabel("Standardized\noil price", fontsize=11, fontweight="bold")
ax_top.set_title(
    "External Oil Price Shock and Rolling Correlations",
    fontsize=15,
    fontweight="bold",
    pad=10,
)
ax_top.grid(axis="y", alpha=0.22, linestyle="--", linewidth=0.7)
ax_top.tick_params(axis="x", labelbottom=False)
ax_top.tick_params(axis="y", labelsize=9)

for col, label, color in series:
    smoothed = df[col].rolling(3, center=True, min_periods=1).mean()
    ax_main.plot(
        df["month"],
        df[col],
        color=color,
        linewidth=1.0,
        alpha=0.22,
        zorder=1,
    )
    ax_main.plot(
        df["month"],
        smoothed,
        color=color,
        linewidth=2.4,
        label=label,
        zorder=2,
    )

ax_main.axhline(0, linestyle="--", linewidth=0.9, color="#777777")
ax_main.axvspan(
    pd.to_datetime("2020-01-01"),
    pd.to_datetime("2020-12-01"),
    color="#8FB3D9",
    alpha=0.10,
    linewidth=0,
)
ax_main.axvspan(
    pd.to_datetime("2021-01-01"),
    pd.to_datetime("2023-12-01"),
    color="#8FB3D9",
    alpha=0.10,
    linewidth=0,
)

ax_main.set_ylabel("12-month rolling correlation", fontsize=11, fontweight="bold")
ax_main.set_xlabel("Month", fontsize=11, fontweight="bold")
ax_main.set_ylim(-1.0, 1.05)
ax_main.grid(axis="y", alpha=0.22, linestyle="--", linewidth=0.7)
ax_main.xaxis.set_major_locator(mdates.YearLocator(2))
ax_main.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax_main.tick_params(axis="x", rotation=35, labelsize=9)
ax_main.tick_params(axis="y", labelsize=9)

legend = ax_main.legend(
    frameon=True,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.04),
    ncol=3,
    fontsize=10.5,
    handlelength=2.6,
    columnspacing=1.4,
    borderaxespad=0.2,
)
legend.get_frame().set_edgecolor("#D0D0D0")
legend.get_frame().set_linewidth(0.8)
legend.get_frame().set_facecolor("white")
legend.get_frame().set_alpha(0.95)

for ax in [ax_top, ax_main]:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

plt.subplots_adjust(top=0.92, bottom=0.12, left=0.08, right=0.98)

tiff_file = FIG_DIR / "fig3_3_rolling_correlation_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
