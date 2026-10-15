"""Fixed components restriction, collinearity, and exact stationary Link 1."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm,chi2
from statsmodels.stats.outliers_influence import variance_inflation_factor
from phase2b_core import *

def collinearity(d,mid):
    X=d['X'];names=d['cols'];Z=X[:,1:];Z=(Z-Z.mean(axis=0))/Z.std(axis=0,ddof=1)
    A=np.column_stack([np.ones(len(Z)),Z]);_,s,vh=np.linalg.svd(Z,full_matrices=False)
    eig=s*s;ci=s.max()/s;rawcond=np.linalg.cond(X);stdcond=np.linalg.cond(Z)
    parts=(vh.T**2)/eig;parts=parts/parts.sum(axis=1,keepdims=True)
    rows=[]
    for j,name in enumerate(names[1:]):
        vif=variance_inflation_factor(A,j+1)
        for k in range(len(eig)):
            rows.append(dict(model=mid,horizon=d['h'],term=name,N=len(X),VIF=vif,raw_condition_number=rawcond,standardized_condition_number=stdcond,dimension=k+1,eigenvalue=eig[k],condition_index=ci[k],variance_decomposition_proportion=parts[j,k],standardization='demean and sample-SD-scale nonintercept columns; intercept excluded from eigendecomposition'))
    return rows

def components_and_collinearity(primary,long):
    rows=[];diag=[]
    for mid,ds in primary.items():
        for d in ds:
            h=d['h'];y=d['y'];u=build(long,y,SHOCK,h,components=True)
            assert np.array_equal(d['valid'],u['valid'])
            assert np.allclose(long.dlog_oil_rmb,long.dlog_brent+long.dlog_fx,atol=1e-10,equal_nan=True)
            # Both models retain the SAME composite shock lag controls and outcome lag controls.
            for c in d['cols'][2:]: assert np.array_equal(d['z'][c].to_numpy(),u['z'][c].to_numpy(),equal_nan=True)
            f=u['fit'];r=hac(f,max(12,h+1));j=u['cols'].index('dlog_brent');k=u['cols'].index('dlog_fx')
            w=np.zeros(len(f.params));w[j]=1;w[k]=-1;diff=float(w@f.params);se=float(np.sqrt(w@r.cov_params()@w))
            rows.append(dict(outcome=y,horizon=h,N=int(f.nobs),restricted_coefficient=float(d['fit'].params[d['j']]),brent_coefficient=float(f.params[j]),fx_coefficient=float(f.params[k]),brent_hac_se=float(r.bse[j]),fx_hac_se=float(r.bse[k]),difference=diff,hac_se_difference=se,hac_ci_low=diff-norm.ppf(.975)*se,hac_ci_high=diff+norm.ppf(.975)*se,wald_chi2=(diff/se)**2,raw_p=float(2*norm.sf(abs(diff/se))),maxlags=max(12,h+1),identical_sample=True,identical_controls=True,restriction='current beta_Brent_h = beta_FX_h; composite shock lags1,2 retained in both',interpretation='rejection challenges composite restriction; nonrejection is compatibility, not proof of equality'))
            save(u['z'].loc[u['valid']],f'phase2b_design_COMPONENTS_{y}_h{h}.csv',DATA)
            if h in (0,3,6,12):diag+=collinearity(d,mid);diag+=collinearity(u,f'COMPONENTS_{y}')
    out=adjust(pd.DataFrame(rows),['outcome']);save(out,'lp_composite_components.csv');save(diag,'multicollinearity_diagnostics.csv')

def link1(short):
    exact=pd.read_csv(DATA/'phase2a75_design_SEASONAL_MECH1.csv',parse_dates=['month'])
    y='dlog_import_unit_price';cols=['const']+[f'{SHOCK}_lag{j}' for j in range(4)]
    original=pd.DataFrame({'month':short.month,y:short[y],'const':1.})
    for j in range(4):original[f'{SHOCK}_lag{j}']=calendar_lag(short,SHOCK,j)
    z=original.dropna();assert z.month.reset_index(drop=True).equals(exact.month)
    assert np.allclose(z[[y]+cols],exact[[y]+cols],atol=1e-12)
    rows=[]
    for q in (-1,0,1):
        z=exact[['month',y]+cols].copy();xc=cols.copy()
        if q>=0:
            for j in range(q+1):
                name=f'dlog_import_quantity_lag{j}';mapping=pd.Series(calendar_lag(short,'dlog_import_quantity',j).to_numpy(),index=short.month)
                z[name]=z.month.map(mapping);xc.append(name)
        z=z.dropna();assert z.month.equals(exact.month)
        save(z,f'phase2b_design_MECH1_quantity{q}.csv',DATA)
        f=sm.OLS(z[y].to_numpy(float),z[xc].to_numpy(float)).fit()
        for l in (12,6,18):
            r=hac(f,l);V=r.cov_params();coef=r.params
            for j in range(4):
                k=xc.index(f'{SHOCK}_lag{j}');ci=r.conf_int()[k]
                rows.append(dict(model=f'MECH1_quantity{q}',quantity_order=q,record_type='oil_lag',term=xc[k],lag=j,N=len(z),sample_start=z.month.min().strftime('%Y-%m'),sample_end=z.month.max().strftime('%Y-%m'),coefficient=coef[k],ols_se=f.bse[k],hc3_se=f.get_robustcov_results(cov_type='HC3').bse[k],hac_se=r.bse[k],hac_ci_low=ci[0],hac_ci_high=ci[1],raw_p=r.pvalues[k],maxlags=l))
            w=np.zeros(len(xc));w[1:5]=1;effect=float(w@coef);se=np.sqrt(w@V@w)
            rows.append(dict(model=f'MECH1_quantity{q}',quantity_order=q,record_type='cumulative',term='oil_lags0..3_sum',N=len(z),coefficient=effect,hac_se=se,hac_ci_low=effect-norm.ppf(.975)*se,hac_ci_high=effect+norm.ppf(.975)*se,raw_p=2*norm.sf(abs(effect/se)),maxlags=l))
            b=coef[1:5];C=V[1:5,1:5];wstat=float(b@np.linalg.inv(C)@b)
            rows.append(dict(model=f'MECH1_quantity{q}',quantity_order=q,record_type='joint',term='oil_lags0..3_joint_zero',N=len(z),wald_chi2=wstat,df=4,raw_p=chi2.sf(wstat,4),maxlags=l))
            save(pd.DataFrame(V,index=xc,columns=xc).reset_index(names='term'),f'phase2b_covariance_MECH1_q{q}_HAC{l}.csv')
    out=adjust(pd.DataFrame(rows),['model','maxlags','record_type']);save(out,'mechanism_link1_final.csv')
