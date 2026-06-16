from typing import List
import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# 1. Path configuration
# =========================
ROOT = Path(r"D:\Anew_file\统计建模\Mainfiles")
DATA_DIR = ROOT / "02_clean" / "monthly_master"
OUT_DIR = ROOT / "04_results" / "chapter2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Long-sample and short-sample master files
LONG_FILE = DATA_DIR / "master_monthly_long_1998_2026.xlsx"
SHORT_FILE = DATA_DIR / "master_monthly_v1_filled_full_openpyxl.xlsx"

# =========================
# 2. Read data; always use openpyxl for xlsx files
# =========================
df_long = pd.read_excel(LONG_FILE, engine="openpyxl")
df_short = pd.read_excel(SHORT_FILE, engine="openpyxl")

# =========================
# 3. Basic cleaning function
# =========================
def clean_master(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Standardize month as datetime
    df["month"] = pd.to_datetime(df["month"], errors="coerce")

    # Sort observations
    df = df.sort_values("month").reset_index(drop=True)

    # Drop duplicate months, keeping the first record
    df = df.drop_duplicates(subset=["month"], keep="first")

    # Convert all remaining columns to numeric values
    for col in df.columns:
        if col != "month":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


df_long = clean_master(df_long)
df_short = clean_master(df_short)

# =========================
# 4. Missing-value summary
# =========================
def missing_summary(df: pd.DataFrame, name: str) -> pd.DataFrame:
    summary = pd.DataFrame({
        "variable": df.columns,
        "missing_count": df.isna().sum().values,
        "missing_ratio": (df.isna().mean().values * 100).round(2),
    })
    summary["dataset"] = name
    return summary


missing_long = missing_summary(df_long, "long")
missing_short = missing_summary(df_short, "short")
missing_all = pd.concat([missing_long, missing_short], ignore_index=True)

# =========================
# 5. Monthly continuity check
# =========================
def month_continuity_check(df: pd.DataFrame) -> pd.DataFrame:
    start = df["month"].min()
    end = df["month"].max()
    full_range = pd.date_range(start=start, end=end, freq="MS")
    missing_months = full_range.difference(df["month"])
    return pd.DataFrame({"missing_month": missing_months})


continuity_long = month_continuity_check(df_long)
continuity_short = month_continuity_check(df_short)

# =========================
# 6. IQR outlier flags; observations are flagged, not deleted
# =========================
def outlier_flag_iqr(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    result = []
    for col in cols:
        x = df[col].dropna()
        if len(x) == 0:
            continue
        q1 = x.quantile(0.25)
        q3 = x.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        flag = ((df[col] < lower) | (df[col] > upper)).astype(int)
        temp = pd.DataFrame({
            "month": df["month"],
            "variable": col,
            "outlier_flag": flag,
        })
        result.append(temp)
    if result:
        return pd.concat(result, ignore_index=True)
    return pd.DataFrame(columns=["month", "variable", "outlier_flag"])


key_cols_long = [
    "brent_usd", "cny_per_usd", "oil_rmb",
    "cpi_yoy", "ppi_yoy", "ppi_purchase_yoy",
    "ppi_fuel_power_yoy",
]

key_cols_short = [
    "brent_usd", "cny_per_usd", "oil_rmb",
    "cpi_yoy", "ppi_yoy", "ppi_purchase_yoy",
    "ppi_fuel_power_yoy",
    "import_crude_oil_qty_10k_ton",
    "import_crude_oil_value_100m_rmb",
    "import_crude_oil_unit_price_yuan_per_kg",
]

outlier_long = outlier_flag_iqr(df_long, [c for c in key_cols_long if c in df_long.columns])
outlier_short = outlier_flag_iqr(df_short, [c for c in key_cols_short if c in df_short.columns])

# =========================
# 7. Standardized copies for plotting; original values are retained
# =========================
def add_zscore(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        if col not in df.columns:
            continue
        mean_ = df[col].mean()
        std_ = df[col].std()
        if pd.notna(std_) and std_ != 0:
            df[col + "_z"] = (df[col] - mean_) / std_
        else:
            df[col + "_z"] = np.nan
    return df


plot_cols_long = [
    "oil_rmb", "cpi_yoy", "ppi_yoy", "ppi_fuel_power_yoy",
]
plot_cols_short = [
    "oil_rmb", "cpi_yoy", "ppi_yoy", "ppi_fuel_power_yoy",
    "import_crude_oil_unit_price_yuan_per_kg",
]

df_long_plot = add_zscore(df_long, plot_cols_long)
df_short_plot = add_zscore(df_short, plot_cols_short)

# =========================
# 8. Export outputs
# =========================
df_long.to_excel(OUT_DIR / "master_long_clean_v1.xlsx", index=False, engine="openpyxl")
df_short.to_excel(OUT_DIR / "master_short_clean_v1.xlsx", index=False, engine="openpyxl")

missing_all.to_excel(OUT_DIR / "missing_summary.xlsx", index=False, engine="openpyxl")
continuity_long.to_excel(OUT_DIR / "continuity_long.xlsx", index=False, engine="openpyxl")
continuity_short.to_excel(OUT_DIR / "continuity_short.xlsx", index=False, engine="openpyxl")

outlier_long.to_excel(OUT_DIR / "outlier_flag_long.xlsx", index=False, engine="openpyxl")
outlier_short.to_excel(OUT_DIR / "outlier_flag_short.xlsx", index=False, engine="openpyxl")

df_long_plot.to_excel(OUT_DIR / "master_long_plot_ready.xlsx", index=False, engine="openpyxl")
df_short_plot.to_excel(OUT_DIR / "master_short_plot_ready.xlsx", index=False, engine="openpyxl")

print("第二章预处理完成，结果已输出到：", OUT_DIR)
