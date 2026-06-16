from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from plos_figure_export import save_plos_figure


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "04_results" / "figures_english"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Arial",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 10.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

horizons = np.arange(7)

data = {
    "Purchase price index for fuel and power": {
        "coef": np.array([0.0520, 0.0792, 0.0880, 0.0697, 0.0840, 0.0850, 0.0196]),
        "low": np.array([0.0050, 0.0136, 0.0200, 0.0205, 0.0080, 0.0070, 0.0027]),
        "high": np.array([0.1080, 0.1449, 0.1380, 0.1189, 0.1350, 0.1320, 0.0364]),
        "color": "#0072B2",
        "fill": "#A6CEE3",
    },
    "Producer price index": {
        "coef": np.array([0.0220, 0.0251, 0.0260, 0.0194, 0.0230, 0.0220, -0.0015]),
        "low": np.array([0.0050, 0.0057, 0.0040, 0.0042, 0.0080, 0.0070, -0.0072]),
        "high": np.array([0.0400, 0.0446, 0.0420, 0.0345, 0.0380, 0.0380, 0.0041]),
        "color": "#D55E00",
        "fill": "#FDBF6F",
    },
    "Consumer price index": {
        "coef": np.array([-0.0060, 0.0009, -0.0020, 0.0000, -0.0020, -0.0020, -0.0029]),
        "low": np.array([-0.0100, -0.0046, -0.0080, -0.0060, -0.0090, -0.0090, -0.0048]),
        "high": np.array([-0.0020, 0.0064, 0.0040, 0.0061, 0.0050, 0.0050, -0.0010]),
        "color": "#009E73",
        "fill": "#B2DF8A",
    },
}

short_name_map = {
    "Purchase price index for fuel and power": "Fuel and power\npurchase price",
    "Producer price index": "Producer\nprice index",
    "Consumer price index": "Consumer\nprice index",
}

fig, (ax_path, ax_total) = plt.subplots(
    1,
    2,
    figsize=(16.8, 6.9),
    gridspec_kw={
        "width_ratios": [3.0, 1.65],
        "wspace": 0.42,
    },
    facecolor="white",
)

for label, vals in data.items():
    ax_path.fill_between(
        horizons,
        vals["low"],
        vals["high"],
        color=vals["fill"],
        alpha=0.32,
        linewidth=0,
        label=f"{label} 95% CI",
    )
    ax_path.plot(
        horizons,
        vals["coef"],
        color=vals["color"],
        linewidth=2.5,
        marker="o",
        markersize=5.5,
        markerfacecolor="white",
        markeredgewidth=1.8,
        label=label,
    )

ax_path.axhline(0, color="#666666", linestyle="--", linewidth=0.9)
ax_path.set_xlabel("Lag horizon", fontweight="bold")
ax_path.set_ylabel("Cumulative lag effect", fontweight="bold", labelpad=10)
ax_path.set_title("Cumulative Lag Effect Paths", fontweight="bold", pad=16)
ax_path.set_xticks(horizons)
ax_path.set_ylim(-0.02, 0.16)
ax_path.grid(axis="y", alpha=0.24, linestyle="--", linewidth=0.7)

final_labels = list(data.keys())
final_values = np.array([vals["coef"][-1] for vals in data.values()])
colors = [vals["color"] for vals in data.values()]
y_pos = np.arange(len(final_labels))

ax_total.barh(
    y_pos,
    final_values,
    color=colors,
    alpha=0.92,
    height=0.55,
)

ax_total.axvline(0, color="#333333", linestyle="--", linewidth=0.9)
ax_total.set_yticks(y_pos)
ax_total.set_yticklabels(
    [short_name_map[label] for label in final_labels],
    fontsize=9,
)
ax_total.set_title("Total Cumulative Effect (lags 0–6)", fontweight="bold", pad=16)
ax_total.set_xlim(-0.012, 0.024)
ax_total.grid(axis="x", alpha=0.24, linestyle="--", linewidth=0.7)
ax_total.set_axisbelow(True)

for i, value in enumerate(final_values):
    if value >= 0:
        ax_total.text(
            value + 0.0010,
            i,
            f"{value:.4f}",
            va="center",
            ha="left",
            fontsize=9.5,
        )
    else:
        ax_total.text(
            value - 0.0010,
            i,
            f"{value:.4f}",
            va="center",
            ha="right",
            fontsize=9.5,
        )

for ax in (ax_path, ax_total):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

handles, labels = ax_path.get_legend_handles_labels()
line_handles = handles[1::2]
line_labels = labels[1::2]
fill_handles = handles[0::2]

legend = fig.legend(
    [fill_handles[0], *line_handles],
    ["95% confidence interval", *line_labels],
    loc="upper center",
    ncol=2,
    frameon=True,
    fontsize=10.5,
    handlelength=2.4,
    columnspacing=1.5,
    bbox_to_anchor=(0.5, 0.90),
)

legend.get_frame().set_edgecolor("#D0D0D0")
legend.get_frame().set_linewidth(0.8)
legend.get_frame().set_facecolor("white")
legend.get_frame().set_alpha(0.96)

fig.suptitle(
    "Cumulative Effects of RMB-denominated Oil Price Shock on Price Indices",
    fontsize=15.5,
    fontweight="bold",
    y=0.985,
)

plt.tight_layout(rect=[0.035, 0.02, 1, 0.82])

tiff_file = FIG_DIR / "fig4_2_cumulative_effect_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
print("Final cumulative effects:")
for label, value in zip(final_labels, final_values):
    print(f"- {label}: {value:.4f}")
