
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import statsmodels.api as sm
from plos_figure_export import save_plos_figure

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

def pick_first(paths):
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError("未找到短样本数据文件。")

SHORT_FILE = pick_first([
    ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx",
    ROOT / "02_clean" / "monthly_master" / "master_monthly_v1_filled_full_openpyxl.xlsx",
])

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

df = pd.read_excel(SHORT_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)
if "oil_rmb" not in df.columns and "brent_usd" in df.columns and "cny_per_usd" in df.columns:
    df["oil_rmb"] = pd.to_numeric(df["brent_usd"], errors="coerce") * pd.to_numeric(df["cny_per_usd"], errors="coerce")
for c in df.columns:
    if c != "month":
        df[c] = pd.to_numeric(df[c], errors="coerce")

def stars(p):
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""

def cum_effect(temp, yvar, xvar, lags=3):
    temp = temp[[yvar, xvar, "month"]].copy()
    for lag in range(lags + 1):
        temp[f"{xvar}_lag{lag}"] = temp[xvar].shift(lag)
    use_cols = [yvar] + [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    reg = temp[use_cols].dropna()
    if len(reg) < 18:
        return None
    X = sm.add_constant(reg[[f"{xvar}_lag{lag}" for lag in range(lags + 1)]])
    y = reg[yvar]
    m = sm.OLS(y, X).fit(cov_type="HC3")
    coef_names = [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    return float(m.params[coef_names].sum()), float(m.pvalues[coef_names].min())

dep_vars = [("ppi_fuel_power_yoy", "燃料动力购进价格同比"),
            ("ppi_yoy", "PPI同比"),
            ("cpi_yoy", "CPI同比")]
phases = [
    ("2015-01-01", "2019-12-31", "平稳期"),
    ("2020-01-01", "2020-12-31", "疫情冲击期"),
    ("2021-01-01", "2023-12-31", "冲击集中释放期"),
    ("2024-01-01", "2026-12-31", "高位回落期"),
]

mat = []
ann = []
for yvar, yname in dep_vars:
    rv, ra = [], []
    for start, end, pname in phases:
        sub = df[(df["month"] >= pd.to_datetime(start)) & (df["month"] <= pd.to_datetime(end))]
        out = cum_effect(sub, yvar, "oil_rmb", 3)
        if out is None:
            rv.append(np.nan); ra.append("")
        else:
            coef, p = out
            rv.append(coef); ra.append(f"{coef:.3f}{stars(p)}")
    mat.append(rv); ann.append(ra)

mat = np.array(mat)

fig, ax = plt.subplots(figsize=(10.5, 5.8))
im = ax.imshow(mat, cmap="coolwarm", aspect="auto")
ax.set_xticks(range(len(phases))); ax.set_xticklabels([x[2] for x in phases], fontsize=11)
ax.set_yticks(range(len(dep_vars))); ax.set_yticklabels([x[1] for x in dep_vars], fontsize=11)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=11, color="black")
cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04); cbar.set_label("0–3期累计效应")
ax.set_title("图6-1 不同阶段中人民币计价油价冲击的系数热图", fontsize=17, pad=14)
ax.set_xlabel("阶段"); ax.set_ylabel("价格层级")
plt.tight_layout()
out = FIG_DIR / "fig6_1_phase_heatmap.tif"
save_plos_figure(fig, out, dpi=300, preview_png=True)
plt.show()
print("已保存：", out)
