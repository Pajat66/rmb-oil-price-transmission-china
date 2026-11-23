"""Retained S2/S3 runners and Link1 fixed-specification precision diagnostics."""
import argparse
import os
from pathlib import Path
import sys

from reestimate_validation_202610 import AUDIT_ROOT, CORE, check_numeric

import numpy as np
import pandas as pd
import statsmodels.api as sm

COV_LAGS = (6, 12, 18)
OIL_TERMS = [f"dlog_oil_rmb_lag{lag}" for lag in range(4)]
CUSTOMS_OUTCOME = "dlog_import_unit_price"


def historical(work):
    os.environ["RMB_R3_WORKDIR"] = str(work.resolve())
    from phase15_common import load_canonical, write_csv
    from phase2b_core import load
    import stationarity_analysis
    import phase2a_stationarity
    import phase2a9_core
    import phase2a_models
    import phase2a5_core
    import table3_lag_selection

    canon = {sample: load_canonical(sample) for sample in ("long", "short")}
    stationary = {sample: load(sample) for sample in canon}
    stationarity_analysis.run(canon["long"], canon["short"])
    phase2a_stationarity.run(stationary)
    yoy, _, _ = phase2a9_core.aligned()
    phase2a9_core.stationarity(yoy)
    # S3 Original lag audit uses the 2015+ short grid, as frozen N and starts show.
    table3_lag_selection.run(canon["short"])
    long = stationary["long"]
    for maxlag, name in [(12, "long_dlm_lag_grid_0_12.csv"), (18, "long_dlm_lag_grid_0_18_sensitivity.csv")]:
        grid = [phase2a_models.grid(long, "long", y, phase2a_models.SHOCK, maxlag)[0]
                for y in phase2a_models.OUTCOMES]
        write_csv(pd.concat(grid, ignore_index=True), name)
    phase2a5_core.run_initial()
    print(f"HISTORICAL_COMPLETE={work}", flush=True)


