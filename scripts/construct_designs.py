"""Export true designs after a successful, hash-bound six-object data gate.
No frozen CSVs or inference modules are read or imported.
"""
from pathlib import Path
import argparse,hashlib,json,sys
sys.dont_write_bytecode=True
PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE/'src/science'))
from interface import configure,external_directory,sha

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',required=True,type=Path)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--data-gate-receipt',required=True,type=Path)
    args=parser.parse_args();work=configure(args.work_dir)
    gate=json.loads(args.data_gate_receipt.read_text())
    if gate['status']!='PASS_ALL_SIX_ANALYSIS_OBJECTS' or len(gate['new_object_sha256'])!=6:
        raise ValueError('All six rebuilt objects must pass before design construction')
    for name,expected in gate['new_object_sha256'].items():
        if sha(work/'01_data'/name)!=expected:raise ValueError('Data changed since gate: '+name)
    out=external_directory(args.output_dir,'pure design output',create=True)
    if any(out.iterdir()):raise ValueError('Use a new empty output directory')
    import numpy as np
    import pandas as pd
    sys.path.insert(0,str(PACKAGE/'src/s18'))
    from design_construction import build_design,build_link1,YLIST,SHOCK
    from common_designs import construct
    from stage1_helpers import array_hash,month_hash
    long=pd.read_csv(work/'01_data/long_sample_transformed.csv',parse_dates=['month'])
    short=pd.read_csv(work/'01_data/short_sample_transformed.csv',parse_dates=['month'])
    designs=[(f'PRIMARY_{y}_h{h}',build_design(long,y,SHOCK,h),'raw') for y in YLIST for h in range(13)]
    common=pd.read_csv(work/'01_data/long_sample_transformed.csv',parse_dates=['month'],float_precision='round_trip')
    designs += [(f"S18_{d['outcome']}_h{d['h']}_p{d['p']}",d,'shape') for d in construct(common)]
    designs.append(('LINK1',build_link1(short),'raw'))
    records=[]
    for key,d,kind in designs:
        months=pd.PeriodIndex(d['months'],freq='M').astype(str).tolist()
        np.savez_compressed(out/f'{key}.npz',X=d['X'],Y=d['Y'],valid=d['valid'],columns=np.array(d['cols']),months=np.array(months))
        def digest(a):return array_hash(a) if kind=='shape' else hashlib.sha256(np.ascontiguousarray(a,dtype='<f8').tobytes()).hexdigest()
        records.append({'model':key,'N':len(d['Y']),'columns':d['cols'],'start':months[0],'end':months[-1],'month_sha256':month_hash(months),'X_sha256':digest(d['X']),'Y_sha256':digest(d['Y']),'hash_rule':'shape prefix + little endian float64 C bytes' if kind=='shape' else 'little endian float64 C bytes'})
    (out/'design_registry.json').write_text(json.dumps({'status':'CONSTRUCTED_ONLY_NOT_ESTIMATED','data_gate_sha256':sha(args.data_gate_receipt),'designs':records,'real_fits':0},indent=2))
    print(f'Constructed {len(records)} designs; no inference executed')
if __name__=='__main__':main()
