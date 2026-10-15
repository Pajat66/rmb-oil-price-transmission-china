"""Frozen rolling/recursive paths, cross-equation hierarchy and mechanism windows."""
import numpy as np
import pandas as pd
from phase2c_core import *

def primary_windows(designs):
    rec=[];roll=[];hier=[];cache={}
    def get(y,h,start,end):
        key=(y,h,str(start),str(end))
        if key not in cache:
            d=designs[y][h];z=d['z'];z=z[(z.month>=start)&(z.month<=end)]
            r,v,_=estimate(d,z);cache[key]=(r,v)
        return cache[key]
    for y,ds in designs.items():
        for h in SUMMARY_H:
            d=ds[h];z=d['z'];months=z.month
            for e in range(119,len(z)):
                r,_,_=estimate(d,z.iloc[:e+1]);cache[(y,h,str(months.iloc[0]),str(months.iloc[e]))]=(r,estimate(d,z.iloc[:e+1])[1])
                rec.append(dict(outcome=y,horizon=h,end_date=r['end'],last_response_date=(months.iloc[e]+pd.DateOffset(months=h)).strftime('%Y-%m'),hac12_se=r['hac_se'],**r))
            for window in WINDOWS:
                for e in range(window-1,len(z)):
                    r,v,_=estimate(d,z.iloc[e-window+1:e+1]);cache[(y,h,str(months.iloc[e-window+1]),str(months.iloc[e]))]=(r,v)
                    roll.append(dict(outcome=y,horizon=h,window=window,role='PRIMARY' if window==120 else 'SENSITIVITY',last_response_date=(months.iloc[e]+pd.DateOffset(months=h)).strftime('%Y-%m'),**r))
        print(f'windows {y} complete',flush=True)
    # Hierarchy windows have common shock-origin dates across outcomes/horizons.
    for h in (3,6):
        common=designs[YLIST[0]][h]['z'].month.reset_index(drop=True)
        for method,window in [('recursive',120)]+[('rolling',w) for w in WINDOWS]:
            for e in range(window-1,len(common)):
                start=common.iloc[0 if method=='recursive' else e-window+1];end=common.iloc[e]
                per={};cum={};vp={};vc={}
                for y in YLIST:
                    rr=[];vv=[]
                    for k in range(h+1):
                        r,v=get(y,k,start,end);rr.append(r['coefficient']);vv.append(v)
                    per[y]=rr[h];cum[y]=sum(rr);vp[y]=vv[h];vc[y]=np.sum(vv,axis=0)
                for response,point,vec in [('period',per,vp),('cumulative',cum,vc)]:
                    for a,b in ((YLIST[0],YLIST[1]),(YLIST[0],YLIST[2]),(YLIST[1],YLIST[2])):
                        value=point[a]-point[b];r=scalar_result(value,vec[a]-vec[b])
                        hier.append(dict(method=method,window=window,horizon=h,response_type=response,contrast=f'{a} minus {b}',start=start.strftime('%Y-%m'),end=end.strftime('%Y-%m'),N=len(vp[a]),uncertainty='full paired cross-equation/horizon Bartlett HAC12; pointwise, overlapping windows not independent',**r))
    save(rec,'recursive_lp_coefficients.csv');save(roll,'rolling_lp_coefficients.csv');save(hier,'hierarchy_stability.csv')
    return pd.DataFrame(rec),pd.DataFrame(roll),pd.DataFrame(hier)

