"""Phase3A presentation only. No model fitting or statistical-policy changes.

All final inferential claims read frozen Phase2B/2C tables. Earlier diagnostics
are explicitly historical provenance in S2/S3, never final primary evidence.
"""
from pathlib import Path
import argparse, hashlib, json, re
import numpy as np
import pandas as pd

OUTCOMES = {'d_fuel_power_inflation':'Fuel', 'd_ppi_inflation':'PPI', 'd_cpi_inflation':'CPI'}
REQUIRED = '''phase2b_inference_summary lp_final_coefficients lp_cumulative_response lp_bootstrap_ci lp_joint_tests price_hierarchy_tests relative_pass_through_bootstrap lp_composite_components multicollinearity_diagnostics mechanism_link1_final mechanism_lp_fuel mechanism_lp_ppi terminal_cpi_lp structural_stability_summary recursive_lp_coefficients rolling_lp_coefficients structural_break_supwald parameter_stability_tests hierarchy_stability mechanism_link1_stability mechanism_link2_stability future_shock_placebo reverse_predictive_diagnostic'''.split()
COMPANIONS = '''phase2b_all_lp_cumulative_hac phase2b_all_lp_cumulative_bootstrap phase2b_all_lp_period_results phase2b_all_lp_bootstrap_ci phase2c_recursive_endpoint_drift phase2c_rolling_evidence_summary phase2c_hierarchy_evidence_summary break_subsample_lp broad_period_sensitivity phase2c_break_cumulative'''.split()
HISTORY = '''stationarity_full transformed_stationarity_full yoy_aligned_stationarity_full long_dlm_lag_grid_0_12 long_dlm_lag_grid_0_18_sensitivity long_dynamic_dlm_grid long_dynamic_dlm_diagnostics table3_lag_selection_full table3_lag_selection_summary'''.split()
PROHIBITED = 'causal effect; identified structural shock; proves exogeneity; structurally identified pass-through'

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean_records(df):
    # pandas.to_json defaults to 10 decimal places, which would round XLSX
    # inputs. Preserve the original IEEE float values in the JSON bridge.
    return df.astype(object).where(pd.notna(df),None).to_dict(orient='records')
