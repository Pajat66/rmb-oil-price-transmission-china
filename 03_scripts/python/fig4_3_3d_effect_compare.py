from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from plos_figure_export import save_plos_figure


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "04_results" / "figures_english"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Arial",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 11,
})

plot_df = pd.DataFrame({
    "variable": [
        "Purchase price index\nfor fuel and power",
        "Producer price index",
        "Consumer price index",
    ],
    "short_coef": [0.0697, 0.0194, 0.0000],
    "short_lower": [0.0205, 0.0042, -0.0060],
    "short_upper": [0.1189, 0.0345, 0.0061],
    "long_coef": [0.0248, 0.0181, 0.0008],
    "long_lower": [0.0180, 0.0120, -0.0030],
    "long_upper": [0.0315, 0.0242, 0.0046],
    "short_sig": ["***", "**", ""],
    "long_sig": ["", "**", ""],
})

metrics = [
    ("short_coef", "Short-run cumulative effect\n(lags 0-3)"),
    ("long_coef", "Long-run equilibrium\ncoefficient (ARDL)"),
]

metric_map = {"short_coef": 0, "long_coef": 1}
colors = {"short_coef": "#D55E00", "long_coef": "#0072B2"}
text_colors = {"short_coef": "#A04700", "long_coef": "#005A8D"}

fig = plt.figure(figsize=(13.8, 8.4), facecolor="white")
ax = fig.add_subplot(111, projection="3d")

dx = 0.50
dy = 0.52

for i, row in plot_df.iterrows():
    for metric, _ in metrics:
        x = i
        y = metric_map[metric]
        value = float(row[metric])
        bar_height = max(value, 0.0008)

        ax.bar3d(
            x,
            y,
            0,
            dx,
            dy,
            bar_height,
            color=colors[metric],
            alpha=0.88,
            edgecolor="#3F3F3F",
            linewidth=0.45,
            shade=True,
        )

        lower_col = "short_lower" if metric == "short_coef" else "long_lower"
        upper_col = "short_upper" if metric == "short_coef" else "long_upper"
        sig_col = "short_sig" if metric == "short_coef" else "long_sig"
        low = float(row[lower_col])
        high = float(row[upper_col])
        cx = x + dx / 2
        cy = y + dy / 2

        ax.plot([cx, cx], [cy, cy], [low, high], color="#222222", linewidth=1.8)
        ax.plot([cx - 0.07, cx + 0.07], [cy, cy], [low, low], color="#222222", linewidth=1.1)
        ax.plot([cx - 0.07, cx + 0.07], [cy, cy], [high, high], color="#222222", linewidth=1.1)

        ax.text(
            cx,
            cy,
            max(value, high) + 0.006,
            f"{value:.3f}{row[sig_col]}",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
            color=text_colors[metric],
        )

short_xlabels = [
    "Fuel and power\npurchase price",
    "Producer\nprice index",
    "Consumer\nprice index",
]

ax.set_xticks(np.arange(len(plot_df)) + dx / 2)
ax.set_xticklabels(short_xlabels, rotation=0, ha="center", fontsize=10)
ax.tick_params(axis="x", pad=2)

ax.set_yticks([metric_map[m] + dy / 2 for m, _ in metrics])
ax.set_yticklabels([label for _, label in metrics], fontsize=11)

ax.set_zlabel("Coefficient estimate", fontsize=12, fontweight="bold", labelpad=12)
ax.set_xlabel("Price index", fontsize=12, fontweight="bold", labelpad=26)
ax.set_ylabel("Effect type", fontsize=12, fontweight="bold", labelpad=28)
ax.set_zlim(0, 0.115)

xx = np.linspace(-0.25, len(plot_df), 2)
yy = np.linspace(-0.2, 2.0, 2)
xx_grid, yy_grid = np.meshgrid(xx, yy)
zz_grid = np.zeros_like(xx_grid)
ax.plot_surface(xx_grid, yy_grid, zz_grid, color="#E8F1FA", alpha=0.20, linewidth=0)

ax.set_title(
    "Short-run Cumulative Effects and Long-run Equilibrium Coefficients",
    fontsize=17,
    fontweight="bold",
    pad=18,
)
ax.view_init(elev=26, azim=-48)

for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis._axinfo["grid"]["linestyle"] = "-"
    axis._axinfo["grid"]["linewidth"] = 0.8
    axis._axinfo["grid"]["color"] = (0.78, 0.78, 0.78, 1)

legend_handles = [
    Patch(facecolor=colors["short_coef"], edgecolor="#3F3F3F", label="Short-run effect"),
    Patch(facecolor=colors["long_coef"], edgecolor="#3F3F3F", label="Long-run coefficient"),
    Patch(facecolor="white", edgecolor="#222222", label="95% interval / uncertainty range"),
]
legend = fig.legend(
    handles=legend_handles,
    loc="center right",
    ncol=1,
    frameon=True,
    fontsize=12,
    bbox_to_anchor=(0.985, 0.64),
    borderpad=0.9,
    labelspacing=1.0,
    handlelength=1.8,
    title="Legend",
    title_fontsize=12.5,
)
legend.get_frame().set_edgecolor("#D0D0D0")
legend.get_frame().set_linewidth(0.8)
legend.get_frame().set_facecolor("white")
legend.get_frame().set_alpha(0.96)

fig.text(
    0.055,
    0.035,
    "Notes: labels above bars report coefficient estimates and significance levels.",
    ha="left",
    va="bottom",
    fontsize=10.5,
    color="#475569",
)

plt.subplots_adjust(left=0.02, right=0.80, top=0.88, bottom=0.20)

tiff_file = OUT_DIR / "fig4_3_3d_effect_compare_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
