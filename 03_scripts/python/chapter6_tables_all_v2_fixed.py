import pandas as pd
import numpy as np
from pathlib import Path
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "04_results" / "chapter6"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def pick_first(paths):
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError("未找到可用的数据文件，请检查 chapter2 清洗结果或 monthly_master 文件夹。")


LONG_FILE = pick_first([
    ROOT / "04_results" / "chapter2" / "master_long_clean_v1.xlsx",
    ROOT / "02_clean" / "monthly_master" / "master_monthly_long_1998_2026.xlsx",
])

SHORT_FILE = pick_first([
    ROOT / "04_results" / "chapter2" / "master_short_clean_v1.xlsx",
    ROOT / "02_clean" / "monthly_master" / "master_monthly_v1_filled_full_openpyxl.xlsx",
])


def stars(p):
    """Return conventional significance stars from a p-value."""
    if p is None or not np.isfinite(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def load_df(path):
    df = pd.read_excel(path, engine="openpyxl")
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        df = df.sort_values("month").reset_index(drop=True)
    if "oil_rmb" not in df.columns and "brent_usd" in df.columns and "cny_per_usd" in df.columns:
        df["oil_rmb"] = pd.to_numeric(df["brent_usd"], errors="coerce") * pd.to_numeric(df["cny_per_usd"], errors="coerce")
    for c in df.columns:
        if c != "month":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


df_long = load_df(LONG_FILE)
df_short = load_df(SHORT_FILE)

control_var = None
if "indust_va_cum_yoy" in df_short.columns:
    control_var = "indust_va_cum_yoy"
elif "indust_va_yoy" in df_short.columns:
    control_var = "indust_va_yoy"


def dlm_result(df, yvar, xvar, lags=3, cum_horizon=3, control=None, start=None, end=None, min_obs=20):
    """
    Estimate a distributed lag model and report the cumulative effect over lag 0-cum_horizon.

    Important correction:
    - The cumulative effect, confidence interval, p-value, and significance stars are all based on
      the same linear combination of coefficients: beta_0 + ... + beta_cum_horizon.
    - The old code used the minimum p-value of individual lag coefficients for significance, which
      could create contradictions such as a 95% CI crossing zero but showing ***.
    - When lags=6 and cum_horizon=3, the model is estimated with lags 0-6, but the reported cumulative
      effect is still only beta_0 + beta_1 + beta_2 + beta_3. This keeps the table label "0-3期累计效应"
      correct.
    """
    temp = df.copy()
    if start is not None:
        temp = temp[temp["month"] >= pd.to_datetime(start)]
    if end is not None:
        temp = temp[temp["month"] <= pd.to_datetime(end)]
    if yvar not in temp.columns or xvar not in temp.columns:
        return None

    for lag in range(lags + 1):
        temp[f"{xvar}_lag{lag}"] = temp[xvar].shift(lag)

    use_cols = [yvar] + [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    if control is not None and control in temp.columns:
        use_cols.append(control)

    temp = temp[["month"] + use_cols].dropna()
    if len(temp) < min_obs:
        return None

    xcols = [f"{xvar}_lag{lag}" for lag in range(lags + 1)]
    if control is not None and control in temp.columns:
        xcols.append(control)

    X = sm.add_constant(temp[xcols])
    y = temp[yvar]
    model = sm.OLS(y, X).fit(cov_type="HC3")

    max_cum_lag = min(cum_horizon, lags)
    coef_names = [f"{xvar}_lag{lag}" for lag in range(max_cum_lag + 1)]

    cum = float(model.params[coef_names].sum())
    cov = model.cov_params().loc[coef_names, coef_names]
    var_cum = float(cov.values.sum())

    if var_cum < 0 and abs(var_cum) < 1e-12:
        var_cum = 0.0
    se = float(np.sqrt(var_cum)) if var_cum >= 0 else np.nan

    if np.isfinite(se) and se > 0:
        lower = cum - 1.96 * se
        upper = cum + 1.96 * se
        z_value = cum / se
        p_cum = float(2 * stats.norm.sf(abs(z_value)))
    else:
        lower = np.nan
        upper = np.nan
        z_value = np.nan
        p_cum = np.nan

    return {
        "cum_0_3": cum,
        "se_cum": se,
        "z_cum": z_value,
        "p_cum": p_cum,
        "lower": float(lower) if np.isfinite(lower) else np.nan,
        "upper": float(upper) if np.isfinite(upper) else np.nan,
        "sig": stars(p_cum),
        "adj_r2": float(model.rsquared_adj),
        "nobs": int(model.nobs),
        "model": model
    }


dep_vars = [
    ("ppi_fuel_power_yoy", "燃料动力购进价格同比"),
    ("ppi_yoy", "PPI同比"),
    ("cpi_yoy", "CPI同比"),
]

shock_vars = [
    ("oil_rmb", "人民币计价油价"),
    ("brent_usd", "Brent原油价格"),
    ("cny_per_usd", "人民币兑美元汇率"),
]

# Table 6-1: alternative-variable robustness checks, manuscript Table 10
rows = []
for yvar, yname in dep_vars:
    for xvar, xname in shock_vars:
        if xvar in df_short.columns and yvar in df_short.columns:
            r = dlm_result(df_short, yvar, xvar, lags=3, cum_horizon=3)
            if r is not None:
                rows.append({
                    "被解释变量": yname,
                    "冲击变量": xname,
                    "0-3期累计效应": round(r["cum_0_3"], 4),
                    "95%CI下界": round(r["lower"], 4),
                    "95%CI上界": round(r["upper"], 4),
                    "累计效应p值": round(r["p_cum"], 4),
                    "显著性": r["sig"],
                    "调整后R2": round(r["adj_r2"], 4),
                    "样本量N": r["nobs"]
                })
table6_1 = pd.DataFrame(rows)

# Table 6-2: alternative-model robustness checks
rows = []
for yvar, yname in dep_vars:
    runs = [
        ("基准DLM(0-6期)", dlm_result(df_short, yvar, "oil_rmb", lags=6, cum_horizon=3)),
        ("缩短滞后DLM(0-3期)", dlm_result(df_short, yvar, "oil_rmb", lags=3, cum_horizon=3)),
        ("加入控制变量DLM(0-6期)", dlm_result(df_short, yvar, "oil_rmb", lags=6, cum_horizon=3, control=control_var)),
    ]
    for label, r in runs:
        if r is not None:
            rows.append({
                "被解释变量": yname,
                "模型设定": label,
                "0-3期累计效应": round(r["cum_0_3"], 4),
                "95%CI下界": round(r["lower"], 4),
                "95%CI上界": round(r["upper"], 4),
                "累计效应p值": round(r["p_cum"], 4),
                "显著性": r["sig"],
                "调整后R2": round(r["adj_r2"], 4),
                "样本量N": r["nobs"],
                "控制变量": control_var if ("控制变量" in label and control_var) else "无"
            })
table6_2 = pd.DataFrame(rows)

# Table 6-3: phase heterogeneity; relaxed minimum sample threshold to avoid empty pandemic-period cells
phases = [
    ("2015-01-01", "2019-12-31", "平稳期"),
    ("2020-01-01", "2020-12-31", "疫情冲击期"),
    ("2021-01-01", "2023-12-31", "冲击集中释放期"),
    ("2024-01-01", "2026-12-31", "高位回落期"),
]
rows = []
for yvar, yname in dep_vars:
    for start, end, pname in phases:
        r = dlm_result(df_short, yvar, "oil_rmb", lags=3, cum_horizon=3, start=start, end=end, min_obs=8)
        if r is not None:
            rows.append({
                "被解释变量": yname,
                "阶段": pname,
                "0-3期累计效应": round(r["cum_0_3"], 4),
                "95%CI下界": round(r["lower"], 4),
                "95%CI上界": round(r["upper"], 4),
                "累计效应p值": round(r["p_cum"], 4),
                "显著性": r["sig"],
                "调整后R2": round(r["adj_r2"], 4),
                "样本量N": r["nobs"]
            })
table6_3 = pd.DataFrame(rows)

# Local projection models
def lp_responses(df, yvar, shock="oil_rmb", H=6, p=2):
    temp = df[[yvar, shock, "month"]].dropna().copy()
    if len(temp) < 30:
        return None, None

    temp[yvar + "_z"] = (temp[yvar] - temp[yvar].mean()) / temp[yvar].std()
    temp[shock + "_z"] = (temp[shock] - temp[shock].mean()) / temp[shock].std()

    rows = []
    for h in range(H + 1):
        t = temp.copy()
        t["lead_y"] = t[yvar + "_z"].shift(-h)
        xcols = [shock + "_z"]
        for lag in range(1, p + 1):
            t[f"{yvar}_lag{lag}"] = t[yvar + "_z"].shift(lag)
            t[f"{shock}_lag{lag}"] = t[shock + "_z"].shift(lag)
            xcols.extend([f"{yvar}_lag{lag}", f"{shock}_lag{lag}"])

        reg = t[["lead_y"] + xcols].dropna()
        if len(reg) < 20:
            continue

        X = sm.add_constant(reg[xcols])
        y = reg["lead_y"]
        m = sm.OLS(y, X).fit(cov_type="HC3")
        coef = float(m.params[shock + "_z"])
        se = float(m.bse[shock + "_z"])
        rows.append({
            "h": h,
            "coef": coef,
            "lower": coef - 1.96 * se,
            "upper": coef + 1.96 * se,
            "pval": float(m.pvalues[shock + "_z"])
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return None, None

    peak_idx = out["coef"].abs().idxmax()
    summary = {
        "h0响应": round(float(out.loc[out["h"] == 0, "coef"].iloc[0]) if (out["h"] == 0).any() else np.nan, 4),
        "峰值响应": round(float(out.loc[peak_idx, "coef"]), 4),
        "峰值期": int(out.loc[peak_idx, "h"]),
        "0-6期累计响应": round(float(out["coef"].sum()), 4),
        "响应方向": "正向" if out["coef"].sum() > 0 else "负向"
    }
    return out, summary


lp_full = []
summ_rows = []
for yvar, yname in dep_vars:
    full, summ = lp_responses(df_short, yvar)
    if full is not None:
        full["被解释变量"] = yname
        lp_full.append(full)
    if summ is not None:
        summ["被解释变量"] = yname
        summ_rows.append(summ)
table6_4 = pd.DataFrame(summ_rows)
lp_full_df = pd.concat(lp_full, ignore_index=True) if lp_full else pd.DataFrame()

# Path analysis with standardized variables
path_vars = ["oil_rmb", "import_crude_oil_unit_price_yuan_per_kg", "ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]
available_path_vars = [v for v in path_vars if v in df_short.columns]
tmp = df_short[["month"] + available_path_vars].dropna().copy()
for v in available_path_vars:
    std_v = tmp[v].std()
    tmp[v + "_z"] = (tmp[v] - tmp[v].mean()) / std_v if std_v != 0 else 0


def fit_std(y, Xvars):
    needed = [y] + Xvars
    missing = [v for v in needed if v not in available_path_vars]
    if missing:
        raise KeyError(f"路径分析缺少变量：{missing}")
    X = sm.add_constant(tmp[[v + "_z" for v in Xvars]])
    yy = tmp[y + "_z"]
    return sm.OLS(yy, X).fit(cov_type="HC3")


m1 = fit_std("import_crude_oil_unit_price_yuan_per_kg", ["oil_rmb"])
m2 = fit_std("ppi_fuel_power_yoy", ["import_crude_oil_unit_price_yuan_per_kg"])
m3 = fit_std("ppi_yoy", ["import_crude_oil_unit_price_yuan_per_kg", "ppi_fuel_power_yoy"])
m4 = fit_std("cpi_yoy", ["ppi_fuel_power_yoy", "ppi_yoy"])

direct_rows = []
for model, pairs in [
    (m1, [("oil_rmb_z", "人民币计价油价 → 原油进口单价")]),
    (m2, [("import_crude_oil_unit_price_yuan_per_kg_z", "原油进口单价 → 燃料动力购进价格同比")]),
    (m3, [("import_crude_oil_unit_price_yuan_per_kg_z", "原油进口单价 → PPI同比"),
          ("ppi_fuel_power_yoy_z", "燃料动力购进价格同比 → PPI同比")]),
    (m4, [("ppi_fuel_power_yoy_z", "燃料动力购进价格同比 → CPI同比"),
          ("ppi_yoy_z", "PPI同比 → CPI同比")]),
]:
    for varname, label in pairs:
        direct_rows.append({
            "路径": label,
            "标准化系数": round(float(model.params[varname]), 4),
            "p值": round(float(model.pvalues[varname]), 4),
            "显著性": stars(float(model.pvalues[varname]))
        })
table6_5a = pd.DataFrame(direct_rows)

b1 = float(m1.params["oil_rmb_z"])
b2 = float(m2.params["import_crude_oil_unit_price_yuan_per_kg_z"])
b3 = float(m3.params["import_crude_oil_unit_price_yuan_per_kg_z"])
b4 = float(m3.params["ppi_fuel_power_yoy_z"])
b5 = float(m4.params["ppi_fuel_power_yoy_z"])
b6 = float(m4.params["ppi_yoy_z"])

indirect_rows = [
    {"间接路径": "oil_rmb → import_price → fuel → cpi", "间接效应": round(b1 * b2 * b5, 5)},
    {"间接路径": "oil_rmb → import_price → ppi → cpi", "间接效应": round(b1 * b3 * b6, 5)},
    {"间接路径": "oil_rmb → import_price → fuel → ppi → cpi", "间接效应": round(b1 * b2 * b4 * b6, 5)},
]
indirect_rows.append({
    "间接路径": "总间接效应",
    "间接效应": round(sum(x["间接效应"] for x in indirect_rows), 5)
})
table6_5b = pd.DataFrame(indirect_rows)

# Variable contribution ranking with random forest
feature_candidates = [
    "oil_rmb", "brent_usd", "cny_per_usd",
    "import_crude_oil_unit_price_yuan_per_kg",
    "ppi_fuel_power_yoy", "ppi_yoy", "ppi_purchase_yoy"
]
feature_candidates = [c for c in feature_candidates if c in df_short.columns]
target_candidates = [
    ("ppi_fuel_power_yoy", "燃料动力购进价格同比"),
    ("ppi_yoy", "PPI同比"),
    ("cpi_yoy", "CPI同比"),
]
imp_rows = []
for tvar, tname in target_candidates:
    if tvar not in df_short.columns:
        continue
    usable_features = [c for c in feature_candidates if c != tvar]
    temp = df_short[[tvar] + usable_features].dropna().copy()
    if len(temp) < 30 or len(usable_features) < 2:
        continue
    X = temp[usable_features].values
    y = temp[tvar].values
    rf = RandomForestRegressor(
        n_estimators=500,
        random_state=42,
        min_samples_leaf=3
    )
    rf.fit(X, y)
    imp = rf.feature_importances_
    for feat, val in zip(usable_features, imp):
        imp_rows.append({"目标变量": tname, "解释变量": feat, "重要性": float(val)})

importance_raw = pd.DataFrame(imp_rows)
if not importance_raw.empty:
    agg = (importance_raw.groupby("解释变量", as_index=False)["重要性"]
           .mean()
           .sort_values("重要性", ascending=False)
           .reset_index(drop=True))
    agg["重要性"] = agg["重要性"].round(4)
    agg["排序"] = np.arange(1, len(agg) + 1)
    table6_6 = agg[["排序", "解释变量", "重要性"]]
else:
    table6_6 = pd.DataFrame(columns=["排序", "解释变量", "重要性"])

# Write results to a multi-sheet Excel workbook
out_file = OUT_DIR / "chapter6_tables.xlsx"
with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
    table6_1.to_excel(writer, sheet_name="表6-1 替代变量稳健性", index=False)
    table6_2.to_excel(writer, sheet_name="表6-2 替代模型稳健性", index=False)
    table6_3.to_excel(writer, sheet_name="表6-3 阶段异质性", index=False)
    table6_4.to_excel(writer, sheet_name="表6-4 LP摘要", index=False)
    lp_full_df.to_excel(writer, sheet_name="附表 LP全响应", index=False)
    table6_5a.to_excel(writer, sheet_name="表6-5A 路径直接效应", index=False)
    table6_5b.to_excel(writer, sheet_name="表6-5B 路径间接效应", index=False)
    table6_6.to_excel(writer, sheet_name="表6-6 变量贡献排序", index=False)

print("第六章表格已生成：", out_file)