def link1_diagnostics(wave):
    # Full-sample and frozen/revision controls and designs are the original Phase 2B designs.
    from phase2b_core import hac
    core = pd.read_csv(CORE / "customs_link1.csv")
    from reestimate_core_202610 import revised_short, fit_link1

    old_dir, new_dir = wave / "old/01_data", wave / "new/01_data"
    read = lambda folder, layer: pd.read_csv(folder / f"short_sample_{layer}.csv", parse_dates=["month"])
    revised = revised_short(read(old_dir, "canonical"), read(old_dir, "transformed"),
                            read(new_dir, "canonical"), read(new_dir, "transformed"))
    revision_dir = wave / "link1_revised"
    revision_dir.mkdir(exist_ok=True)
    fit_link1(revised, revision_dir)
    partitions = {"old": old_dir, "revised_overlap": revision_dir, "full_new": new_dir}
    summaries, cells, leads, contributions = [], [], [], []
    for scenario, folder in partitions.items():
        transformed_path = (wave / ("new" if scenario == "full_new" else "old")
                            / "01_data/short_sample_transformed.csv")
        transformed = pd.read_csv(transformed_path, parse_dates=["month"])
        levels = pd.read_csv(transformed_path.with_name("short_sample_canonical.csv"), parse_dates=["month"])
        qcol = "import_crude_oil_qty_10k_ton"
        vcol = "import_crude_oil_value_100m_rmb"
        ucol = "import_crude_oil_unit_price_yuan_per_kg"
        check_numeric(levels[ucol], 10*levels[vcol]/levels[qcol])
        check_numeric(levels.oil_rmb, levels.brent_usd*levels.cny_per_usd)
        check_numeric(transformed["dlog_oil_rmb"], 100 * np.log(levels.oil_rmb).diff())
        if scenario != "revised_overlap":
            check_numeric(transformed[CUSTOMS_OUTCOME], 100 * np.log(levels[ucol]).diff())
        dated = (revised if scenario == "revised_overlap" else transformed).set_index("month")
        for q in (-1, 0, 1):
            model = f"MECH1_quantity{q}"
            z = pd.read_csv(folder / f"phase2b_design_{model}.csv", parse_dates=["month"])
            if z.month.duplicated().any() or not pd.DatetimeIndex(z.month).equals(
                    pd.date_range(z.month.min(), z.month.max(), freq="MS")):
                raise ValueError(f"Noncontiguous Link1 calendar: {scenario} q={q}")
            cols = z.columns.drop(["month", CUSTOMS_OUTCOME]).tolist()
            check_numeric(z[CUSTOMS_OUTCOME], dated[CUSTOMS_OUTCOME].reindex(z.month))
            for j, term in enumerate(OIL_TERMS):
                check_numeric(z[term], dated["dlog_oil_rmb"].shift(j).reindex(z.month))
            for j in range(q+1):
                term = f"dlog_import_quantity_lag{j}"
                check_numeric(z[term], dated["dlog_import_quantity"].shift(j).reindex(z.month))
            X = z[cols].to_numpy()
            fit = sm.OLS(z[CUSTOMS_OUTCOME].to_numpy(), X).fit()
            weights = np.array([term in OIL_TERMS for term in cols], dtype=float)
            oil_indices = [cols.index(term) for term in OIL_TERMS]
            influence = fit.get_influence()
            deletion_difference = influence.dfbeta @ weights
            score = (X @ np.linalg.solve(X.T@X, weights)) * fit.resid
            score *= np.sqrt(len(z) / (len(z)-len(cols)))
            for row in range(len(z)):
                leads.append(dict(scenario=scenario, quantity_control=q, month=z.month.iloc[row].strftime("%Y-%m"),
                                  residual=fit.resid[row], leverage=influence.hat_matrix_diag[row],
                                  studentized_residual=influence.resid_studentized_internal[row],
                                  cooks_distance=influence.cooks_distance[0][row],
                                  cumulative_coefficient_minus_case_deleted=deletion_difference[row],
                                  cumulative_hac_score=score[row]))
            for bandwidth in COV_LAGS:
                robust = hac(fit, bandwidth)
                matrix = np.asarray(robust.cov_params())
                covariance_dir = folder if scenario == "revised_overlap" else folder.parent / "03_tables"
                file = covariance_dir / f"phase2b_covariance_MECH1_q{q}_HAC{bandwidth}.csv"
                check_numeric(matrix, pd.read_csv(file).set_index("term").loc[cols, cols])
                saved = core.loc[(core.scenario == scenario) & (core.model == model) &
                                 (core.maxlags == bandwidth) & (core.record_type == "cumulative")].iloc[0]
                oil = matrix[np.ix_(oil_indices, oil_indices)]
                point, variance = float(weights@fit.params), float(weights@matrix@weights)
                check_numeric([point, np.sqrt(variance)], [saved.coefficient, saved.hac_se])
                diagonal = np.trace(oil)
                by_month = score**2
                by_lag = [float(by_month.sum())]
                for offset in range(1, bandwidth+1):
                    cross = (1-offset/(bandwidth+1))*score[offset:]*score[:-offset]
                    by_month[offset:] += cross
                    by_month[:-offset] += cross
                    by_lag.append(2*float(cross.sum()))
                check_numeric([oil.sum(), by_month.sum(), sum(by_lag)], [variance]*3)
                added = z.month.gt(pd.Timestamp("2026-02-01")).to_numpy()
                summaries.append(dict(scenario=scenario, quantity_control=q, bandwidth=bandwidth,
                                      N=len(z), coefficient=point, ci_low=saved.hac_ci_low,
                                      ci_high=saved.hac_ci_high, hac_se=saved.hac_se,
                                      oil_diagonal_variance=diagonal, oil_off_diagonal_variance=variance-diagonal,
                                      hac_variance=variance, lag_zero=by_lag[0], lag_nonzero=sum(by_lag[1:]),
                                      variance_attributed_to_2026_03_onward=by_month[added].sum(),
                                      variance_attributed_to_pre_extension=by_month[~added].sum()))
                for offset, value in enumerate(by_lag):
                    contributions.append(dict(scenario=scenario, quantity_control=q, bandwidth=bandwidth,
                                              score_lag=offset, variance_contribution=value))
                for a, term_a in enumerate(cols):
                    for b, term_b in enumerate(cols):
                        cells.append(dict(scenario=scenario, quantity_control=q, bandwidth=bandwidth,
                                          row_term=term_a, column_term=term_b, covariance=matrix[a, b],
                                          enters_oil_sum=bool(weights[a] and weights[b])))
    return tuple(pd.DataFrame(rows) for rows in (summaries, cells, leads, contributions))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_key")
    parser.add_argument("vintage", choices=("old", "new"))
    args = parser.parse_args()
    work = AUDIT_ROOT / args.run_key / args.vintage
    if not work.resolve().is_relative_to(AUDIT_ROOT.resolve()) or not work.is_dir():
        raise ValueError("Expected the isolated worker directory")
    historical(work)
