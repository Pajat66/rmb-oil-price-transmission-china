import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import statsmodels.api as sm
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
# 3. Helper function: extract period-by-period coefficients
# =========================
def lag_coefs(yvar, xvar, lags=3):
    temp = df[[yvar, xvar]].copy()
    for lag in range(lags + 1):
        temp[f"{xvar}_lag{lag}"] = temp[xvar].shift(lag)
    use_cols = [yvar] + [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    temp = temp[use_cols].dropna()

    X = temp[[f"{xvar}_lag{lag}" for lag in range(lags + 1)]]
    X = sm.add_constant(X)
    y = temp[yvar]
    model = sm.OLS(y, X).fit(cov_type="HC3")

    rows = []
    for lag in range(lags + 1):
        name = f"{xvar}_lag{lag}"
        coef = model.params[name]
        pval = model.pvalues[name]
        rows.append({"lag": lag, "coef": coef, "pval": pval})
    return pd.DataFrame(rows)

# =========================
# 4. Transmission paths
# =========================
paths = [
    ("人民币计价油价 → 原油进口单价", "import_crude_oil_unit_price_yuan_per_kg", "oil_rmb"),
    ("原油进口单价 → 燃料动力购进价格同比", "ppi_fuel_power_yoy", "import_crude_oil_unit_price_yuan_per_kg"),
    ("原油进口单价 → PPI同比", "ppi_yoy", "import_crude_oil_unit_price_yuan_per_kg"),
    ("燃料动力购进价格同比 → CPI同比", "cpi_yoy", "ppi_fuel_power_yoy"),
    ("PPI同比 → CPI同比", "cpi_yoy", "ppi_yoy"),
]

plot_data = []
for path_name, yvar, xvar in paths:
    tmp = lag_coefs(yvar, xvar, lags=3)
    tmp["path"] = path_name
    plot_data.append(tmp)

plot_df = pd.concat(plot_data, ignore_index=True)

# =========================
# 5. Plot
# =========================
fig, ax = plt.subplots(figsize=(12, 7))

path_order = [p[0] for p in paths]
lag_order = [0, 1, 2, 3]

y_map = {name: i for i, name in enumerate(path_order[::-1])}
x_map = {lag: lag for lag in lag_order}

for _, row in plot_df.iterrows():
    x = x_map[row["lag"]]
    y = y_map[row["path"]]

    size = 2000 * abs(row["coef"]) + 40
    color = "#b91c1c" if row["coef"] > 0 else "#1d4ed8"

    # Stronger significance is shown with a thicker border
    if row["pval"] < 0.01:
        lw = 2.4
    elif row["pval"] < 0.05:
        lw = 1.8
    elif row["pval"] < 0.10:
        lw = 1.2
    else:
        lw = 0.6

    ax.scatter(
        x, y, s=size, color=color, alpha=0.65,
        edgecolor="black", linewidth=lw
    )

    ax.text(x, y, f"{row['coef']:.2f}", ha="center", va="center", fontsize=9, color="black")

ax.set_xticks(range(len(lag_order)))
ax.set_xticklabels([f"lag {i}" for i in lag_order], fontsize=11)

ax.set_yticks(range(len(path_order)))
ax.set_yticklabels(path_order[::-1], fontsize=11)

ax.set_title("图5-3 机制传导各环节滞后效应气泡热图", fontsize=17, pad=18)
ax.set_xlabel("滞后期")
ax.set_ylabel("传导路径")

ax.grid(alpha=0.18, linestyle="--")

# Legend notes
ax.text(
    3.65, len(path_order)-0.2,
    "颜色：红=正向，蓝=负向\n圆点大小：|系数|\n边框粗细：显著性强弱",
    ha="left", va="top", fontsize=10,
    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cbd5e1")
)

plt.tight_layout()

out_file = FIG_DIR / "fig5_3_mechanism_bubble_heatmap.tif"
save_plos_figure(fig, out_file, dpi=300, preview_png=True)
plt.show()

print("已保存：", out_file)
