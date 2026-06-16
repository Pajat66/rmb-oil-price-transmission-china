from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from plos_figure_export import save_plos_figure


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "04_results" / "figures_english"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def pick_first(paths):
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("No short-sample data file was found.")


SHORT_FILE = pick_first([
    ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx",
    ROOT / "02_clean" / "monthly_master" / "master_monthly_v1_filled_full_openpyxl.xlsx",
])

plt.rcParams.update({
    "font.family": "Arial",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "xtick.color": "#222222",
    "ytick.color": "#222222",
})

df = pd.read_excel(SHORT_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

if "oil_rmb" not in df.columns and {"brent_usd", "cny_per_usd"}.issubset(df.columns):
    df["oil_rmb"] = (
        pd.to_numeric(df["brent_usd"], errors="coerce")
        * pd.to_numeric(df["cny_per_usd"], errors="coerce")
    )

for col in df.columns:
    if col != "month":
        df[col] = pd.to_numeric(df[col], errors="coerce")

targets = [
    {
        "var": "ppi_fuel_power_yoy",
        "label": "Purchase price index for fuel and power",
        "color": "#0072B2",
        "fill": "#9ECAE1",
        "linestyle": "-",
        "marker": "o",
    },
    {
        "var": "ppi_yoy",
        "label": "Producer price index",
        "color": "#D55E00",
        "fill": "#FDBE85",
        "linestyle": "--",
        "marker": "s",
    },
    {
        "var": "cpi_yoy",
        "label": "Consumer price index",
        "color": "#009E73",
        "fill": "#C7B9E8",
        "linestyle": ":",
        "marker": "^",
    },
]


def local_projection(df, yvar, shock="oil_rmb", max_horizon=6, lag_order=2):
    temp = df[[yvar, shock, "month"]].dropna().copy()
    temp[yvar + "_z"] = (temp[yvar] - temp[yvar].mean()) / temp[yvar].std()
    temp[shock + "_z"] = (temp[shock] - temp[shock].mean()) / temp[shock].std()

    rows = []
    for horizon in range(max_horizon + 1):
        t = temp.copy()
        t["lead_y"] = t[yvar + "_z"].shift(-horizon)
        x_cols = [shock + "_z"]
        for lag in range(1, lag_order + 1):
            t[f"{yvar}_lag{lag}"] = t[yvar + "_z"].shift(lag)
            t[f"{shock}_lag{lag}"] = t[shock + "_z"].shift(lag)
            x_cols.extend([f"{yvar}_lag{lag}", f"{shock}_lag{lag}"])

        reg = t[["lead_y"] + x_cols].dropna()
        if len(reg) < 20:
            continue

        x = sm.add_constant(reg[x_cols])
        y = reg["lead_y"]
        model = sm.OLS(y, x).fit(cov_type="HC3")
        coef = float(model.params[shock + "_z"])
        se = float(model.bse[shock + "_z"])
        rows.append({
            "horizon": horizon,
            "coef": coef,
            "lower": coef - 1.96 * se,
            "upper": coef + 1.96 * se,
        })

    return pd.DataFrame(rows)


fig, ax = plt.subplots(figsize=(11.8, 6.6), facecolor="white")

for item in targets:
    out = local_projection(df, item["var"], "oil_rmb", max_horizon=6, lag_order=2)
    ax.fill_between(
        out["horizon"],
        out["lower"],
        out["upper"],
        color=item["fill"],
        alpha=0.22,
        linewidth=0,
        zorder=1,
    )
    ax.plot(
        out["horizon"],
        out["lower"],
        color=item["fill"],
        alpha=0.7,
        linewidth=0.85,
        linestyle=":",
        zorder=2,
    )
    ax.plot(
        out["horizon"],
        out["upper"],
        color=item["fill"],
        alpha=0.7,
        linewidth=0.85,
        linestyle=":",
        zorder=2,
    )
    ax.plot(
        out["horizon"],
        out["coef"],
        marker=item["marker"],
        markersize=5.5,
        markerfacecolor="white",
        markeredgewidth=1.6,
        linewidth=2.4,
        linestyle=item["linestyle"],
        color=item["color"],
        label=item["label"],
        zorder=3,
    )

ax.axhline(0, color="#6F6F6F", linestyle="--", linewidth=0.9)
ax.set_xticks(range(7))
ax.set_xlabel("Forecast horizon", fontsize=11, fontweight="bold")
ax.set_ylabel("Standardized response coefficient", fontsize=11, fontweight="bold")
ax.set_title(
    "Dynamic Responses from Local Projection Models",
    fontsize=15.5,
    fontweight="bold",
    pad=14,
)
ax.grid(axis="y", alpha=0.24, linestyle="--", linewidth=0.7)
ax.tick_params(axis="both", labelsize=9)

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

legend = ax.legend(
    loc="upper right",
    frameon=True,
    fontsize=10.5,
    handlelength=3.0,
    borderpad=0.7,
    labelspacing=0.7,
)
legend.get_frame().set_edgecolor("#D0D0D0")
legend.get_frame().set_linewidth(0.8)
legend.get_frame().set_facecolor("white")
legend.get_frame().set_alpha(0.96)

plt.tight_layout()

tiff_file = FIG_DIR / "fig6_2_lp_irf_band_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")