def regime_paths(designs,breaks):
    significant=breaks[breaks.detected_break]
    rows=[];sums=[];origins=[]
    dates=sorted(significant.candidate_break_date.unique())
    for day in dates:
        scenario=f'FORMAL_BREAK_{day}';origins.append(dict(scenario=scenario,break_date=day,source=';'.join(f'{r.outcome}:h{r.horizon}' for r in significant[significant.candidate_break_date==day].itertuples()),selection='BH-FDR<.05 among nine formal bootstrap tests'))
        for y,ds in designs.items():
            for side in ('pre','post'):
                rrows=[];vecs=[]
                fullmonths=ds[0]['z'].month
                for h,d in enumerate(ds):
                    z=d['z'];z=z[z.month<=pd.Timestamp(day) if side=='pre' else z.month>pd.Timestamp(day)]
                    r,v,_=estimate(d,z,l=max(12,h+1));rrows.append(r)
                    padded=np.zeros(len(fullmonths));pos=fullmonths.isin(z.month).to_numpy();padded[pos]=v;vecs.append(padded)
                    rows.append(dict(scenario=scenario,break_date=day,outcome=y,period=side,horizon=h,post_selection=True,**r))
                for h in range(13):sums.append(dict(scenario=scenario,break_date=day,outcome=y,period=side,horizon=h,post_selection=True,N=rrows[h]['N'],**scalar_result(sum(r['coefficient'] for r in rrows[:h+1]),np.sum(vecs[:h+1],axis=0),max(12,h+1))))
    # An empty file with explicit schema is meaningful: no corrected-significant break.
    path=pd.DataFrame(rows,columns=['scenario','break_date','outcome','period','horizon','post_selection','coefficient','hac_se','hac_ci_low','hac_ci_high','raw_p','N','start','end','maxlags'])
    if len(path):path=adjust(path,['scenario','outcome','period'])
    save(path,'break_subsample_lp.csv');save(pd.DataFrame(sums,columns=['scenario','break_date','outcome','period','horizon','post_selection','N','estimate','hac_se','ci_low','ci_high','raw_p','maxlags']),'phase2c_break_cumulative.csv')
    save(pd.DataFrame(origins,columns=['scenario','break_date','source','selection']),'phase2c_break_period_registry.csv',AUDIT)
    if len(path): broad=path.copy();broad['period_policy']='data-driven formal break, exploratory post-selection HAC'
    else:
        common=designs[YLIST[0]][12]['z'].month;split=common.iloc[len(common)//2-1];b=[]
        for y,ds in designs.items():
            for h,d in enumerate(ds):
                for side in ('first_half','second_half'):
                    z=d['z'];z=z[z.month.isin(common)];z=z[z.month<=split if side=='first_half' else z.month>split]
                    r,_,_=estimate(d,z,l=max(12,h+1));b.append(dict(scenario='EQUAL_HALVES_COMMON_H12_CALENDAR',break_date=split.strftime('%Y-%m'),outcome=y,period=side,horizon=h,post_selection=False,period_policy='prespecified equal halves fallback; no regime story',**r))
        broad=adjust(pd.DataFrame(b),['outcome','period'])
    save(broad,'broad_period_sensitivity.csv')
    return path,broad

def mechanism_windows():
    link1=read_design('MECH1_quantity-1');d=link1;z=d['z'];w=np.array([0,1,1,1,1]);one=[];half=[]
    for e in range(59,len(z)):
        r,v,f=estimate(d,z.iloc[e-59:e+1],weight=w)
        one.append(dict(link='LINK1',method='rolling60',record_type='cumulative_lags0..3',precision='INSUFFICIENT_PRECISION_FOR_STABILITY_CLAIM',**r))
        for j in range(4):
            rr,_,_=estimate(d,z.iloc[e-59:e+1],term=f'{SHOCK}_lag{j}');one.append(dict(link='LINK1',method='rolling60',record_type=f'lag{j}',precision='DESCRIPTIVE_DRIFT_DIAGNOSTIC',**rr))
    for side,zz in [('first_half',z.iloc[:len(z)//2]),('second_half',z.iloc[len(z)//2:])]:
        r,v,_=estimate(d,zz,weight=w);half.append((side,r,v,zz))
        one.append(dict(link='LINK1',method=side,record_type='cumulative_lags0..3',precision='INSUFFICIENT_PRECISION_FOR_STABILITY_CLAIM',**r))
        for j in range(4):
            rr,_,_=estimate(d,zz,term=f'{SHOCK}_lag{j}');one.append(dict(link='LINK1',method=side,record_type=f'lag{j}',precision='DESCRIPTIVE_DRIFT_DIAGNOSTIC',**rr))
    vec=np.zeros(len(z));vec[:len(z)//2]=-half[0][2];vec[len(z)//2:]=half[1][2]
    diff=scalar_result(half[1][1]['coefficient']-half[0][1]['coefficient'],vec)
    one.append(dict(link='LINK1',method='second_minus_first',record_type='cumulative_lags0..3',precision='DRIFT_EVIDENCE' if diff['raw_p']<.05 else 'INSUFFICIENT_PRECISION_FOR_STABILITY_CLAIM',N=len(z),start=z.month.min().strftime('%Y-%m'),end=z.month.max().strftime('%Y-%m'),**diff))
    two=[]
    for y in YLIST[:2]:
        ds=[read_design(f'MECH2_{y}_quantity0',h) for h in range(13)]
        base=ds[0]['z'];day=base.month.iloc[len(base)//2-1]
        for h,d in enumerate(ds):
            z=d['z'];counts=[int((z.month<=day).sum()),int((z.month>day).sum())]
            for side,N in zip(('first_half','second_half'),counts):
                zz=z[z.month<=day if side=='first_half' else z.month>day]
                if min(counts)<60:
                    two.append(dict(outcome=y,horizon=h,method=side,N=N,start=zz.month.min().strftime('%Y-%m'),end=zz.month.max().strftime('%Y-%m'),split_date=day.strftime('%Y-%m'),inferential=False,precision='INSUFFICIENT_PRECISION_FOR_STABILITY_CLAIM',disposition='SKIPPED_PAIRED_HALF_N_BELOW60'))
                else:
                    r,_,_=estimate(d,zz,l=max(12,h+1),term='dlog_import_unit_price')
                    two.append(dict(outcome=y,horizon=h,method=side,split_date=day.strftime('%Y-%m'),inferential=True,precision='INSUFFICIENT_PRECISION_FOR_STABILITY_CLAIM',**r))
            for e in range(59,len(z)):
                r,_,_=estimate(d,z.iloc[e-59:e+1],l=max(12,h+1),term='dlog_import_unit_price')
                two.append(dict(outcome=y,horizon=h,method='rolling60',split_date=day.strftime('%Y-%m'),inferential=True,precision='INSUFFICIENT_PRECISION_FOR_STABILITY_CLAIM',**r))
    one=save(one,'mechanism_link1_stability.csv');two=save(two,'mechanism_link2_stability.csv')
    return one,two
