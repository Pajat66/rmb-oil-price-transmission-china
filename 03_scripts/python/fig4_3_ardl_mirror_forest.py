import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle
from plos_figure_export import save_plos_figure

# =========================
# 1. Path configuration
# =========================
ROOT = Path(r"D:\Anew_file\统计建模\Mainfiles")
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# 2. Matplotlib font configuration
# =========================
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# =========================
# 3. Data entry
# Notes:
# Left side = short-run cumulative effect, from Table 4-4; 0-3 period cumulative effect is recommended
# Right side = long-run equilibrium coefficient, from Table 4-5
#
# If table values are updated later, only edit this block.
# =========================
plot_df = pd.DataFrame({
    "变量": ["燃料动力购进价格同比", "PPI同比", "CPI同比"],

    # Short-run cumulative effect over periods 0-3
    "short_coef": [0.0697, 0.0194, 0.0000],
    "short_lower": [0.0205, 0.0042, -0.0060],
    "short_upper": [0.1189, 0.0345, 0.0061],

    # Long-run equilibrium coefficients from ARDL
    "long_coef": [0.0248, 0.0181, 0.0008],

    # Add long-run coefficient confidence intervals here if available; otherwise leave blank
    "long_lower": [np.nan, np.nan, np.nan],
    "long_upper": [np.nan, np.nan, np.nan],

    # Significance markers for display on the figure
    "short_sig": ["***", "**", ""],
    "long_sig": ["", "**", ""]
})

# For the mirror chart, short-run coefficients are shown as negative only for visual layout; actual values are unchanged
plot_df["short_plot"] = -plot_df["short_coef"]
plot_df["short_lower_plot"] = -plot_df["short_upper"]
plot_df["short_upper_plot"] = -plot_df["short_lower"]

# =========================
# 4. Color configuration
# =========================
color_map = {
    "燃料动力购进价格同比": "#0f766e",
    "PPI同比": "#1d4ed8",
    "CPI同比": "#2f855a"
}

fill_map = {
    "燃料动力购进价格同比": "#99f6e4",
    "PPI同比": "#bfdbfe",
    "CPI同比": "#bbf7d0"
}

# =========================
# 5. Plot
# =========================
fig, ax = plt.subplots(figsize=(13, 7))

y_pos = np.arange(len(plot_df))[::-1]   # Arrange entries from top to bottom.
plot_df["y"] = y_pos

# Calculate coordinate limits
max_left = abs(plot_df["short_lower_plot"]).max()
max_right = np.nanmax([
    plot_df["long_coef"].max(),
    plot_df["long_upper"].max() if plot_df["long_upper"].notna().any() else plot_df["long_coef"].max()
])

xmax = max(max_left, max_right) + 0.03
ax.set_xlim(-xmax, xmax)

# Lightly separate the left and right background regions
ax.axvspan(-xmax, 0, color="#f8fafc", alpha=0.85)
ax.axvspan(0, xmax, color="#f8fafc", alpha=0.85)

# Center vertical line
ax.axvline(0, color="gray", linewidth=1.2)

# Center label box
box_width = xmax * 0.18
for _, row in plot_df.iterrows():
    y = row["y"]
    rect = Rectangle(
        (-box_width / 2, y - 0.33),
        box_width,
        0.66,
        facecolor="#e2e8f0",
        edgecolor="white",
        linewidth=1.5,
        zorder=2
    )
    ax.add_patch(rect)
    ax.text(0, y, row["变量"], ha="center", va="center", fontsize=12, fontweight="bold", zorder=3)

# Left side: short-run cumulative effect shown as a mirror layout
for _, row in plot_df.iterrows():
    y = row["y"]
    color = color_map[row["变量"]]
    fill = fill_map[row["变量"]]

    # Confidence interval line
    ax.plot([row["short_lower_plot"], row["short_upper_plot"]], [y, y],
            color=color, linewidth=2.2, solid_capstyle="round", zorder=4)

    # Endpoint caps
    ax.plot([row["short_lower_plot"], row["short_lower_plot"]], [y - 0.07, y + 0.07],
            color=color, linewidth=1.6, zorder=4)
    ax.plot([row["short_upper_plot"], row["short_upper_plot"]], [y - 0.07, y + 0.07],
            color=color, linewidth=1.6, zorder=4)

    # Point marker
    ax.scatter(row["short_plot"], y, s=90, color=color, edgecolor="white", linewidth=1, zorder=5)

    # Value and significance label
    label_left = f"{row['short_coef']:.3f}{row['short_sig']}"
    ax.text(row["short_lower_plot"] - 0.01, y, label_left,
            ha="right", va="center", fontsize=11, color=color)

# Right side: long-run equilibrium coefficient
for _, row in plot_df.iterrows():
    y = row["y"]
    color = color_map[row["变量"]]

    if pd.notna(row["long_lower"]) and pd.notna(row["long_upper"]):
        ax.plot([row["long_lower"], row["long_upper"]], [y, y],
                color=color, linewidth=2.2, solid_capstyle="round", zorder=4)
        ax.plot([row["long_lower"], row["long_lower"]], [y - 0.07, y + 0.07],
                color=color, linewidth=1.6, zorder=4)
        ax.plot([row["long_upper"], row["long_upper"]], [y - 0.07, y + 0.07],
                color=color, linewidth=1.6, zorder=4)

    # Diamond marker
    ax.scatter(row["long_coef"], y, s=110, color=color, marker="D",
               edgecolor="white", linewidth=1, zorder=5)

    label_right = f"{row['long_coef']:.3f}{row['long_sig']}"
    ax.text(row["long_coef"] + 0.008, y, label_right,
            ha="left", va="center", fontsize=11, color=color)

# Top labels for the left and right sides
ax.text(-xmax * 0.55, len(plot_df) - 0.35, "短期累计效应（0–3期）",
        ha="center", va="bottom", fontsize=13, fontweight="bold", color="#334155")
ax.text(xmax * 0.55, len(plot_df) - 0.35, "长期均衡系数（ARDL）",
        ha="center", va="bottom", fontsize=13, fontweight="bold", color="#334155")

# X-axis labels show absolute values for easier left-right comparison
ticks = np.linspace(-round(xmax, 2), round(xmax, 2), 7)
ax.set_xticks(ticks)
ax.set_xticklabels([f"{abs(t):.2f}" for t in ticks], fontsize=11)

ax.set_yticks([])
ax.set_xlabel("系数绝对值（左侧为短期累计效应，右侧为长期均衡系数）", fontsize=12)

# Grid
ax.grid(axis="x", alpha=0.18, linestyle="--")

# Title
ax.set_title("图4-3 短期累计效应与长期均衡系数镜像比较图", fontsize=18, pad=18)

# Remove extra spines
for spine in ["top", "right", "left"]:
    ax.spines[spine].set_visible(False)

plt.tight_layout()

out_file = FIG_DIR / "fig4_3_ardl_mirror_forest.tif"
save_plos_figure(fig, out_file, dpi=300, preview_png=True)
plt.show()

print("已保存：", out_file)
