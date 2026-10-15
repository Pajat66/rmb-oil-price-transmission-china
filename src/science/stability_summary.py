"""Numerical stability summaries retained; no private editorial dependencies."""
import numpy as np
import pandas as pd
from phase2c_core import *
def finalize(ds,rec,roll,hier,br,par,paths,broad,m1,m2,leads,reverse):
    drift=[]
    for y,aa in ds.items():
        for h in SUMMARY_H:
            d=aa[h];z=d['z'];r0,v0,_=estimate(d,z.iloc[:120]);r1,v1,_=estimate(d)
            padded=np.zeros(len(z));padded[:120]=v0
            rr=scalar_result(r1['coefficient']-r0['coefficient'],v1-padded)
            drift.append(dict(outcome=y,horizon=h,N_initial=120,N_final=len(z),initial_coefficient=r0['coefficient'],final_coefficient=r1['coefficient'],**rr))
    drift=adjust(pd.DataFrame(drift),['outcome']);save(drift,'phase2c_recursive_endpoint_drift.csv')
    rollsum=[]
    for (y,h,w),g in roll.groupby(['outcome','horizon','window']):
        rollsum.append(dict(outcome=y,horizon=h,window=w,n_windows=len(g),fraction_point_positive=float((g.coefficient>0).mean()),fraction_ci_positive=float((g.hac_ci_low>0).mean()),fraction_ci_negative=float((g.hac_ci_high<0).mean()),fraction_ci_cross_zero=float(((g.hac_ci_low<=0)&(g.hac_ci_high>=0)).mean()),coefficient_min=float(g.coefficient.min()),coefficient_max=float(g.coefficient.max()),clear_sign_reversal=bool((g.hac_ci_low>0).any() and (g.hac_ci_high<0).any()),interpretation='dependent overlapping windows; descriptive fractions, no binomial significance test'))
    RS=save(rollsum,'phase2c_rolling_evidence_summary.csv')
    hiersum=[]
    for key,g in hier.groupby(['method','window','horizon','response_type','contrast']):
        method,w,h,resp,contrast=key
        hiersum.append(dict(method=method,window=w,horizon=h,response_type=resp,contrast=contrast,n_windows=len(g),fraction_point_positive=float((g.estimate>0).mean()),fraction_ci_positive=float((g.ci_low>0).mean()),fraction_ci_negative=float((g.ci_high<0).mean()),fraction_ci_cross_zero=float(((g.ci_low<=0)&(g.ci_high>=0)).mean()),interpretation='pointwise HAC paired uncertainty; no simultaneous/independent-window inference'))
    HS=save(hiersum,'phase2c_hierarchy_evidence_summary.csv')
    summary=[]
    for y in YLIST:
        bb=br[br.outcome==y];pp=par[par.outcome==y];dd=drift[drift.outcome==y];rr=RS[(RS.outcome==y)&(RS.window==120)]
        sup=bool(bb.detected_break.any());cus=bool(((pp.test=='RECURSIVE_CUSUM')&(pp.fdr_q<.05)).any());hansen=bool(((pp.test=='HANSEN')&(pp.fdr_q<.05)).any());signflip=bool(rr.clear_sign_reversal.any());drifted=bool((dd.holm_p<.05).any())
        strongwindows=all(max(r.fraction_point_positive,1-r.fraction_point_positive)>=.9 and max(r.fraction_ci_positive,r.fraction_ci_negative)>.5 for r in rr.itertuples())
        if (sup and (cus or hansen)) or signflip:status='TIME_VARYING'
        elif sup or cus or hansen or drifted:status='PARTIALLY_STABLE'
        elif strongwindows:status='STABLE'
        else:status='INCONCLUSIVE'
        ownpaths=paths[(paths.outcome==y)&paths.break_date.isin(bb[bb.detected_break].candidate_break_date)] if len(paths) else paths
        if len(ownpaths):
            pivot=ownpaths.pivot_table(index=['scenario','horizon'],columns='period',values='coefficient');sg=(np.sign(pivot['pre'])==np.sign(pivot['post']))
            prepost=f'{int(sg.sum())}/{len(sg)} period-horizon signs consistent; estimated-break uncertainty not incorporated'
        else:prepost='NOT_APPLICABLE_NO_OWN_DETECTED_BREAK'
        relevant=HS[(HS.method=='rolling')&(HS.window==120)&(HS.response_type=='cumulative')&HS.contrast.str.contains(y,regex=False)]
        hierarchy='; '.join(f'{r.contrast} h{r.horizon}: positive CI {r.fraction_ci_positive:.1%}, cross-zero {r.fraction_ci_cross_zero:.1%}' for r in relevant.itertuples())
        auxiliary=bool((pp.classical_reject!=(pp.fdr_q<.05)).any())
        summary.append(dict(outcome=y,recursive_stability='ENDPOINT_DRIFT_HOLM_SIGNIFICANT' if drifted else 'NO_CORRECTED_ENDPOINT_DRIFT; not an equivalence test',rolling_sign_stability='CLEAR_CI_SIGN_REVERSAL' if signflip else ('PERSISTENT_SIGN_WITH_PRECISION' if strongwindows else 'IMPRECISE_OR_SIGN_VARIABLE'),supwald_result='REJECT_CONSTANT_FULL_PARAMETER_VECTOR' if sup else 'NO_CORRECTED_REJECTION',CUSUM_result='REJECT' if cus else 'NO_CORRECTED_REJECTION',Hansen_result='REJECT' if hansen else 'NO_CORRECTED_REJECTION',break_date_if_any=';'.join(bb[bb.detected_break].candidate_break_date.unique()),pre_post_sign_consistency=prepost,hierarchy_consistency=hierarchy,final_status=status,mixed_evidence=bool(sup!=cus or sup!=hansen),auxiliary_classical_bootstrap_disagreement=auxiliary,classification_scope='equation parameter stability; all-parameter tests do not isolate oil coefficient change'))
    SUM=save(summary,'structural_stability_summary.csv')
    return SUM
