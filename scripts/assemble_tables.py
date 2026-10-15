"""Build Tables1-6 and S1-S17 CSV/payload from computed results in a private workspace."""
from pathlib import Path
import argparse,csv,json,shutil,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/science'))
from interface import configure

def assemble(work):
    work=configure(work)
    mapping=json.loads((ROOT/'metadata/table_input_mapping.json').read_text(encoding='utf-8'))
    for name,r in mapping.items():
        if r['role']=='HISTORICAL_REFERENCE':
            out=work/'03_tables'/name
            if not out.exists():shutil.copy2(ROOT/r['path'],out)
    # This provenance table describes the local source receipt, without inferring historical queries.
    source_log=work/'00_audit/source_log_resolution.csv'
    if not source_log.exists():
        receipt=json.loads((work/'input_receipt.json').read_text(encoding='utf-8'))
        with source_log.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['key','relative_path','sha256']);writer.writeheader();writer.writerows(receipt['files'])
    from table_assembly import main
    main(work)
    return work/'03_final_tables'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',type=Path,required=True);a=p.parse_args()
    print(assemble(a.work_dir))
if __name__=='__main__':main()
