"""Phase2C reads saved Phase2B designs. No variable construction/model selection."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from statsmodels.stats.diagnostic import breaks_hansen
from phase15_common import ROOT,REV,DATA,TABLES,AUDIT,LOGS
from phase2b_core import save,digest,hac,adjust,YLIST,SHOCK

SEED=2026100402
B=5000
SUMMARY_H=(0,3,6,12)
WINDOWS=(120,96,144)

def read_design(mid,h=None):
    name=f'phase2b_design_{mid}'+(f'_h{h}' if h is not None else '')+'.csv'
    z=pd.read_csv(DATA/name,parse_dates=['month'])
    assert not z.isna().any().any()
    assert pd.PeriodIndex(z.month,freq='M').equals(pd.period_range(z.month.min(),z.month.max(),freq='M'))
    # Link1 uses its original dependent-variable column; all LP designs use response.
    dep='response' if 'response' in z else 'dlog_import_unit_price'
    cols=[c for c in z.columns if c not in ('month',dep)]
    return {'z':z,'cols':cols,'dep':dep,'mid':mid,'h':h,'source':DATA/name}

def estimate(d,z=None,l=12,term=SHOCK,weight=None):
    z=d['z'] if z is None else z
    assert len(z)>=60, 'Inferential window below 60 is forbidden'
    X=z[d['cols']].to_numpy(float);y=z[d['dep']].to_numpy(float)
    f=sm.OLS(y,X).fit();r=hac(f,l)
    w=np.zeros(len(d['cols']))
    if weight is not None:w=np.asarray(weight)
    else:w[d['cols'].index(term)]=1
    beta=float(w@f.params);se=float(np.sqrt(w@r.cov_params()@w))
    ci=norm.ppf(.975)*se
    influence=(X@np.linalg.inv(X.T@X)@w)*f.resid*np.sqrt(len(z)/(len(z)-X.shape[1]))
    return dict(coefficient=beta,hac_se=se,hac_ci_low=beta-ci,hac_ci_high=beta+ci,raw_p=float(2*norm.sf(abs(beta/se))),N=len(z),start=z.month.min().strftime('%Y-%m'),end=z.month.max().strftime('%Y-%m'),maxlags=l),influence,f

def hac_var(v,l=12):
    ans=float(v@v)
    for j in range(1,min(l,len(v)-1)+1):ans+=2*(1-j/(l+1))*float(v[j:]@v[:-j])
    return max(ans,0.)

def scalar_result(value,v,l=12):
    se=np.sqrt(hac_var(v,l));a=norm.ppf(.975)*se
    return dict(estimate=float(value),hac_se=float(se),ci_low=float(value-a),ci_high=float(value+a),raw_p=float(2*norm.sf(abs(value/se))) if se>0 else np.nan,maxlags=l)

def candidate_grid(ds,h,trim=.15):
    z=ds[h]['z'];n=len(z);out=[]
    for k in range(int(np.ceil(trim*n)),int(np.floor((1-trim)*n))+1):
        day=z.month.iloc[k-1]
        if all((d['z'].month<=day).sum()>=60 and (d['z'].month>day).sum()>=60 for d in ds):out.append(k)
    return np.array(out,dtype=int)

def prefix_setup(X,candidates):
    prefix=np.cumsum(np.einsum('ni,nj->nij',X,X),axis=0)
    left=prefix[candidates-1];right=prefix[-1]-left
    assert np.all(np.linalg.matrix_rank(left)==X.shape[1]) and np.all(np.linalg.matrix_rank(right)==X.shape[1])
    return np.linalg.inv(left),np.linalg.inv(right),np.linalg.inv(prefix[-1])

def supwald(Y,X,candidates,setup):
    """Classical full-coefficient Wald=p*Chow F, calibrated by dependent-wild null bootstrap.

    Every draw refits unrestricted segments and restricted equation at every date.
    No classical F critical values are used for unknown-break inference.
    """
    Y=np.atleast_2d(Y);n,p=X.shape;il,ir,iall=setup
    xy=np.cumsum(Y[:,:,None]*X[None,:,:],axis=1);left=xy[:,candidates-1,:];right=xy[:,-1,None,:]-left
    lquad=np.einsum('bci,cij,bcj->bc',left,il,left,optimize=True)
    rquad=np.einsum('bci,cij,bcj->bc',right,ir,right,optimize=True)
    rss_split=(Y*Y).sum(axis=1)[:,None]-lquad-rquad
    rss_null=(Y*Y).sum(axis=1)-np.einsum('bi,ij,bj->b',xy[:,-1],iall,xy[:,-1],optimize=True)
    assert (rss_split>0).all()
    W=np.maximum(0,(rss_null[:,None]-rss_split)/(rss_split/(n-2*p)))
    return W,W.max(axis=1)

def recursive_operator(X,skip=60):
    n,p=X.shape;R=np.zeros((n-skip,n));inv=np.linalg.inv(X[:skip].T@X[:skip])
    for t in range(skip,n):
        row=X[t];v=inv@row;den=1+row@v
        R[t-skip,t]=1/np.sqrt(den);R[t-skip,:t]=-(X[:t]@v)/np.sqrt(den)
        inv-=np.outer(v,v)/den
    return R

def cusumstat(Y,operator):
    rr=np.atleast_2d(Y)@operator.T;n=rr.shape[1]
    scaled=rr/rr.std(axis=1,ddof=1)[:,None]
    path=np.cumsum(scaled,axis=1)
    upper=.948*np.sqrt(n)+2*.948*np.arange(n)/np.sqrt(n)
    return np.max(np.abs(path)/upper,axis=1),path,upper

def hansen_batch(Y,X):
    # Linear transformation of X leaves Hansen statistic invariant; improve conditioning.
    X=X.copy();X[:,1:]=(X[:,1:]-X[:,1:].mean(axis=0))/X[:,1:].std(axis=0,ddof=1)
    inv=np.linalg.inv(X.T@X);betas=np.atleast_2d(Y)@X@inv;u=np.atleast_2d(Y)-betas@X.T
    sq=u*u;ft=np.concatenate([u[:,:,None]*X[None,:,:],(sq-sq.mean(axis=1)[:,None])[:,:,None]],axis=2)
    cs=ft.cumsum(axis=1);F=len(X)*np.einsum('bni,bnj->bij',ft,ft,optimize=True);S=np.einsum('bni,bnj->bij',cs,cs,optimize=True)
    return np.trace(np.linalg.solve(F,S),axis1=1,axis2=2)

def null_bootstrap(d,ds,outcome,h):
    z=d['z'];X=z[d['cols']].to_numpy(float);Y=z[d['dep']].to_numpy(float);n,p=X.shape
    f=sm.OLS(Y,X).fit();lev=np.sum(X*(X@np.linalg.inv(X.T@X)),axis=1)
    residual=f.resid/np.sqrt(1-lev);residual-=residual.mean()
    candidates=candidate_grid(ds,h);setup=prefix_setup(X,candidates)
    W,maxw=supwald(Y,X,candidates,setup);best=int(candidates[np.argmax(W[0])])
    operator=recursive_operator(X);cu,cp,upper=cusumstat(Y,operator);ha=float(breaks_hansen(f)[0])
    assert np.isclose(ha,hansen_batch(Y,X)[0],rtol=1e-8)
    # Gaussian MA(12) multipliers have exactly Bartlett covariance through lag12.
    rng=np.random.default_rng(np.random.SeedSequence([SEED,YLIST.index(outcome),h]))
    maxima=[];cumstats=[];hanstats=[];preview=[];fail=[]
    for a in range(0,B,250):
        m=min(250,B-a);e=rng.standard_normal((m,n+12))
        c=np.cumsum(np.pad(e,((0,0),(1,0))),axis=1);multipliers=(c[:,13:]-c[:,:-13])/np.sqrt(13)
        ystar=f.fittedvalues[None,:]+residual[None,:]*multipliers
        _,w=supwald(ystar,X,candidates,setup);cc,_,_=cusumstat(ystar,operator);hh=hansen_batch(ystar,X)
        ok=np.isfinite(w)&np.isfinite(cc)&np.isfinite(hh)
        for i in np.where(~ok)[0]:fail.append(dict(outcome=outcome,horizon=h,draw=a+int(i),reason='NUMERICAL_NONFINITE'))
        maxima.extend(w);cumstats.extend(cc);hanstats.extend(hh)
        if a==0:preview=ystar[0].copy()
    maxima=np.array(maxima);cumstats=np.array(cumstats);hanstats=np.array(hanstats)
    np.savez_compressed(DATA/f'phase2c_null_bootstrap_{outcome}_h{h}.npz',supwald=maxima,cusum=cumstats,hansen=hanstats,first_null_draw=preview,candidates=candidates,seed=SEED)
    pval=lambda a,v:float((1+np.sum(a[np.isfinite(a)]>=v))/(1+np.isfinite(a).sum()))
    br=dict(outcome=outcome,horizon=h,candidate_break_date=z.month.iloc[best-1].strftime('%Y-%m'),first_post_date=z.month.iloc[best].strftime('%Y-%m'),max_statistic=float(maxw[0]),bootstrap_p=pval(maxima,maxw[0]),trim=.15,N=n,n_pre=best,n_post=n-best,n_candidates=len(candidates),df=p,bootstrap_B=B,seed=SEED,bootstrap_method='null-imposed fixed-design dependent Gaussian wild; MA13 Bartlett lag12; HC2 residuals',statistic_definition='all-parameter classical Wald = p*Chow F; bootstrap calibrated, no classical critical values',date_definition='last pre-break shock-origin month; not a confidence-set estimate')
    tests=[dict(outcome=outcome,horizon=h,test='RECURSIVE_CUSUM',statistic=float(cu[0]),bootstrap_p=pval(cumstats,cu[0]),classical_95_boundary_ratio=1.,classical_reject=bool(cu[0]>1),N=n,initial_N=60,calibration='same null dependent-wild bootstrap; BDE classical boundary auxiliary'),dict(outcome=outcome,horizon=h,test='HANSEN',statistic=ha,bootstrap_p=pval(hanstats,ha),classical_95_critical=1.9,classical_reject=bool(ha>1.9),N=n,calibration='same null dependent-wild bootstrap; conventional six-regressor critical auxiliary')]
    profile=[dict(outcome=outcome,horizon=h,candidate_break_date=z.month.iloc[k-1].strftime('%Y-%m'),statistic=float(v),n_pre=int(k),n_post=n-int(k)) for k,v in zip(candidates,W[0])]
    cusumrows=[dict(outcome=outcome,horizon=h,month=z.month.iloc[60+i].strftime('%Y-%m'),cusum=float(v),lower_95=float(-upper[i]),upper_95=float(upper[i])) for i,v in enumerate(cp[0])]
    print(f'stability {outcome} h{h}: supW={maxw[0]:.3f}, p={br["bootstrap_p"]:.4f}, candidate={br["candidate_break_date"]}',flush=True)
    return br,tests,profile,cusumrows,fail
