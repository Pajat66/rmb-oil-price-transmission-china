"""Compare independently reproduced October 2026 data and estimates to the release."""
from hashlib import sha256
from pathlib import Path
import numpy as np
import pandas as pd

import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("core", type=Path, help="Output of reproduce_202610.py --core")
parser.add_argument("validation", type=Path, help="Output of reproduce_validation.py")
parser.add_argument("extensions", type=Path, help="Output of reproduce_extensions.py")
parser.add_argument("--receipt", type=Path, required=True, help="Output CSV comparing each group")
args = parser.parse_args()
RUN, VALIDATION_RUN = args.core, args.validation
C, V = root / "results/core", root / "results/validation"
D = root / "data/model_inputs/2026-10"
RECORDS = []
TOL = dict(atol=2e-12, rtol=2e-9, equal_nan=True)
PVALUES = {"raw_p", "fdr_q", "holm_p", "bh_q", "bootstrap_p", "p_value"}
COEFF = ["estimate", "hac_se", "hac_ci_low", "hac_ci_high", "raw_p", "fdr_q", "holm_p"]
BOOT = ["bootstrap_se", "bootstrap_ci_low", "bootstrap_ci_high", "bootstrap_p", "valid_draws", "failed_draws"]


def read(path):
    return pd.read_csv(path, float_precision="round_trip")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def frame_equal(name, observed, expected, keys=(), fields=None):
    if keys:
        observed = observed.set_index(list(keys), verify_integrity=True).sort_index()
        expected = expected.set_index(list(keys), verify_integrity=True).sort_index()
    if fields is None:
        fields = [col for col in expected if col in observed and not col.endswith("_sha256")]
    assert observed.index.equals(expected.index), (name, "index")
    errors = []
    for k in fields:
        a, b = observed[k], expected[k]
        if a.isna().all() and b.isna().all():
            continue
        if all(pd.api.types.is_numeric_dtype(c) and not pd.api.types.is_bool_dtype(c) for c in (a, b)):
            np.testing.assert_allclose(a, b, **TOL, err_msg=f"{name}: {k}")
            if k in PVALUES:
                np.testing.assert_array_equal(a < .05, b < .05, err_msg=f"{name}: {k} at .05")
            comp = np.isfinite(a) & np.isfinite(b)
            if comp.any():
                errors.append(float((a[comp] - b[comp]).abs().max()))
        else:
            assert (a.eq(b) | (a.isna() & b.isna())).all(), (name, k)
    RECORDS.append(dict(check=name, rows=len(expected), fields=len(fields),
                        compared_values=len(expected) * len(fields), max_abs_error=max(errors, default=0)))
    print(f"{name}: {len(expected)} rows, {len(fields)} fields", flush=True)


keys = ["model", "horizon"]
for p in sorted(D.glob("*.csv")):
    assert digest(RUN / "01_data" / p.name) == digest(p), p.name
    RECORDS.append(dict(check=p.name, rows=len(read(p)), fields=len(read(p).columns), compared_values=read(p).size,
                        max_abs_error=0))
prim = read(C / "primary_lp_comparison.csv")
prim = prim[[n for n in prim if n in [*keys, "response_type"] or n.endswith("_new")]]
prim.columns = prim.columns.str.removesuffix("_new")
for sample in ("long", "short"):
    actual = RUN / sample
    link2 = read(C / "customs_link2.csv").query('scenario == "full_new" and block_length == 12')
    expected = prim if sample == "long" else link2
    for kind, alternate in (("period", "coefficient"), ("cumulative", "cumulative_effect")):
        a = read(actual / f"{kind}.csv").rename(columns={alternate: "estimate"})
        b = expected[expected.response_type.eq(kind)]
        frame_equal(f"{sample} {kind} HAC", a, b, keys, COEFF + (["N", "sample_start", "sample_end"] if kind == "period" else []))
        a = read(actual / f"{kind}_boot.csv")
        b = read(C / "inference_sensitivity.csv").query('scenario == "full_new" and method == "MBB"')
        b = b[b["sample"].eq({"long": "primary", "short": "link2"}[sample]) & b.response_type.eq(kind)].rename(columns={"ci_low":"bootstrap_ci_low","ci_high":"bootstrap_ci_high"})
        frame_equal(f"{sample} {kind} bootstrap L6/L12/L18", a, b, [*keys, "block_length"], BOOT)
    for source, response in (("sensitivity", "period"), ("cumulative_sensitivity", "cumulative")):
        a = read(actual / f"{source}.csv").rename(columns={"coefficient":"estimate","cumulative_effect":"estimate",
                                                         "hac_ci_low":"ci_low","hac_ci_high":"ci_high"})
        b = read(C / "inference_sensitivity.csv").query('scenario == "full_new" and method == "HAC"')
        b = b[b["sample"].eq({"long": "primary", "short": "link2"}[sample]) & b.response_type.eq(response)]
        frame_equal(f"{sample} {response} HAC sensitivities", a, b, [*keys, "policy", "maxlags"],
                    ["estimate", "hac_se", "ci_low", "ci_high", "raw_p", "fdr_q", "holm_p"])
