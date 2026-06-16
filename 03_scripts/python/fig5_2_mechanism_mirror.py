from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from plos_figure_export import save_plos_figure


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx"
FIG_DIR = ROOT / "04_results" / "figures_english"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Arial",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 11,
})

df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

if "oil_rmb" not in df.columns and {"brent_usd", "cny_per_usd"}.issubset(df.columns):
    df["oil_rmb"] = (
        pd.to_numeric(df["brent_usd"], errors="coerce")
        * pd.to_numeric(df["cny_per_usd"], errors="coerce")
    )

need_cols = [
    "oil_rmb",
    "import_crude_oil_unit_price_yuan_per_kg",
    "ppi_fuel_power_yoy",
    "ppi_yoy",
    "cpi_yoy",
]

for col in need_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")


def run_path(yvar, xvar, lags=3):
    temp = df[[yvar, xvar]].copy()
    for lag in range(lags + 1):
        temp[f"{xvar}_lag{lag}"] = temp[xvar].shift(lag)

    lag_cols = [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    temp = temp[[yvar] + lag_cols].dropna()

    x = sm.add_constant(temp[lag_cols])
    y = temp[yvar]
    model = sm.OLS(y, x).fit(cov_type="HC3")

    cum_coef = model.params[lag_cols].sum()
    min_p = model.pvalues[lag_cols].min()
    if min_p < 0.01:
        sig = "***"
    elif min_p < 0.05:
        sig = "**"
    elif min_p < 0.10:
        sig = "*"
    else:
        sig = ""

    return {
        "cum_coef": cum_coef,
        "adj_r2": model.rsquared_adj,
        "sig": sig,
    }


paths = [
    ("M1", "RMB oil price -> crude oil import unit price", "import_crude_oil_unit_price_yuan_per_kg", "oil_rmb"),
    ("M2", "Crude oil import unit price -> purchase price index for fuel and power", "ppi_fuel_power_yoy", "import_crude_oil_unit_price_yuan_per_kg"),
    ("M3", "Crude oil import unit price -> producer price index", "ppi_yoy", "import_crude_oil_unit_price_yuan_per_kg"),
    ("M4", "Purchase price index for fuel and power -> consumer price index", "cpi_yoy", "ppi_fuel_power_yoy"),
    ("M5", "Producer price index -> consumer price index", "cpi_yoy", "ppi_yoy"),
]

rows = []
for code, path_name, yvar, xvar in paths:
    result = run_path(yvar, xvar, lags=3)
    rows.append({
        "code": code,
        "path": path_name,
        "short_effect": result["cum_coef"],
        "model_fit": result["adj_r2"],
        "sig": result["sig"],
    })

plot_df = pd.DataFrame(rows)
plot_df["short_display"] = plot_df["short_effect"].abs()
plot_df["model_fit_display"] = plot_df["model_fit"]

metrics = [
    ("short_display", "Short-run cumulative\neffect"),
    ("model_fit_display", "Model explanatory\npower"),
]
metric_map = {"short_display": 0, "model_fit_display": 1}
colors = {"short_display": "#D55E00", "model_fit_display": "#0072B2"}
text_colors = {"short_display": "#A04700", "model_fit_display": "#005A8D"}
label_boxes = {
    "short_display": dict(boxstyle="round,pad=0.22", fc="white", ec="#A04700", lw=0.9, alpha=0.94),
    "model_fit_display": dict(boxstyle="round,pad=0.22", fc="white", ec="#005A8D", lw=0.9, alpha=0.94),
}

xpos, ypos, zpos, dx, dy, dz, bar_colors = [], [], [], [], [], [], []
for i, row in plot_df.iterrows():
    for metric, _ in metrics:
        xpos.append(i)
        ypos.append(metric_map[metric])
        zpos.append(0)
        dx.append(0.55)
        dy.append(0.46)
        dz.append(float(row[metric]))
        bar_colors.append(colors[metric])

fig = plt.figure(figsize=(15.5, 8.8), facecolor="white")
ax = fig.add_subplot(111, projection="3d")

ax.bar3d(
    np.array(xpos),
    np.array(ypos),
    np.array(zpos),
    np.array(dx),
    np.array(dy),
    np.array(dz),
    color=bar_colors,
    alpha=0.88,
    shade=True,
    edgecolor="#3F3F3F",
    linewidth=0.45,
)

ax.set_xticks(np.arange(len(plot_df)) + 0.28)
ax.set_xticklabels(plot_df["code"], fontsize=11, fontweight="bold")

ax.set_yticks([0.23, 1.23])
ax.set_yticklabels([label for _, label in metrics], fontsize=11)

ax.set_zlabel("Display value", fontsize=12, fontweight="bold", labelpad=12)
ax.set_xlabel("Mechanism path", fontsize=12, fontweight="bold", labelpad=16)
ax.set_ylabel("Metric", fontsize=12, fontweight="bold", labelpad=16)
ax.set_title(
    "Stepwise Mechanism Effects in Imported Inflation Transmission",
    fontsize=17,
    fontweight="bold",
    pad=18,
)

ax.view_init(elev=23, azim=-48)
ax.set_zlim(0, max(plot_df["model_fit_display"].max(), plot_df["short_display"].max()) * 1.18)

for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis._axinfo["grid"]["linestyle"] = "-"
    axis._axinfo["grid"]["linewidth"] = 0.8
    axis._axinfo["grid"]["color"] = (0.78, 0.78, 0.78, 1)

for i, row in plot_df.iterrows():
    short_val = float(row["short_effect"])
    short_text = f"{short_val:.3f}{row['sig']}"
    ax.text(
        i + 0.28,
        0.23,
        float(row["short_display"]) + 0.06,
        short_text,
        ha="center",
        va="bottom",
        fontsize=12.5,
        fontweight="bold",
        color=text_colors["short_display"],
        bbox=label_boxes["short_display"],
    )

    fit_val = float(row["model_fit"])
    ax.text(
        i + 0.28,
        1.23,
        fit_val + 0.06,
        f"{fit_val:.3f}",
        ha="center",
        va="bottom",
        fontsize=12.5,
        fontweight="bold",
        color=text_colors["model_fit_display"],
        bbox=label_boxes["model_fit_display"],
    )

legend_handles = [
    Patch(facecolor=colors["short_display"], edgecolor="#3F3F3F", label="Short-run cumulative effect"),
    Patch(facecolor=colors["model_fit_display"], edgecolor="#3F3F3F", label="Model explanatory power"),
]
legend = fig.legend(
    handles=legend_handles,
    loc="center right",
    ncol=1,
    frameon=True,
    fontsize=12,
    bbox_to_anchor=(0.985, 0.74),
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

path_note = "\n".join([f"{row.code}: {row.path}" for row in plot_df.itertuples()])
fig.text(
    0.76,
    0.43,
    path_note,
    ha="left",
    va="top",
    fontsize=10.5,
    color="#263238",
    bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#D0D0D0", alpha=0.96),
)

fig.text(
    0.055,
    0.08,
    "Notes: short-run effects are shown by absolute height; labels report signed estimates and significance levels.",
    ha="left",
    va="bottom",
    fontsize=11,
    color="#475569",
)

plt.subplots_adjust(left=0.02, right=0.74, top=0.90, bottom=0.12)

tiff_file = FIG_DIR / "fig5_2_mechanism_3dbar_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
