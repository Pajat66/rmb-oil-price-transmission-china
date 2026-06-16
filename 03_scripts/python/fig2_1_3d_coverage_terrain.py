import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from plos_figure_export import save_plos_figure

# =========================
# Figure 2-1: optimized 3D terrain chart for major-variable sample coverage
# =========================

ROOT = Path(r"D:\Anew_file\统计建模\Mainfiles")
OUT_DIR = ROOT / "04_results" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

def pick_first(paths):
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError("未找到长样本文件，请检查路径。")

DATA_FILE = pick_first([
    ROOT / "04_results" / "chapter2" / "master_long_clean_v1.xlsx",
    ROOT / "02_clean" / "monthly_master" / "master_monthly_long_1998_2026.xlsx",
    ROOT / "02_clean" / "monthly_master" / "master_monthly_v1.xlsx",
])

df = pd.read_excel(DATA_FILE, engine="openpyxl")
if "month" not in df.columns:
    raise ValueError("数据中未找到 month 列。")

df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

candidate_vars = [
    "brent_usd",
    "cny_per_usd",
    "oil_rmb",
    "cpi_yoy",
    "cpi_transport_comm_yoy",
    "core_cpi_proxy_yoy",
    "ppi_yoy",
    "ppi_purchase_yoy",
    "ppi_fuel_power_yoy",
    "indust_va_yoy",
    "indust_va_cum_yoy",
]
vars_used = [v for v in candidate_vars if v in df.columns]
if len(vars_used) < 5:
    raise ValueError("可用变量过少，请检查长样本主表列名。")

# Binary coverage matrix
cover = df[vars_used].notna().astype(int).values
n_time = cover.shape[0]
n_var  = cover.shape[1]

# Improvement 1: increase layer spacing to separate variables clearly
LAYER_GAP = 0.30          # Previously 0.03; increased tenfold.
X, Y = np.meshgrid(np.arange(n_time), np.arange(n_var))
Z = cover.T.astype(float)
Z_plot = Z + (Y * LAYER_GAP)   # Baseline offset of 0.30 for each layer.

# Improvement 2: high-contrast colors; covered=green, missing=red
cmap_cover = LinearSegmentedColormap.from_list(
    "cover_map",
    ["#c0392b", "#27ae60"],   # Missing maps to red; covered maps to green.
    N=256
)
# Map colors from the original 0/1 values, independent of baseline offsets
norm_color = plt.Normalize(vmin=0, vmax=1)
facecolors  = cmap_cover(norm_color(Z))

# Canvas and subplot layout
fig = plt.figure(figsize=(18, 11), facecolor="white")
# Reserve right-side space for annotations
ax = fig.add_axes([0.03, 0.08, 0.72, 0.85], projection="3d")
ax.set_facecolor("#f8fafc")

# Main terrain surface
ax.plot_surface(
    X, Y, Z_plot,
    rstride=1, cstride=1,
    facecolors=facecolors,
    linewidth=0.0,
    antialiased=True,
    shade=True,          # Enable shading to strengthen the 3D effect.
    alpha=0.95
)

# Improvement 3: enlarge missing-value points and make them more visible
miss_y, miss_x = np.where(Z == 0)
if len(miss_x) > 0:
    ax.scatter(
        miss_x, miss_y,
        Z_plot[miss_y, miss_x] + 0.05,  # Slightly above the surface to avoid occlusion.
        color="#e74c3c",
        s=18,
        alpha=0.90,
        depthshade=True,
        zorder=5
    )

# Improvement 4: move coverage labels to a right-side 2D text box to avoid 3D occlusion
cover_rate = cover.mean(axis=0)
ax_right = fig.add_axes([0.76, 0.15, 0.22, 0.70])
ax_right.set_xlim(0, 1)
ax_right.set_ylim(-0.5, n_var - 0.5)
ax_right.axis("off")

ax_right.text(0.5, n_var - 0.1, "各变量覆盖率",
              ha="center", va="bottom", fontsize=12,
              fontweight="bold", color="#1e293b")

for j, (vname, rate) in enumerate(zip(vars_used, cover_rate)):
    bar_color = "#27ae60" if rate >= 0.95 else ("#f39c12" if rate >= 0.80 else "#e74c3c")
    # Background bar
    ax_right.barh(j, rate, height=0.55,
                  color=bar_color, alpha=0.25, left=0)
    # Full-cell border
    ax_right.barh(j, 1.0, height=0.55,
                  color="#e2e8f0", alpha=0.6, left=0, zorder=0)
    ax_right.barh(j, rate, height=0.55,
                  color=bar_color, alpha=0.75, left=0, zorder=1)
    ax_right.text(rate + 0.02, j, f"{rate:.1%}",
                  va="center", ha="left", fontsize=10, color="#1e293b")

ax_right.set_yticks(range(n_var))
ax_right.set_yticklabels(vars_used, fontsize=10)
ax_right.tick_params(left=False)

# Improvement 5: adjust the view angle and elevation for clearer layering
ax.view_init(elev=35, azim=-52)

# Axis ticks
tick_count = 8
xticks = np.linspace(0, n_time - 1, tick_count, dtype=int)
xticklabels = [df["month"].dt.strftime("%Y-%m").iloc[i] for i in xticks]
ax.set_xticks(xticks)
ax.set_xticklabels(xticklabels, rotation=28, ha="right", fontsize=9)

ax.set_yticks(np.arange(n_var))
ax.set_yticklabels(vars_used, fontsize=9.5)

# Improvement 6: align z-axis ticks with actual layer heights
z_ticks = [j * LAYER_GAP for j in range(n_var)]
z_labels = [f"L{j+1}" for j in range(n_var)]
ax.set_zticks(z_ticks)
ax.set_zticklabels(z_labels, fontsize=8)

ax.set_xlabel("月  份", labelpad=14, fontsize=12)
ax.set_ylabel("变  量", labelpad=14, fontsize=12)
ax.set_zlabel("层高（变量层）", labelpad=10, fontsize=10)

ax.set_title("图2-1  主要变量样本覆盖三维地形图",
             fontsize=18, pad=20, fontweight="bold")

# Grid styling
for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis._axinfo["grid"]["linestyle"] = ":"
    axis._axinfo["grid"]["color"]     = "#cbd5e1"
    axis._axinfo["grid"]["linewidth"] = 0.6

# Legend
legend_patches = [
    mpatches.Patch(color="#27ae60", alpha=0.85, label="非缺失（覆盖高原）"),
    mpatches.Patch(color="#c0392b", alpha=0.85, label="缺失（凹坑）"),
    mpatches.Patch(color="#e74c3c", alpha=0.90, label="缺失散点标注"),
]
ax.legend(
    handles=legend_patches,
    loc="upper left",
    bbox_to_anchor=(0.0, 0.92),
    fontsize=10,
    framealpha=0.9,
    edgecolor="#94a3b8"
)

# Bottom note
fig.text(
    0.50, 0.01,
    "注：绿色高原区域表示该月份变量有完整观测值；红色区域/散点表示缺失。"
    "各变量按时间轴分层展示，右侧条形图显示各变量的总体覆盖率。",
    ha="center", va="bottom", fontsize=10.5, color="#475569"
)

# Output
tiff_file = OUT_DIR / "fig2_1_3d_coverage_terrain_v2.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()
print("Preview PNG saved to:", tiff_file.with_suffix(".png"))
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
