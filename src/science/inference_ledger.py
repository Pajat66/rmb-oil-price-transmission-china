"""Scientific claim classifications retained; no reviewer/editorial records."""
import numpy as np
import pandas as pd
from phase2b_core import *
def excludes(lo,hi): return (lo>0) or (hi<0)

def finalize(R,S,CI,CU,CH,J,H,shares,old=None,design_audit=None,policy=None,began=None):
    ledger=[]
    for _,r in R.iterrows():
        bs=CI[(CI.model==r.model)&(CI.horizon==r.horizon)]
        b=bs[bs.block_length==12].iloc[0];ss=S[(S.model==r.model)&(S.horizon==r.horizon)]
        bootstable=all(excludes(x.bootstrap_ci_low,x.bootstrap_ci_high) and np.sign(x.bootstrap_ci_low)==np.sign(r.coefficient) for x in bs.itertuples())
        hacstable=all(excludes(x.ci_low,x.ci_high) and np.sign(x.ci_low)==np.sign(r.coefficient) for x in ss.itertuples())
        robust=r.fdr_q<.05 and bootstable and hacstable
        word='ROBUST_ASSOCIATION' if robust else ('SUGGESTIVE_ASSOCIATION' if r.raw_p<.05 or excludes(b.bootstrap_ci_low,b.bootstrap_ci_high) else 'NO_CLEAR_EVIDENCE')
        j=J[(J.model==r.model)&(J.block_length==12)&(J.window=='all')]
        ledger.append(dict(claim_id=f'{r.model}_period_h{r.horizon}',model=r.model,claim_type='period_response',estimate=r.coefficient,hac_ci_low=r.hac_ci_low,hac_ci_high=r.hac_ci_high,bootstrap_ci_low=b.bootstrap_ci_low,bootstrap_ci_high=b.bootstrap_ci_high,raw_p=r.raw_p,fdr_q=r.fdr_q,holm_p=r.holm_p,joint_test=float(j.iloc[0].raw_p) if len(j) else np.nan,robustness_status='STABLE_HAC_AND_BLOCK_CI' if hacstable and bootstable else 'SENSITIVITY_OR_IMPRECISION',allowed_wording=word,family=f'{r.model}:13 period horizons'))
    cumsens=pd.read_csv(TABLES/'phase2b_all_lp_cumulative_hac_sensitivity.csv')
    for mid in CH.model.unique():
        for _,r in CH[CH.model==mid].iterrows():
            bs=CU[(CU.model==mid)&(CU.horizon==r.horizon)];b=bs[bs.block_length==12].iloc[0]
            stable=all(excludes(x.bootstrap_ci_low,x.bootstrap_ci_high) and np.sign(x.bootstrap_ci_low)==np.sign(r.cumulative_effect) for x in bs.itertuples())
            css=cumsens[(cumsens.model==mid)&(cumsens.horizon==r.horizon)]
            hacstable=all(excludes(x.hac_ci_low,x.hac_ci_high) and np.sign(x.hac_ci_low)==np.sign(r.cumulative_effect) for x in css.itertuples())
            # Cumulative inference has its own secondary family; period FDR is never reused.
            word='ROBUST_ASSOCIATION' if r.fdr_q<.05 and stable and hacstable else ('SUGGESTIVE_ASSOCIATION' if r.raw_p<.05 or excludes(b.bootstrap_ci_low,b.bootstrap_ci_high) else 'NO_CLEAR_EVIDENCE')
            j=J[(J.model==mid)&(J.block_length==12)&(J.window=='all')]
            ledger.append(dict(claim_id=f'{mid}_cumulative_h{r.horizon}',model=mid,claim_type='cumulative_response',estimate=r.cumulative_effect,hac_ci_low=r.hac_ci_low,hac_ci_high=r.hac_ci_high,bootstrap_ci_low=b.bootstrap_ci_low,bootstrap_ci_high=b.bootstrap_ci_high,raw_p=r.raw_p,fdr_q=r.fdr_q,holm_p=r.holm_p,joint_test=float(j.iloc[0].raw_p) if len(j) else np.nan,robustness_status='STABLE_HAC_AND_BLOCK_CI' if stable and hacstable else 'SENSITIVITY_OR_IMPRECISION',allowed_wording=word,family=f'{mid}:13 cumulative horizons; separate secondary family'))
    for _,r in H[H.block_length==12].iterrows():
        ss=H[(H.contrast==r.contrast)&(H.horizon==r.horizon)]
        stable=all(excludes(x.bootstrap_ci_low,x.bootstrap_ci_high) and np.sign(x.bootstrap_ci_low)==np.sign(r.difference) for x in ss.itertuples())
        word='ROBUST_ASSOCIATION' if r.fdr_q<.05 and stable else ('SUGGESTIVE_ASSOCIATION' if r.raw_p<.05 or excludes(r.bootstrap_ci_low,r.bootstrap_ci_high) else 'NO_CLEAR_EVIDENCE')
        ledger.append(dict(claim_id=f'HIERARCHY_{r.contrast}_h{r.horizon}',model='paired primary LP bootstrap',claim_type='hierarchy_difference',estimate=r.difference,bootstrap_ci_low=r.bootstrap_ci_low,bootstrap_ci_high=r.bootstrap_ci_high,raw_p=r.raw_p,fdr_q=r.fdr_q,holm_p=r.holm_p,robustness_status='STABLE_BLOCK_CI' if stable else 'SENSITIVITY_OR_IMPRECISION',allowed_wording=word,family='9 hierarchy contrasts; separate from period horizons'))
    for _,r in J[J.block_length==12].iterrows():
        ss=J[(J.model==r.model)&(J.window==r.window)]
        stable=bool((ss.raw_p<.05).all());word='ROBUST_ASSOCIATION' if r.fdr_q<.05 and stable else ('SUGGESTIVE_ASSOCIATION' if r.raw_p<.05 else 'NO_CLEAR_EVIDENCE')
        ledger.append(dict(claim_id=f'{r.model}_joint_{r.window}',model=r.model,claim_type='joint_zero_test',estimate=r.wald_statistic,raw_p=r.raw_p,fdr_q=r.fdr_q,holm_p=r.holm_p,joint_test=r.raw_p,robustness_status='STABLE_BLOCK_TEST' if stable else 'SENSITIVITY_OR_IMPRECISION',allowed_wording=word,family=f'{r.model}:4 joint windows'))
    for r in shares:
        if r['block_length']==12:ledger.append(dict(claim_id=f"SHARE_{r['outcome']}_h{r['horizon']}",model='normalized absolute cumulative responses',claim_type='descriptive_share',estimate=r['median'],bootstrap_ci_low=r['ci_low'],bootstrap_ci_high=r['ci_high'],robustness_status=r['recommendation'],allowed_wording='DESCRIPTIVE_ONLY',family='no hypothesis test; normalized descriptive share'))
    link=pd.read_csv(TABLES/'mechanism_link1_final.csv')
    for _,r in link[link.maxlags==12].iterrows():
        ss=link[(link.model==r.model)&(link.record_type==r.record_type)&(link.term==r.term)]
        stable=bool((ss.raw_p<.05).all());word='ROBUST_ASSOCIATION' if r.fdr_q<.05 and stable else ('SUGGESTIVE_ASSOCIATION' if r.raw_p<.05 else 'NO_CLEAR_EVIDENCE')
        ledger.append(dict(claim_id=f'{r.model}_{r.term}',model=r.model,claim_type='link1_'+r.record_type,estimate=r.coefficient if pd.notna(r.coefficient) else r.wald_chi2,hac_ci_low=r.hac_ci_low,hac_ci_high=r.hac_ci_high,raw_p=r.raw_p,fdr_q=r.fdr_q,holm_p=r.holm_p,joint_test=r.raw_p if r.record_type=='joint' else np.nan,robustness_status='STABLE_HAC_TEST' if stable else 'SENSITIVITY_OR_IMPRECISION',allowed_wording=word,family=f'{r.model}:{r.record_type}',not_applicable='bootstrap not required for frozen single-equation Link1'))
    comp=pd.read_csv(TABLES/'lp_composite_components.csv')
    for _,r in comp.iterrows():
        ledger.append(dict(claim_id=f'COMPONENT_RESTRICTION_{r.outcome}_h{r.horizon}',model='unrestricted Brent+FX LP',claim_type='composite_restriction',estimate=r.difference,hac_ci_low=r.hac_ci_low,hac_ci_high=r.hac_ci_high,raw_p=r.raw_p,fdr_q=r.fdr_q,holm_p=r.holm_p,robustness_status='HAC_RESTRICTION_TEST',allowed_wording='SUGGESTIVE_ASSOCIATION' if r.fdr_q<.05 else 'NO_CLEAR_EVIDENCE',family=f'{r.outcome}:13 component equality tests',not_applicable='nonrejection never establishes equivalence; bootstrap not requested'))
    L=save(ledger,'phase2b_inference_summary.csv')
    return L
