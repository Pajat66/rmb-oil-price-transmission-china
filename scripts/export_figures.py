"""Read saved Figure 5–7 statistics; no fitting or resampling is performed.
The formal drawing modules in src/plotting include the 2026-10-15 visual redesign.
"""
from pathlib import Path
import argparse,csv,hashlib,json,sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/plotting'))
def verified(path):
    path=Path(path).resolve()
    rows=json.loads((ROOT/'validation/checksums/files.json').read_text())
    key=path.relative_to(ROOT).as_posix()
    record=next(r for r in rows if r['target_path']==key)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==record['target_sha256'],key
    return path
def read(path):return pd.read_csv(verified(path),float_precision='round_trip')
def inputs(number,prepare_plot=False):
    if number==5:
        with verified(ROOT/'figures/source/figure_5_brent_fx_components_source.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        assert len(rows)==39
        return (rows,),{'saved_rows':39,'horizons':list(range(13))}
    if number==6:
        source=read(ROOT/'figures/source/figure_6_import_cost_innovative_source.csv')
        link=read(ROOT/'reference/statistics/mechanism_link1_final.csv')
        selected=link[(link.quantity_order==-1)&(link.maxlags==12)]
        lags=selected[selected.record_type=='oil_lag'].sort_values('lag')
        total=selected[selected.record_type=='cumulative'].iloc[0]
        assert lags.lag.tolist()==[0.,1.,2.,3.]
        assert np.isclose(lags.coefficient.sum(),total.coefficient,rtol=0,atol=1e-14)
        path=verified(ROOT/'reference/bootstrap/phase2b_bootstrap_paths_short_L12.npz')
        draws={};kdes={};matched=0
        with np.load(path,allow_pickle=False) as arrays:
            for label,y in [('Fuel','d_fuel_power_inflation'),('PPI','d_ppi_inflation')]:
                a=arrays[f'MECH2_{y}_quantity0'];assert a.shape==(5000,13) and np.isfinite(a).all()
                cumulative=np.cumsum(a,axis=1)
                for h in range(13):
                    d=cumulative[:,h];r=source[(source.outcome==label)&(source.lag_or_horizon.astype(str)==str(h))].iloc[0]
                    assert np.allclose(np.quantile(d,[.025,.975],method='linear'),[r.ci_low,r.ci_high],rtol=0,atol=1e-14)
                    draws[(label,h)]=d
                    if prepare_plot:
                        from scipy.stats import gaussian_kde
                        kdes[(label,h)]=gaussian_kde(d,bw_method='scott')
                    matched+=1
        return (source,draws,kdes,lags,total),{'saved_interval_pairs_verified':matched,'KDE_rule_for_render':'Scott','KDE_executed':prepare_plot,'saved_paths_only':True}
    source=read(ROOT/'figures/source/figure_7_temporal_stability_source.csv')
    summary=read(ROOT/'figures/source/figure_7_temporal_stability_recursive_summary.csv')
    formal=source[source.diagnostic_type.isin(['SUP_WALD','RECURSIVE_CUSUM','HANSEN'])].copy()
    formal['test']=formal.diagnostic_type
    assert len(formal)==27 and sorted(formal.horizon.unique())==[0,3,6]
    return (source,summary,formal),{'saved_formal_tests':27,'formal_horizons':[0,3,6],'descriptive_horizons':[0,3,6,12]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--figure',type=int,choices=[5,6,7],required=True);p.add_argument('--validate-only',action='store_true');p.add_argument('--output-dir',type=Path);a=p.parse_args()
    args,checks=inputs(a.figure,prepare_plot=not a.validate_only)
    if a.validate_only:
        print(json.dumps({'figure':a.figure,'status':'PASS_FROZEN_INPUT_INTERFACE_ONLY','estimation':False,'resampling':False,'checks':checks,'render_equivalence':'PENDING_R3_EXECUTION'}));return
    if not a.output_dir:p.error('--output-dir is required for export')
    a.output_dir.mkdir(parents=True,exist_ok=False)
    module=__import__(f'figure{a.figure}_plot')
    function=module.draw if a.figure==5 else module.plot
    fig,qa=function(*args)
    fig.savefig(a.output_dir/f'Figure {a.figure}.png',dpi=300)
    fig.savefig(a.output_dir/f'Figure {a.figure}.svg')
    (a.output_dir/'render_checks.json').write_text(json.dumps({'figure':a.figure,'checks':checks,'plot_geometry':qa,'source_reproduction':'PENDING_R3_EXECUTION'},indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
if __name__=='__main__':main()