def main(root):
    root = Path(root).resolve(); audit=root/'00_audit'; dst=root/'03_final_tables'; src=root/'03_tables'
    audit.mkdir(exist_ok=True); dst.mkdir(exist_ok=True)
    tables={name:pd.read_csv(src/(name+'.csv')) for name in REQUIRED+COMPANIONS+HISTORY}
    manifest=[]
    for name,df in tables.items():
        historical=name in HISTORY
        phase='HISTORICAL_PROVENANCE' if historical else ('Phase2C' if name in REQUIRED[13:] or name.startswith('phase2c') or name in ('break_subsample_lp','broad_period_sensitivity') else 'Phase2B')
        p=src/(name+'.csv')
        manifest.append(dict(path=p.relative_to(root).as_posix(),phase=phase,role='historical_diagnostic_only' if historical else 'frozen_scientific_evidence',rows=len(df),bytes=p.stat().st_size,sha256=digest(p)))
    for name in ('phase2b_prespecified_inference_policy.json','phase2c_prespecified_policy.json','phase2b_primary_model_registry.csv','phase2c_frozen_input_registry.csv','source_log_resolution.csv'):
        p=audit/name
        manifest.append(dict(path=p.relative_to(root).as_posix(),phase='POLICY_OR_PROVENANCE',role='fixed_policy_or_source_metadata',rows=None,bytes=p.stat().st_size,sha256=digest(p)))
    for name in ('long_sample_canonical.csv','short_sample_canonical.csv','long_sample_transformed.csv','short_sample_transformed.csv'):
        p=root/'01_data'/name
        manifest.append(dict(path=p.relative_to(root).as_posix(),phase='CANONICAL_INPUT',role='data_definition_and_reproduction_input',rows=len(pd.read_csv(p)),bytes=p.stat().st_size,sha256=digest(p)))
    pd.DataFrame(manifest).to_csv(audit/'final_evidence_freeze_manifest.csv',index=False,encoding='utf-8-sig')
    stability=tables['structural_stability_summary'].set_index('outcome').final_status.to_dict()
    ledger=[]
    for _,r in tables['phase2b_inference_summary'].iterrows():
        mid=str(r.model); kind=r.claim_type; cid=str(r.claim_id); designation='SI'; outcome=''
        h=int(re.search(r'h(\d+)$',cid).group(1)) if re.search(r'h(\d+)$',cid) else None
        for y,label in OUTCOMES.items():
            if mid=='PRIMARY_'+y:
                outcome=y
                h=int(re.search(r'h(\d+)$',cid).group(1)) if re.search(r'h(\d+)$',cid) else None
                if kind in ('period_response','cumulative_response'):
                    cid=f'PRIMARY_{label}_{"PERIOD" if kind=="period_response" else "CUM"}_h{h}'
                    designation='MAIN_AND_SI'
                elif kind=='joint_zero_test':
                    cid=f'PRIMARY_{label}_JOINT_'+str(cid).split('_joint_')[-1]
        allowed='Observational association / response; preserve estimate and uncertainty.'
        prohibited=PROHIBITED; evidence=str(r.robustness_status)
        if outcome:
            label=OUTCOMES[outcome]
            if label=='Fuel':
                allowed='Stronger and more persistent association / response than downstream price stages; temporal variation remains.'
                prohibited+='; largest causal effect'
            elif label=='PPI':
                allowed='Smaller short-to-medium-horizon response than fuel-and-power prices.'
                if kind=='cumulative_response' and h==12:
                    allowed+=' At h=12 cumulative bootstrap uncertainty includes zero; longer-horizon evidence is weaker.'
                    evidence='LIMITED_LONG_HORIZON'; prohibited+='; robust cumulative effect at h=12'
            else:
                allowed='Smaller and less persistent response; short-run evidence exists; longer-horizon cumulative evidence becomes weaker.'
                prohibited+='; no response; zero response; close to zero at all horizons'
        if mid.startswith('MECH2_') and kind=='cumulative_response':
            label=next((v for y,v in OUTCOMES.items() if y in mid),'')
            h=int(re.search(r'h(\d+)$',cid).group(1)); q='QUANTITY1_' if 'quantity1' in mid else ''
            cid=f'MECH2_{label}_{q}CUM_h{h}'
            allowed='Observational import-unit-price association; period evidence and cumulative uncertainty must be distinguished; no causal mediation.'
        if outcome and kind=='period_response':
            allowed+=' Outcome-level context only. This period-horizon estimate is '+('positive' if r.estimate>0 else 'negative' if r.estimate<0 else 'zero in the frozen numerical source')+'. Its evidence status is '+str(r.robustness_status)+'. Cumulative persistence does not imply a positive or supported coefficient at every period horizon.'
        if kind=='hierarchy_difference':
            # Replaced below by direct, explicit contrast rows.
            continue
        if kind=='descriptive_share': continue
        if kind=='composite_restriction':
            allowed='Economically motivated composite measure; nonrejection is compatible with a parsimonious local-currency representation.'
            prohibited+='; contains more information; outperforms Brent and FX; provides additional explanatory power; proves coefficient equality'
        bootstrap_p=np.nan
        if kind in ('period_response','cumulative_response') and h is not None:
            boot=tables['phase2b_all_lp_bootstrap_ci' if kind=='period_response' else 'phase2b_all_lp_cumulative_bootstrap']
            hit=boot[(boot.model==mid)&(boot.horizon==h)&(boot.block_length==12)]
            if len(hit): bootstrap_p=hit.iloc[0].bootstrap_p
        p_method='HAC asymptotic normal raw p; separate '+('period' if kind=='period_response' else 'cumulative')+' BH/Holm family; bootstrap p reported separately' if kind in ('period_response','cumulative_response') else ('null-centered path-bootstrap Wald p; window-family BH/Holm' if kind=='joint_zero_test' else 'HAC-based test; claim-specific frozen family')
        b=dict(claim_id=cid,analysis_source='Phase2B/03_tables/phase2b_inference_summary.csv',source_claim_id=r.claim_id,source_row_index=int(r.name),claim_type=kind,model=mid,outcome=outcome or mid,horizon=h,estimate=r.estimate,hac_ci_low=r.hac_ci_low,hac_ci_high=r.hac_ci_high,bootstrap_ci_low=r.bootstrap_ci_low,bootstrap_ci_high=r.bootstrap_ci_high,bootstrap_p=bootstrap_p,raw_p=r.raw_p,bh_q=r.fdr_q,holm_p=r.holm_p,p_method=p_method,family=r.family,stability_status=stability.get(outcome,'NOT_CLASSIFIED_AS_PRIMARY'),inference_robustness_status=evidence,allowed_wording=allowed,prohibited_wording=prohibited,main_si_designation=designation,not_applicable=r.not_applicable)
        ledger.append(b)
    def add(cid,source,kind,estimate=np.nan,hac_low=np.nan,hac_high=np.nan,boot_low=np.nan,boot_high=np.nan,p=np.nan,q=np.nan,holm=np.nan,status='NOT_APPLICABLE',allowed='',prohibited=PROHIBITED,designation='MAIN_AND_SI',outcome='',horizon=None,evidence='',family='',method=''):
        ledger.append(dict(claim_id=cid,analysis_source=source,source_claim_id='',source_row_index=np.nan,claim_type=kind,model='',outcome=outcome,horizon=horizon,estimate=estimate,hac_ci_low=hac_low,hac_ci_high=hac_high,bootstrap_ci_low=boot_low,bootstrap_ci_high=boot_high,bootstrap_p=p if kind=='hierarchy_difference' else np.nan,raw_p=p,bh_q=q,holm_p=holm,p_method=method,family=family,stability_status=status,inference_robustness_status=evidence,allowed_wording=allowed,prohibited_wording=prohibited,main_si_designation=designation,not_applicable='Intervals/tests absent in source are not applicable; never substituted with zero.'))
    contrasts={f'{a} minus {b}':f'{OUTCOMES[a]}_{OUTCOMES[b]}' for a,b in [('d_fuel_power_inflation','d_ppi_inflation'),('d_fuel_power_inflation','d_cpi_inflation'),('d_ppi_inflation','d_cpi_inflation')]}
    hier=tables['price_hierarchy_tests'].query('block_length == 12').copy()
    hier['contrast_label']=hier.contrast.map(contrasts).str.replace('_',' - ')
    hier['evidence_label']=['SUPPORTED' if r.bootstrap_ci_low>0 and r.fdr_q<.05 else 'SUGGESTIVE' if r.bootstrap_ci_low>0 else 'UNCLEAR' for _,r in hier.iterrows()]
    for _,r in hier.iterrows():
        label=contrasts[r.contrast]; allowed={'SUPPORTED':'Direct paired bootstrap evidence supports the stated positive cumulative contrast.','SUGGESTIVE':'PPI exceeds CPI only suggestively at h=6; percentile interval excludes zero but centered test and BH q do not pass 0.05.','UNCLEAR':'PPI versus CPI at h=12 is unclear; interval includes zero.'}[r.evidence_label]
        add(f'HIERARCHY_{label}_h{r.horizon}','Phase2B/03_tables/price_hierarchy_tests.csv','hierarchy_difference',r.difference,boot_low=r.bootstrap_ci_low,boot_high=r.bootstrap_ci_high,p=r.bootstrap_p,q=r.fdr_q,holm=r.holm_p,allowed=allowed,prohibited=PROHIBITED+'; complete hierarchy is robust at all horizons',horizon=r.horizon,evidence=r.evidence_label,family='nine hierarchy contrasts; primary block12',method='null-centered paired bootstrap; plus-one p')
    shares=tables['relative_pass_through_bootstrap'].copy()
    for _,r in shares.query('block_length == 12').iterrows():
        add(f'RELATIVE_{OUTCOMES[r.outcome]}_h{r.horizon}','Phase2B/03_tables/relative_pass_through_bootstrap.csv','normalized_descriptive_share',r.point_share,boot_low=r.ci_low,boot_high=r.ci_high,allowed='Normalized descriptive response share, displayed together with bootstrap uncertainty; CPI excluded from denominator.',prohibited=PROHIBITED+'; 78.2%; 21.8%; structural pass-through weights',designation='SI',outcome=r.outcome,horizon=r.horizon,evidence=r.recommendation,method='percentile bootstrap share interval; inferential p not defined')
    for y,label in OUTCOMES.items():
        cc=tables['lp_composite_components'].query('outcome == @y')
        add('COMPOSITE_'+label,'Phase2B/03_tables/lp_composite_components.csv','composite_summary',q=cc.fdr_q.min(),holm=cc.holm_p.min(),allowed='Parsimonious local-currency representation; no systematic corrected restriction rejection; nonrejection does not prove coefficient equality.',prohibited=PROHIBITED+'; contains more information; outperforms Brent and FX; provides additional explanatory power',outcome=y,method='minimum adjusted q across 13 separately reported restrictions; not a new omnibus p')
        add('STABILITY_'+label,'Phase2C/03_tables/structural_stability_summary.csv','structural_stability',status=stability[y],allowed=f'{label}: {stability[y]}; corrected nonrejection does not prove constant parameters.',prohibited=PROHIBITED+'; STABLE; stable at all horizons',outcome=y,evidence=stability[y])
        place=tables['future_shock_placebo']; place=place[(place.outcome==y)&(place.record_type=='joint_leads1..3')].iloc[0]
        rev=tables['reverse_predictive_diagnostic'].query('outcome == @y')
        add('ENDOGENEITY_'+label,'Phase2C/03_tables/future_shock_placebo.csv; reverse_predictive_diagnostic.csv','endogeneity_limitation',p=place.raw_p,q=place.fdr_q,holm=place.holm_p,allowed='Conditional anticipation and reverse predictive diagnostics do not identify exogeneity.'+(' PPI anticipation / reverse predictive evidence must remain in limitations.' if label=='PPI' else ''),designation='SI_AND_LIMITATIONS',outcome=y,evidence='PPI_LIMITATION_REQUIRED' if label=='PPI' else 'DIAGNOSTIC_ONLY',family='three joint lead tests; separate reverse families',method='HAC joint future-lead test; reverse results in S15')
    link1=tables['mechanism_link1_final']; r=link1[(link1.quantity_order==-1)&(link1.maxlags==12)&(link1.record_type=='cumulative')].iloc[0]
    add('MECH1_SUM','Phase2B/03_tables/mechanism_link1_final.csv','link1_cumulative',r.coefficient,hac_low=r.hac_ci_low,hac_high=r.hac_ci_high,p=r.raw_p,q=r.fdr_q,holm=r.holm_p,allowed='Oil-cost movement is positively associated with import unit-price changes over lags0–3; no causal-chain identification.',method='covariance-aware lag0..3 sum; HAC12; bootstrap interval unavailable in frozen Link1 source')
    for _,r in tables['phase2c_recursive_endpoint_drift'].iterrows():
        add(f'RECURSIVE_DRIFT_{OUTCOMES[r.outcome]}_h{r.horizon}','Phase2C/03_tables/phase2c_recursive_endpoint_drift.csv','recursive_endpoint_drift',r.estimate,hac_low=r.ci_low,hac_high=r.ci_high,p=r.raw_p,q=r.fdr_q,holm=r.holm_p,status=stability[r.outcome],allowed='Shared-sample HAC endpoint coefficient contrast; Fuel h=12 negative drift survives Holm correction.' if OUTCOMES[r.outcome]=='Fuel' and r.horizon==12 else 'Auxiliary endpoint drift comparison; nonrejection is not equivalence.',designation='SI_AND_LIMITATIONS',outcome=r.outcome,horizon=r.horizon,method='full influence HAC12; Holm family4 per outcome')
    L=pd.DataFrame(ledger); assert L.claim_id.is_unique
    L.to_csv(audit/'final_claim_ledger.csv',index=False,encoding='utf-8-sig')
    dictionary=[]
    definitions=[('dlog_oil_rmb','Local-currency oil cost','100 x calendar log difference of Brent USD x CNY/USD','Approx. monthly percent change','EIA Brent; FRED EXCHUS exchange rate (Board of Governors of the Federal Reserve System, US)','long'),('dlog_brent','Brent crude oil','100 x calendar log difference','Approx. monthly percent change','EIA','long'),('dlog_fx','CNY per USD','100 x calendar log difference','Approx. monthly percent change','FRED, EXCHUS (Board of Governors of the Federal Reserve System, US)','long'),('d_fuel_power_inflation','Fuel-and-power purchase price inflation','Calendar difference of year-on-year index minus 100','Percentage-point change in YoY inflation','NBS','long'),('d_ppi_inflation','Producer price inflation','Calendar difference of year-on-year index minus 100','Percentage-point change in YoY inflation','NBS','long'),('d_cpi_inflation','Consumer price inflation','Calendar difference of year-on-year index minus 100','Percentage-point change in YoY inflation','NBS','long'),('dlog_import_unit_price','Crude-oil import unit price (RMB/kg)','100 x calendar log difference','Approx. monthly percent change','China Customs','short'),('dlog_import_quantity','Crude-oil import quantity (10,000 tonnes)','100 x calendar log difference','Approx. monthly percent change','China Customs','short'),('indust_va_yoy','Industrial value added growth','Observed reported YoY growth; not a primary control','Percent growth','NBS','long'),('indust_va_cum_yoy','Cumulative industrial value added growth','Observed cumulative YoY growth; not substituted for monthly growth','Percent growth','NBS','long')]
    for var,label,transform,unit,source,sample in definitions:
        df=pd.read_csv(root/'01_data'/f'{sample}_sample_transformed.csv'); col=var
        valid=df[col].notna()
        dictionary.append(dict(variable=var,definition=label,transformation=transform,units=unit,canonical_period=f'{df.month.min()[:7]} to {df.month.max()[:7]}',observed_transformed_period=f'{df.loc[valid,"month"].min()[:7]} to {df.loc[valid,"month"].max()[:7]}',observed_months=int(valid.sum()),missing_months=int((~valid).sum()),source=source,primary_use='fixed shock or outcome' if var in list(OUTCOMES)+['dlog_oil_rmb'] else 'diagnostic / mechanism / accounting',source_file=f'01_data/{sample}_sample_transformed.csv'))
    D=pd.DataFrame(dictionary)
    payload=[]; architecture=[]
    def publish(df,stem,title,note,role,sources,sheet=None):
        df=df.copy(); df.to_csv(dst/(stem+'.csv'),index=False,encoding='utf-8-sig')
        architecture.append(dict(table_id=stem,title=title,designation=role,rows=len(df),source_files=sources,note=note))
        payload.append(dict(id=stem,title=title,note=note,role=role,sheet=sheet or stem[:31],columns=df.columns.tolist(),rows=clean_records(df)))
    publish(D[['variable','definition','transformation','units','canonical_period','source']], 'MAIN_TABLE_1','Variables, transformations, samples and sources','LP estimation months are shock-origin months, 1998-04 to 2026-02 at h0 and 1998-04 to 2025-02 at h12. Mechanism samples are shorter; S1 gives full accounting. The exchange rate is the monthly average of available daily observations from FRED series EXCHUS, published by the Board of Governors of the Federal Reserve System under G.5 Foreign Exchange Rates. The series is expressed in CNY per USD and is not seasonally adjusted.','MAIN','01_data/*_sample_transformed.csv; transformation_layer.py')
    m2=[]
    for y,label in OUTCOMES.items():
        row={'Outcome':label}
        for h in (3,6,12):
            r=L[L.claim_id==f'PRIMARY_{label}_CUM_h{h}'].iloc[0]
            row.update({f'h{h}_estimate':r.estimate,f'h{h}_CI_low':r.bootstrap_ci_low,f'h{h}_CI_high':r.bootstrap_ci_high})
        for w in ('short','all'):
            r=tables['lp_joint_tests'].query('outcome == @y and block_length == 12 and window == @w').iloc[0]
            row[f'joint_{w}_BH_q']=r.fdr_q
            row[f'joint_{w}_evidence']='SUPPORTED' if r.fdr_q<.05 else 'WEAKER_AFTER_CORRECTION'
        m2.append(row)
    publish(pd.DataFrame(m2),'MAIN_TABLE_2','Primary LP cumulative responses','Cumulative = sum of separately estimated h0..h coefficients. Pointwise percentile 95% intervals, moving-block12, B=5000. Units: percentage points per one approximate percent oil-cost change. Joint q uses four-window family per outcome. CPI short-run period evidence exists despite weaker corrected joint windows.','MAIN','final_claim_ledger.csv; lp_joint_tests.csv')
    publish(hier[['contrast_label','horizon','difference','bootstrap_ci_low','bootstrap_ci_high','bootstrap_p','fdr_q','evidence_label']],'MAIN_TABLE_3','Direct price-stage hierarchy tests','Paired block12 bootstrap. Nine contrasts form the BH family. Percentile intervals and centered tests need not be exact inverses; h6 PPI-CPI is suggestive, h12 unclear.','MAIN','price_hierarchy_tests.csv')
    m4=[]
    for y,label in OUTCOMES.items():
        df=tables['lp_composite_components'].query('outcome == @y')
        m4.append(dict(Outcome=label,restriction_tested='Current Brent coefficient = current FX coefficient; composite lags1,2 retained',minimum_adjusted_q=df.fdr_q.min(),rejected_horizons='none' if not (df.fdr_q<.05).any() else ','.join(df.loc[df.fdr_q<.05,'horizon'].astype(str)),interpretation='Compatible with a parsimonious local-currency representation. Nonrejection does not prove equality.'))
    publish(pd.DataFrame(m4),'MAIN_TABLE_4','Composite versus Brent and FX restriction diagnostic','Same months and controls; 13 restrictions per outcome. No information-criterion evidence from blocked DLM is used.','MAIN','lp_composite_components.csv')
    mech=[]
    for _,r in link1.query('maxlags == 12 and record_type == "cumulative"').iterrows():
        mech.append(dict(Panel='A',Association='Oil to import unit price',window='sum lags0..3',quantity_control={-1:'none',0:'quantity lag0',1:'quantity lags0,1'}[r.quantity_order],estimate=r.coefficient,HAC_CI_low=r.hac_ci_low,HAC_CI_high=r.hac_ci_high,bootstrap_CI_low=np.nan,bootstrap_CI_high=np.nan,BH_q=r.fdr_q,allowed_interpretation='Positive observational association; bootstrap CI unavailable in frozen Link1.'))
    for tag,label,panel in [('fuel','Fuel','B'),('ppi','PPI','C')]:
        df=tables['mechanism_lp_'+tag].query('block_length == 12 and horizon in [3,6]')
        for _,r in df.iterrows():
            mech.append(dict(Panel=panel,Association='Import unit price to '+label,window=f'cumulative h0..{r.horizon}',quantity_control='quantity lag0' if 'quantity1' in r.model else 'none',estimate=r.cumulative_effect,HAC_CI_low=r.hac_ci_low_cumulative_hac,HAC_CI_high=r.hac_ci_high_cumulative_hac,bootstrap_CI_low=r.bootstrap_ci_low_cumulative,bootstrap_CI_high=r.bootstrap_ci_high_cumulative,BH_q=r.fdr_q_cumulative_hac,allowed_interpretation='Positive short-to-medium cumulative association; no identified mediation.' if label=='Fuel' else 'Period evidence exists; cumulative short-to-medium interval includes zero.'))
    publish(pd.DataFrame(mech),'MAIN_TABLE_5','Mechanism associations and quantity controls','Panel A: fixed stationary p3 design, HAC12 lag sum (no frozen bootstrap CI); numerical zero p/q reflects underflow. Panels B/C: fixed import-price LP and block12 bootstrap; quantity sensitivity uses matched source design. No causal chain is identified.','MAIN','mechanism_link1_final.csv; mechanism_lp_fuel.csv; mechanism_lp_ppi.csv')
    m6=[]
    for y,label in OUTCOMES.items():
        r=tables['structural_stability_summary'].query('outcome == @y').iloc[0]
        drift=tables['phase2c_recursive_endpoint_drift'].query('outcome == @y and horizon == 12').iloc[0]
        br=tables['structural_break_supwald'].query('outcome == @y'); par=tables['parameter_stability_tests'].query('outcome == @y')
        m6.append(dict(Outcome=label,Sup_Wald=r.supwald_result,Sup_Wald_min_q=br.fdr_q.min(),CUSUM=r.CUSUM_result,CUSUM_min_q=par.query('test == "RECURSIVE_CUSUM"').fdr_q.min(),Hansen_bootstrap=r.Hansen_result,Hansen_min_q=par.query('test == "HANSEN"').fdr_q.min(),recursive_h12_drift=drift.estimate,recursive_h12_Holm_p=drift.holm_p,rolling_assessment=r.rolling_sign_stability,final_status=r.final_status))
    publish(pd.DataFrame(m6),'MAIN_TABLE_6','Structural stability summary','All-parameter tests h0/3/6 use fixed null bootstrap. Recursive period-coefficient h12 endpoint drift uses shared-sample HAC12. Fuel is PARTIALLY_STABLE, PPI/CPI INCONCLUSIVE. Nonrejection does not establish parameter constancy. Candidate may move to SI for manuscript brevity.','MAIN_CANDIDATE','structural_stability_summary.csv; structural_break_supwald.csv; parameter_stability_tests.csv; phase2c_recursive_endpoint_drift.csv')
    publish(D,'S1_Data_definitions','S1. Detailed data definitions and transformations','Observed and missing counts precede lag/lead losses; full monthly calendar retained. The exchange rate is the monthly average of available daily observations from FRED series EXCHUS, published by the Board of Governors of the Federal Reserve System under G.5 Foreign Exchange Rates. The series is expressed in CNY per USD and is not seasonally adjusted.','SI','01_data/*_sample_transformed.csv',sheet='S1 Definitions')
    for name,sheet in [('stationarity_full','S2 Levels'),('transformed_stationarity_full','S2 Transformed'),('yoy_aligned_stationarity_full','S2 YoY historical')]:
        publish(tables[name],'S2_'+name,'S2. Full stationarity diagnostics','Historical frozen diagnostic provenance. No primary-model selection or re-estimation occurs in Phase3A. ADF/KPSS deterministic specifications, lags and critical values preserved.','SI_HISTORICAL',name+'.csv',sheet)
    for name,sheet in [('table3_lag_selection_full','S3 Original lag audit'),('long_dlm_lag_grid_0_12','S3 Stationary lag0-12'),('long_dlm_lag_grid_0_18_sensitivity','S3 Lag0-18 sensitivity'),('long_dynamic_dlm_grid','S3 Dynamic lag audit'),('long_dynamic_dlm_diagnostics','S3 DLM diagnostics')]:
        publish(tables[name],'S3_'+name,'S3. Historical DLM specification and lag-selection audit','HISTORICAL ONLY. Original DLM is not the final primary inference framework. Information criteria explain specification history, not final response evidence.','SI_HISTORICAL',name+'.csv',sheet)
    copies=[('S4_Primary_LP_h0_h12','lp_final_coefficients','Full primary LP period coefficients','S4 Period LP'),('S5_Cumulative_LP','lp_cumulative_response','Cumulative LP responses and bootstrap sensitivity','S5 Cumulative LP'),('S6_Joint_tests','lp_joint_tests','Joint horizon tests','S6 Joint'),('S7_Hierarchy_contrasts','price_hierarchy_tests','Hierarchy contrasts and block sensitivity','S7 Hierarchy'),('S8_Composite_restrictions','lp_composite_components','Composite versus components restrictions','S8 Restrictions'),('S9_Multicollinearity','multicollinearity_diagnostics','VIF, condition indices and variance decompositions','S9 Collinearity'),('S10_Link1','mechanism_link1_final','Oil to import-price full results','S10 Link1'),('S11_Link2_Fuel','mechanism_lp_fuel','Import-price LP to Fuel','S11 Fuel LP'),('S11_Link2_PPI','mechanism_lp_ppi','Import-price LP to PPI','S11 PPI LP'),('S12_Terminal_CPI','terminal_cpi_lp','Terminal CPI period associations','S12 CPI period'),('S13_SupWald','structural_break_supwald','Structural break tests','S13 SupWald'),('S13_Parameter_tests','parameter_stability_tests','Parameter-stability tests','S13 Parameters'),('S13_Final_status','structural_stability_summary','Final stability classifications','S13 Status'),('S14_Recursive','recursive_lp_coefficients','Recursive LP full paths','S14 Recursive'),('S14_Rolling','rolling_lp_coefficients','Rolling LP full paths','S14 Rolling'),('S14_Endpoint_drift','phase2c_recursive_endpoint_drift','Recursive endpoint drift','S14 Drift'),('S14_Rolling_summary','phase2c_rolling_evidence_summary','Rolling evidence summaries','S14 Roll summary'),('S14_Hierarchy','hierarchy_stability','Rolling paired hierarchy','S14 Hierarchy'),('S14_Link1_stability','mechanism_link1_stability','Link1 temporal stability','S14 Link1'),('S14_Link2_stability','mechanism_link2_stability','Link2 temporal stability','S14 Link2'),('S15_Lead_placebo','future_shock_placebo','Conditional future-lead placebo diagnostics','S15 Leads'),('S15_Reverse_predictive','reverse_predictive_diagnostic','Reverse predictive associations','S15 Reverse'),('S16_Relative_shares','relative_pass_through_bootstrap','Normalized descriptive response shares with uncertainty','S16 Shares')]
    for stem,name,title,sheet in copies:
        if stem=='S14_Hierarchy': title='Rolling and recursive paired hierarchy'
        note='Frozen Phase2B/2C observational evidence. All estimates, uncertainty and multiplicity fields preserved; no significance stars.'
        if stem.startswith('S14'): note+=' Overlapping-window summaries are descriptive, pointwise, retrospective, not independent repeated tests or forecasts.'
        if stem.startswith('S15'): note+=' Retain PPI anticipation/reverse predictive limitation; these diagnostics do not establish exogeneity.'
        if stem.startswith('S16'): note+=' Shares use absolute Fuel/(Fuel+PPI), CPI excluded; not structural weights.'
        publish(tables[name],stem,title,note,'SI',name+'.csv',sheet)
    terminals=set(tables['terminal_cpi_lp'].model)
    publish(tables['phase2b_all_lp_cumulative_hac'].query('model in @terminals'),'S12_Terminal_cumulative_HAC','Terminal CPI cumulative HAC associations','Separate cumulative families; observational secondary associations.','SI','phase2b_all_lp_cumulative_hac.csv','S12 CPI cumulative HAC')
    publish(tables['phase2b_all_lp_cumulative_bootstrap'].query('model in @terminals'),'S12_Terminal_bootstrap','Terminal CPI cumulative bootstrap intervals','Block lengths12/6/18 preserved, pointwise intervals.','SI','phase2b_all_lp_cumulative_bootstrap.csv','S12 CPI bootstrap')
    accounting=[]
    for sample in ('long','short'):
        df=pd.read_csv(root/'01_data'/f'{sample}_sample_canonical.csv')
        for v in ('indust_va_yoy','indust_va_cum_yoy'):
            miss=df[v].isna()
            accounting.append(dict(sample=sample,variable=v,calendar_N=len(df),observed_N=int((~miss).sum()),missing_N=int(miss.sum()),missing_months=';'.join(df.loc[miss,'month'].str[:7]),primary_policy='Omit industrial VA; no interpolation and no calendar compression',control_issue='Monthly and cumulative growth are distinct variables',limitation='Omitted domestic activity may confound observational associations'))
    publish(pd.DataFrame(accounting),'S17_Industrial_missing_accounting','Industrial-control and missing-data accounting','January reporting gaps remain missing. Import quantity is not a general domestic-activity substitute. Primary lag/lead samples exclude endpoints only; see registry below.','SI','01_data/*_sample_canonical.csv; industrial_control_strategy.md','S17 Missing data')
    reg=pd.read_csv(audit/'phase2b_primary_model_registry.csv'); reg=reg[reg.status.isin(['PRIMARY','SECONDARY','ROBUSTNESS']) & reg.N.notna()]
    publish(reg,'S17_Final_sample_registry','Final LP sample and fixed terms','Per-equation final N, exact terms and date hash. No pandemic N=9 inferential result; pandemic descriptive-only data omitted.','SI','phase2b_primary_model_registry.csv','S17 Sample registry')
    pd.DataFrame(architecture).to_csv(audit/'final_table_architecture.csv',index=False,encoding='utf-8-sig')
    (dst/'tables_workbook_payload.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    (dst/'TABLE_CAPTIONS.md').write_text('\n\n'.join('## '+a['table_id']+'\n\n'+a['title']+'. '+a['note']+'\n\nSource: '+a['source_files'] for a in architecture),encoding='utf-8')
    print(f'Built {len(ledger)} claims, {len(architecture)} CSV tables. No estimation performed.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--revision-root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();main(args.revision_root)
