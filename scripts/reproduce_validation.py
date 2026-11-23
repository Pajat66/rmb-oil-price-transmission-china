"""Run the sealed October inference and stability kernels from rebuilt input matrices."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("rebuilt", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
work = args.output.resolve()
work.mkdir(parents=True)
os.environ["RMB_R3_WORKDIR"] = str(work)
root = Path(__file__).resolve().parents[1]
for folder in ("src/science", "src/s18"):
    sys.path.insert(0, str(root / folder))

from interface import seed_references
seed_references(work)
for sample in ("long", "short"):
    for layer in ("canonical", "transformed"):
        name = f"{sample}_sample_{layer}.csv"
        shutil.copyfile(args.rebuilt / "01_data" / name, work / "01_data" / name)
from design_construction import build_link1
from phase2b_core import load
fit = build_link1(load("short"))
fit["z"].loc[fit["valid"]].to_csv(work / "01_data/phase2a75_design_SEASONAL_MECH1.csv", index=False, encoding="utf-8-sig")
from main_estimation import main
from inference_ledger import finalize
finalize(*main())
print("PHASE2B complete", flush=True)
from stability_estimation import main as stability
stability()
print("PHASE2C complete", flush=True)
from stage1_estimation import estimate
from stage2_estimation import run
estimate()
summary = run()
(work / "s18/bootstrap_receipt.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("S18 complete", flush=True)

from validation_202610_support import historical
historical(work)
