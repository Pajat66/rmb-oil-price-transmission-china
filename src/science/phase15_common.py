"""Phase 1.5 uses only Phase 1 canonical CSVs as data inputs."""
from pathlib import Path
import hashlib

import numpy as np
import pandas as pd

from runtime_paths import SCIENTIFIC_WORK_DIR
ROOT = Path(__file__).resolve().parents[2]
REV = SCIENTIFIC_WORK_DIR
DATA = REV / "01_data"
TABLES = REV / "03_tables"
AUDIT = REV / "00_audit"
LOGS = REV / "05_logs"
LONG_FILE = DATA / "long_sample_canonical.csv"
SHORT_FILE = DATA / "short_sample_canonical.csv"
PRICE_VARS = ["ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]
REGRESSION_VARS = ["brent_usd", "cny_per_usd", "oil_rmb", "cpi_yoy", "ppi_yoy",
                   "ppi_purchase_yoy", "ppi_fuel_power_yoy", "indust_va_yoy",
                   "indust_va_cum_yoy", "import_crude_oil_unit_price_yuan_per_kg",
                   "import_crude_oil_qty_10k_ton", "import_crude_oil_value_100m_rmb"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_canonical(sample):
    path = LONG_FILE if sample == "long" else SHORT_FILE if sample == "short" else None
    if path is None:
        raise ValueError(sample)
    df = pd.read_csv(path)
    if "month" not in df:
        raise ValueError(f"{path}: missing month")
    df.month = pd.to_datetime(df.month, errors="raise").dt.to_period("M").dt.to_timestamp()
    if df.month.isna().any() or df.month.duplicated().any():
        raise ValueError(f"{path}: invalid/duplicate month")
    df = df.sort_values("month").reset_index(drop=True)
    periods = pd.PeriodIndex(df.month, freq="M")
    expected = pd.period_range(periods.min(), periods.max(), freq="M")
    if not periods.equals(expected):
        raise ValueError(f"{path}: missing calendar month")
    return df


def calendar_lag(df, variable, lag):
    """Month-key lookup; never shift rows after dropping missing values."""
    if lag < 0:
        raise ValueError("lag must be nonnegative")
    periods = pd.PeriodIndex(df.month, freq="M")
    lookup = pd.Series(pd.to_numeric(df[variable], errors="coerce").to_numpy(), index=periods)
    if lookup.index.has_duplicates:
        raise ValueError("duplicate month before lag")
    return pd.Series(lookup.reindex(periods - lag).to_numpy(), index=df.index,
                     name=f"{variable}_lag{lag}")


def calendar_lead(df, variable, lead):
    periods = pd.PeriodIndex(df.month, freq="M")
    lookup = pd.Series(pd.to_numeric(df[variable], errors="coerce").to_numpy(), index=periods)
    return pd.Series(lookup.reindex(periods + lead).to_numpy(), index=df.index,
                     name=f"{variable}_lead{lead}")


def calendar_difference(df, variable):
    return pd.to_numeric(df[variable], errors="coerce") - calendar_lag(df, variable, 1)


def write_csv(df, name, folder=TABLES):
    path = folder / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path
