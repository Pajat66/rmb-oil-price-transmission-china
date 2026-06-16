
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import statsmodels.api as sm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from plos_figure_export import save_plos_figure

ROOT = Path(r"D:\Anew_file\统计建模\Mainfiles")
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

vars_needed = ["oil_rmb", "import_crude_oil_unit_price_yuan_per_kg", "ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]
tmp = df[["month"] + vars_needed].dropna().copy()
for v in vars_needed:
    tmp[v] = pd.to_numeric(tmp[v], errors="coerce")
    tmp[v + "_z"] = (tmp[v] - tmp[v].mean()) / tmp[v].std()

def stars(p):
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""

def fit(y, Xvars):
    X = sm.add_constant(tmp[[x + "_z" for x in Xvars]])
    yv = tmp[y + "_z"]
    return sm.OLS(yv, X).fit(cov_type="HC3")

m1 = fit("import_crude_oil_unit_price_yuan_per_kg", ["oil_rmb"])
m2 = fit("ppi_fuel_power_yoy", ["import_crude_oil_unit_price_yuan_per_kg"])
m3 = fit("ppi_yoy", ["import_crude_oil_unit_price_yuan_per_kg", "ppi_fuel_power_yoy"])
m4 = fit("cpi_yoy", ["ppi_fuel_power_yoy", "ppi_yoy"])

paths = [
    ("人民币计价油价", "原油进口单价", float(m1.params["oil_rmb_z"]), float(m1.pvalues["oil_rmb_z"])),
    ("原油进口单价", "燃料动力购进价格同比", float(m2.params["import_crude_oil_unit_price_yuan_per_kg_z"]), float(m2.pvalues["import_crude_oil_unit_price_yuan_per_kg_z"])),
    ("原油进口单价", "PPI同比", float(m3.params["import_crude_oil_unit_price_yuan_per_kg_z"]), float(m3.pvalues["import_crude_oil_unit_price_yuan_per_kg_z"])),
    ("燃料动力购进价格同比", "PPI同比", float(m3.params["ppi_fuel_power_yoy_z"]), float(m3.pvalues["ppi_fuel_power_yoy_z"])),
    ("燃料动力购进价格同比", "CPI同比", float(m4.params["ppi_fuel_power_yoy_z"]), float(m4.pvalues["ppi_fuel_power_yoy_z"])),
    ("PPI同比", "CPI同比", float(m4.params["ppi_yoy_z"]), float(m4.pvalues["ppi_yoy_z"])),
]

b1 = float(m1.params["oil_rmb_z"]); b2 = float(m2.params["import_crude_oil_unit_price_yuan_per_kg_z"])
b3 = float(m3.params["import_crude_oil_unit_price_yuan_per_kg_z"]); b4 = float(m3.params["ppi_fuel_power_yoy_z"])
b5 = float(m4.params["ppi_fuel_power_yoy_z"]); b6 = float(m4.params["ppi_yoy_z"])
indirect_total = b1*b2*b5 + b1*b3*b6 + b1*b2*b4*b6

fig, ax = plt.subplots(figsize=(13, 7.5))
ax.set_xlim(0, 12); ax.set_ylim(0, 10); ax.axis("off")

node_pos = {
    "人民币计价油价": (1.5, 5.0),
    "原油进口单价": (4.2, 5.0),
    "燃料动力购进价格同比": (7.1, 7.2),
    "PPI同比": (7.1, 3.8),
    "CPI同比": (10.1, 5.4),
}
node_color = {
    "人民币计价油价": "#fee2e2",
    "原油进口单价": "#ffedd5",
    "燃料动力购进价格同比": "#ccfbf1",
    "PPI同比": "#dbeafe",
    "CPI同比": "#dcfce7",
}
for node, (x, y) in node_pos.items():
    box = FancyBboxPatch((x-1.0, y-0.45), 2.0, 0.9, boxstyle="round,pad=0.03,rounding_size=0.08",
                         linewidth=1.6, edgecolor="#475569", facecolor=node_color[node])
    ax.add_patch(box)
    ax.text(x, y, node, ha="center", va="center", fontsize=12.5, fontweight="bold")

def add_arrow(src, dst, coef, pval, color, rad=0.0):
    x1, y1 = node_pos[src]; x2, y2 = node_pos[dst]
    lw = 1.5 + 4.5 * abs(coef)
    arr = FancyArrowPatch((x1+1.0, y1), (x2-1.0, y2), arrowstyle="-|>", mutation_scale=18,
                          linewidth=lw, color=color, alpha=0.9, connectionstyle="arc3,rad=%s" % rad)
    ax.add_patch(arr)
    mx = (x1 + x2) / 2; my = (y1 + y2) / 2 + (0.45 if y2 >= y1 else -0.45)
    ax.text(mx, my, f"{coef:.3f}{stars(pval)}", ha="center", va="center", fontsize=11,
            color=color, bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9))

add_arrow("人民币计价油价", "原油进口单价", paths[0][2], paths[0][3], "#b91c1c")
add_arrow("原油进口单价", "燃料动力购进价格同比", paths[1][2], paths[1][3], "#c2410c")
add_arrow("原油进口单价", "PPI同比", paths[2][2], paths[2][3], "#2563eb")
add_arrow("燃料动力购进价格同比", "PPI同比", paths[3][2], paths[3][3], "#0f766e", rad=-0.18)
add_arrow("燃料动力购进价格同比", "CPI同比", paths[4][2], paths[4][3], "#0f766e", rad=0.15)
add_arrow("PPI同比", "CPI同比", paths[5][2], paths[5][3], "#1d4ed8", rad=-0.15)

box = FancyBboxPatch((4.6, 8.55), 3.2, 0.8, boxstyle="round,pad=0.03,rounding_size=0.08",
                     linewidth=1.1, edgecolor="#cbd5e1", facecolor="#f8fafc")
ax.add_patch(box)
ax.text(6.2, 8.95, f"总间接效应（oil_rmb → CPI） = {indirect_total:.3f}",
        ha="center", va="center", fontsize=11.5, color="#334155")
ax.text(9.3, 1.2, "实线：直接路径\n箭头旁数值：标准化路径系数\n星号：显著性水平",
        ha="left", va="center", fontsize=11,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cbd5e1"))
ax.set_title("图6-3 输入型通胀传导关系路径分析图", fontsize=17, pad=16)
plt.tight_layout()
out = FIG_DIR / "fig6_3_path_sem_style.tif"
save_plos_figure(fig, out, dpi=300, preview_png=True)
plt.show()
print("已保存：", out)
