"""Explicit private input/work/output locations and frozen policy preparation."""
from pathlib import Path
import hashlib, json, os, shutil, sys

PACKAGE = Path(__file__).resolve().parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def external_directory(path, role, create=False):
    p=Path(path).expanduser().resolve()
    protected=[PACKAGE]
    protected += [q for q in PACKAGE.parent.iterdir() if q.is_dir() and (q.name.startswith(('R1','R2','R3')) or q.name=='rmb-oil-price-transmission-china')]
    if p==PACKAGE.parent:raise ValueError('Use a separate new work/output directory, not the project root')
    if any(p==q.resolve() or p.is_relative_to(q.resolve()) for q in protected):
        raise ValueError(f'{role} must be outside candidate and protected source directories')
    if create:p.mkdir(parents=True,exist_ok=True)
    return p

def configure(work):
    work=external_directory(work,'work directory')
    os.environ['RMB_R3_WORKDIR']=str(work)
    os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
    os.environ.setdefault('MKL_NUM_THREADS','1')
    os.environ.setdefault('OMP_NUM_THREADS','1')
    for sub in ('src/science','src/s18','src/plotting'):
        sys.path.insert(0,str(PACKAGE/sub))
    return work

def seed_references(work):
    for name in ('01_data','03_tables','00_audit','05_logs'):(work/name).mkdir(parents=True,exist_ok=True)
    copies={
        'reference/registries/phase2a_sample_frame_registry.csv':'00_audit/phase2a_sample_frame_registry.csv',
        'reference/statistics/lp_stationary_preHAC.csv':'03_tables/lp_stationary_preHAC.csv',
        'reference/registries/phase2a9_lp_readiness_registry.csv':'00_audit/phase2a9_lp_readiness_registry.csv',
        'reference/registries/phase2b_primary_model_registry.csv':'00_audit/phase2b_primary_model_registry.csv',
        'reference/statistics/lp_final_coefficients.csv':'03_tables/lp_final_coefficients.csv',
        'reference/statistics/lp_cumulative_response.csv':'03_tables/lp_cumulative_response.csv',
        'config/phase2b_prespecified_inference_policy.json':'00_audit/phase2b_prespecified_inference_policy.json',
        'config/phase2c_prespecified_policy.json':'00_audit/phase2c_prespecified_policy.json'}
    for src,dst in copies.items():
        out=work/dst
        if not out.exists():shutil.copy2(PACKAGE/src,out)
    return copies

def prepare_designs(work):
    """R3 only: rebuild formal designs, and verify source numerical seals."""
    import numpy as np
    import pandas as pd
    from design_construction import build_design as build,YLIST,SHOCK,build_link1
    from phase15_common import calendar_lag,DATA
    def load(sample):
        d=pd.read_csv(DATA/f'{sample}_sample_transformed.csv',parse_dates=['month'])
        assert pd.PeriodIndex(d.month,freq='M').equals(pd.period_range(d.month.min(),d.month.max(),freq='M'))
        return d
    def save(frame,name,folder):
        frame.to_csv(folder/name,index=False,encoding='utf-8-sig')
    long,short=load('long'),load('short')
    seals=json.loads((PACKAGE/'reference/registries/design_array_seals.json').read_text(encoding='utf-8'))
    def ah(a):
        return hashlib.sha256(np.ascontiguousarray(a,dtype='<f8').tobytes()).hexdigest()
    for y in YLIST:
        for h in range(13):
            d=build(long,y,SHOCK,h)
            key=f'PRIMARY_{y}_h{h}'
            seal=seals[key]
            if ah(d['X'])!=seal['X_sha256'] or ah(d['Y'])!=seal['Y_sha256']:
                raise ValueError('Exact design seal mismatch: '+key+'; stop, do not silently substitute vintage')
            save(d['z'].loc[d['valid']],f'phase2b_design_{key}.csv',DATA)
    link=build_link1(short)
    z=link['z'].loc[link['valid']];cols=link['cols']
    seal=seals['LINK1']
    if ah(z[cols].to_numpy(float))!=seal['X_sha256'] or ah(z.dlog_import_unit_price.to_numpy(float))!=seal['Y_sha256']:
        raise ValueError('Exact Link1 design seal mismatch; stop')
    save(z,'phase2a75_design_SEASONAL_MECH1.csv',DATA)

def require_r3(args):
    if not args.r3_authorized:
        raise SystemExit('PENDING_R3_AUTHORIZATION: full/data execution requires --r3-authorized after explicit R3 approval. R2B permits quick/dry-run/frozen export only.')
