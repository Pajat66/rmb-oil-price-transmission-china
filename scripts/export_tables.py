"""Export frozen tables or newly computed CSVs without estimation."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/science'))
from interface import external_directory
from xlsx_export import read_csv,write_workbook
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-dir',type=Path,default=ROOT/'tables');p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--si',action='store_true');a=p.parse_args()
    out=external_directory(a.output_dir,'output directory',create=True)
    if a.si:
        index=json.loads((ROOT/'metadata/si_sheet_index.json').read_text(encoding='utf-8'))
        for n in range(1,18):
            selected=[r for r in index if r['id'].startswith(f'S{n}_')]
            write_workbook([(r['sheet'],read_csv(a.source_dir/(r['id']+'.csv'))) for r in selected],out/f'S{n} Table.xlsx')
    else:
        for n in range(1,7):
            candidates=[a.source_dir/f'Table {n}.csv',a.source_dir/f'MAIN_TABLE_{n}.csv']
            source=next((p for p in candidates if p.is_file()),None)
            if source is None:raise FileNotFoundError(f'Table {n} CSV missing')
            write_workbook([(f'Table {n}',read_csv(source))],out/f'Table {n}.xlsx')
    print('CSV export complete; no statistical estimation. Frozen journal originals retained separately.')
if __name__=='__main__':main()