joint = read(C / "primary_joint_tests.csv").query('scenario == "full_new"').drop(columns="scenario")
frame_equal("Joint window tests", read(RUN / "long/joint.csv"), joint, ["model", "window", "block_length"])
link1 = read(C / "customs_link1.csv").query('scenario == "full_new"')
link_names = ["model", "maxlags", "record_type", "term"]
dates = read(RUN / "link1_dates.csv").iloc[0]
link1_actual = read(RUN / "link1.csv").assign(sample_start=dates.sample_start, sample_end=dates.sample_end)
frame_equal("Link 1 HAC quantities and kernels", link1_actual, link1, link_names)
registry = read(V / "samples/final_sample_registry.csv")
registry = registry[registry.vintage.eq("2026-10") & registry.horizon.notna()]
if (VALIDATION_RUN / "00_audit/phase2b_primary_model_registry.csv").exists():
    a = read(VALIDATION_RUN / "00_audit/phase2b_primary_model_registry.csv").dropna(subset=["horizon"])
    frame_equal("S17 all equation months, terms, and N", a, registry, keys,
                ["status", "outcome", "shock", "sample", "N", "terms", "lag_policy", "sample_hash"])
    for family in ("phase2b", "stability", "s18"):
        for p in sorted((V / family).glob("*.csv")):
            candidates = [VALIDATION_RUN / d / p.name for d in ("03_tables", "s18/stage1", "s18/stage2")]
            q = next((candidate for candidate in candidates if candidate.exists()), None)
            if q is None:
                continue
            b = read(p)
            b = b[b.vintage.eq("2026-10")].drop(columns="vintage").reset_index(drop=True)
            a = read(q)
            frame_equal(f"{family}/{p.name}", a, b)

terminal_names = {
    "s12_terminal_bootstrap": "phase2b_all_lp_cumulative_bootstrap",
    "s12_terminal_cumulative_hac": "phase2b_all_lp_cumulative_hac"
}
for label, target in terminal_names.items():
    observed = read(VALIDATION_RUN / "03_tables" / f"{target}.csv")
    observed = observed[observed.model.str.startswith("TERMINAL_") | observed.model.eq("PRIMARY_d_cpi_inflation")].reset_index(drop=True)
    expected = read(V / "phase2b" / f"{label}.csv").query('vintage == "2026-10"').reset_index(drop=True)
    frame_equal(label, observed, expected)

for q in sorted((V / "historical").glob("*.csv")):
    expected = read(q).query('vintage == "2026-10"').reset_index(drop=True)
    frame_equal(f"historical/{q.name}", read(VALIDATION_RUN / "03_tables" / q.name), expected)

ext = root / "results/extensions"
for p in sorted(args.extensions.glob("*.csv")):
    if (ext / p.name).exists():
        frame_equal(f"extensions/{p.name}", read(p), read(ext / p.name))
assert sum(r["check"].startswith("extensions/") for r in RECORDS) == 9

for f in ("phase2b_bootstrap_failures.csv", "phase2c_bootstrap_failures.csv"):
    assert read(VALIDATION_RUN / "05_logs" / f).empty
link1_cov = read(V / "link1/hac_covariance.csv").query('scenario == "full_new"')
for (q, l), b in link1_cov.groupby(["quantity_control", "bandwidth"]):
    matrix = read(RUN / "short" / f"phase2b_covariance_MECH1_q{q}_HAC{l}.csv")
    observed = matrix.melt(id_vars="term", var_name="column_term", value_name="covariance").rename(columns={"term":"row_term"})
    frame_equal(f"Link 1 complete covariance q={q} L={l}", observed, b, ["row_term", "column_term"], ["covariance"])
destination = args.receipt
pd.DataFrame(RECORDS).to_csv(destination, index=False, encoding="utf-8-sig")
print(sum(r["compared_values"] for r in RECORDS), "cells compared.", flush=True)




