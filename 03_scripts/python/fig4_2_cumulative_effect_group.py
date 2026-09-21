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
# Switch back to master_short_clean_v1.xlsx if required by the analysis design
# Otherwise continue using master_short_plot_ready.xlsx
DATA_FILE = ROOT / "04_results" / "chapter2" / "master_short_plot_ready.xlsx"
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# 2. Global Matplotlib style and minus-sign handling
# =========================
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Microsoft YaHei", "PingFang SC", "sans-serif"], 
    "axes.unicode_minus": False, # Ensure minus signs render correctly.
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.linewidth": 1
})

# =========================
# 3. Read data with openpyxl to avoid engine errors
# =========================
df = pd.read_excel(DATA_FILE, engine="openpyxl")
df["month"] = pd.to_datetime(df["month"], errors="coerce")
df = df.sort_values("month").reset_index(drop=True)

control_var = None
if "indust_va_cum_yoy" in df.columns:
    control_var = "indust_va_cum_yoy"
elif "indust_va_yoy" in df.columns:
    control_var = "indust_va_yoy"

if "oil_rmb" not in df.columns and "brent_usd" in df.columns:
    df["oil_rmb"] = df["brent_usd"] * df["cny_per_usd"]

need_cols = ["oil_rmb", "ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]
if control_var:
    need_cols.append(control_var)

df[need_cols] = df[need_cols].apply(pd.to_numeric, errors="coerce")

# =========================
# 4. Construct lagged variables
# =========================
max_lag = 6
for lag in range(max_lag + 1):
    df[f"oil_rmb_lag{lag}"] = df["oil_rmb"].shift(lag)

# =========================
# 5. Regression estimation and cumulative effects
# =========================
def run_dlm_and_cum(yvar):
    lag_cols = [f"oil_rmb_lag{lag}" for lag in range(max_lag + 1)]
    use_cols = [yvar] + lag_cols
    if control_var:
        use_cols.append(control_var)

    temp = df[use_cols].dropna()

    X = temp[lag_cols + ([control_var] if control_var else [])]
    X = sm.add_constant(X)
    y = temp[yvar]

    model = sm.OLS(y, X).fit(cov_type="HC3")

    coef_names = lag_cols
    horizons = list(range(0, max_lag + 1))

    rows = []
    for h in horizons:
        used = coef_names[:h+1]
        cum_coef = model.params[used].sum()

        cov = model.cov_params().loc[used, used]
        ones = np.ones(len(used))
        cum_var = ones @ cov.values @ ones   
        cum_se = np.sqrt(cum_var)

        lower = cum_coef - 1.96 * cum_se
        upper = cum_coef + 1.96 * cum_se

        rows.append({
            "horizon": h,
            "cum_coef": cum_coef,
            "lower": lower,
            "upper": upper
        })

    return pd.DataFrame(rows)

targets = [
    ("ppi_fuel_power_yoy", "燃料动力购进价格同比"),
    ("ppi_yoy", "工业生产者出厂价格指数 (PPI)"),
    ("cpi_yoy", "居民消费价格指数 (CPI)"),
]

# Store results in dictionary format
results = {y: run_dlm_and_cum(y) for y, _ in targets}

# =========================
# 6. Plot with improved spacing and annotations
# =========================
# Widen the canvas and increase wspace to avoid crowding between panels
fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(14, 5.5),
    gridspec_kw={"width_ratios": [3, 1.2], "wspace": 0.35} 
)

colors = ["#1b9e77", "#377eb8", "#4daf4a"]

# Left panel: cumulative paths
for i, (yvar, label) in enumerate(targets):
    df_plot = results[yvar]
    
    ax1.plot(df_plot["horizon"], df_plot["cum_coef"],
             color=colors[i], linewidth=2, label=label)

    ax1.fill_between(df_plot["horizon"],
                     df_plot["lower"], df_plot["upper"],
                     color=colors[i], alpha=0.15)

# Zero line
ax1.axhline(0, color="black", linestyle="--", linewidth=1)

ax1.set_xlabel("滞后期 (Horizon)")
ax1.set_ylabel("累计效应")
ax1.set_xticks([0,1,2,3,4,5,6])
ax1.set_title("滞后累计效应路径")
ax1.grid(alpha=0.2)
ax1.legend(frameon=False)
ax1.set_ylim(-0.015, 0.16)

# Right panel: total cumulative effect over periods 0-6
final_vals = []
labels = []

for yvar, label in targets:
    val = results[yvar].loc[results[yvar]["horizon"] == 6, "cum_coef"].values[0]
    final_vals.append(val)
    labels.append(label)

y_pos = np.arange(len(labels))

ax2.barh(y_pos, final_vals, color=colors, alpha=0.85)
ax2.axvline(0, color="black", linestyle="--", linewidth=1)

ax2.set_yticks(y_pos)
ax2.set_yticklabels(labels)
ax2.set_title("总累计效应 (0–6期)")

# Expand the x-axis range to leave space for negative bars and labels
ax2.set_xlim(-0.012, 0.025)

# Value labels: positive values align right, negative values align left
for i, v in enumerate(final_vals):
    offset = 0.001 
    if v >= 0:
        ax2.text(v + offset, i, f"{v:.4f}", va='center', ha='left', fontsize=10)
    else:
        ax2.text(v - offset, i, f"{v:.4f}", va='center', ha='right', fontsize=10)

ax2.grid(axis="x", alpha=0.2)

# =========================
# 7. Save output
# =========================
fig.suptitle("油价冲击的累计效应", fontsize=15)
plt.tight_layout()

tiff_file = FIG_DIR / "fig4_2_sci_style.tif"
result = save_plos_figure(fig, tiff_file, dpi=300, preview_png=True)
out_file = tiff_file
plt.show()

print("已保存：", out_file)
