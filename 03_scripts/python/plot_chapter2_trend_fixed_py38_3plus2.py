from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from plos_figure_export import save_plos_figure

try:
    from statsmodels.nonparametric.smoothers_lowess import lowess as sm_lowess
except ImportError:
    sm_lowess = None


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "04_results" / "chapter2"
FIG_DIR = ROOT / "04_results" / "figures_english"
FIG_DIR.mkdir(parents=True, exist_ok=True)

LONG_FILE = DATA_DIR / "master_long_plot_ready.xlsx"
SHORT_FILE = DATA_DIR / "master_short_plot_ready.xlsx"

plt.rcParams.update({
    "font.family": "Arial",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#4D4D4D",
    "axes.linewidth": 0.8,
    "xtick.color": "#222222",
    "ytick.color": "#222222",
})


def fallback_lowess(y, frac=0.2):
    """Small weighted smoother used only when statsmodels is unavailable."""
    y = np.asarray(y, dtype=float)
    x = np.arange(len(y), dtype=float)
    n = len(y)
    span = max(3, int(np.ceil(frac * n)))
    fitted = np.full(n, np.nan)

    for i in range(n):
        distances = np.abs(x - x[i])
        bandwidth = np.partition(distances, min(span, n - 1))[min(span, n - 1)]
        if bandwidth == 0:
            bandwidth = 1.0
        weights = (1 - np.clip(distances / bandwidth, 0, 1) ** 3) ** 3
        mask = weights > 0
        if mask.sum() < 2:
            fitted[i] = y[i]
            continue
        coef = np.polyfit(x[mask], y[mask], deg=1, w=weights[mask])
        fitted[i] = np.polyval(coef, x[i])
    return fitted


def smooth_lowess(y, x, frac=0.2):
    valid = y.notna()
    if valid.sum() <= 3:
        return valid, None
    if sm_lowess is not None:
        fitted = sm_lowess(y[valid], x[valid], frac=frac, return_sorted=False)
    else:
        fitted = fallback_lowess(y[valid].to_numpy(), frac=frac)
    return valid, fitted


df_short = pd.read_excel(SHORT_FILE, engine="openpyxl")
df_short["month"] = pd.to_datetime(df_short["month"])

plot_vars = [
    ("oil_rmb_z", "RMB-denominated oil price"),
    ("ppi_fuel_power_yoy_z", "Purchase price index for fuel and power"),
    ("ppi_yoy_z", "Producer price index"),
    ("cpi_yoy_z", "Consumer price index"),
    ("import_crude_oil_unit_price_yuan_per_kg_z", "Crude oil import unit price"),
]

plot_vars = [(col, title) for col, title in plot_vars if col in df_short.columns]

if len(plot_vars) != 5:
    print(
        f"Warning: expected 5 variables, found {len(plot_vars)}. "
        "The figure will use the available variables."
    )

fig = plt.figure(figsize=(15, 9), facecolor="white")
gs = GridSpec(2, 6, figure=fig)
axes = []

if len(plot_vars) >= 1:
    axes.append(fig.add_subplot(gs[0, 0:2]))
if len(plot_vars) >= 2:
    axes.append(fig.add_subplot(gs[0, 2:4]))
if len(plot_vars) >= 3:
    axes.append(fig.add_subplot(gs[0, 4:6]))
if len(plot_vars) >= 4:
    axes.append(fig.add_subplot(gs[1, 1:3]))
if len(plot_vars) >= 5:
    axes.append(fig.add_subplot(gs[1, 3:5]))

x = np.arange(len(df_short))
raw_color = "#9ecae1"
smooth_color = "#ff7f0e"

for ax, (col, title) in zip(axes, plot_vars):
    y = df_short[col]
    ax.plot(
        df_short["month"],
        y,
        color=raw_color,
        linewidth=1.2,
        alpha=0.75,
        label="Raw standardized series",
    )

    valid, lowess_fit = smooth_lowess(y, x, frac=0.2)
    if lowess_fit is not None:
        ax.plot(
            df_short.loc[valid, "month"],
            lowess_fit,
            color=smooth_color,
            linewidth=2.2,
            label="LOWESS smoothed trend",
        )

    ax.axhline(0, color="#B0B0B0", linestyle="--", linewidth=0.8, zorder=0)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=8)
    ax.set_xlabel("Time", fontsize=11, fontweight="bold")
    ax.set_ylabel("Standardized value", fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", rotation=45, labelsize=9, width=0.8)
    ax.tick_params(axis="y", labelsize=9, width=0.8)
    ax.grid(False)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles,
    labels,
    loc="upper center",
    ncol=2,
    frameon=True,
    fontsize=11,
    bbox_to_anchor=(0.5, 0.98),
)

plt.subplots_adjust(
    top=0.88,
    bottom=0.11,
    left=0.07,
    right=0.98,
    hspace=0.45,
    wspace=0.30,
)

tiff_file = FIG_DIR / "fig2_2_standardized_trend_lowess_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
