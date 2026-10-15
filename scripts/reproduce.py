"""Quick verification and explicitly authorized private R3 scientific execution."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/science'))
from interface import configure,external_directory,require_r3,seed_references,prepare_designs

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['plan','quick','dry-run','prepare-data','main-lp','stability','s15','full'])
    p.add_argument('--raw-data-dir',type=Path)
    p.add_argument('--work-dir',type=Path)
    p.add_argument('--output-dir',type=Path)
    p.add_argument('--input-config',type=Path)
    p.add_argument('--r3-authorized',action='store_true')
    a=p.parse_args()
    if a.command=='plan':
        print((ROOT/'config/execution_plan.json').read_text(encoding='utf-8'));return
    if a.command in ('quick','dry-run'):
        from verify_results import verify
        print(json.dumps(verify(),indent=2));return
    require_r3(a)
    if not a.work_dir:p.error('--work-dir required')
    if a.command=='full' and not a.output_dir:p.error('--output-dir required before full execution')
    work=configure(a.work_dir)
    if a.command in ('prepare-data','full'):
        if not a.raw_data_dir:p.error('--raw-data-dir required')
        if work.exists() and any(work.iterdir()):p.error('data preparation requires a new empty work directory')
        from data_interface import prepare
        prepare(a.raw_data_dir,work,a.input_config)
    if a.command=='prepare-data':return
    seed_references(work)
    if a.command in ('main-lp','full'):
        if (work/'main_execution_receipt.json').exists():p.error('completed main output exists; use a new workspace')
        prepare_designs(work)
        from main_estimation import main as main_lp
        from inference_ledger import finalize
        result=main_lp();finalize(*result)
        (work/'main_execution_receipt.json').write_text(json.dumps({'status':'COMPUTED_AWAITING_R3_COMPARISON','B':5000,'seed':20261004}),encoding='utf-8')
    if a.command in ('stability','full'):
        if (work/'stability_execution_receipt.json').exists():p.error('completed stability output exists')
        from stability_estimation import main as stability
        stability()
        (work/'stability_execution_receipt.json').write_text(json.dumps({'status':'COMPUTED_AWAITING_R3_COMPARISON','B':5000,'formal_h':[0,3,6]}),encoding='utf-8')
    if a.command=='s15':
        from phase2c_core import YLIST,read_design
        from s15_diagnostics import diagnostics
        diagnostics({y:[read_design(f'PRIMARY_{y}',h) for h in range(13)] for y in YLIST})
    if a.command=='full':
        from stage1_estimation import estimate
        from stage2_estimation import run
        estimate();summary=run()
        (work/'s18/stage2/execution_summary.json').write_text(json.dumps(summary),encoding='utf-8')
        if not a.output_dir:p.error('--output-dir required for full export')
        sys.path.insert(0,str(ROOT/'scripts'))
        from s18_stage3 import rebuild
        rebuild(work/'s18/stage1',work/'s18/stage2',external_directory(a.output_dir,'output directory',create=True)/'S18 Table.xlsx')
        from assemble_tables import assemble
        assemble(work)
        print('Numerical chains and final table CSVs computed. Rebind figure source CSVs to new statistics, export, and compare before any Full Reproduction PASS.')

if __name__=='__main__':main()
