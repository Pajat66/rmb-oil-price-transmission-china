"""Frozen Phase 2B designs and prespecified inference. No transformation/lag search."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests
from phase15_common import ROOT, REV, DATA, TABLES, AUDIT, LOGS, calendar_lag, calendar_lead

SEED=20261004
B=5000
BLOCKS=(12,6,18)
YLIST=['d_fuel_power_inflation','d_ppi_inflation','d_cpi_inflation']
SHOCK='dlog_oil_rmb'

def save(rows,name,folder=TABLES):
    out=rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)
    out.to_csv(folder/name,index=False,encoding='utf-8-sig')
    return out

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def load(sample):
    d=pd.read_csv(DATA/f'{sample}_sample_transformed.csv',parse_dates=['month'])
    assert pd.PeriodIndex(d.month,freq='M').equals(pd.period_range(d.month.min(),d.month.max(),freq='M'))
    return d

def build(df,y,shock,h,quantity=False,components=False):
    from design_construction import build_design
    design=build_design(df,y,shock,h,quantity,components)
    design['fit']=sm.OLS(design['Y'],design['X']).fit()
    return design

def hac(f,l): return f.get_robustcov_results(cov_type='HAC',maxlags=l,kernel='bartlett',use_correction=True,use_t=False)

def result(d,mid,group):
    f=d['fit'];j=d['j'];h=d['h'];l=max(12,h+1);r=hac(f,l);hc=f.get_robustcov_results(cov_type='HC3',use_t=False)
    ci=r.conf_int()[j]
    return dict(model=mid,group=group,outcome=d['y'],shock=d['shock'],horizon=h,N=int(f.nobs),sample_start=d['months'].min().strftime('%Y-%m'),sample_end=d['months'].max().strftime('%Y-%m'),coefficient=float(f.params[j]),ols_se=float(f.bse[j]),hc3_se=float(hc.bse[j]),hac_se=float(r.bse[j]),hac_ci_low=float(ci[0]),hac_ci_high=float(ci[1]),raw_p=float(r.pvalues[j]),maxlags=l,kernel='Bartlett',small_sample_correction=True,use_t=False)

def adjust(df,by,p='raw_p'):
    df=df.copy();df['fdr_q']=np.nan;df['holm_p']=np.nan
    for _,ix in df.groupby(by).groups.items():
        df.loc[ix,'fdr_q']=multipletests(df.loc[ix,p],method='fdr_bh')[1]
        df.loc[ix,'holm_p']=multipletests(df.loc[ix,p],method='holm')[1]
    return df

def cov_path(designs,bandwidth):
    # Observation-level OLS influences retain distinct h-specific N and dates.
    V=[]
    for d in designs:
        f=d['fit'];a=(d['X']@np.linalg.inv(d['X'].T@d['X'])[:,d['j']])*f.resid
        a*=np.sqrt(f.nobs/(f.nobs-len(f.params)))
        v=np.zeros(d['ncalendar']);v[d['valid']]=a;V.append(v)
    V=np.array(V).T;C=V.T@V
    for l in range(1,bandwidth+1):
        g=V[l:].T@V[:-l];C+=(1-l/(bandwidth+1))*(g+g.T)
    return C

def boot(design_sets,sample,block):
    """Moving-block pairs bootstrap of calendar-indexed LP observation vectors.

    Lag/lead pairs are created before resampling; no synthetic lag at block joins.
    Shared draw indices across equations preserve hierarchy/path covariance.
    Weighted OLS using row multiplicities exactly refits the duplicated data.
    """
    n=next(iter(design_sets.values()))[0]['ncalendar']
    rng=np.random.default_rng(np.random.SeedSequence([SEED,block,0 if sample=='long' else 1]))
    starts=rng.integers(0,n-block+1,size=(B,int(np.ceil(n/block))))
    indices=(starts[:,:,None]+np.arange(block)).reshape(B,-1)[:,:n]
    assert all(np.all(np.diff(indices[:,a:min(a+block,n)],axis=1)==1) for a in range(0,n,block))
    np.savez_compressed(DATA/f'phase2b_bootstrap_indices_{sample}_L{block}.npz',indices=indices,starts=starts,seed=SEED)
    paths={};failures=[]
    for mid,ds in design_sets.items():
        path=np.full((B,13),np.nan)
        for a in range(0,B,250):
            ix=indices[a:a+250];counts=np.zeros((len(ix),n))
            np.add.at(counts,(np.arange(len(ix))[:,None],ix),1)
            for h,d in enumerate(ds):
                w=counts[:,d['valid']];X=d['X'];Y=d['Y']
                xx=np.einsum('bi,ij,ik->bjk',w,X,X,optimize=True)
                xy=np.einsum('bi,ij,i->bj',w,X,Y,optimize=True)
                ok=(np.linalg.matrix_rank(xx)==X.shape[1])&(w.sum(axis=1)>X.shape[1])
                beta=np.full((len(ix),X.shape[1]),np.nan)
                if ok.any(): beta[ok]=np.linalg.solve(xx[ok],xy[ok])
                path[a:a+len(ix),h]=beta[:,d['j']]
                for k in np.where(~ok)[0]: failures.append(dict(sample=sample,block_length=block,model=mid,horizon=h,draw=a+int(k),reason='NUMERICAL_RANK_OR_N_FAILURE'))
        paths[mid]=path
        print(f'bootstrap {sample} L={block} {mid}: {np.isfinite(path).all(axis=1).sum()}/{B}',flush=True)
    np.savez_compressed(DATA/f'phase2b_bootstrap_paths_{sample}_L{block}.npz',**paths)
    return paths,failures

def interval(draws,point):
    good=np.asarray(draws);good=good[np.isfinite(good)]
    lo,hi=np.quantile(good,[.025,.975]);err=good-point
    # Null-centered two-sided bootstrap test, plus-one Monte Carlo correction.
    p=(1+np.count_nonzero(np.abs(err)>=abs(point)))/(len(good)+1)
    return dict(bootstrap_se=float(np.std(good,ddof=1)),bootstrap_ci_low=float(lo),bootstrap_ci_high=float(hi),basic_ci_low=float(2*point-hi),basic_ci_high=float(2*point-lo),bootstrap_p=float(p),valid_draws=len(good),failed_draws=B-len(good))
