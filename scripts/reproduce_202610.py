"""Rebuild the October 2026 input matrices and, optionally, the core estimates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src/science", "src/s18"):
    sys.path.insert(0, str(ROOT / folder))


def rebuild(args):
    import monthly_update as update
    update.RAW = args.historical_raw.resolve()
    update.NEW = args.update_raw.resolve()
    from monthly_update_audit import canonical, yoy
    from transformation_layer import transform

    historical, _, customs_old, _, _ = update.historical()
    recent, customs_new, _, _, _ = update.incoming()
    levels = update.reconcile(historical, recent, customs_old, customs_new)
    from phase15_common import load_canonical
    data = args.output / "01_data"
    data.mkdir()
    samples = (("long", "1998-01", 346), ("short", "2015-01", 142))
    for name, _, _ in samples:
        base = canonical(levels[name], name)
        base.to_csv(data / f"{name}_sample_canonical.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    long_base = load_canonical("long")
    frames = {}
    for name, start, count in samples:
        base = load_canonical(name)
        assert len(base) == count
        assert pd.DatetimeIndex(base.month).equals(pd.date_range(start, "2026-10", freq="MS"))
        transformed = transform(base)
        target = data / f"{name}_sample_transformed.csv"
        transformed.to_csv(target, index=False, encoding="utf-8-sig", lineterminator="\n")
        aligned = yoy(base, long_base if name == "short" else None)
        prices = ["fuel_power_inflation", "ppi_inflation", "cpi_inflation"]
        aligned = pd.concat([base, aligned.drop(columns="month"), transformed[prices]], axis=1)
        aligned.to_csv(data / f"{name}_sample_yoy_aligned.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
        frames[name] = pd.read_csv(target, parse_dates=["month"])
        print(f"Rebuilt {name}: {len(base)} months", flush=True)
    return frames


def core(args, frames):
    import phase2b_core as kernels
    from reestimate_core_202610 import fit_lp, fit_link1, csv
    policy = json.loads((ROOT / "config/phase2b_prespecified_inference_policy.json").read_text(encoding="utf-8"))
    assert (kernels.SEED, kernels.B, kernels.BLOCKS) == (
        policy["seed"], policy["replications"], tuple(policy["block_lengths"]))
    print(f"Formal MBB: B={kernels.B}, seed={kernels.SEED}, blocks={kernels.BLOCKS}", flush=True)
    for sample in ("long", "short"):
        case = args.output / sample
        bundle = fit_lp(frames[sample], kernels, policy, sample, case)
        for name, frame in bundle.items():
            if frame is not None:
                csv(frame, case / f"{name}.csv")
        print(f"Completed {sample}: {len(bundle['period'])} period equations", flush=True)
    link1, dates = fit_link1(frames["short"], args.output / "short")
    csv(link1, args.output / "link1.csv")
    csv(pd.DataFrame([dates], columns=["sample_start", "sample_end"]), args.output / "link1_dates.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-raw", type=Path, default=ROOT / "data/raw/historical", help="Historical exports with paths and hashes from config/raw_inputs.json")
    parser.add_argument("--update-raw", type=Path, default=ROOT / "data/raw/october", help="October-vintage exports from config/monthly_update_202610.json")
    parser.add_argument("--output", type=Path, required=True, help="New directory for results")
    parser.add_argument("--core", action="store_true", help="Refit the 39 core LPs and customs models, including the formal bootstrap")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True)
    os.environ["RMB_R3_WORKDIR"] = str(args.output)
    frames = rebuild(args)
    if args.core:
        core(args, frames)
    hashes = {path.relative_to(args.output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(args.output.rglob("*")) if path.is_file()}
    (args.output / "sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

