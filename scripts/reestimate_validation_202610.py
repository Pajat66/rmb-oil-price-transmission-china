"""Run the surviving Phase 2B, Phase 2C and S18 code against one sealed vintage."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from hashlib import sha256

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "reference"
CORE = ROOT / "analysis/2026-10/core_models/20261121T090611489399"
AUDIT_ROOT = ROOT / "private_work/validation_2026-10"
OLD = ROOT.parents[1] / "rmb-oil-price-transmission-china/05_revision/01_data"
NEW = ROOT / "data/processed/2026-10/01_data"
for folder in ("src/science", "src/s18"):
    sys.path.insert(0, str(ROOT / folder))
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np
import pandas as pd

PAIR_WINDOWS = (3, 6, 12)


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def check_numeric(actual, expected, *, atol=2e-12, rtol=2e-9):
    np.testing.assert_allclose(actual, expected, atol=atol, rtol=rtol, equal_nan=True)


def verify_core():
    receipt = json.loads((CORE / "reproduction.json").read_text(encoding="utf-8"))
    if receipt["baseline"] != "PASS" or receipt["frozen_failures"]:
        raise ValueError("Prior core reproduction is not accepted")
    for name, digest in receipt["outputs_sha256"].items():
        if sha(CORE / name) != digest:
            raise ValueError(f"Prior core output changed: {name}")
    for name, digest in receipt["inputs_and_code_sha256"].items():
        source = OLD / name.removeprefix("frozen/") if name.startswith("frozen/") else ROOT / name
        if sha(source) != digest:
            raise ValueError(f"Prior core input changed: {source}")
    return receipt


def prepare(vintage, work):
    from interface import seed_references
    from phase15_common import DATA
    from design_construction import build_link1
    from phase2b_core import load

    seed_references(work)
    source = OLD if vintage == "old" else NEW
    for sample in ("long", "short"):
        for layer in ("canonical", "transformed"):
            name = f"{sample}_sample_{layer}.csv"
            shutil.copy2(source / name, DATA / name)
    if vintage == "old":
        name = "phase2a75_design_SEASONAL_MECH1.csv"
        shutil.copy2(OLD / name, DATA / name)
    else:
        fit = build_link1(load("short"))
        fit["z"].loc[fit["valid"]].to_csv(DATA / "phase2a75_design_SEASONAL_MECH1.csv",
                                            index=False, encoding="utf-8-sig")


def cached_bootstrap(vintage):
    """Reuse only the previous core paths and validate them against the sealed report."""
    import phase2b_core as core

    scenario = "old" if vintage == "old" else "full_new"
    core_receipts = pd.read_csv(CORE / "inference_sensitivity.csv")
    core_receipts = core_receipts[(core_receipts.scenario == scenario) & (core_receipts.method == "MBB")]
    prior = ROOT / "private_work/core_models_2026-10/20261121T090611489399"

    def boot(designs, sample, block):
        recovered = {}
        for mid, ds in designs.items():
            if mid.startswith("PRIMARY_"):
                same_horizon = [path for name, path in designs.items() if name.startswith("PRIMARY_")]
                for h, d in enumerate(ds):
                    assert all(d["months"].reset_index(drop=True).equals(
                        other[h]["months"].reset_index(drop=True)) for other in same_horizon)
            if not mid.startswith(("PRIMARY_", "MECH2_")):
                continue
            file = prior / f"{'old' if vintage == 'old' else 'full'}_{sample}" / (
                f"phase2b_bootstrap_paths_{sample}_L{block}.npz")
            if not file.is_file():
                continue
            with np.load(file, allow_pickle=False) as paths:
                path = paths[mid]
            if path.shape != (core.B, len(ds)):
                raise ValueError(f"Invalid prior bootstrap shape: {mid} L={block}")
            points = np.array([d["fit"].params[d["j"]] for d in ds])
            for kind, values, estimates in [("period", path, points),
                                             ("cumulative", path.cumsum(axis=1), points.cumsum())]:
                expected = core_receipts.loc[(core_receipts.model == mid) &
                                             (core_receipts.block_length == block) &
                                             (core_receipts.response_type == kind)].sort_values("horizon")
                actual = pd.DataFrame([core.interval(values[:, h], estimates[h]) for h in range(len(ds))])
                check_numeric(estimates, expected.estimate)
                check_numeric(actual.valid_draws, expected.valid_draws, atol=0, rtol=0)
                check_numeric(actual.failed_draws, expected.failed_draws, atol=0, rtol=0)
                for local, reference in [("bootstrap_se", "bootstrap_se"), ("bootstrap_ci_low", "ci_low"),
                                         ("bootstrap_ci_high", "ci_high"), ("bootstrap_p", "bootstrap_p")]:
                    check_numeric(actual[local], expected[reference])
            recovered[mid] = path
        missing = {mid: ds for mid, ds in designs.items() if mid not in recovered}
        computed, failed = core.boot(missing, sample, block) if missing else ({}, [])
        for mid, path in recovered.items():
            failed.extend(dict(sample=sample, block_length=block, model=mid, horizon=int(h), draw=int(j),
                               reason="NUMERICAL_RANK_OR_N_FAILURE")
                          for j, h in np.argwhere(~np.isfinite(path)))
        all_paths = {**recovered, **computed}
        np.savez_compressed(core.DATA / f"phase2b_bootstrap_paths_{sample}_L{block}.npz", **all_paths)
        print(f"MBB {sample} L={block}: {len(recovered)} validated prior paths, {len(missing)} calculated", flush=True)
        return all_paths, failed

    return boot


def run_worker(vintage, key):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key):
        raise ValueError("Run key must be a simple directory name")
    verify_core()
    work = AUDIT_ROOT / key / vintage
    work.mkdir(parents=True)
    os.environ["RMB_R3_WORKDIR"] = str(work)
    prepare(vintage, work)

    import main_estimation
    from inference_ledger import finalize
    from stability_estimation import main as stability
    from stage1_estimation import estimate as s18_stage1
    from stage2_estimation import run as s18_stage2

    main_estimation.boot = cached_bootstrap(vintage)
    outputs = main_estimation.main()
    finalize(*outputs)
    print(f"PHASE2B_COMPLETE={work}", flush=True)
    stability()
    print(f"PHASE2C_COMPLETE={work}", flush=True)
    s18_stage1()
    summary = s18_stage2()
    (work / "s18" / "bootstrap_receipt.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"VALIDATION_WORKER_COMPLETE={work}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vintage", choices=("old", "new"))
    parser.add_argument("--run-key", required=True)
    args = parser.parse_args()
    run_worker(args.vintage, args.run_key)


if __name__ == "__main__":
    main()
