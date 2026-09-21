import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from plos_figure_export import save_plos_figure

# =========================
# 1. Path configuration
# =========================
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "04_results" / "chapter2"
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# =========================
# 2. Read data; force openpyxl for xlsx files
# =========================
df = pd.read_excel(DATA_DIR / "master_long_clean_v1.xlsx", engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")

# =========================
# 3. Key correction: recompute oil_rmb to avoid blank values from Excel formula columns
# =========================
for col in ["brent_usd", "cny_per_usd", "oil_rmb"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "brent_usd" in df.columns and "cny_per_usd" in df.columns:
    recalculated = df["brent_usd"] * df["cny_per_usd"]
    if "oil_rmb" not in df.columns:
        df["oil_rmb"] = recalculated
    else:
        df["oil_rmb"] = df["oil_rmb"].fillna(recalculated)

# =========================
# 4. Select major variables
# =========================
cols = [
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
    "indust_va_cum_yoy"
]

# Keep only columns that actually exist to avoid errors
cols = [c for c in cols if c in df.columns]

# =========================
# 5. Convert to a sample-coverage chart: 1=observed, 0=missing
# =========================
coverage_matrix = df[cols].notna().T.astype(int)

# =========================
# 6. Plot
# =========================
fig, ax = plt.subplots(figsize=(14, 6))
im = ax.imshow(coverage_matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1)

ax.set_yticks(range(len(cols)))
ax.set_yticklabels(cols, fontsize=10)

tick_idx = np.linspace(0, len(df) - 1, 8, dtype=int)
ax.set_xticks(tick_idx)
ax.set_xticklabels(df["month"].dt.strftime("%Y-%m").iloc[tick_idx], rotation=45, ha="right")

ax.set_title("图2-1 主要变量样本覆盖与缺失值分布热图", fontsize=14)
ax.set_xlabel("月份")
ax.set_ylabel("变量")

cbar = plt.colorbar(im, ax=ax)
cbar.set_label("样本覆盖（1=非缺失，0=缺失）")

plt.tight_layout()
outfile = FIG_DIR / "fig2_1_sample_coverage_heatmap_fixed.tif"
save_plos_figure(fig, outfile, dpi=300, preview_png=True)
plt.show()

print("图片已保存到：", outfile)
