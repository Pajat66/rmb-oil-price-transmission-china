"""Re-estimate registered October extension results from rebuilt matrices."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import run_extensions_202610 as ext

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("rebuilt", type=Path)
parser.add_argument("plan", type=Path)
parser.add_argument("hash_receipt", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
assert hashlib.sha256(args.plan.read_bytes()).hexdigest() == args.hash_receipt.read_text().split()[0]
plan = json.loads(args.plan.read_text(encoding="utf-8"))
args.output.mkdir(parents=True)
os.environ["RMB_R3_WORKDIR"] = str(args.output.resolve())
import phase2b_core as core
config = plan["inference"]["bootstrap"]
assert (core.B, core.SEED, list(core.BLOCKS)) == (config["reps"], config["seed"], config["blocks"])
long, short = (ext.read_months(args.rebuilt / "01_data" / f"{name}_sample_transformed.csv", plan["sample"][name])
               for name in ("long", "short"))
designs, expanded, boot_designs, memberships, diagnostics = ext.construct(long, plan)
simulations = {}
core.DATA = args.output
for block in core.BLOCKS:
    paths, failed = core.boot(boot_designs, "long", block)
    assert not failed and all(ext.np.isfinite(x).all() and x.shape == (core.B, 13) for x in paths.values())
    simulations[block] = paths
hac, mbb, windows, hierarchy, sign_hierarchy = ext.intervals(designs, expanded, simulations, plan, core)
estimates = ext.link1(short, plan, core)
keys = ["scenario", "outcome", "component", "response_type", "horizon", "N", "estimate"]
primary = hac[hac.hac_policy.eq("PRIMARY")]
merged = mbb.merge(primary.drop(columns=["fdr_q", "holm_p"]), on=keys, validate="many_to_one")
adjusted = primary[keys + ["fdr_q", "holm_p"]].rename(columns={"fdr_q": "hac_fdr_q", "holm_p": "hac_holm_p"})
merged = merged.merge(adjusted, on=keys, validate="many_to_one")
outputs = {"symmetric_responses": merged[merged.component.eq("symmetric")],
           "extreme_period_short_window_tests": windows, "extreme_period_paired_hierarchy": hierarchy,
           "link1_exploratory_influence": estimates, "asymmetric_responses_and_tests": merged[merged.scenario.eq("full_sample")],
           "asymmetric_direction_hierarchy": sign_hierarchy, "hac_bandwidth_sensitivity": hac,
           "estimation_calendar": memberships, "asymmetry_design_diagnostics": diagnostics}
for name, frame in outputs.items():
    ext.write(frame, args.output / f"{name}.csv")
print("Nine extension tables regenerated.", flush=True)
