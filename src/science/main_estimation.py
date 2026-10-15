"""Frozen primary and secondary LP scientific orchestration. Explicit R3 gate in CLI."""
from datetime import datetime,timezone
import hashlib,json
import numpy as np
import pandas as pd
from scipy.stats import chi2
from phase2b_core import *
def main():
    policy=json.loads((AUDIT/"phase2b_prespecified_inference_policy.json").read_text(encoding="utf-8"))
    long,short=load('long'),load('short')
    primary={f'PRIMARY_{y}':[build(long,y,SHOCK,h) for h in range(13)] for y in YLIST}
    secondary={};shortsets={}
    for y in YLIST[:2]:
        for q in (False,True):
            mid=f'MECH2_{y}_quantity{int(q)}';shortsets[mid]=[build(short,y,'dlog_import_unit_price',h,q) for h in range(13)]
    # Oil->CPI is the existing primary model; three distinct secondary shocks.
    for x in ('d_fuel_power_inflation','d_ppi_inflation'):
        mid=f'TERMINAL_{x}';secondary[mid]=[build(long,YLIST[2],x,h) for h in range(13)]
    shortsets['TERMINAL_dlog_import_unit_price']=[build(short,YLIST[2],'dlog_import_unit_price',h) for h in range(13)]
    allsets={**primary,**secondary,**shortsets}
    registry=[];rows=[];sens=[];design_audit=[]
    frozen=pd.read_csv(TABLES/'lp_stationary_preHAC.csv');allow=pd.read_csv(AUDIT/'phase2a9_lp_readiness_registry.csv')
    for mid,ds in allsets.items():
        group='PRIMARY' if mid in primary else ('ROBUSTNESS' if 'quantity1' in mid else 'SECONDARY')
        for d in ds:
            rows.append(result(d,mid,group));f=d['fit'];h=d['h']
            monthhash=hashlib.sha256('|'.join(d['months'].dt.strftime('%Y-%m')).encode()).hexdigest()
            registry.append(dict(model=mid,status=group,outcome=d['y'],shock=d['shock'],horizon=h,sample='long' if mid in primary or mid in secondary else 'short',N=int(f.nobs),terms=';'.join(d['cols']),lag_policy='shock1,2;outcome1,2;fixed',sample_hash=monthhash))
            save(d['z'].loc[d['valid']],f'phase2b_design_{mid}_h{h}.csv',DATA)
            for tag,l in [('PRIMARY',max(12,h+1)),('HAC6_OVERLAP',max(6,h+1)),('HAC12_PLUS_H',12+h)]:
                r=hac(f,l);j=d['j'];ci=r.conf_int()[j]
                sens.append(dict(model=mid,outcome=d['y'],horizon=h,policy=tag,maxlags=l,coefficient=float(f.params[j]),hac_se=float(r.bse[j]),ci_low=float(ci[0]),ci_high=float(ci[1]),raw_p=float(r.pvalues[j])))
            if mid in primary:
                a=frozen[(frozen.dependent_variable==d['y'])&(frozen.horizon==h)&(frozen.response_type=='period_response')].iloc[0]
                rid=f"LP_{d['y']}_period_response_h{h}";prior=allow[allow.model_id==rid].iloc[0]
                design_audit.append(dict(model=mid,horizon=h,coefficient_delta=float(f.params[d['j']]-a.shock_coefficient),N_match=int(f.nobs)==a.N,dates_match=d['months'].min().strftime('%Y-%m')==a.start and d['months'].max().strftime('%Y-%m')==a.end,terms_match=';'.join(d['cols'])==prior.mean_terms,sample_hash_match=monthhash==prior.sample_hash))
    # Archive every prior DLM/SARIMAX/YoY equation, explicitly overriding earlier candidate roles.
    registry.extend([dict(model='MECH1_OIL_IMPORT_p3',status='SECONDARY',terms='const;dlog_oil_rmb_lag0..3',reason='exact saved stationary design'),dict(model='MECH1_QUANTITY_q0_q1',status='ROBUSTNESS',reason='fixed quantity sensitivity'),dict(model='COMPOSITE_COMPONENTS',status='ROBUSTNESS',reason='replace current composite only; retain composite lag controls'),dict(model='PANDEMIC_N9',status='ARCHIVED',reason='DROP_FROM_INFERENTIAL_TABLES'),dict(model='MANTEL',status='ARCHIVED',reason='SUPPORTING_INFORMATION_ONLY')])
    save(registry,'phase2b_primary_model_registry.csv',AUDIT)
    save(design_audit,'phase2b_frozen_design_checks.csv',AUDIT)
    R=adjust(pd.DataFrame(rows),['model']);S=adjust(pd.DataFrame(sens),['model','policy'])
    save(R[R.group=='PRIMARY'],'lp_final_coefficients.csv');save(S[S.model.isin(primary)],'lp_final_hac_sensitivity.csv')
    save(R[R.group=='PRIMARY'],'lp_multiple_testing.csv');save(S,'phase2b_all_lp_hac_sensitivity.csv')
    save(R,'phase2b_all_lp_period_results.csv')
    boots={};fails=[]
    for l in BLOCKS:
        bp,ff=boot({**primary,**secondary},'long',l);boots[l]=bp;fails+=ff
        bp,ff=boot(shortsets,'short',l);boots[l].update(bp);fails+=ff
    save(pd.DataFrame(fails,columns=['sample','block_length','model','horizon','draw','reason']),'phase2b_bootstrap_failures.csv',LOGS)
    cirows=[];cumrows=[];cumhac=[];covrows=[];cumhacsensitivity=[]
    for mid,ds in allsets.items():
        point=R[R.model==mid].sort_values('horizon').coefficient.to_numpy();cp=np.cumsum(point)
        for h in range(13):
            C=cov_path(ds[:h+1],max(12,h+1));se=np.sqrt(np.ones(h+1)@C@np.ones(h+1));p=2*norm.sf(abs(cp[h]/se))
            cumhac.append(dict(model=mid,horizon=h,cumulative_effect=cp[h],hac_se=se,hac_ci_low=cp[h]-norm.ppf(.975)*se,hac_ci_high=cp[h]+norm.ppf(.975)*se,raw_p=p,maxlags=max(12,h+1)))
            for tag,l in [('PRIMARY',max(12,h+1)),('HAC6_OVERLAP',max(6,h+1)),('HAC12_PLUS_H',12+h)]:
                C=cov_path(ds[:h+1],l);se=np.sqrt(C.sum())
                cumhacsensitivity.append(dict(model=mid,horizon=h,policy=tag,maxlags=l,cumulative_effect=cp[h],hac_se=se,hac_ci_low=cp[h]-norm.ppf(.975)*se,hac_ci_high=cp[h]+norm.ppf(.975)*se,raw_p=2*norm.sf(abs(cp[h]/se))))
        for l in BLOCKS:
            path=boots[l][mid];cum=np.cumsum(path,axis=1)
            C=np.cov(path[np.isfinite(path).all(axis=1)].T,ddof=1)
            for i in range(13):
                for j in range(13):covrows.append(dict(model=mid,block_length=l,horizon_i=i,horizon_j=j,covariance=C[i,j]))
            for h in range(13):
                cirows.append(dict(model=mid,outcome=ds[0]['y'],horizon=h,block_length=l,coefficient=point[h],**interval(path[:,h],point[h])))
                cumrows.append(dict(model=mid,outcome=ds[0]['y'],horizon=h,block_length=l,cumulative_effect=cp[h],**interval(cum[:,h],cp[h])))
    CI=pd.DataFrame(cirows);CU=pd.DataFrame(cumrows);CH=adjust(pd.DataFrame(cumhac),['model'])
    save(CI[CI.model.isin(primary)],'lp_bootstrap_ci.csv');save(CU[CU.model.isin(primary)].merge(CH,on=['model','horizon','cumulative_effect']),'lp_cumulative_response.csv')
    save(CI,'phase2b_all_lp_bootstrap_ci.csv');save(CU,'phase2b_all_lp_cumulative_bootstrap.csv');save(CH,'phase2b_all_lp_cumulative_hac.csv');save(covrows,'phase2b_bootstrap_path_covariance.csv')
    save(adjust(pd.DataFrame(cumhacsensitivity),['model','policy']),'phase2b_all_lp_cumulative_hac_sensitivity.csv')
    joint=[]
    for mid in primary:
        point=R[R.model==mid].sort_values('horizon').coefficient.to_numpy()
        for l in BLOCKS:
            path=boots[l][mid];path=path[np.isfinite(path).all(axis=1)]
            for window,hs in policy['joint_windows'].items():
                C=np.cov(path[:,hs].T);C=np.atleast_2d(C);rank=np.linalg.matrix_rank(C);inv=np.linalg.pinv(C)
                b=point[hs];w=float(b@inv@b);e=path[:,hs]-b;ww=np.einsum('bi,ij,bj->b',e,inv,e)
                joint.append(dict(model=mid,outcome=mid.replace('PRIMARY_',''),block_length=l,window=window,horizons=','.join(map(str,hs)),null='all listed period coefficients = 0',wald_statistic=w,covariance_rank=rank,df=len(hs),chi2_p=float(chi2.sf(w,rank)),raw_p=(1+np.count_nonzero(ww>=w))/(len(path)+1),method='full path bootstrap covariance; centered bootstrap Wald calibration',valid_draws=len(path)))
    J=adjust(pd.DataFrame(joint),['model','block_length']);save(J,'lp_joint_tests.csv')
    hierarchy=[];shares=[]
    points={y:np.cumsum(R[R.model==f'PRIMARY_{y}'].sort_values('horizon').coefficient.to_numpy()) for y in YLIST}
    for l in BLOCKS:
        paths={y:np.cumsum(boots[l][f'PRIMARY_{y}'],axis=1) for y in YLIST}
        for h in (3,6,12):
            for a,b in ((YLIST[0],YLIST[1]),(YLIST[0],YLIST[2]),(YLIST[1],YLIST[2])):
                diff=points[a][h]-points[b][h]
                hierarchy.append(dict(contrast=f'{a} minus {b}',horizon=h,block_length=l,difference=diff,**interval(paths[a][:,h]-paths[b][:,h],diff)))
        for h in (3,6):
            den=np.abs(paths[YLIST[0]][:,h])+np.abs(paths[YLIST[1]][:,h]);valid=np.isfinite(den)&(den>0)
            for y in YLIST[:2]:
                vals=np.abs(paths[y][valid,h])/den[valid];lo,med,hi=np.quantile(vals,[.025,.5,.975])
                shares.append(dict(outcome=y,horizon=h,block_length=l,point_share=abs(points[y][h])/(abs(points[YLIST[0]][h])+abs(points[YLIST[1]][h])),median=med,ci_low=lo,ci_high=hi,ci_width=hi-lo,valid_draws=len(vals),zero_denominator_draws=int(np.sum(den==0)),failed_draws=int(np.sum(~np.isfinite(den))),interpretation='normalized descriptive shares; NOT structural pass-through weights',recommendation='DELETE_HEADLINE_PERCENTAGES' if hi-lo>.2 else 'DESCRIPTIVE_WITH_CI_ONLY'))
    H=pd.DataFrame(hierarchy);H['raw_p']=H.bootstrap_p;H=adjust(H,['block_length']);save(H,'price_hierarchy_tests.csv');save(shares,'relative_pass_through_bootstrap.csv')
    from phase2b_diagnostics import components_and_collinearity,link1
    components_and_collinearity(primary,long);link1(short)
    for y,tag in zip(YLIST[:2],['fuel','ppi']):
        mids=[m for m in shortsets if m.startswith(f'MECH2_{y}')]
        out=R[R.model.isin(mids)].merge(CI[CI.model.isin(mids)],on=['model','outcome','horizon','coefficient']).merge(CU[CU.model.isin(mids)],on=['model','outcome','horizon','block_length'],suffixes=('','_cumulative')).merge(CH[CH.model.isin(mids)],on=['model','horizon','cumulative_effect'],suffixes=('','_cumulative_hac'))
        save(out,f'mechanism_lp_{tag}.csv')
    terminal=R[(R.model.str.startswith('TERMINAL_'))|(R.model=='PRIMARY_d_cpi_inflation')].copy();terminal['interpretation']='downstream association / response; no causal mediation';save(terminal,'terminal_cpi_lp.csv')
    return R,S,CI,CU,CH,J,H,shares
