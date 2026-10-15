"""Regenerate S18 payload from Stage1/2 CSV, never from saved payload rows."""
from pathlib import Path
import csv,hashlib
S1=None;S2=None;POLICY_HASHES=None
TITLE="S18 Table. Lag-order sensitivity of stationary local projections, cumulative associations, and direct price-stage contrasts."
LABEL={"d_fuel_power_inflation":"Fuel","d_ppi_inflation":"PPI","d_cpi_inflation":"CPI"}
ORDER={"Fuel":0,"PPI":1,"CPI":2};PS=[1,2,3,4,6]
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def read(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def n(row,key):return float(row[key])

def integer(row,key):return int(float(row[key]))

def boolean(row,key):
    assert row[key].lower() in ["true","false"]
    return row[key].lower()=="true"

def build_payload():
    specs=[]
    trace=[]
    def spec(name,title,note,headers,rows,formats,widths,sources,keys,start=5,table_name=None,flags=None):
        assert len(headers)==len(widths)==len(formats) and all(len(r)==len(headers) for r in rows)
        assert len({tuple(r[i] for i in keys) for r in rows})==len(rows)
        result=dict(sheet=name,title=title,note=note,headers=headers,rows=rows,formats=formats,widths=widths,sources=sources,
            header_row=start,first_data_row=start+1,table_name=table_name or name.replace("_",""),key_columns=keys,flag_columns=flags or {},preview_rows=12)
        specs.append(result);return result
    dec="0.000000;-0.000000;0.000000"
    prob='[<0.0001]0.000000E+00;0.000000'
    i="0";text="@"
    ic=read(S1/"lp_lag_information_criteria.csv")
    period=read(S1/"lp_lag_period_hac.csv")
    lookup={(r["outcome"],integer(r,"horizon"),integer(r,"p"),r["criterion"]):(r,line) for line,r in enumerate(ic,2)}
    rows=[]
    for r in sorted(period,key=lambda r:(ORDER[r["outcome_label"]],integer(r,"horizon"),integer(r,"p"))):
        key=(r["outcome"],integer(r,"horizon"),integer(r,"p"));values=[r["outcome_label"],key[1],key[2],integer(r,"N"),integer(r,"k")]
        used=[]
        for criterion in ["AIC","BIC","HQIC"]:
            v,line=lookup[(*key,criterion)];assert n(v,"value")==n(r,criterion)
            values.extend([n(v,"value"),n(v,"delta_to_min"),n(v,"delta_vs_p2")]);used.append(line)
        rows.append(values)
        trace.append(dict(sheet="A1_Information_Criteria",row=len(rows)+5,source="S1/lp_lag_information_criteria.csv",source_rows=used,key=list(key)))
    assert len(rows)==195
    spec("A1_Information_Criteria","A1. Information criteria","Gaussian OLS working likelihood. Compare only within outcome and h. Δmin = value minus minimum; Δp2 = value minus p2.",
        ["Outcome","h","p","N","k","AIC","AIC Δmin","AIC Δp2","BIC","BIC Δmin","BIC Δp2","HQIC","HQIC Δmin","HQIC Δp2"],rows,
        [text,i,i,i,i]+[dec]*9,[10,5,5,7,5]+[13]*9,["S1/lp_lag_information_criteria.csv","S1/lp_lag_period_hac.csv"],[0,1,2])
    wald=read(S1/"lp_lag_extra_terms_wald.csv")
    rows=[]
    for r in sorted(wald,key=lambda r:(ORDER[r["outcome_label"]],integer(r,"horizon"),integer(r,"p"))):
        rows.append([r["outcome_label"],integer(r,"horizon"),integer(r,"p"),integer(r,"N"),integer(r,"df"),integer(r,"maxlags"),n(r,"wald_statistic"),
            n(r,"raw_p"),n(r,"bh_q"),n(r,"holm_p"),"Yes" if boolean(r,"reject_bh_05") else "No","Yes" if boolean(r,"reject_holm_05") else "No"])
        trace.append(dict(sheet="A2_Additional_Lags_Wald",row=len(rows)+5,source="S1/lp_lag_extra_terms_wald.csv",source_rows=[wald.index(r)+2],key=[r["outcome_label"],integer(r,"horizon"),integer(r,"p")]))
    assert len(rows)==45 and sum(r[-2]=="Yes" for r in rows)==4 and sum(r[-1]=="Yes" for r in rows)==4
    spec("A2_Additional_Lags_Wald","A2. Additional lag controls","HAC Wald tests of oil and own-outcome lags 3..p. Four corrected rejections concern additional controls, not the current oil coefficient.",
        ["Outcome","h","p","N","df","HAC L","Wald W","Raw p","BH q","Holm p","BH reject","Holm reject"],rows,
        [text,i,i,i,i,i,dec,prob,prob,prob,text,text],[10,5,5,7,5,8,13,14,14,14,11,12],["S1/lp_lag_extra_terms_wald.csv"],[0,1,2],flags={"10":8,"11":9})
    cumulative=read(S2/"lag_stage2_cumulative_mbb.csv")
    rows=[]
    for r in sorted(cumulative,key=lambda r:(ORDER[r["outcome"]],integer(r,"p"),integer(r,"H"))):
        rows.append([r["outcome"],integer(r,"p"),integer(r,"H"),n(r,"point_estimate"),n(r,"ci_low"),n(r,"ci_high"),n(r,"bootstrap_se"),n(r,"raw_p"),n(r,"bh_q"),n(r,"holm_p"),
            "Yes" if boolean(r,"positive_CI") else "No","Yes" if boolean(r,"reject_bh_05") else "No","Yes" if boolean(r,"reject_holm_05") else "No"])
        trace.append(dict(sheet="B_Cumulative_MBB",row=len(rows)+5,source="S2/lag_stage2_cumulative_mbb.csv",source_rows=[cumulative.index(r)+2],key=[r["outcome"],integer(r,"p"),integer(r,"H")]))
    assert len(rows)==195
    spec("B_Cumulative_MBB","B. Cumulative associations","L=12 shared MBB, 5,000 effective draws. Pointwise percentile CI. Filter H=3, 6 or 12 for the principal summaries.",
        ["Outcome","p","H","Cumulative","CI lower","CI upper","MBB SE","Raw p","BH q","Holm p","CI > 0","BH reject","Holm reject"],rows,
        [text,i,i]+[dec]*4+[prob]*3+[text]*3,[10,5,5]+[13]*4+[14]*3+[10,11,12],["S2/lag_stage2_cumulative_mbb.csv"],[0,1,2],flags={"11":8,"12":9})
    paired=read(S2/"lag_stage2_paired_stage_contrasts.csv")
    contrastorder={"Fuel–PPI":0,"Fuel–CPI":1,"PPI–CPI":2}
    rows=[]
    for r in sorted(paired,key=lambda r:(integer(r,"p"),integer(r,"H"),contrastorder[r["contrast"]])):
        rows.append([integer(r,"p"),integer(r,"H"),r["contrast"],n(r,"point_estimate"),n(r,"ci_low"),n(r,"ci_high"),n(r,"bootstrap_se"),n(r,"raw_p"),n(r,"bh_q"),n(r,"holm_p"),
            "Yes" if boolean(r,"reject_bh_05") else "No","Yes" if boolean(r,"reject_holm_05") else "No"])
        trace.append(dict(sheet="C_Paired_Contrasts",row=len(rows)+5,source="S2/lag_stage2_paired_stage_contrasts.csv",source_rows=[paired.index(r)+2],key=[integer(r,"p"),integer(r,"H"),r["contrast"]]))
    assert len(rows)==45
    spec("C_Paired_Contrasts","C. Direct price-stage contrasts","Nine tests per p. At H=3, p=6 PPI−CPI passes BH (q=0.028794) but not Holm (p=0.067187). Intervals are pointwise.",
        ["p","H","Contrast","Difference","CI lower","CI upper","MBB SE","Raw p","BH q","Holm p","BH reject","Holm reject"],rows,
        [i,i,text]+[dec]*4+[prob]*3+[text]*2,[5,5,14]+[13]*4+[14]*3+[11,12],["S2/lag_stage2_paired_stage_contrasts.csv"],[0,1,2],flags={"10":8,"11":9})
    cross=read(S2/"lag_stage2_cross_p_differences.csv")
    rows=[]
    for r in sorted(cross,key=lambda r:(ORDER[r["outcome"]],integer(r,"H"),integer(r,"alternative_p"))):
        rows.append([r["outcome"],integer(r,"alternative_p"),integer(r,"H"),n(r,"point_estimate"),n(r,"relative_point_change_percent"),n(r,"ci_low"),n(r,"ci_high"),
            n(r,"bootstrap_se"),n(r,"raw_p"),n(r,"bh_q"),n(r,"holm_p"),"Yes" if boolean(r,"reject_bh_05") else "No","Yes" if boolean(r,"reject_holm_05") else "No"])
        trace.append(dict(sheet="D_Cross_Lag_Comparison",row=len(rows)+5,source="S2/lag_stage2_cross_p_differences.csv",source_rows=[cross.index(r)+2],key=[r["outcome"],integer(r,"alternative_p"),integer(r,"H")]))
    assert len(rows)==36 and all(r[-2:]==["No","No"] for r in rows)
    spec("D_Cross_Lag_Comparison","D. Cross-lag paired differences","Alternative p minus common-sample p=2. Twelve tests per outcome. Corrected nonrejection does not establish equivalence.",
        ["Outcome","Alt p","H","Difference","Change (%)","CI lower","CI upper","MBB SE","Raw p","BH q","Holm p","BH reject","Holm reject"],rows,
        [text,i,i,dec,"0.00",dec,dec,dec,prob,prob,prob,text,text],[10,7,5,13,13,13,13,13,14,14,14,11,12],["S2/lag_stage2_cross_p_differences.csv"],[0,1,2],flags={"11":9,"12":10})
    baseline=read(S1/"lp_lag_p2_baseline_comparison.csv")
    sortedbase=sorted(baseline,key=lambda r:(ORDER[r["outcome_label"]],integer(r,"horizon")))
    rows=[[r["outcome_label"],integer(r,"horizon"),integer(r,"original_N"),integer(r,"common_N"),n(r,"original_cumulative_point"),n(r,"common_cumulative_point"),n(r,"cumulative_delta"),r["original_start"],r["common_start"],r["end"]] for r in sortedbase]
    spec("E_Baseline_Comparison","E1. Original and common-sample p=2","N and origin end refer to h=H, not a single cumulative-sum sample. Original and Stage2 Bootstrap streams are not paired across samples.",
        ["Outcome","H","Formal N","Common N","Formal sum","Common sum","Difference","Formal start","Common start","Origin end"],rows,
        [text,i,i,i,dec,dec,dec,text,text,text],[10,5,10,11,13,13,13,14,14,14],["S1/lp_lag_p2_baseline_comparison.csv"],[0,1],table_name="BaselineCumulative")
    rows=[[r["outcome_label"],integer(r,"horizon"),n(r,"original_coefficient"),n(r,"common_coefficient"),n(r,"coefficient_delta"),n(r,"original_hac_se"),n(r,"common_hac_se"),n(r,"original_raw_p"),n(r,"common_raw_p")] for r in sortedbase]
    spec("E_Baseline_Comparison","E2. Period coefficients and HAC","Raw p columns below are period HAC probabilities, not Bootstrap tests of differences between samples.",
        ["Outcome","h","Formal beta","Common beta","Difference","Formal HAC SE","Common HAC SE","Formal raw p","Common raw p"],rows,
        [text,i]+[dec]*5+[prob]*2,[10,5,13,13,13,17,18,16,16],["S1/lp_lag_p2_baseline_comparison.csv"],[0,1],start=50,table_name="BaselinePeriod")
    for j,r in enumerate(sortedbase):
        for row,tablekey in [(j+6,"cumulative"),(j+51,"period")]:trace.append(dict(sheet="E_Baseline_Comparison",row=row,source="S1/lp_lag_p2_baseline_comparison.csv",source_rows=[baseline.index(r)+2],key=[r["outcome_label"],integer(r,"horizon"),tablekey]))
    joint=read(S2/"lag_stage2_joint_windows.csv")
    wo={"short":0,"medium":1,"late":2,"all":3};ranges={"short":"0–3","medium":"4–6","late":"7–12","all":"0–12"}
    rows=[]
    for r in sorted(joint,key=lambda r:(ORDER[r["outcome"]],integer(r,"p"),wo[r["window"]])):
        assert r["status"]=="EVALUATED"
        rows.append([r["outcome"],integer(r,"p"),r["window"],ranges[r["window"]],integer(r,"df"),n(r,"wald_statistic"),n(r,"raw_p"),n(r,"bh_q"),n(r,"holm_p"),
            "Yes" if boolean(r,"reject_bh_05") else "No","Yes" if boolean(r,"reject_holm_05") else "No"])
        trace.append(dict(sheet="F_Joint_Windows",row=len(rows)+5,source="S2/lag_stage2_joint_windows.csv",source_rows=[joint.index(r)+2],key=[r["outcome"],integer(r,"p"),r["window"]]))
    assert len(rows)==60
    spec("F_Joint_Windows","F. Joint period-response windows","Bootstrap-calibrated vector tests, not cumulative-sum tests. CPI p=6 short/all pass BH but not Holm.",
        ["Outcome","p","Window","h range","df","Wald W","Boot p","BH q","Holm p","BH reject","Holm reject"],rows,
        [text,i,text,text,i,dec,prob,prob,prob,text,text],[10,5,11,10,5,13,14,14,14,11,12],["S2/lag_stage2_joint_windows.csv"],[0,1,2],flags={"9":7,"10":8})
    p1={}
    p2={}
    definitions=[
        ["Purpose","Additional Supporting Information for the retained p=2 reference. Lag-order sensitivity evaluates p=1, 2, 3, 4 and 6; it does not certify an optimal or dynamically sufficient p."],
        ["Assembly status","Assembled and checked locally. Not uploaded, published, or accepted by the journal. The formal manuscript, Figures 1–7, Tables 1–6 and S1–S17 remain unchanged."],
        ["Fuel","d_fuel_power_inflation: calendar-month first difference of the fuel-and-power purchase-price year-on-year inflation rate (percentage points)."],
        ["PPI","d_ppi_inflation: calendar-month first difference of the producer-price year-on-year inflation rate (percentage points)."],
        ["CPI","d_cpi_inflation: calendar-month first difference of the consumer-price year-on-year inflation rate (percentage points)."],
        ["Oil explanatory variable","dlog_oil_rmb = 100 × calendar-month difference of log(Brent USD × CNY per USD). One unit approximates a 1% monthly RMB oil-price increase."],
        ["Coefficient units","Percentage-point association with changes in year-on-year inflation per one unit of dlog_oil_rmb. Cumulative sums are not cumulative price-level growth or causal effects."],
        ["p, h and H","p is the number of oil-change and own-outcome lags (1..p each). h is a period projection horizon (0..12); H is the upper horizon in the coefficient sum C(H)=sum of beta(h), h=0..H."],
        ["Regression design","OLS with intercept, current dlog_oil_rmb, p oil-change lags and p own-outcome lags; k=2+2p. No future outcome is a predictor."],
        ["Common sample","Each h uses identical origin months for all p and outcomes. Origin start: 1998-08; h0 end 2026-02, N331; h12 end 2025-02, N319. Endpoint changes with h."],
        ["Formal p=2 reference","Original p=2 starts 1998-04 (N335 at h0; N323 at h12). Common p=2 removes four initial origin months. E1 N/end columns describe the last component h=H, not one sample for the cumulative sum. E2 compares period HAC only."],
        ["OLS working likelihood","Gaussian OLS log likelihood profiles variance at RSS/N. AIC=-2ll+2k; BIC=-2ll+log(N)k; HQIC=-2ll+2log(log(N))k. Count intercept and mean coefficients, exclude scale, matching existing code."],
        ["Information-criterion scope","Ordinary OLS criteria, not HAC criteria. Compare only within outcome, h and the common sample. Δmin=value−minimum; Δp2=value−p2. No cross-outcome/h absolute comparisons or global voting."],
        ["Additional-control Wald","Test oil and own-outcome lags 3..p equal zero for p3/4/6 at h0/1/3/6/12 (2/4/8 restrictions). Bartlett HAC, max(12,h+1), N/(N−k) correction, full-rank asymptotic χ² test."],
        ["Wald family","15 tests per outcome (3 extensions × 5 h). BH primary; Holm sensitivity. Rejection concerns extra controls, not the current oil coefficient. Four rejections remain in A2."],
        ["Stage1 adverse evidence","At h6 all outcomes favor p6 by AIC/BIC/HQIC and reject added controls after BH/Holm. PPI h12 also rejects. Fuel/PPI h6–9 favor p6; p6 is the candidate boundary."],
        ["MBB construction","Noncircular length-12 blocks sampled from 338 source-calendar months; preconstruct lag/lead pairs, concatenate 29 blocks and truncate to 338 rows. All p, outcomes and h share each index vector."],
        ["Horizon-specific draws","Apply the frozen h-specific valid-month mask after shared resampling. N* varies by draw/h, identically across p and outcomes at that draw/h. Lags and leads are not reconstructed at block joins."],
        ["MBB parameters","5,000 globally effective repetitions; seed 2026101202, SeedSequence [2026101202,12,0]. 5,000 attempts, zero failed/removed repetitions. Every equation is fully refitted."],
        ["Cumulative draws","Sum the h-specific period coefficients within each shared repetition, retaining each h's endpoint sample. Paired stage and cross-p differences subtract within that same repetition."],
        ["Interval definition","95% pointwise percentile MBB CI (linear/type-7 quantiles), L12 only. Not HAC intervals, simultaneous bands or FDR-adjusted intervals. MBB SE uses ddof=1."],
        ["Scalar probability","Two-sided null-centered p=(1+count(|draw−point|≥|point|))/(5000+1). Plus-one Monte Carlo correction. Percentile intervals and centered-test decisions are not strict inverses."],
        ["Cumulative family","13 H tests per outcome–p; 15 separate families. BH and Holm saved results are reported separately from the pointwise intervals."],
        ["Stage-difference family","Nine paired contrasts per p (Fuel−PPI, Fuel−CPI, PPI−CPI at H3/6/12); five separate families. Do not infer differences from marginal-CI overlap or different significance levels."],
        ["H3 ordering boundary","All p retain positive paired H3 intervals and three BH-supported contrasts. For p6 PPI−CPI, BH q=0.028794 but Holm p=0.067187. No universal correction-method or block-length claim."],
        ["Cross-p family","12 paired differences per outcome (p1/3/4/6 minus common p2 × H3/6/12); three families. None rejects after BH/Holm. Nonrejection does not establish equivalence; no equivalence margin/test."],
        ["Relative-change column","Change (%) stores 100 × (alternative cumulative−p2 cumulative)/p2 cumulative. The stored number is already a percentage; do not multiply it by 100 again."],
        ["Joint-window family","Four vector-zero windows per outcome–p: short h0–3, medium h4–6, late h7–12, all h0–12. Full-path covariance and centered-bootstrap Wald calibration; not cumulative-sum or primary χ² p tests."],
        ["CPI joint boundary","CPI p6 short/all BH q=0.048390, Holm p=0.083183. Other p do not pass BH for these windows. Threshold crossing alone does not establish a strong uniformly supported joint path."],
        ["Other block lengths","Alternative p were NOT run at L6 or L18. Original p2 multi-block analyses remain separate; no multi-block ROBUST_ASSOCIATION label is transferred to this sensitivity."],
        ["Policy timing","Stage1 and Stage2 policies were fixed before their respective computations during manuscript revision. Stage2 was informed by Stage1 results. Neither is described as original-study preregistration."],
        ["Reading the flags","Yes/No is the saved rejection decision at 0.05 (BH or Holm); CI>0 is a separate interval sign flag. Pale amber indicates BH/Holm disagreement or added-control rejection, not an economic direction."],
        ["Numeric precision","Cells contain numbers parsed directly from frozen CSV values without display rounding. Display uses six decimals (small p/q in scientific notation); Change (%) uses two. Full double precision is retained in XLSX storage."],
        ["Editable snapshot","The workbook is an editable assembly of frozen statistical outputs, not an Excel estimation engine. It does not re-estimate models, bootstrap, or adjust families when numeric cells are changed."],
        ["Source aliases","S1=05_revision/08_lp_lag_sensitivity; S2=S1/stage2_mbb. Project: rmb-oil-price-transmission-china. Exact source paths and SHA256 are in S18_PROVENANCE.json and the assembly QA audit."],
    ]
    for item in specs:
        if item["table_name"]!="BaselinePeriod":definitions.append([item["sheet"],"; ".join(item["sources"])])
    definitions.extend([["Stage1 policy SHA256",POLICY_HASHES[0]],["Stage2 policy SHA256",POLICY_HASHES[1]]])
    readmespec=dict(sheet="README",title=TITLE,note="Stationary LP lag-order sensitivity. Local assembly; supporting evidence and inferential limits are defined below.",
        headers=["Topic","Definition / source"],rows=definitions,formats=[text,text],widths=[31,125],sources=[],header_row=5,first_data_row=6,table_name="S18Readme",key_columns=[0],flag_columns={},preview_rows=12)
    return dict(title=TITLE,sheets=[readmespec]+specs,trace=trace,assembly_only=True,statistical_estimation=False)
