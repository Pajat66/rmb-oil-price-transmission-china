import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import statsmodels.api as sm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from plos_figure_export import save_plos_figure

# =========================
# 1. Path configuration
# =========================
ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx"
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# =========================
# 2. Read data
# =========================
df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

# Recompute oil_rmb if it is missing
if "oil_rmb" not in df.columns and "brent_usd" in df.columns and "cny_per_usd" in df.columns:
    df["oil_rmb"] = pd.to_numeric(df["brent_usd"], errors="coerce") * pd.to_numeric(df["cny_per_usd"], errors="coerce")

need_cols = [
    "oil_rmb",
    "import_crude_oil_unit_price_yuan_per_kg",
    "ppi_fuel_power_yoy",
    "ppi_yoy",
    "cpi_yoy"
]
for col in need_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# 3. Helper function: calculate the 0-3 period cumulative effect for a path
# =========================
def cumulative_effect(yvar, xvar, lags=3):
    temp = df[[yvar, xvar]].copy()
    for lag in range(lags + 1):
        temp[f"{xvar}_lag{lag}"] = temp[xvar].shift(lag)
    use_cols = [yvar] + [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    temp = temp[use_cols].dropna()

    X = temp[[f"{xvar}_lag{lag}" for lag in range(lags + 1)]]
    X = sm.add_constant(X)
    y = temp[yvar]

    model = sm.OLS(y, X).fit(cov_type="HC3")

    coef_names = [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    cum_coef = model.params[coef_names].sum()
    cov = model.cov_params().loc[coef_names, coef_names]
    cum_var = cov.values.sum()
    cum_se = np.sqrt(cum_var)
    lower = cum_coef - 1.96 * cum_se
    upper = cum_coef + 1.96 * cum_se

    # Significance classification
    pvals = model.pvalues[coef_names]
    min_p = pvals.min()
    if min_p < 0.01:
        sig = "***"
    elif min_p < 0.05:
        sig = "**"
    elif min_p < 0.10:
        sig = "*"
    else:
        sig = ""

    return {
        "coef": cum_coef,
        "lower": lower,
        "upper": upper,
        "sig": sig
    }

# =========================
# 4. Calculate path strengths across transmission links
# =========================
paths = {
    ("人民币计价油价", "原油进口单价"): cumulative_effect("import_crude_oil_unit_price_yuan_per_kg", "oil_rmb", lags=3),
    ("原油进口单价", "燃料动力购进价格同比"): cumulative_effect("ppi_fuel_power_yoy", "import_crude_oil_unit_price_yuan_per_kg", lags=3),
    ("原油进口单价", "PPI同比"): cumulative_effect("ppi_yoy", "import_crude_oil_unit_price_yuan_per_kg", lags=3),
    ("燃料动力购进价格同比", "CPI同比"): cumulative_effect("cpi_yoy", "ppi_fuel_power_yoy", lags=3),
    ("PPI同比", "CPI同比"): cumulative_effect("cpi_yoy", "ppi_yoy", lags=3),
}

# =========================
# 5. Plot
# =========================
fig, ax = plt.subplots(figsize=(14, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

node_pos = {
    "人民币计价油价": (1.5, 8.0),
    "原油进口单价": (4.2, 8.0),
    "燃料动力购进价格同比": (6.9, 9.0),
    "PPI同比": (6.9, 7.0),
    "CPI同比": (9.0, 8.0),
}

node_color = {
    "人民币计价油价": "#fee2e2",
    "原油进口单价": "#ffedd5",
    "燃料动力购进价格同比": "#ccfbf1",
    "PPI同比": "#dbeafe",
    "CPI同比": "#dcfce7",
}

edge_color = {
    ("人民币计价油价", "原油进口单价"): "#b91c1c",
    ("原油进口单价", "燃料动力购进价格同比"): "#c2410c",
    ("原油进口单价", "PPI同比"): "#2563eb",
    ("燃料动力购进价格同比", "CPI同比"): "#0f766e",
    ("PPI同比", "CPI同比"): "#1d4ed8",
}

# Nodes
for node, (x, y) in node_pos.items():
    box = FancyBboxPatch(
        (x - 0.95, y - 0.42), 1.9, 0.84,
        boxstyle="round,pad=0.03,rounding_size=0.08",
        linewidth=1.4, edgecolor="#475569", facecolor=node_color[node]
    )
    ax.add_patch(box)
    ax.text(x, y, node, ha="center", va="center", fontsize=12, fontweight="bold")

# Arrows
max_abs = max(abs(v["coef"]) for v in paths.values())

for (src, dst), info in paths.items():
    x1, y1 = node_pos[src]
    x2, y2 = node_pos[dst]

    width = 1.5 + 10 * abs(info["coef"]) / max_abs

    arrow = FancyArrowPatch(
        (x1 + 0.95, y1), (x2 - 0.95, y2),
        arrowstyle="-|>", mutation_scale=18,
        linewidth=width / 2.2,
        color=edge_color[(src, dst)],
        alpha=0.88,
        connectionstyle="arc3,rad=0.0"
    )
    ax.add_patch(arrow)

    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2 + (0.28 if y2 >= y1 else -0.28)

    label = f"{info['coef']:.3f}{info['sig']}"
    ax.text(
        mid_x, mid_y, label,
        ha="center", va="center",
        fontsize=11, color=edge_color[(src, dst)],
        bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85)
    )

ax.set_title("图5-1 输入型通胀机制传导路径图", fontsize=17, pad=18)
ax.text(
    5.0, 1.0,
    "注：箭头旁数值为0–3期累计效应，星号分别表示10%、5%、1%显著性水平。",
    ha="center", va="center", fontsize=11, color="#475569"
)

out_file = FIG_DIR / "fig5_1_mechanism_path.tif"
save_plos_figure(fig, out_file, dpi=300, preview_png=True)
plt.show()

print("已保存：", out_file)
