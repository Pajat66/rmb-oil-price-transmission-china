"""Original S15 scientific diagnostics, without private runner/protection entry point.
Not executed in R2A. Uses the same isolated work-directory interface as LPs.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2
from phase2c_core import *

def diagnostics(designs):
    leads=[];reverse=[]
    for y,ds in designs.items():
        d=ds[0];z=d['z'].copy();monthmap=pd.Series(z[SHOCK].to_numpy(),index=pd.PeriodIndex(z.month,freq='M'))
        for j in (1,2,3):z[f'oil_lead{j}']=monthmap.reindex(pd.PeriodIndex(z.month,freq='M')+j).to_numpy()
        z=z.dropna();cols=d['cols']+[f'oil_lead{j}' for j in (1,2,3)]
        f=sm.OLS(z.response.to_numpy(float),z[cols].to_numpy(float)).fit();r=hac(f,12)
        save(z,f'phase2c_design_placebo_{y}.csv',DATA)
        for j in (1,2,3):
            k=cols.index(f'oil_lead{j}');ci=r.conf_int()[k]
            leads.append(dict(outcome=y,record_type='individual_lead',lead=j,N=len(z),coefficient=float(r.params[k]),hac_se=float(r.bse[k]),hac_ci_low=float(ci[0]),hac_ci_high=float(ci[1]),raw_p=float(r.pvalues[k]),maxlags=12,current_oil_control=True,interpretation='conditional anticipatory association diagnostic; exogeneity not identified'))
        ix=[cols.index(f'oil_lead{j}') for j in (1,2,3)];b=r.params[ix];C=r.cov_params()[np.ix_(ix,ix)];w=float(b@np.linalg.inv(C)@b);p=float(chi2.sf(w,3))
        leads.append(dict(outcome=y,record_type='joint_leads1..3',N=len(z),wald_chi2=w,df=3,raw_p=p,maxlags=12,current_oil_control=True,interpretation='anticipatory association detected; reinforce endogeneity limitation' if p<.05 else 'no strong evidence of anticipatory association in this diagnostic; exogeneity not identified'))
        for j in (1,2,3):
            zz=d['z'].copy();zz['future_oil']=monthmap.reindex(pd.PeriodIndex(zz.month,freq='M')+j).to_numpy();zz=zz.dropna()
            # Same past controls; retain current oil as forecast baseline, add current price change.
            xc=d['cols']+['response'];fr=sm.OLS(zz.future_oil.to_numpy(float),zz[xc].to_numpy(float)).fit();rr=hac(fr,12);k=xc.index('response');ci=rr.conf_int()[k]
            reverse.append(dict(outcome=y,future_horizon=j,N=len(zz),coefficient=float(rr.params[k]),hac_se=float(rr.bse[k]),hac_ci_low=float(ci[0]),hac_ci_high=float(ci[1]),raw_p=float(rr.pvalues[k]),maxlags=12,dependent='future dlog_oil_rmb',predictor='current '+y,controls='current oil; oil lags1,2; price outcome lags1,2; constant',interpretation='secondary reverse predictive association; no causal identification'))
            save(zz,f'phase2c_design_reverse_{y}_lead{j}.csv',DATA)
    leads=pd.DataFrame(leads);parts=[]
    for typ,g in leads.groupby('record_type'):
        parts.append(adjust(g,['outcome'] if typ=='individual_lead' else ['record_type']))
    leads=save(pd.concat(parts,ignore_index=True),'future_shock_placebo.csv');reverse=save(adjust(pd.DataFrame(reverse),['outcome']),'reverse_predictive_diagnostic.csv')
    return leads,reverse

