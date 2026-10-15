"""Official statsmodels ADF and KPSS on intact calendar-month series.

Recurring January gaps are marked untestable, never compressed into adjacency.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

from phase15_common import (REGRESSION_VARS, TABLES, calendar_difference,
                            load_canonical, write_csv)

ALPHA = 0.05
ADF_MAX_LAG = 12
MIN_CONTIGUOUS = 36


def series_status(df, variable, transformed):
    if variable not in df:
        return None, "NOT_IN_SAMPLE", 0, 0
    series = pd.to_numeric(df[variable], errors="coerce")
    if transformed == "first_difference":
        series = calendar_difference(df, variable)
        series = series.iloc[1:]
    missing = int(series.isna().sum())
    if missing:
        run_id = series.notna().ne(series.notna().shift()).cumsum()
        max_contiguous = int(series.groupby(run_id).apply(lambda x: x.notna().sum()).max())
        return None, "UNTESTABLE_CALENDAR_GAPS", int(series.notna().sum()), max_contiguous
    if len(series) < MIN_CONTIGUOUS:
        return None, "INSUFFICIENT_CONTIGUOUS_N", len(series), len(series)
    return series.astype(float).to_numpy(), "TESTED", len(series), len(series)


def run(long_df=None, short_df=None):
    samples = {"long": load_canonical("long") if long_df is None else long_df,
               "short": load_canonical("short") if short_df is None else short_df}
    rows = []
    for sample, df in samples.items():
        for variable in REGRESSION_VARS:
            for transform in ("level", "first_difference"):
                values, status, observed_N, max_run = series_status(df, variable, transform)
                for deterministic in ("c", "ct"):
                    for test in ("ADF", "KPSS"):
                        row = {"sample": sample, "variable": variable, "transformation": transform,
                               "test": test, "deterministic_specification": deterministic,
                               "lag_selection_method": "AIC; maxlag=12" if test == "ADF" else "statsmodels auto",
                               "selected_lag": np.nan, "statistic": np.nan, "p_value": np.nan,
                               "critical_1pct": np.nan, "critical_5pct": np.nan, "critical_10pct": np.nan,
                               "N": observed_N, "max_contiguous_N": max_run, "status": status,
                               "conclusion": status}
                        if status == "TESTED":
                            if test == "ADF":
                                result = adfuller(values, maxlag=ADF_MAX_LAG, regression=deterministic, autolag="AIC")
                                statistic, pval, used_lag, nobs, critical = result[:5]
                                row.update({"selected_lag": int(used_lag), "statistic": float(statistic),
                                            "p_value": float(pval), "critical_1pct": float(critical["1%"]),
                                            "critical_5pct": float(critical["5%"]),
                                            "critical_10pct": float(critical["10%"]), "N": int(nobs),
                                            "conclusion": "REJECT_UNIT_ROOT" if pval < ALPHA else "DO_NOT_REJECT_UNIT_ROOT"})
                            else:
                                with warnings.catch_warnings():
                                    warnings.simplefilter("ignore", category=Warning)
                                    statistic, pval, used_lag, critical = kpss(values, regression=deterministic, nlags="auto")
                                row.update({"selected_lag": int(used_lag), "statistic": float(statistic),
                                            "p_value": float(pval), "critical_1pct": float(critical["1%"]) if "1%" in critical else np.nan,
                                            "critical_5pct": float(critical["5%"]),
                                            "critical_10pct": float(critical["10%"]),
                                            "conclusion": "REJECT_STATIONARITY" if pval < ALPHA else "DO_NOT_REJECT_STATIONARITY"})
                        rows.append(row)
    full = pd.DataFrame(rows)
    write_csv(full, "stationarity_full.csv")
    summary = []
    conflicts = []
    for sample in samples:
        for variable in REGRESSION_VARS:
            def pull(transform, test, deterministic="c"):
                return full[(full["sample"] == sample) & (full.variable == variable)
                            & (full.transformation == transform) & (full.test == test)
                            & (full.deterministic_specification == deterministic)].iloc[0]
            a, k = pull("level", "ADF"), pull("level", "KPSS")
            ad, kd = pull("first_difference", "ADF"), pull("first_difference", "KPSS")
            at, kt = pull("level", "ADF", "ct"), pull("level", "KPSS", "ct")
            if a.status != "TESTED":
                evidence = a.status
                conflict = ""
            else:
                adf_stationary = a.conclusion == "REJECT_UNIT_ROOT"
                kpss_stationary = k.conclusion == "DO_NOT_REJECT_STATIONARITY"
                diff_stationary = ad.status == "TESTED" and ad.conclusion == "REJECT_UNIT_ROOT" and kd.conclusion == "DO_NOT_REJECT_STATIONARITY"
                trend_stationary = at.conclusion == "REJECT_UNIT_ROOT" and kt.conclusion == "DO_NOT_REJECT_STATIONARITY"
                if adf_stationary and kpss_stationary:
                    evidence = "I(0)_LEVEL_CONSENSUS"
                elif not adf_stationary and not kpss_stationary and diff_stationary:
                    evidence = "I(1)_DIFFERENCE_CONSENSUS"
                elif not adf_stationary and not kpss_stationary:
                    evidence = "POSSIBLE_I2_OR_BREAK"
                else:
                    evidence = "BORDERLINE / MIXED EVIDENCE"
                reason = []
                if adf_stationary != kpss_stationary:
                    reason.append("ADF/KPSS constant conflict")
                if trend_stationary != (adf_stationary and kpss_stationary):
                    reason.append("constant versus trend sensitivity")
                conflict = "; ".join(reason)
                if conflict:
                    conflicts.append({"sample": sample, "variable": variable, "transformation": "level",
                                      "reason": conflict, "ADF_c_p": a.p_value, "KPSS_c_p": k.p_value,
                                      "ADF_ct_p": at.p_value, "KPSS_ct_p": kt.p_value,
                                      "integration_evidence": evidence})
            summary.append({"sample": sample, "variable": variable, "integration_evidence": evidence,
                            "ADF_c_statistic": a.statistic, "ADF_c_p": a.p_value, "ADF_c_lag": a.selected_lag,
                            "KPSS_c_statistic": k.statistic, "KPSS_c_p": k.p_value, "KPSS_c_lags": k.selected_lag,
                            "ADF_ct_p": at.p_value, "KPSS_ct_p": kt.p_value,
                            "first_difference_ADF_c_p": ad.p_value, "first_difference_KPSS_c_p": kd.p_value,
                            "level_N": a.N, "max_contiguous_N": a.max_contiguous_N,
                            "conflict_reason": conflict,
                            "cointegration_framework_screen": "BLOCKED_POSSIBLE_I2" if evidence == "POSSIBLE_I2_OR_BREAK" else
                            "INDETERMINATE" if evidence in ("BORDERLINE / MIXED EVIDENCE", "UNTESTABLE_CALENDAR_GAPS") else
                            "NOT_IN_SAMPLE" if evidence == "NOT_IN_SAMPLE" else "NO_I2_EVIDENCE"})
    summary_df = pd.DataFrame(summary)
    conflict_df = pd.DataFrame(conflicts, columns=["sample", "variable", "transformation", "reason",
                                                    "ADF_c_p", "KPSS_c_p", "ADF_ct_p", "KPSS_ct_p", "integration_evidence"])
    write_csv(summary_df, "stationarity_summary.csv")
    write_csv(conflict_df, "stationarity_conflicts.csv")
    return full, summary_df, conflict_df


if __name__ == "__main__":
    _, summary, conflict = run()
    print(summary[["sample", "variable", "integration_evidence"]].to_string(index=False))
    print(f"conflicts={len(conflict)}")
