"""Rebuild Table 3 candidate grid, preserving the old DLM definition.

Old definition: y on an intercept, oil_rmb lags 0..p, and contemporaneous
indust_va_cum_yoy. Both varying and fixed calendar samples are reported.
"""
import numpy as np
import pandas as pd

from historical_data_adapter import REV, load_long_sample, load_short_sample
from model_core import fit_ols, lag_frame

YVARS = ["ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]
OLD_AIC = {"ppi_fuel_power_yoy": (6, 902.822), "ppi_yoy": (6, 654.469), "cpi_yoy": (6, 358.897)}
OLD_BIC = {"ppi_fuel_power_yoy": (6, 927.682), "ppi_yoy": (6, 679.328), "cpi_yoy": (0, 370.836)}


def run(df, max_lag=12):
    records = []
    summary = []
    for y in YVARS:
        common, _, common_audit = lag_frame(df, y, ["oil_rmb"], {"oil_rmb": max_lag}, ["indust_va_cum_yoy"])
        common_months = set(common.month)
        for p in range(max_lag + 1):
            varying, cols, _ = lag_frame(df, y, ["oil_rmb"], {"oil_rmb": p}, ["indust_va_cum_yoy"])
            for mode, data in (("naive_varying_sample", varying),
                               ("fixed_common_sample", varying[varying.month.isin(common_months)])):
                fit = fit_ols(data, y, cols, cov_type="nonrobust")
                n = len(data)
                k = len(fit.params)
                ll = float(fit.llf)
                # Explicit Gaussian likelihood criteria, with k regression parameters.
                records.append({"dependent_variable": y, "sample_mode": mode, "lag": p,
                                "N": n, "k": k, "RSS": float(sum(fit.resid ** 2)),
                                "log_likelihood": ll, "AIC": -2 * ll + 2 * k,
                                "BIC": -2 * ll + np.log(n) * k,
                                "HQIC": -2 * ll + 2 * np.log(np.log(n)) * k,
                                "adjusted_R2": float(fit.rsquared_adj),
                                "start": data.month.min().strftime("%Y-%m"),
                                "end": data.month.max().strftime("%Y-%m"),
                                "control": "indust_va_cum_yoy"})
        for mode in ("naive_varying_sample", "fixed_common_sample"):
            subset = [r for r in records if r["dependent_variable"] == y and r["sample_mode"] == mode]
            for criterion in ("AIC", "BIC", "HQIC"):
                winner = min(subset, key=lambda r: (r[criterion], r["lag"]))
                old = (OLD_AIC if criterion == "AIC" else OLD_BIC).get(y) if criterion != "HQIC" else None
                old_candidate = next((r for r in subset if old and r["lag"] == old[0]), None)
                summary.append({"dependent_variable": y, "sample_mode": mode, "criterion": criterion,
                                "selected_lag": winner["lag"], "N": winner["N"], "value": winner[criterion],
                                "old_manuscript_lag": old[0] if old else np.nan,
                                "old_manuscript_value": old[1] if old else np.nan,
                                "reproduced_value_at_old_lag": old_candidate[criterion] if old_candidate else np.nan,
                                "old_vs_new_abs_difference": abs(old_candidate[criterion] - old[1]) if old_candidate else np.nan,
                                "formal_comparison": mode == "fixed_common_sample"})
    full = pd.DataFrame(records)
    summ = pd.DataFrame(summary)
    full.to_csv(REV / "03_tables/table3_lag_selection_full.csv", index=False)
    summ.to_csv(REV / "03_tables/table3_lag_selection_summary.csv", index=False)
    return full, summ


if __name__ == "__main__":
    run(load_short_sample(load_long_sample()))
