"""Rebuild S18 from eight CSV inputs and an empty OOXML layout.

The layout contains no saved cell values, formulas or shared strings. All data,
headings, definitions and 762 formulas are written anew. No XLSX snapshot, saved
payload, Word, PDF, Node or proprietary spreadsheet runtime is read.
"""
from pathlib import Path
import argparse,hashlib,json,math,sys,zipfile
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/s18'))
sys.path.insert(0,str(ROOT/'src/science'))
from interface import external_directory
import csv_payload
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('',NS)
Q=lambda name:'{'+NS+'}'+name

def letter(n):
    result=''
    while n:n,r=divmod(n-1,26);result=chr(65+r)+result
    return result

def rebuild(stage1_dir,stage2_dir,output):
    stage1_dir=Path(stage1_dir).resolve();stage2_dir=Path(stage2_dir).resolve();output=Path(output).resolve()
    external_directory(output.parent,'output directory',create=True)
    if output.exists():raise FileExistsError('Use a new output filename; frozen files are never overwritten')
    if output.is_relative_to(stage1_dir) or output.is_relative_to(stage2_dir):raise ValueError('Output must be outside CSV source directories')
    csv_payload.S1=stage1_dir;csv_payload.S2=stage2_dir
    summary_path=stage2_dir/'execution_summary.json'
    if summary_path.is_file():
        summary=json.loads(summary_path.read_text(encoding='utf-8'))
        if (summary.get('attempted'),summary.get('effective'),summary.get('rejected'))!=(5000,5000,0):
            raise ValueError('Frozen S18 explanatory text assumes 5000 attempts and zero rejected draws; reconcile new execution evidence before export')
    csv_payload.POLICY_HASHES=json.loads((ROOT/'config/source_policy_fingerprints.json').read_text(encoding='utf-8'))['original_policy_sha256']
    payload=csv_payload.build_payload()
    layout=json.loads((ROOT/'config/s18_ooxml_layout.json').read_text(encoding='utf-8'))
    trees={s['name']:ET.fromstring(layout['parts'][s['part']]) for s in layout['sheets']}
    cells={};rows={}
    for name,tree in trees.items():
        sd=tree.find(Q('sheetData'));rows[name]={int(r.attrib['r']):r for r in sd}
        cells[name]={c.attrib['r']:c for r in sd for c in r}
        if any(len(c) for c in cells[name].values()):raise ValueError('Layout contains forbidden saved cell payload')
    formula_count=0;payload_count=0
    def put(sheet,row,col,value,formula=None):
        coord=letter(col)+str(row)
        if coord not in cells[sheet]:
            rd=rows[sheet].get(row)
            if rd is None:
                rd=ET.SubElement(trees[sheet].find(Q('sheetData')),Q('row'),r=str(row));rows[sheet][row]=rd
            cell=ET.SubElement(rd,Q('c'),r=coord);cells[sheet][coord]=cell
        cell=cells[sheet][coord]
        for child in list(cell):cell.remove(child)
        cell.attrib.pop('t',None)
        if formula:
            cell.set('t','str');ET.SubElement(cell,Q('f')).text=formula.lstrip('=');ET.SubElement(cell,Q('v')).text=str(value)
        elif isinstance(value,bool):
            cell.set('t','b');ET.SubElement(cell,Q('v')).text='1' if value else '0'
        elif isinstance(value,(int,float)):
            if not math.isfinite(value):raise ValueError('Nonfinite Excel payload')
            ET.SubElement(cell,Q('v')).text=repr(value)
        elif value is not None:
            cell.set('t','inlineStr');ET.SubElement(ET.SubElement(cell,Q('is')),Q('t')).text=str(value)
    for spec in payload['sheets']:
        sheet=spec['sheet'];hr=spec['header_row']
        put(sheet,hr-3,1,spec['title']);put(sheet,hr-2,1,spec['note'])
        for col,value in enumerate(spec['headers'],1):put(sheet,hr,col,value)
        flags={int(k):int(v) for k,v in spec['flag_columns'].items()}
        for r,data in enumerate(spec['rows'],spec['first_data_row']):
            for j,value in enumerate(data):
                if j in flags:
                    f=f'=IF({letter(flags[j]+1)}{r}<0.05,"Yes","No")'
                    calculated='Yes' if data[flags[j]]<.05 else 'No'
                    if calculated!=value:raise ValueError('CSV rejection flag disagrees with p/q threshold')
                    put(sheet,r,j+1,calculated,f);formula_count+=1
                else:put(sheet,r,j+1,value)
                payload_count+=1
    if len(trees)!=8 or formula_count!=762 or payload_count!=8302:
        raise ValueError(f'S18 structure mismatch: {len(trees)}, {formula_count}, {payload_count}')
    parts=layout['parts'].copy()
    for sheet in layout['sheets']:parts[sheet['part']]=ET.tostring(trees[sheet['name']],encoding='unicode')
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,text in parts.items():z.writestr(name,text.encode('utf-8'))
    input_files=sorted({(stage1_dir if src.startswith('S1/') else stage2_dir)/src.split('/',1)[1] for spec in payload['sheets'] for src in spec['sources']})
    receipt={'status':'GENERATED_FROM_CSV_AWAITING_COMPARISON','sheets':list(trees),'payload_cells':payload_count,'formulas':formula_count,
             'inputs':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in input_files],
             'snapshot_read':False,'saved_payload_read':False,'estimation':False,'bootstrap':False,
             'native_excel_recalculation':'NOT_EXECUTED; simple IF caches computed from rebuilt CSV values',
             'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    output.with_suffix('.row_trace.json').write_text(json.dumps(payload['trace'],indent=2,ensure_ascii=False),encoding='utf-8')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage1-dir',type=Path,required=True);p.add_argument('--stage2-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    print(json.dumps(rebuild(a.stage1_dir,a.stage2_dir,a.output_dir/'S18 Table.xlsx'),indent=2))
if __name__=='__main__':main()
