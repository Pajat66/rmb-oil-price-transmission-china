"""Original S18 numerical kernels; no run/freeze/editorial entry point. Not executed in R2A."""
import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

TARGET=5000


BLOCK=12


def generate(rng,B,n):
    starts=rng.integers(0,n-BLOCK+1,size=(B,int(np.ceil(n/BLOCK))))
    index=(starts[:,:,None]+np.arange(BLOCK)).reshape(B,-1)[:,:n]
    return starts,index


def counts_from(index,n):
    counts=np.zeros((len(index),n),dtype=float)
    np.add.at(counts,(np.arange(len(index))[:,None],index),1)
    return counts


def fit_batch(index,designs):
    n=designs[0]["ncalendar"]
    counts=counts_from(index,n)
    shape=(len(index),5,3,13)
    path=np.full(shape,np.nan)
    ranks=np.zeros(shape,dtype=np.uint8)
    cond=np.full(shape,np.nan)
    status=np.ones(shape,dtype=np.uint8)
    nobs=np.zeros((len(index),13),dtype=np.uint16)
    failures=[]
    for d in designs:
        w=counts[:,d["valid"]]
        X,Y=d["X"],d["Y"]
        k=X.shape[1]
        gram=np.einsum("bi,ij,ik->bjk",w,X,X,optimize=True)
        xy=np.einsum("bi,ij,i->bj",w,X,Y,optimize=True)
        singular=np.linalg.svd(gram,compute_uv=False)
        rank=(singular>singular[:,0,None]*k*np.finfo(float).eps).sum(axis=1)
        condition=np.divide(singular[:,0],singular[:,-1],out=np.full(len(index),np.inf),where=singular[:,-1]>0)
        N=w.sum(axis=1)
        if d["pi"]==d["yi"]==0:nobs[:,d["h"]]=N.astype(np.uint16)
        else:assert np.array_equal(N,nobs[:,d["h"]])
        ok=(rank==k)&(N>k)
        beta=np.full((len(index),k),np.nan)
        if ok.any():
            try:beta[ok]=np.linalg.solve(gram[ok],xy[ok])
            except np.linalg.LinAlgError:
                for i in np.where(ok)[0]:
                    try:beta[i]=np.linalg.solve(gram[i],xy[i])
                    except np.linalg.LinAlgError:ok[i]=False
        ok &= np.isfinite(beta).all(axis=1)
        key=(slice(None),d["pi"],d["yi"],d["h"])
        path[key]=beta[:,1]
        ranks[key]=rank.astype(np.uint8)
        cond[key]=condition
        status[key]=np.where(ok,0,1)
        for i in np.flatnonzero(~ok):
            failures.append(dict(batch_draw=int(i),p=d["p"],outcome=d["outcome"],horizon=d["h"],N=int(N[i]),k=k,rank=int(rank[i]),
                gram_condition_number=float(condition[i]),reason="RANK_OR_N_OR_SOLVE_FAILURE"))
    good=(status==0).all(axis=(1,2,3))&np.isfinite(path).all(axis=(1,2,3))
    return dict(path=path,ranks=ranks,condition=cond,status=status,N=nobs,good=good,failures=failures)


def scalar_interval(draws,point):
    assert len(draws)==TARGET and np.isfinite(draws).all()
    lo,hi=np.quantile(draws,[.025,.975],method="linear")
    count=int(np.count_nonzero(np.abs(draws-point)>=abs(point)))
    return dict(ci_low=float(lo),ci_high=float(hi),bootstrap_se=float(np.std(draws,ddof=1)),
        raw_p=(1+count)/(len(draws)+1),null_tail_count=count,valid_draws=len(draws),interval_type="95% pointwise paired MBB percentile; L12",test_type="two-sided null-centered plus-one")


def adjust(rows,group):
    d=pd.DataFrame(rows)
    for key,ids in d.groupby(group,sort=False).groups.items():
        p=d.loc[ids,"raw_p"]
        assert p.notna().all()
        d.loc[ids,"bh_q"]=multipletests(p,method="fdr_bh")[1]
        d.loc[ids,"holm_p"]=multipletests(p,method="holm")[1]
        d.loc[ids,"family_size"]=len(ids)
        d.loc[ids,"family"]=str(key)
    d["reject_bh_05"]=d.bh_q<.05
    d["reject_holm_05"]=d.holm_p<.05
    if "ci_low" in d:
        d["positive_CI"]=d.ci_low>0
        d["support"]=np.where((d.point_estimate>0)&d.positive_CI&d.reject_bh_05,"L12_CI_AND_BH_POSITIVE_SUPPORT",
            np.where(d.positive_CI|d.reject_bh_05,"CI_TEST_OR_FDR_DISAGREEMENT_OR_DIRECTION_CHECK","NO_CORRECTED_SUPPORT"))
    return d

