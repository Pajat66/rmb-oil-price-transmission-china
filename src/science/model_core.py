"""Calendar-safe OLS and cumulative-effect helpers."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm


def lag_frame(df, y, xvars, lag_orders, controls=(), lead=0, start=None, end=None):
    data = df.copy().sort_values("month").reset_index(drop=True)
    if start is not None:
        data = data.loc[data.month >= pd.Timestamp(start)].copy().reset_index(drop=True)
    if end is not None:
        data = data.loc[data.month <= pd.Timestamp(end)].copy().reset_index(drop=True)
    if data.month.duplicated().any():
        raise ValueError("duplicate observation month")
    expected = pd.period_range(data.month.min(), data.month.max(), freq="M")
    if len(expected) != len(data):
        raise ValueError("lag_frame requires continuous calendar months")
    cols = []
    for x in xvars:
        for lag in range(lag_orders[x] + 1):
            col = f"{x}_lag{lag}"
            data[col] = data[x].shift(lag)
            cols.append(col)
    for control in controls:
        cols.append(control)
    target = y if lead == 0 else f"{y}_lead{lead}"
    if lead:
        data[target] = data[y].shift(-lead)
    max_lag = max(lag_orders.values(), default=0)
    eligible = data.iloc[max_lag:len(data) - lead if lead else len(data)].copy()
    model_df = eligible[["month", target] + cols].dropna()
    audit = {
        "raw_start": data.month.min().strftime("%Y-%m"), "raw_end": data.month.max().strftime("%Y-%m"),
        "raw_N": int(len(data)), "lag_loss": int(max_lag + lead),
        "missing_value_loss": int(len(eligible) - len(model_df)),
        "final_start": model_df.month.min().strftime("%Y-%m") if len(model_df) else "",
        "final_end": model_df.month.max().strftime("%Y-%m") if len(model_df) else "",
        "final_N": int(len(model_df)),
    }
    assert audit["raw_N"] - audit["lag_loss"] - audit["missing_value_loss"] == audit["final_N"]
    return model_df, cols, audit


def fit_ols(model_df, y, xcols, cov_type="HC3"):
    X = sm.add_constant(model_df[xcols].astype(float), has_constant="add")
    fit = sm.OLS(model_df[y].astype(float), X).fit(cov_type=cov_type)
    if not np.isfinite(fit.params).all():
        raise ValueError("nonfinite coefficient")
    return fit


def cumulative(fit, terms):
    effect = float(fit.params[terms].sum())
    cov = fit.cov_params().loc[terms, terms].to_numpy()
    se = float(np.sqrt(max(cov.sum(), 0)))
    p = float(2 * norm.sf(abs(effect / se))) if se > 0 else np.nan
    return {"cumulative_effect": effect, "cumulative_se": se,
            "ci_lower": effect - 1.96 * se, "ci_upper": effect + 1.96 * se,
            "p_value": p}
