"""Reproduce the frozen core inference before fitting the October 2026 sample."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "science"))

# Preserve the environment used for the frozen matrix calculations.
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
import pandas as pd
import scipy
from scipy.stats import chi2, norm
import statsmodels

PROCESSED = ROOT / "data/processed/2026-10/01_data"
FROZEN = ROOT.parents[1] / "rmb-oil-price-transmission-china/05_revision/01_data"
REFERENCE = ROOT / "reference/statistics"
POLICY_PATH = ROOT / "config/phase2b_prespecified_inference_policy.json"
UPDATE_MANIFEST = ROOT / "data/manifests/2026-10/output_sha256.csv"
BASELINE_INVENTORY = ROOT / "data/reports/2026-10/baseline_inventory.csv"
RESULTS = ROOT / "analysis/2026-10/core_models"
AUDIT_PARENT = ROOT / "private_work/core_models_2026-10"
ORIGIN_COLUMNS = ["N", "sample_start", "sample_end"]
PAIR = ["model", "horizon"]
TOLERANCE = dict(rtol=1e-8, atol=1e-10)
HORIZONS = range(13)
OLD_END = "2026-02"
REVISION_MONTHS = pd.to_datetime(["2026-01-01", "2026-02-01"])
QUANTITY = "import_crude_oil_qty_10k_ton"
VALUE = "import_crude_oil_value_100m_rmb"
UNIT_VALUE = "import_crude_oil_unit_price_yuan_per_kg"
IMPORT_PRICE = "dlog_import_unit_price"
SCENARIOS = ("old", "revised_overlap", "full_new")


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def csv(frame, path):
    frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def read_months(path, start, end):
    frame = pd.read_csv(path, parse_dates=["month"])
    expected = pd.date_range(start, end, freq="MS")
    if not pd.DatetimeIndex(frame.month).equals(expected):
        raise ValueError(f"Unexpected month grid: {path}")
    return frame


def provenance(frozen, audit):
    old = pd.read_csv(BASELINE_INVENTORY)
    new = pd.read_csv(UPDATE_MANIFEST).set_index("path").sha256
    checks = {}
    for sample in ("long", "short"):
        for kind in ("canonical", "transformed"):
            name = f"{sample}_sample_{kind}.csv"
            path = frozen / name
            row = old[(old.path.str.endswith("/" + name)) & old.role.eq(f"历史模型 {sample} {kind}")]
            valid_hashes = set(row.sha256.dropna())
            checks["frozen/" + name] = sha(path)
            if valid_hashes != {checks["frozen/" + name]}:
                raise ValueError(f"Frozen input differs from the audited baseline: {path}")
            path = PROCESSED / name
            key = path.relative_to(ROOT).as_posix()
            checks[key] = sha(path)
            if checks[key] != new.loc[key]:
                raise ValueError(f"Updated input differs from the accepted release: {path}")
    exact = frozen / "phase2a75_design_SEASONAL_MECH1.csv"
    checks["frozen/" + exact.name] = sha(exact)
    checks["config/phase2b_prespecified_inference_policy.json"] = sha(POLICY_PATH)
    for path in sorted(REFERENCE.glob("*.csv")):
        if path.name in REFERENCE_NAMES:
            checks[path.relative_to(ROOT).as_posix()] = sha(path)
    for name in ("scripts/reestimate_core_202610.py", "scripts/core_202610_summary.py",
                 "src/science/phase2b_core.py", "src/science/phase2b_diagnostics.py",
                 "src/science/design_construction.py", "src/science/phase15_common.py",
                 "src/science/transformation_layer.py"):
        checks[name] = sha(ROOT / name)
    environment = {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                   "scipy": scipy.__version__, "statsmodels": statsmodels.__version__,
                   "blas_threads": 1}
    (audit / "provenance.json").write_text(json.dumps({"hashes": checks, "environment": environment},
                                                       indent=2), encoding="utf-8")
    return checks, environment


REFERENCE_NAMES = {
    "lp_final_coefficients.csv", "lp_bootstrap_ci.csv", "lp_cumulative_response.csv",
    "lp_joint_tests.csv", "mechanism_link1_final.csv", "phase2b_covariance_MECH1_q-1_HAC12.csv",
    "phase2b_all_lp_period_results.csv", "phase2b_all_lp_bootstrap_ci.csv",
    "phase2b_all_lp_cumulative_hac.csv", "phase2b_all_lp_cumulative_bootstrap.csv",
    "phase2b_inference_summary.csv",
}


def fit_lp(frame, core, policy, sample, case_dir):
    case_dir.mkdir()
    core.DATA = case_dir
    designs = {}
    for outcome in core.YLIST if sample == "long" else core.YLIST[:2]:
        if sample == "long":
            designs[f"PRIMARY_{outcome}"] = [core.build(frame, outcome, core.SHOCK, h) for h in HORIZONS]
        else:
            for quantity in (0, 1):
                key = f"MECH2_{outcome}_quantity{quantity}"
                designs[key] = [core.build(frame, outcome, IMPORT_PRICE, h, quantity=bool(quantity))
                                for h in HORIZONS]
    period, sensitivity, cumulative_sensitivity, cumulative = [], [], [], []
    for model, path in designs.items():
        group = "PRIMARY" if sample == "long" else "ROBUSTNESS" if model.endswith("quantity1") else "SECONDARY"
        total = np.cumsum([d["fit"].params[d["j"]] for d in path])
        for h, design in enumerate(path):
            period.append(core.result(design, model, group))
            for tag, bandwidth in [("PRIMARY", max(12, h+1)), ("HAC6_OVERLAP", max(6, h+1)),
                                   ("HAC12_PLUS_H", 12+h)]:
                result = core.hac(design["fit"], bandwidth)
                j = design["j"]
                lo, hi = result.conf_int()[j]
                sensitivity.append(dict(model=model, horizon=h, policy=tag, maxlags=bandwidth,
                                        coefficient=result.params[j], hac_se=result.bse[j], ci_low=lo,
                                        ci_high=hi, raw_p=result.pvalues[j]))
                cov = core.cov_path(path[:h+1], bandwidth)
                se = np.sqrt(cov.sum())
                if tag == "PRIMARY":
                    ones = np.ones(h+1)
                    primary_se = np.sqrt(ones @ cov @ ones)
                    cumulative.append(cumulative_row(model, h, tag, bandwidth, total[h], primary_se))
                cumulative_sensitivity.append(cumulative_row(model, h, tag, bandwidth, total[h], se))
    period, sensitivity, cumulative, cumulative_sensitivity = [
        core.adjust(pd.DataFrame(rows), grouping) for rows, grouping in [
            (period, ["model"]), (sensitivity, ["model", "policy"]),
            (cumulative, ["model"]), (cumulative_sensitivity, ["model", "policy"])]]
    cumulative = cumulative.drop(columns="policy")
    period_boot, cumulative_boot, joint, failures = [], [], [], []
    for block in core.BLOCKS:
        paths, failed = core.boot(designs, sample, block)
        failures.extend(failed)
        for model, path in paths.items():
            estimates = period.loc[period.model.eq(model)].sort_values("horizon").coefficient.to_numpy()
            cumulative_estimates = np.cumsum(estimates)
            cum_path = np.cumsum(path, axis=1)
            outcome = designs[model][0]["y"]
            for h in HORIZONS:
                keys = dict(model=model, outcome=outcome, horizon=h, block_length=block)
                period_boot.append(dict(**keys, coefficient=estimates[h], **core.interval(path[:, h], estimates[h])))
                cumulative_boot.append(dict(**keys, cumulative_effect=cumulative_estimates[h],
                                            **core.interval(cum_path[:, h], cumulative_estimates[h])))
            if sample == "long":
                joint.extend(joint_tests(path, estimates, model, outcome, block, policy))
    if failures:
        csv(pd.DataFrame(failures), case_dir / "bootstrap_failures.csv")
    return dict(period=period, cumulative=cumulative, period_boot=pd.DataFrame(period_boot),
                cumulative_boot=pd.DataFrame(cumulative_boot), sensitivity=sensitivity,
                cumulative_sensitivity=cumulative_sensitivity,
                joint=core.adjust(pd.DataFrame(joint), ["model", "block_length"]) if joint else None,
                eligibility=half_sample_eligibility(designs) if sample == "short" else None)


def cumulative_row(model, h, tag, bandwidth, estimate, se):
    critical = norm.ppf(.975)
    return dict(model=model, horizon=h, policy=tag, maxlags=bandwidth, cumulative_effect=estimate,
                hac_se=se, hac_ci_low=estimate-critical*se, hac_ci_high=estimate+critical*se,
                raw_p=2*norm.sf(abs(estimate/se)))


def joint_tests(path, estimates, model, outcome, block, policy):
    path = path[np.isfinite(path).all(axis=1)]
    for window, horizons in policy["joint_windows"].items():
        cov = np.atleast_2d(np.cov(path[:, horizons].T))
        rank = np.linalg.matrix_rank(cov)
        inv = np.linalg.pinv(cov)
        point = estimates[horizons]
        stat = float(point @ inv @ point)
        deviations = path[:, horizons] - point
        draws = np.einsum("bi,ij,bj->b", deviations, inv, deviations)
        yield dict(model=model, outcome=outcome, block_length=block, window=window,
                   horizons=",".join(map(str, horizons)), null="all listed period coefficients = 0",
                   wald_statistic=stat, covariance_rank=rank, df=len(horizons), chi2_p=float(chi2.sf(stat, rank)),
                   raw_p=(1+np.count_nonzero(draws >= stat))/(len(path)+1),
                   method="full path bootstrap covariance; centered bootstrap Wald calibration",
                   valid_draws=len(path))


def half_sample_eligibility(designs):
    rows = []
    for model, path in designs.items():
        if not model.endswith("quantity0"):
            continue
        first = path[0]["months"]
        split = first.iloc[len(first)//2-1]
        for d in path:
            left = int(d["months"].le(split).sum())
            right = len(d["months"]) - left
            rows.append(dict(model=model, horizon=d["h"], split_date=split.strftime("%Y-%m"),
                             first_half_n=left, second_half_n=right, minimum_n=60,
                             status="eligible" if min(left, right) >= 60 else "SKIPPED_PAIRED_HALF_N_BELOW60"))
    return pd.DataFrame(rows)


def fit_link1(frame, case_dir, exact=None):
    import phase2b_diagnostics as diagnostics
    from design_construction import build_link1

    design = build_link1(frame)
    if exact is None:
        csv(design["z"].loc[design["valid"]], case_dir / "phase2a75_design_SEASONAL_MECH1.csv")
    else:
        (case_dir / exact.name).write_bytes(exact.read_bytes())
    diagnostics.DATA = case_dir

    def save(rows, name, folder=case_dir):
        result = pd.DataFrame(rows)
        csv(result, folder / name)
        return result

    diagnostics.save = save
    diagnostics.link1(frame)
    link = pd.read_csv(case_dir / "mechanism_link1_final.csv")
    origin = design["months"].dt.strftime("%Y-%m")
    return link, (origin.iloc[0], origin.iloc[-1])


def revised_short(frozen_levels, old, updated, transformed):
    revised = frozen_levels.copy()
    mask = revised.month.isin(REVISION_MONTHS)
    updates = updated.set_index("month").loc[REVISION_MONTHS]
    revised.loc[mask, QUANTITY] = updates.import_quantity_kg.to_numpy() / 1e7
    revised.loc[mask, VALUE] = updates.import_value_cny.to_numpy() / 1e8
    revised.loc[mask, UNIT_VALUE] = (updates.import_value_cny / updates.import_quantity_kg).to_numpy()
    from transformation_layer import transform

    fields = [IMPORT_PRICE, "dlog_import_quantity", "dlog_import_value"]
    recomputed = transform(revised)[fields]
    np.testing.assert_allclose(recomputed.loc[~mask], old.loc[~mask, fields], **TOLERANCE, equal_nan=True)
    np.testing.assert_allclose(recomputed.loc[mask], transformed.set_index("month").loc[REVISION_MONTHS, fields],
                               **TOLERANCE, equal_nan=True)
    result = old.copy()
    result.loc[mask, fields] = recomputed.loc[mask, fields]
    if not result.loc[~mask].equals(old.loc[~mask]):
        raise ValueError("Overlap update changed a month outside Jan/Feb 2026")
    return result


def compare(actual, reference, keys, records, dataset):
    ref = reference.set_index(keys, verify_integrity=True).sort_index()
    got = actual.set_index(keys, verify_integrity=True).sort_index()
    if not ref.index.equals(got.index) or not set(ref.columns).issubset(got.columns):
        raise ValueError(f"{dataset}: frozen rows or columns differ")
    for col in ref:
        x, y = ref[col], got[col]
        label = col
        error = None
        if pd.api.types.is_float_dtype(x):
            a, b = x.to_numpy(float), y.to_numpy(float)
            mask = np.isclose(a, b, equal_nan=True, **TOLERANCE)
            # Bootstrap p-values are discrete plus-one counts and must reproduce exactly
            # at their original Monte Carlo resolution.
            if col == "bootstrap_p" or (dataset == "primary_joint" and col in {"raw_p", "fdr_q", "holm_p"}):
                mask &= np.isclose(a, b, rtol=0, atol=5e-14, equal_nan=True)
            finite = np.isfinite(a) & np.isfinite(b)
            error = float(np.max(np.abs(a[finite]-b[finite]))) if finite.any() else None
            if col in {"raw_p", "fdr_q", "holm_p", "bootstrap_p"}:
                mask &= (a < .05) == (b < .05)
        else:
            mask = (x.eq(y) | (x.isna() & y.isna())).to_numpy()
        records.append(dict(dataset=dataset, field=label, compared=len(x), mismatches=int((~mask).sum()),
                            max_abs_error=error, first_mismatch=str(ref.index[np.flatnonzero(~mask)[0]]) if not mask.all() else ""))


def validate_baseline(primary, link2, link1, audit):
    def ref(name):
        return pd.read_csv(REFERENCE / f"{name}.csv")

    records = []
    cumulative = primary["cumulative_boot"].merge(primary["cumulative"], on=[*PAIR, "cumulative_effect"],
                                                   validate="many_to_one")
    for dataset, actual, expected, keys in [
        ("primary_period", primary["period"], ref("lp_final_coefficients"), PAIR),
        ("primary_mbb", primary["period_boot"], ref("lp_bootstrap_ci"), [*PAIR, "block_length"]),
        ("primary_cumulative", cumulative, ref("lp_cumulative_response"), [*PAIR, "block_length"]),
        ("primary_joint", primary["joint"], ref("lp_joint_tests"), ["model", "block_length", "window"]),
        ("Link1", link1, ref("mechanism_link1_final"), ["model", "maxlags", "record_type", "term"]),
        ("Link1_covariance", pd.read_csv(audit / "old_short/phase2b_covariance_MECH1_q-1_HAC12.csv"),
         ref("phase2b_covariance_MECH1_q-1_HAC12"), ["term"]),
        *[("Link2_"+actual, link2[actual], ref(reference).loc[lambda f: f.model.str.startswith("MECH2_")], keys)
          for actual, reference, keys in [
              ("period", "phase2b_all_lp_period_results", PAIR),
              ("cumulative", "phase2b_all_lp_cumulative_hac", PAIR),
              ("period_boot", "phase2b_all_lp_bootstrap_ci", [*PAIR, "block_length"]),
              ("cumulative_boot", "phase2b_all_lp_cumulative_bootstrap", [*PAIR, "block_length"])]]]:
        compare(actual, expected, keys, records, dataset)
    from core_202610_summary import primary_intervals
    classification = primary_intervals(primary)
    old_claims = ref("phase2b_inference_summary")
    old_claims = old_claims.loc[old_claims.model.str.startswith("PRIMARY_")
                                & old_claims.claim_type.isin(["period_response", "cumulative_response"])]
    compare(classification, old_claims[["claim_id", "allowed_wording", "robustness_status"]],
            ["claim_id"], records, "primary_classification")
    table = pd.DataFrame(records)
    csv(table, audit / "frozen_comparisons.csv")
    n_failed = int(table.mismatches.sum())
    if n_failed:
        print(table.loc[table.mismatches.gt(0)].to_string(index=False), flush=True)
        raise RuntimeError(f"Baseline failed: {n_failed} numeric or exact-field comparison failures")
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-data-dir", type=Path, default=FROZEN)
    args = parser.parse_args()
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    audit = AUDIT_PARENT / run_id
    audit.mkdir(parents=True)
    print(f"LOCAL_AUDIT={audit}", flush=True)
    os.environ["RMB_R3_WORKDIR"] = str(audit)
    import phase2b_core as core

    from core_202610_summary import export, verify_exports
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if (policy["seed"], policy["replications"], tuple(policy["block_lengths"]), policy["horizons"],
            policy["outcomes"], policy["shock"]) != (
            core.SEED, core.B, core.BLOCKS, list(HORIZONS), core.YLIST, core.SHOCK):
        raise ValueError("Prespecified policy does not match the frozen kernels")
    frozen = args.frozen_data_dir.resolve()
    checks, environment = provenance(frozen, audit)
    old_long = read_months(frozen / "long_sample_transformed.csv", "1998-01", OLD_END)
    old_short = read_months(frozen / "short_sample_transformed.csv", "2015-01", OLD_END)
    old_lp = fit_lp(old_long, core, policy, "long", audit / "old_long")
    old_link2 = fit_lp(old_short, core, policy, "short", audit / "old_short")
    old_link1, old_dates = fit_link1(old_short, audit / "old_short",
                                     frozen / "phase2a75_design_SEASONAL_MECH1.csv")
    gate = validate_baseline(old_lp, old_link2, old_link1, audit)
    print(f"BASELINE_PASS fields={len(gate)} comparisons={gate.compared.sum()}", flush=True)

    long = read_months(PROCESSED / "long_sample_transformed.csv", "1998-01", "2026-10")
    short = read_months(PROCESSED / "short_sample_transformed.csv", "2015-01", "2026-10")
    # The two primary vintages differ by sample length alone on the model fields.
    primary_fields = [core.SHOCK, *core.YLIST]
    np.testing.assert_allclose(long.loc[:len(old_long)-1, primary_fields], old_long[primary_fields],
                               **TOLERANCE, equal_nan=True)
    np.testing.assert_allclose(short.loc[:len(old_short)-1, primary_fields], old_short[primary_fields],
                               **TOLERANCE, equal_nan=True)
    old_levels = read_months(frozen / "short_sample_canonical.csv", "2015-01", OLD_END)
    updated_levels = read_months(PROCESSED / "short_sample_canonical.csv", "2015-01", "2026-10")
    revised = revised_short(old_levels, old_short, updated_levels, short)
    revised_fields = [IMPORT_PRICE, "dlog_import_quantity", "dlog_import_value"]
    np.testing.assert_allclose(short.loc[:len(revised)-1, revised_fields], revised[revised_fields],
                               **TOLERANCE, equal_nan=True)

    full_lp = fit_lp(long, core, policy, "long", audit / "full_long")
    updated_link2 = fit_lp(revised, core, policy, "short", audit / "revised_short")
    updated_link1, revised_dates = fit_link1(revised, audit / "revised_short")
    full_link2 = fit_lp(short, core, policy, "short", audit / "full_short")
    full_link1, full_dates = fit_link1(short, audit / "full_short")
    run_dir = RESULTS / run_id
    staging = audit / "deliverables"
    staging.mkdir()
    export(staging, {"old": old_lp, "full_new": full_lp},
           dict(zip(SCENARIOS, [old_link1, updated_link1, full_link1])),
           dict(zip(SCENARIOS, [old_link2, updated_link2, full_link2])),
           dict(zip(SCENARIOS, [old_dates, revised_dates, full_dates])), gate, checks, environment, policy)
    verify_exports(staging)
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(run_dir)
    print(f"CORE_RESULTS_READY={run_dir}", flush=True)


if __name__ == "__main__":
    main()
