"""October 2026 prespecified extensions using the original Phase 2B kernels."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/science"))
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
import pandas as pd
import scipy
from scipy.stats import norm
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

PAIR_LABELS = ("Fuel minus PPI", "Fuel minus CPI", "PPI minus CPI")
PAIRS = ((0, 1), (0, 2), (1, 2))
NAMES = ("Fuel", "PPI", "CPI")
BASIS = ("symmetric", "rise", "fall", "rise_minus_fall")


def hashed(path):
    return sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write(frame, path):
    frame.to_csv(path, encoding="utf-8-sig", index=False, lineterminator="\n")


def close(a, b, message):
    np.testing.assert_allclose(a, b, rtol=2e-9, atol=2e-12, equal_nan=True, err_msg=message)


def verify_registration(folder):
    path = folder / "prespecification.json"
    expected = (folder / "prespecification.sha256").read_text().split()[0]
    require(hashed(path) == expected, "Prespecification hash mismatch")
    plan = json.loads(path.read_text(encoding="utf-8"))
    core = ROOT / plan["core_release"]
    second = ROOT / plan["validation_release"]
    receipts = {}
    for directory, hash_field in [(core, "outputs_sha256"), (second, "output_hashes")]:
        receipt_path = directory / "reproduction.json"
        receipts[receipt_path.relative_to(ROOT).as_posix()] = hashed(receipt_path)
        original = json.loads(receipt_path.read_text(encoding="utf-8"))
        for relative, expected_hash in original[hash_field].items():
            require(hashed(directory / relative) == expected_hash, f"Prior stage output changed: {relative}")
        if "report_sha256" in original:
            require(hashed(directory / "第二轮实验总报告.md") == original["report_sha256"], "Second-wave report changed")
    prior = json.loads((core / "reproduction.json").read_text(encoding="utf-8"))
    require(prior["baseline"] == "PASS" and not prior["frozen_failures"], "Core reproduction is not accepted")
    for sample in ("long", "short"):
        relative = f"{plan['input_release']}/{sample}_sample_transformed.csv"
        receipts[relative] = hashed(ROOT / relative)
        require(receipts[relative] == prior["inputs_and_code_sha256"][relative], f"Input changed: {sample}")
    return plan, core, second, receipts


def read_months(path, span):
    frame = pd.read_csv(path, parse_dates=["month"])
    require(pd.DatetimeIndex(frame.month).equals(pd.date_range(*span, freq="MS")), f"Missing months in {path}")
    return frame


def eligible_dates(months, h, windows):
    date = months.dt.to_period("M")
    intersects = np.zeros(len(months), dtype=bool)
    for start, end in windows:
        intersects |= ((date - 3 <= pd.Period(end, freq="M")) &
                       (date + h >= pd.Period(start, freq="M"))).to_numpy()
    return ~intersects


def design_subset(original, mask, split):
    valid = original["valid"] & mask
    z = original["z"].loc[valid]
    x = z[original["cols"]].to_numpy(float)
    terms = list(original["cols"])
    if split:
        current = x[:, 1]
        pos, neg = np.maximum(current, 0), np.minimum(current, 0)
        require(np.array_equal(pos + neg, current), "x_pos + x_neg must recover the observed signed shock")
        x = np.column_stack((x[:, 0], pos, neg, x[:, 2:]))
        terms = [terms[0], "x_pos", "x_neg", *terms[2:]]
    y = z.response.to_numpy(float)
    require(np.isfinite(x).all() and np.isfinite(y).all() and len(x) > x.shape[1]
            and np.linalg.matrix_rank(x) == x.shape[1], f"Rank or sample failure: {original['y']} h={original['h']}")
    return dict(original, valid=valid, X=x, Y=y, cols=terms, months=z.month, fit=sm.OLS(y, x).fit())


def construct(long, plan):
    from design_construction import build_design
    spec = plan["sample"]
    designs, masks = {}, []
    base = {outcome: [build_design(long, outcome, spec["shock"], h) for h in spec["horizons"]]
            for outcome in spec["outcomes"]}
    baseline = "full_sample"
    scenarios = {baseline: [], **plan["A"]["scenarios"]}
    boot_designs = {}
    diagnostics = []
    for scenario, windows in scenarios.items():
        designs[scenario] = {}
        for outcome, paths in base.items():
            selected = [design_subset(d, eligible_dates(long.month, d["h"], windows), False) for d in paths]
            designs[scenario][outcome] = selected
            boot_designs[design_key(scenario, outcome, "symmetric")] = selected

        for h in spec["horizons"]:
            common = designs[scenario][spec["outcomes"][0]][h]
            mask = common["valid"]
            require(all(np.array_equal(mask, path[h]["valid"]) for path in designs[scenario].values()),
                    f"Outcomes do not share origin months: {scenario}, h={h}")
            removed = base[spec["outcomes"][0]][h]["valid"] & ~mask
            masks.append(dict(scenario=scenario, horizon=h, N=int(mask.sum()), excluded_N=int(removed.sum()),
                              start=common["months"].min().strftime("%Y-%m"),
                              end=common["months"].max().strftime("%Y-%m"),
                              origin_sha256=sha256("|".join(common["months"].dt.strftime("%Y-%m")).encode()).hexdigest(),
                              excluded_shock_origins=";".join(long.month.loc[removed].dt.strftime("%Y-%m"))))
    asymmetric = {}
    for outcome, paths in base.items():
        expanded = [design_subset(d, np.ones(len(long), dtype=bool), True) for d in paths]
        for d, restricted in zip(expanded, designs[baseline][outcome]):
            require(np.array_equal(d["valid"], restricted["valid"]) and np.array_equal(d["Y"], restricted["Y"]),
                    "Same-sample nesting failed")
            require(np.array_equal(d["X"][:, 1] + d["X"][:, 2], restricted["X"][:, 1]) and
                    np.array_equal(d["X"][:, 3:], restricted["X"][:, 2:]), "The remaining LP controls changed")
            x = d["X"]
            z = x[:, 1:]
            sd = z.std(axis=0, ddof=1)
            require((sd > 0).all(), f"Constant asymmetry regressor: {outcome}")
            diagnostics.append(dict(outcome=outcome, horizon=d["h"], N=len(x), N_symmetric=len(restricted["X"]),
                                    positive_N=int((x[:, 1] > 0).sum()), negative_N=int((x[:, 2] < 0).sum()),
                                    zero_N=int(((x[:, 1] == 0) & (x[:, 2] == 0)).sum()),
                                    columns=x.shape[1], rank=np.linalg.matrix_rank(x),
                                    standardized_condition_number=np.linalg.cond((z-z.mean(axis=0))/sd),
                                    vif_rise=variance_inflation_factor(x, 1),
                                    vif_fall=variance_inflation_factor(x, 2),
                                    symmetric_rss=restricted["fit"].ssr, asymmetric_rss=d["fit"].ssr))
            require(d["fit"].ssr <= restricted["fit"].ssr + 1e-9, "Nested fit RSS increased")
        asymmetric[outcome] = expanded
        for branch, j in [("rise", 1), ("fall", 2)]:
            boot_designs[design_key(baseline, outcome, branch)] = [dict(d, j=j) for d in expanded]
    return designs, asymmetric, boot_designs, pd.DataFrame(masks), pd.DataFrame(diagnostics)


def design_key(scenario, outcome, component):
    return f"{scenario}__{outcome}__{component}"


def point_series(path, terms):
    return np.array([d["fit"].params[terms[0][0]] if len(terms) == 1
                     else sum(w*d["fit"].params[j] for j, w in terms) for d in path])


def hac_rows(path, horizon, terms, estimate, cumulative, core):
    h = horizon
    included = path[:h+1] if cumulative else path[h:h+1]
    selected = [dict(d, j=j) for j, _ in terms for d in included]
    weights = np.repeat([w for _, w in terms], len(included))
    for tag, bandwidth in [("PRIMARY", max(12, h+1)), ("HAC6_OVERLAP", max(6, h+1)), ("HAC12_PLUS_H", 12+h)]:
        cov = core.cov_path(selected, bandwidth)
        variance = float(weights @ cov @ weights)
        require(np.isfinite(variance) and variance > 0, f"HAC variance invalid: {path[h]['y']} h={h}")
        se = np.sqrt(variance)
        half = norm.ppf(.975)*se
        yield dict(hac_policy=tag, maxlags=bandwidth, estimate=float(estimate),
                   hac_se=se, hac_ci_low=estimate-half, hac_ci_high=estimate+half,
                   hac_raw_p=2*norm.sf(abs(estimate/se)))


def intervals(designs, asymmetric, simulated, plan, core):
    period, inference, windows, hierarchy, sign_hierarchy = [], [], [], [], []
    highlights = plan["sample"]["main_horizons"]
    original_policy = json.loads((ROOT / "config/phase2b_prespecified_inference_policy.json").read_text())
    from reestimate_core_202610 import joint_tests

    for scenario, equations in designs.items():
        for outcome, symmetric in equations.items():
            alternatives = [("symmetric", symmetric, [(1, 1)])]
            if scenario == "full_sample":
                alternatives.extend((component, asymmetric[outcome], terms) for component, terms in
                                    [("rise", [(1, 1)]), ("fall", [(2, 1)]),
                                     ("rise_minus_fall", [(1, 1), (2, -1)])])
            for component, path, terms in alternatives:
                points = point_series(path, terms)
                for block, block_paths in simulated.items():
                    if component == "rise_minus_fall":
                        draws = (block_paths[design_key(scenario, outcome, "rise")]
                                 - block_paths[design_key(scenario, outcome, "fall")])
                    else:
                        draws = block_paths[design_key(scenario, outcome, component)]
                    if component == "symmetric":
                        windows.extend(dict(scenario=scenario, **entry) for entry in
                                       joint_tests(draws, points, f"PRIMARY_{outcome}", outcome, block, original_policy))
                    for form, betas, paths in [
                            ("period", points, draws), ("cumulative", points.cumsum(), draws.cumsum(axis=1))]:
                        for h, estimate in enumerate(betas):
                            N = len(path[h]["X"])
                            keys = dict(scenario=scenario, outcome=outcome, component=component,
                                        response_type=form, horizon=h, N=N)
                            interval = core.interval(paths[:, h], estimate)
                            inference.append(dict(**keys, block_length=block, estimate=estimate, **interval))
                            if block == core.BLOCKS[0]:
                                period.extend(dict(**keys, **result) for result in
                                              hac_rows(path, h, terms, estimate, form == "cumulative", core))
        # Difference paths use one common bootstrap draw at each horizon.
        branches = ("symmetric", "rise", "fall") if scenario == "full_sample" else ("symmetric",)
        for branch in branches:
            source = equations if branch == "symmetric" else asymmetric
            j = 2 if branch == "fall" else 1
            for block, block_paths in simulated.items():
                for (left, right), label in zip(PAIRS, PAIR_LABELS):
                    outcome_a, outcome_b = [plan["sample"]["outcomes"][i] for i in (left, right)]
                    a, b = source[outcome_a], source[outcome_b]
                    p = (point_series(a, [(j, 1)]) - point_series(b, [(j, 1)])).cumsum()
                    draw = (block_paths[design_key(scenario, outcome_a, branch)] -
                            block_paths[design_key(scenario, outcome_b, branch)]).cumsum(axis=1)
                    for h in highlights:
                        record = dict(scenario=scenario, component=branch, contrast=label, horizon=h,
                                      N=len(a[h]["X"]), block_length=block, estimate=p[h],
                                      **core.interval(draw[:, h], p[h]))
                        (hierarchy if branch == "symmetric" else sign_hierarchy).append(record)
    hac = pd.DataFrame(period)
    hh = hac.component.eq("symmetric")
    hac.loc[hh, ["fdr_q", "holm_p"]] = core.adjust(
        hac.loc[hh], ["scenario", "outcome", "response_type", "hac_policy"], "hac_raw_p")[["fdr_q", "holm_p"]]
    bootstrap = pd.DataFrame(inference)
    bootstrap["family"] = ""
    main = (bootstrap.component.eq("rise_minus_fall") & bootstrap.response_type.eq("cumulative") &
            bootstrap.horizon.isin(highlights))
    secondary = bootstrap.component.eq("rise_minus_fall") & bootstrap.response_type.eq("period")
    bootstrap.loc[main, "family"] = "cumulative_asymmetry_9"
    bootstrap.loc[secondary, "family"] = "period_asymmetry_39"
    for sel, expected_size in [(main, 9), (secondary, 39)]:
        require(bootstrap.loc[sel].groupby("block_length").size().eq(expected_size).all(), "Asymmetry family incomplete")
        q = core.adjust(bootstrap.loc[sel], ["block_length"], "bootstrap_p")
        bootstrap.loc[sel, ["fdr_q", "holm_p"]] = q[["fdr_q", "holm_p"]]
    hierarchy = core.adjust(pd.DataFrame(hierarchy), ["scenario", "block_length"], "bootstrap_p")
    sign_hierarchy = core.adjust(pd.DataFrame(sign_hierarchy), ["component", "block_length"], "bootstrap_p")
    windows = core.adjust(pd.DataFrame(windows), ["scenario", "model", "block_length"])
    return hac, bootstrap, windows, hierarchy, sign_hierarchy


def link1(short, plan, core):
    from design_construction import build_link1
    from phase15_common import calendar_lag

    base = build_link1(short)
    output = []
    for q in (-1, 0, 1):
        calendar = base["z"].copy()
        size = q + 1
        names = [f"dlog_import_quantity_lag{i}" for i in range(size)]
        for i, name in enumerate(names):
            calendar[name] = calendar_lag(short, "dlog_import_quantity", i)
        cols = [*base["cols"], *names]
        case = {"full_sample": [], **plan["link1_exploratory"]["omit"]}
        for scenario, drop in case.items():
            valid = base["valid"] & ~calendar.month.dt.strftime("%Y-%m").isin(drop).to_numpy()
            require(int(base["valid"].sum() - valid.sum()) == len(drop), "Link1 omitted months differ from plan")
            selected = calendar.loc[valid]
            x = selected[cols].to_numpy(float)
            y = selected[base["y"]].to_numpy(float)
            require(np.isfinite(x).all() and np.isfinite(y).all() and len(x) > x.shape[1]
                    and np.linalg.matrix_rank(x) == x.shape[1], f"Unusable Link1 matrix: {scenario}, q={q}")
            fit = sm.OLS(y, x).fit()
            design = dict(base, valid=valid, X=x, Y=y, fit=fit, cols=cols)
            oil = [dict(design, j=i) for i in range(1, 5)]
            effect = fit.params[1:5].sum()
            for l in plan["link1_exploratory"]["bandwidths"]:
                v = core.cov_path(oil, l)
                se = np.sqrt(np.ones(4)@v@np.ones(4))
                if not drop:
                    close(v, core.hac(fit, l).cov_params()[1:5, 1:5], "Calendar HAC reproduces contiguous Link1 HAC")
                gap = norm.ppf(.975)*se
                output.append(dict(scenario=scenario, removed_months=";".join(drop), quantity_order=q, bandwidth=l,
                                   N=len(selected), estimate=effect, hac_se=se, ci_low=effect-gap, ci_high=effect+gap,
                                   contains_one=effect-gap <= 1 <= effect+gap,
                                   month_hash=sha256("|".join(selected.month.dt.strftime("%Y-%m")).encode()).hexdigest(),
                                   analysis_role="FULL_SAMPLE_REFERENCE" if not drop else "EXPLORATORY_INFLUENCE"))
    return pd.DataFrame(output)


def compare_benchmarks(hac, bootstrap, windows, pairs, mechanics, core_release, validation_release):
    core = pd.read_csv(core_release / "primary_lp_comparison.csv").sort_values(["outcome", "response_type", "horizon"])
    filt = hac.scenario.eq("full_sample") & hac.component.eq("symmetric") & hac.hac_policy.eq("PRIMARY")
    response = hac.loc[filt].sort_values(["outcome", "response_type", "horizon"])
    for a, b in [("estimate", "estimate_new"), ("hac_se", "hac_se_new"), ("hac_raw_p", "raw_p_new"),
                 ("hac_ci_low", "hac_ci_low_new"), ("hac_ci_high", "hac_ci_high_new"),
                 ("fdr_q", "fdr_q_new"), ("holm_p", "holm_p_new"), ("N", "N_new")]:
        close(response[a], core[b], f"Full-sample LP benchmark {a}")
    boot = bootstrap.loc[bootstrap.scenario.eq("full_sample") & bootstrap.component.eq("symmetric") &
                         bootstrap.block_length.eq(12)].sort_values(["outcome", "response_type", "horizon"])
    for field in ("bootstrap_se", "bootstrap_ci_low", "bootstrap_ci_high", "bootstrap_p"):
        close(boot[field], core[field+"_new"], f"Full-sample LP MBB benchmark {field}")
    prior_joint = pd.read_csv(core_release / "primary_joint_tests.csv").query("scenario == 'full_new'")
    for label, new, ref, key, cols in [
        ("joint", windows[windows.scenario.eq("full_sample")], prior_joint,
         ["outcome", "block_length", "window"], ["wald_statistic", "raw_p", "fdr_q", "holm_p"]),
        ("hierarchy", pairs[pairs.scenario.eq("full_sample")], pd.read_csv(
            validation_release / "phase2b/price_hierarchy_tests.csv").query("vintage == '2026-10'").rename(
             columns={"difference": "estimate"}).assign(contrast=lambda f: f.contrast.replace(
                 dict(zip(["d_fuel_power_inflation minus d_ppi_inflation",
                           "d_fuel_power_inflation minus d_cpi_inflation",
                           "d_ppi_inflation minus d_cpi_inflation"], PAIR_LABELS)))),
         ["contrast", "block_length", "horizon"], ["estimate", "bootstrap_se", "bootstrap_ci_low", "bootstrap_ci_high",
                                                   "bootstrap_p", "fdr_q", "holm_p", "N"]),
        ("Link1", mechanics[mechanics.scenario.eq("full_sample")],
         pd.read_csv(core_release / "customs_link1.csv").query("scenario == 'full_new' and record_type == 'cumulative'").rename(
             columns={"maxlags": "bandwidth", "coefficient": "estimate", "hac_ci_low": "ci_low", "hac_ci_high": "ci_high"}),
         ["quantity_order", "bandwidth"], ["N", "estimate", "hac_se", "ci_low", "ci_high"]),
    ]:
        f, g = new.set_index(key).sort_index(), ref.set_index(key).sort_index()
        require(f.index.equals(g.index), f"Frozen comparator keys differ: {label}")
        close(f[cols], g[cols], f"Frozen comparator statistics: {label}")


def run(folder):
    plan, previous, validation, inputs = verify_registration(folder)
    final = folder / "results"
    require(not final.exists(), "Use a new folder with a copy of the sealed registration for another run")
    audit = ROOT / "private_work/extensions_2026-10" / folder.name / (
        "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"))
    audit.mkdir(parents=True)
    os.environ["RMB_R3_WORKDIR"] = str(audit)
    import phase2b_core as core

    bootstrap_policy = plan["inference"]["bootstrap"]
    require((core.B, core.SEED, list(core.BLOCKS), core.YLIST, core.SHOCK) ==
            (bootstrap_policy["reps"], bootstrap_policy["seed"], bootstrap_policy["blocks"],
             plan["sample"]["outcomes"], plan["sample"]["shock"]), "Original model and registered policy disagree")
    path = ROOT / plan["input_release"]
    long, short = (read_months(path / f"{name}_sample_transformed.csv", plan["sample"][name])
                   for name in ("long", "short"))
    designs, expanded, boot_designs, memberships, diagnostics = construct(long, plan)
    simulations = {}
    core.DATA = audit
    for block in core.BLOCKS:
        paths, failed = core.boot(boot_designs, "long", block)
        if failed or not all(np.isfinite(x).all() and x.shape == (core.B, 13) for x in paths.values()):
            write(pd.DataFrame(failed), audit / f"failure_L{block}.csv")
            raise ValueError(f"Prespecified effective-draw gate failed at block {block}; see {audit}")
        simulations[block] = paths
    print(f"BOOTSTRAP_COMPLETE={audit}", flush=True)
    hac, mbb, windows, hierarchy, sign_hierarchy = intervals(designs, expanded, simulations, plan, core)
    estimates = link1(short, plan, core)
    compare_benchmarks(hac, mbb, windows, hierarchy, estimates, previous, validation)
    print("FROZEN_BENCHMARKS_PASS", flush=True)
    keys = ["scenario", "outcome", "component", "response_type", "horizon", "N", "estimate"]
    primary_hac = hac[hac.hac_policy.eq("PRIMARY")].drop(columns=["fdr_q", "holm_p"])
    merged = mbb.merge(primary_hac, on=keys, validate="many_to_one")
    # Carry the original HAC family adjustments separately from the new equality families.
    adjusted = hac[hac.hac_policy.eq("PRIMARY")][keys+["fdr_q", "holm_p"]].rename(
        columns={"fdr_q": "hac_fdr_q", "holm_p": "hac_holm_p"})
    merged = merged.merge(adjusted, on=keys, validate="many_to_one")
    stage = audit / "results"
    stage.mkdir()
    tables = {
        "symmetric_responses": merged[merged.component.eq("symmetric")],
        "extreme_period_short_window_tests": windows,
        "extreme_period_paired_hierarchy": hierarchy,
        "link1_exploratory_influence": estimates,
        "asymmetric_responses_and_tests": merged[merged.scenario.eq("full_sample")],
        "asymmetric_direction_hierarchy": sign_hierarchy,
        "hac_bandwidth_sensitivity": hac,
        "estimation_calendar": memberships,
        "asymmetry_design_diagnostics": diagnostics,
    }
    for name, frame in tables.items():
        write(frame, stage / f"{name}.csv")
    manifest = dict(plan_sha256=hashed(folder/"prespecification.json"), input_hashes=inputs,
                    completed_utc=datetime.now(timezone.utc).isoformat(),
                    code_sha256={s: hashed(ROOT/s) for s in [
                        "scripts/run_extensions_202610.py", "scripts/reestimate_core_202610.py",
                        "src/science/phase2b_core.py", "src/science/design_construction.py",
                        "src/science/phase15_common.py", "config/phase2b_prespecified_inference_policy.json"]},
                    checks={"benchmarks": "PASS", "same_sample_and_nested": "PASS",
                            "bootstrap_effective_per_path_each_block": core.B, "bootstrap_rank_failures": 0},
                    environment=dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__,
                                     statsmodels=statsmodels.__version__, scipy=scipy.__version__),
                    result_sha256={p.name: hashed(p) for p in sorted(stage.glob("*.csv"))},
                    local_audit_path=audit.relative_to(ROOT).as_posix())
    (stage / "reproduction.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    stage.rename(final)
    print(f"EXTENSIONS_READY={final}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registered_folder", type=Path)
    run(parser.parse_args().registered_folder.resolve())
