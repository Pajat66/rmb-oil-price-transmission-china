"""Phase 1.5 ADF/KPSS protocol applied to transformed monthly series."""
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

from phase15_common import TABLES, write_csv
from transformation_layer import run as transform_run

CORE = ["dlog_oil_rmb", "dlog_brent", "dlog_fx", "d_cpi_inflation",
        "d_ppi_inflation", "d_ppi_purchase_inflation", "d_fuel_power_inflation"]
CUSTOMS = ["dlog_import_unit_price", "dlog_import_quantity", "dlog_import_value"]


def run(frames=None):
    frames = transform_run() if frames is None else frames
    rows = []
    for sample, df in frames.items():
        for variable in CORE + (CUSTOMS if sample == "short" else []):
            values = pd.to_numeric(df[variable].iloc[1:], errors="coerce")
            if values.isna().any() or len(values) < 36:
                raise ValueError(f"{sample}/{variable}: missing interior months or insufficient N")
            for spec in ("c", "ct"):
                for test in ("ADF", "KPSS"):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        if test == "ADF":
                            statistic, p, lag, nobs, critical = adfuller(values.to_numpy(), maxlag=12,
                                                                         regression=spec, autolag="AIC")[:5]
                            method = "AIC; maxlag=12"
                        else:
                            statistic, p, lag, critical = kpss(values.to_numpy(), regression=spec, nlags="auto")
                            nobs = len(values)
                            method = "statsmodels auto"
                    rows.append({"sample": sample, "variable": variable, "test": test,
                                 "deterministic_specification": spec, "lag_selection_method": method,
                                 "selected_lag": lag, "statistic": statistic, "p_value": p,
                                 "critical_1pct": critical.get("1%", np.nan),
                                 "critical_5pct": critical.get("5%", np.nan),
                                 "critical_10pct": critical.get("10%", np.nan), "N": nobs,
                                 "series_start": df.month.iloc[1].strftime("%Y-%m"),
                                 "series_end": df.month.iloc[-1].strftime("%Y-%m"),
                                 "conclusion": ("REJECT_UNIT_ROOT" if p < .05 else "DO_NOT_REJECT_UNIT_ROOT")
                                 if test == "ADF" else ("REJECT_STATIONARITY" if p < .05 else "DO_NOT_REJECT_STATIONARITY")})
    full = pd.DataFrame(rows)
    write_csv(full, "transformed_stationarity_full.csv")
    summary = []
    for (sample, variable), g in full.groupby(["sample", "variable"], sort=False):
        def get(test, spec):
            return g.loc[(g.test == test) & (g.deterministic_specification == spec)].iloc[0]
        ac, kc, at, kt = get("ADF", "c"), get("KPSS", "c"), get("ADF", "ct"), get("KPSS", "ct")
        clear_c = ac.p_value < .05 and kc.p_value >= .05
        clear_ct = at.p_value < .05 and kt.p_value >= .05
        summary.append({"sample": sample, "variable": variable, "N": len(frames[sample])-1,
                        "ADF_c_p": ac.p_value, "KPSS_c_p": kc.p_value,
                        "ADF_ct_p": at.p_value, "KPSS_ct_p": kt.p_value,
                        "constant_consensus": clear_c, "trend_consensus": clear_ct,
                        "stationarity_status": "CLEARED" if clear_c else "BLOCKED",
                        "trend_sensitivity": clear_c != clear_ct})
    result = pd.DataFrame(summary)
    write_csv(result, "transformed_stationarity_summary.csv")
    return result


if __name__ == "__main__":
    print(run().to_string(index=False))
