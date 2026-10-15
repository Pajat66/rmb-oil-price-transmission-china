"""Canonical Phase 2A transformations on an intact monthly calendar."""
import numpy as np
import pandas as pd

from phase15_common import DATA, calendar_lag, load_canonical

POSITIVE = {
    "dlog_oil_rmb": "oil_rmb",
    "dlog_brent": "brent_usd",
    "dlog_fx": "cny_per_usd",
    "dlog_import_unit_price": "import_crude_oil_unit_price_yuan_per_kg",
    "dlog_import_quantity": "import_crude_oil_qty_10k_ton",
    "dlog_import_value": "import_crude_oil_value_100m_rmb",
}
INFLATION = {
    "cpi_inflation": "cpi_yoy",
    "ppi_inflation": "ppi_yoy",
    "ppi_purchase_inflation": "ppi_purchase_yoy",
    "fuel_power_inflation": "ppi_fuel_power_yoy",
}


def transform(df):
    out = df.copy()
    for name, source in POSITIVE.items():
        if source not in out:
            continue
        values = pd.to_numeric(out[source], errors="coerce")
        if (values.dropna() <= 0).any():
            raise ValueError(f"{source}: nonpositive observed value; log forbidden")
        log = pd.Series(np.log(values), index=out.index)
        out[name] = 100 * (log - calendar_lag(pd.DataFrame({"month": out.month, "log": log}), "log", 1))
    for name, source in INFLATION.items():
        values = pd.to_numeric(out[source], errors="coerce")
        out[name] = values - 100
        out[f"d_{name}"] = out[name] - calendar_lag(out, name, 1)
    return out


def run():
    result = {}
    for sample in ("long", "short"):
        frame = transform(load_canonical(sample))
        frame.to_csv(DATA / f"{sample}_sample_transformed.csv", index=False, encoding="utf-8-sig")
        result[sample] = frame
    return result


if __name__ == "__main__":
    run()
