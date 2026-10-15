"""S18 shared MBB: fixed seed 2026101202, B5000, L12; execution reserved for R3."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/science'))
from interface import configure,require_r3
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--r3-authorized',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    if a.dry_run:
        from verify_results import verify as run
        print(run());return
    require_r3(a);work=configure(a.work_dir)
    if (work/'s18/stage2/lag_stage2_period_draws.npz').exists():p.error('Stage2 output already exists')
    from stage2_estimation import run
    summary=run()
    (work/'s18/stage2/execution_summary.json').write_text(json.dumps(summary),encoding='utf-8')
if __name__=='__main__':main()
