from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
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
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "xtick.color": "#222222",
    "ytick.color": "#222222",
})

df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

control_var = None
if "indust_va_cum_yoy" in df.columns:
    control_var = "indust_va_cum_yoy"
elif "indust_va_yoy" in df.columns:
    control_var = "indust_va_yoy"

need_cols = [
    "oil_rmb",
    "ppi_fuel_power_yoy",
    "ppi_yoy",
    "cpi_yoy",
]

if "oil_rmb" not in df.columns and {"brent_usd", "cny_per_usd"}.issubset(df.columns):
    df["oil_rmb"] = (
        pd.to_numeric(df["brent_usd"], errors="coerce")
        * pd.to_numeric(df["cny_per_usd"], errors="coerce")
    )

if control_var is not None:
    need_cols.append(control_var)

missing_cols = [col for col in need_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

for col in need_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

max_lag = 6
for lag in range(max_lag + 1):
    df[f"oil_rmb_lag{lag}"] = df["oil_rmb"].shift(lag)


def run_dlm(yvar):
    lag_cols = [f"oil_rmb_lag{lag}" for lag in range(max_lag + 1)]
    use_cols = [yvar] + lag_cols + ([control_var] if control_var is not None else [])
    temp = df[["month"] + use_cols].dropna().copy()

    x_cols = lag_cols.copy()
    if control_var is not None:
        x_cols.append(control_var)

    x = sm.add_constant(temp[x_cols])
    y = temp[yvar]
    model = sm.OLS(y, x).fit(cov_type="HC3")

    rows = []
    for lag in range(max_lag + 1):
        name = f"oil_rmb_lag{lag}"
        coef = model.params[name]
        se = model.bse[name]
        rows.append({
            "lag": lag,
            "coef": coef,
            "se": se,
            "lower": coef - 1.96 * se,
            "upper": coef + 1.96 * se,
        })

    return model, pd.DataFrame(rows), len(temp)


targets = [
    ("ppi_fuel_power_yoy", "Purchase price index for fuel and power"),
    ("ppi_yoy", "Producer price index"),
    ("cpi_yoy", "Consumer price index"),
]

results = {}
for yvar, yname in targets:
    model, coef_df, nobs = run_dlm(yvar)
    results[yvar] = {
        "name": yname,
        "model": model,
        "coef_df": coef_df,
        "nobs": nobs,
    }
    print("\n==========================")
    print(f"Dependent variable: {yname}")
    print(f"Observations: {nobs}")
    print(model.summary())

colors = {
    "ppi_fuel_power_yoy": "#0072B2",
    "ppi_yoy": "#D55E00",
    "cpi_yoy": "#009E73",
}
fills = {
    "ppi_fuel_power_yoy": "#A6CEE3",
    "ppi_yoy": "#FDBF6F",
    "cpi_yoy": "#B2DF8A",
}

fig, axes = plt.subplots(1, 3, figsize=(16.8, 5.8), sharey=False, facecolor="white")

for ax, (yvar, yname) in zip(axes, targets):
    coef_df = results[yvar]["coef_df"]
    ax.fill_between(
        coef_df["lag"],
        coef_df["lower"],
        coef_df["upper"],
        color=fills[yvar],
        alpha=0.38,
        label="95% confidence interval",
        linewidth=0,
    )
    ax.plot(
        coef_df["lag"],
        coef_df["coef"],
        color=colors[yvar],
        linewidth=2.4,
        marker="o",
        markersize=5.5,
        markerfacecolor="white",
        markeredgewidth=1.8,
        label="Coefficient estimate",
    )
    ax.axhline(0, color="#6F6F6F", linestyle="--", linewidth=0.9)
    ax.set_xticks(range(max_lag + 1))
    ax.set_xlabel("Lag", fontsize=11, fontweight="bold")
    ax.set_title(yname, fontsize=13, fontweight="bold", pad=10)
    ax.grid(axis="y", alpha=0.24, linestyle="--", linewidth=0.7)
    ax.tick_params(axis="both", labelsize=9)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

axes[0].set_ylabel(
    "Lag coefficient",
    fontsize=12,
    fontweight="bold",
)

handles, labels = axes[0].get_legend_handles_labels()
legend = fig.legend(
    handles,
    labels,
    loc="upper center",
    ncol=2,
    frameon=True,
    fontsize=12.5,
    handlelength=2.4,
    columnspacing=2.2,
    bbox_to_anchor=(0.5, 0.995),
)
legend.get_frame().set_edgecolor("#D0D0D0")
legend.get_frame().set_linewidth(0.8)
legend.get_frame().set_facecolor("white")
legend.get_frame().set_alpha(0.96)

title = "Distributed Lag Coefficient Paths for RMB-denominated Oil Price Shock"
if control_var is not None:
    title += f" (control: {control_var})"
else:
    title += " (without industrial value-added control)"

fig.suptitle(title, fontsize=15.5, fontweight="bold", y=1.065)
plt.tight_layout(rect=[0.02, 0, 1, 0.90])

tiff_file = FIG_DIR / "fig4_1_dlm_path_english.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
plt.show()

print(f"Preview PNG saved to: {tiff_file.with_suffix('.png')}")
print(f"PLOS TIFF saved to: {tiff_file} ({result['size_mb']:.2f} MB)")

out_table = []
for yvar, yname in targets:
    coef_df = results[yvar]["coef_df"].copy()
    coef_df["dependent_variable"] = yname
    coef_df["nobs"] = results[yvar]["nobs"]
    coef_df["control_var"] = control_var if control_var is not None else "None"
    out_table.append(coef_df)

coef_all = pd.concat(out_table, ignore_index=True)
coef_file = FIG_DIR / "fig4_1_dlm_path_coefficients_english.xlsx"
coef_all.to_excel(coef_file, index=False, engine="openpyxl")
print(f"Coefficient table saved to: {coef_file}")
