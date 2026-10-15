"""S18 common-sample Stage1: 195 designs, IC and HAC Wald; execution reserved for R3."""
from pathlib import Path
import argparse,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/science'))
from interface import configure,require_r3,seed_references,prepare_designs
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--r3-authorized',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    if a.dry_run:
        from verify_results import verify as run
        print(run());return
    require_r3(a);work=configure(a.work_dir)
    if (work/'s18/stage1/lp_lag_period_hac.csv').exists():p.error('Stage1 output already exists')
    seed_references(work);prepare_designs(work)
    from stage1_estimation import estimate
    estimate()
if __name__=='__main__':main()
