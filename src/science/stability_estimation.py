"""Formal DWB h0/3/6, windows, secondary stability and S15; R3 gate in CLI."""
import numpy as np
import pandas as pd
from phase2c_core import *
from phase2c_windows import primary_windows,regime_paths,mechanism_windows
from s15_diagnostics import diagnostics
def main():
    ds={y:[read_design(f'PRIMARY_{y}',h) for h in range(13)] for y in YLIST}
    provenance=[]
    for y,aa in ds.items():
        for h,d in enumerate(aa):
            provenance.append(dict(outcome=y,horizon=h,path=str(d['source'].relative_to(REV)),sha256=digest(d['source']),N=len(d['z']),columns=';'.join(d['cols'])))
    save(provenance,'phase2c_frozen_input_registry.csv',AUDIT)
    rec,roll,hier=primary_windows(ds)
    br=[];par=[];profiles=[];cusp=[];fail=[]
    for y,aa in ds.items():
        for h in (0,3,6):
            r,p,g,c,f=null_bootstrap(aa[h],aa,y,h);br.append(r);par+=p;profiles+=g;cusp+=c;fail+=f
    br=pd.DataFrame(br);br['raw_p']=br.bootstrap_p;br['family']='nine primary outcome-horizon break tests';br=adjust(br,['family']);br['detected_break']=br.fdr_q<.05
    par=pd.DataFrame(par);par['raw_p']=par.bootstrap_p;par=adjust(par,['test'])
    save(br,'structural_break_supwald.csv');save(par,'parameter_stability_tests.csv');save(profiles,'phase2c_break_search_profile.csv');save(cusp,'phase2c_cusum_paths.csv')
    save(pd.DataFrame(fail,columns=['outcome','horizon','draw','reason']),'phase2c_bootstrap_failures.csv',LOGS)
    paths,broad=regime_paths(ds,br)
    m1,m2=mechanism_windows();leads,reverse=diagnostics(ds)
    from stability_summary import finalize
    return finalize(ds,rec,roll,hier,br,par,paths,broad,m1,m2,leads,reverse)
