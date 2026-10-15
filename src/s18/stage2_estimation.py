"""S18 Stage2: original shared MBB fitting and inference; R3-only execution."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests
from phase15_common import REV
from stage1_helpers import array_hash
from stage2_kernels import generate,counts_from,fit_batch,scalar_interval,adjust
PS=[1,2,3,4,6]
YV=["d_fuel_power_inflation","d_ppi_inflation","d_cpi_inflation"]
YL=["Fuel","PPI","CPI"]
HS=list(range(13));CH=[3,6,12];ALT=[1,3,4,6]
CONTRASTS=["Fuel–PPI","Fuel–CPI","PPI–CPI"]
PAIRS=[(0,1),(0,2),(1,2)]
WINDOWS={"short":list(range(4)),"medium":[4,5,6],"late":list(range(7,13)),"all":HS}
SEED=2026101202;TARGET=5000;BLOCK=12;MAX_ATTEMPTS=10000;BATCH=250
S1=REV/"s18/stage1";OUT=REV/"s18/stage2"
def dest(name):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);return path
def read(path):return pd.read_csv(path,float_precision="round_trip")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,rows):
    (rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)).to_csv(dest(name),index=False,encoding="utf-8-sig")
def jsave(name,obj):dest(name).write_text(json.dumps(obj,indent=2),encoding="utf-8")
def log(text):print(text,flush=True)
def load_designs():
    source=pd.read_csv(REV/"01_data/long_sample_transformed.csv",parse_dates=["month"],float_precision="round_trip")
    ix=pd.PeriodIndex(source.month,freq="M")
    assert ix.equals(pd.period_range(ix.min(),ix.max(),freq="M"))
    r=read(S1/"lp_lag_period_hac.csv")
    registry=read(S1/"lag_sensitivity_sample_registry.csv")
    membership=read(S1/"lag_sensitivity_sample_months.csv")
    designs=[]
    point=np.full((5,3,13),np.nan)
    rows=[]
    masks=[]
    for h in HS:
        names=membership[membership.horizon==h].shock_origin_month.tolist()
        masks.append(ix.astype(str).isin(names))
        assert ix[masks[h]].astype(str).tolist()==names
    for pi,p in enumerate(PS):
        for yi,y in enumerate(YV):
            for h in HS:
                row=r[(r.p==p)&(r.outcome==y)&(r.horizon==h)].iloc[0]
                g=registry[(registry.p==p)&(registry.outcome==y)&(registry.horizon==h)].iloc[0]
                cols=json.loads(row.design_columns)
                d=read(S1/row.design_file)
                X=d[cols].to_numpy(float)
                Y=d.response.to_numpy(float)
                valid=np.asarray(masks[h],bool)
                assert valid.sum()==row.N==g.N and sha(S1/row.design_file)==row.design_file_sha256
                assert hashlib.sha256("|".join(d.month).encode()).hexdigest()==row.sample_sha256
                expected=np.column_stack([np.ones(valid.sum()),source.dlog_oil_rmb[valid]]+
                    [source[v].shift(l)[valid] for v in ["dlog_oil_rmb",y] for l in range(1,p+1)])
                assert np.array_equal(X,expected) and np.array_equal(Y,source[y].shift(-h)[valid])
                fit=sm.OLS(Y,X).fit()
                delta=float(fit.params[1]-row.coefficient)
                assert abs(delta)<2e-12 and np.linalg.matrix_rank(X)==len(cols)==2+2*p
                point[pi,yi,h]=row.coefficient
                designs.append(dict(pi=pi,yi=yi,p=p,outcome=y,label=YL[yi],h=h,cols=cols,X=X,Y=Y,
                    valid=valid,j=1,ncalendar=len(ix),key=f"p{p}_{y}",month_positions=np.flatnonzero(valid)))
                rows.append(dict(p=p,outcome=y,horizon=h,N=len(Y),coefficient=float(fit.params[1]),stage1_coefficient=float(row.coefficient),delta=delta,
                    sample_sha256=row.sample_sha256,design_file=row.design_file,design_sha256=row.design_sha256))
    save("lag_stage2_point_reconciliation.csv",rows)
    return designs,point,ix

def run():
    check_original_outputs()
    designs,point,ix=load_designs()
    log(f"FORMAL_MBB_BEGIN B_effective_target={TARGET} L={BLOCK} seed={SEED}; shared calendar N={len(ix)}")
    rng=np.random.default_rng(np.random.SeedSequence([SEED,BLOCK,0]))
    attempted=accepted=0
    allparts=[];starts_parts=[];index_parts=[];accepted_ids=[];failures=[];drawrows=[]
    while accepted<TARGET and attempted<MAX_ATTEMPTS:
        size=min(BATCH,TARGET-accepted,MAX_ATTEMPTS-attempted)
        starts,index=generate(rng,size,len(ix))
        batch=fit_batch(index,designs)
        ids=np.arange(attempted,attempted+size)
        allparts.append(batch);starts_parts.append(starts);index_parts.append(index)
        accepted_ids.extend(ids[batch["good"]].tolist())
        for f in batch["failures"]:
            f["attempt_id"]=attempted+f.pop("batch_draw");failures.append(f)
        for j,attempt in enumerate(ids):
            drawrows.append(dict(attempt_id=int(attempt),accepted=bool(batch["good"][j]),seed=SEED,L=BLOCK,
                full_calendar_draw_length=len(ix),block_count=starts.shape[1],index_sha256=array_hash(index[j].astype("<u2")),
                valid_N_h0=int(batch["N"][j,0]),valid_N_h12=int(batch["N"][j,12]),min_valid_N=int(batch["N"][j].min()),
                max_gram_condition_number=float(np.nanmax(batch["condition"][j])),
                failed_equations=int(np.count_nonzero(batch["status"][j])),status="ALL195_VALID" if batch["good"][j] else "GLOBAL_REJECTED"))
        attempted+=size;accepted+=int(batch["good"].sum())
        log(f"MBB_PROGRESS attempts={attempted} globally_valid={accepted} rejected={attempted-accepted}")
    allindex=np.concatenate(index_parts).astype("<u2")
    allstarts=np.concatenate(starts_parts).astype("<u2")
    ids=np.array(accepted_ids,dtype=np.int32)
    allpath=np.concatenate([x["path"] for x in allparts])
    path=allpath[ids]
    np.savez_compressed(dest("lag_stage2_bootstrap_indices.npz"),indices=allindex,starts=allstarts,accepted_attempt_ids=ids,
        calendar_months=ix.astype(str).to_numpy(dtype="U7"),seed=SEED,seed_sequence_entropy=np.array([SEED,BLOCK,0]),block_length=BLOCK)
    np.savez_compressed(dest("lag_stage2_fit_diagnostics.npz"),N_by_attempt_h=np.concatenate([x["N"] for x in allparts]),
        ranks=np.concatenate([x["ranks"] for x in allparts]),gram_condition_numbers=np.concatenate([x["condition"] for x in allparts]),
        fit_status=np.concatenate([x["status"] for x in allparts]),accepted_attempt_ids=ids,p_values=np.array(PS),outcomes=np.array(YL),horizons=np.array(HS),
        status_code_zero="FULL_RANK_FINITE_SOLVE",status_code_one="FIT_FAILED",axis_order="attempt,p,outcome,h")
    failcols=["attempt_id","p","outcome","horizon","N","k","rank","gram_condition_number","reason"]
    save("lag_stage2_bootstrap_failures.csv",pd.DataFrame(failures,columns=failcols))
    acceptedmap={int(a):i for i,a in enumerate(ids)}
    registry=pd.DataFrame(drawrows)
    registry["effective_draw_id"]=registry.attempt_id.map(acceptedmap).fillna(-1).astype(int)
    save("lag_stage2_bootstrap_draw_registry.csv",registry)
    if accepted!=TARGET:
        jsave("lag_stage2_estimation_summary.json",dict(status="FAILED_EFFECTIVE_TARGET",attempted=attempted,valid=accepted,target=TARGET,failures=len(failures)))
        raise RuntimeError("Effective draw target not reached; inference blocked")
    assert path.shape==(TARGET,5,3,13) and np.isfinite(path).all()
    np.savez_compressed(dest("lag_stage2_period_draws.npz"),period_coefficients=path,original_period_points=point,accepted_attempt_ids=ids,
        p_values=np.array(PS),outcomes=np.array(YL),outcome_variables=np.array(YV),horizons=np.array(HS),axis_order="draw,p,outcome,h")
    cumulative=np.cumsum(path,axis=3)
    cp=np.cumsum(point,axis=2)
    np.savez_compressed(dest("lag_stage2_cumulative_draws.npz"),cumulative_coefficients=cumulative,original_cumulative_points=cp,
        accepted_attempt_ids=ids,p_values=np.array(PS),outcomes=np.array(YL),horizons=np.array(HS),axis_order="draw,p,outcome,H")
    cr=[]
    for pi,p in enumerate(PS):
        for yi,y in enumerate(YL):
            for H in HS:
                cr.append(dict(p=p,outcome=y,H=H,point_estimate=float(cp[pi,yi,H]),**scalar_interval(cumulative[:,pi,yi,H],cp[pi,yi,H])))
    C=adjust(cr,["outcome","p"]);assert C.family_size.eq(13).all()
    save("lag_stage2_cumulative_mbb.csv",C)
    stage=np.empty((TARGET,5,3,3));sr=[]
    for pi,p in enumerate(PS):
        for hi,H in enumerate(CH):
            for ci,(a,b) in enumerate(PAIRS):
                stage[:,pi,hi,ci]=cumulative[:,pi,a,H]-cumulative[:,pi,b,H]
                pt=cp[pi,a,H]-cp[pi,b,H]
                sr.append(dict(p=p,H=H,contrast=CONTRASTS[ci],point_estimate=float(pt),**scalar_interval(stage[:,pi,hi,ci],pt)))
    S=adjust(sr,["p"]);assert S.family_size.eq(9).all()
    save("lag_stage2_paired_stage_contrasts.csv",S)
    np.savez_compressed(dest("lag_stage2_paired_stage_draws.npz"),paired_differences=stage,p_values=np.array(PS),H_values=np.array(CH),
        contrasts=np.array(CONTRASTS),accepted_attempt_ids=ids,axis_order="draw,p,H,contrast")
    cross=np.empty((TARGET,4,3,3));xr=[]
    for ai,p in enumerate(ALT):
        pi=PS.index(p)
        for yi,y in enumerate(YL):
            for hi,H in enumerate(CH):
                v=cumulative[:,pi,yi,H]-cumulative[:,PS.index(2),yi,H]
                cross[:,ai,yi,hi]=v
                pt=cp[pi,yi,H]-cp[PS.index(2),yi,H]
                xr.append(dict(alternative_p=p,baseline_p=2,outcome=y,H=H,point_estimate=float(pt),relative_point_change_percent=float(100*pt/cp[PS.index(2),yi,H]),**scalar_interval(v,pt)))
    X=adjust(xr,["outcome"]);assert X.family_size.eq(12).all()
    X=X.drop(columns=["positive_CI","support"])
    X["ci_excludes_zero"]=(X.ci_low>0)|(X.ci_high<0)
    X["difference_support"]=np.where(X.reject_bh_05,"L12_BH_DIFFERENCE_SUPPORT","NO_CORRECTED_DIFFERENCE_EVIDENCE")
    save("lag_stage2_cross_p_differences.csv",X)
    np.savez_compressed(dest("lag_stage2_cross_p_draws.npz"),paired_differences=cross,alternative_p=np.array(ALT),outcomes=np.array(YL),H_values=np.array(CH),
        accepted_attempt_ids=ids,axis_order="draw,alternative_p,outcome,H")
    jr=[];jointcov=[]
    for pi,p in enumerate(PS):
        for yi,y in enumerate(YL):
            for name,hs in WINDOWS.items():
                vals=path[:,pi,yi,hs]
                covariance=np.atleast_2d(np.cov(vals.T,ddof=1))
                rank=int(np.linalg.matrix_rank(covariance));eigen=np.linalg.eigvalsh(covariance)
                if rank!=len(hs) or eigen.min()<=0:
                    jr.append(dict(p=p,outcome=y,window=name,status="NOT EVALUATED",reason="COVARIANCE_RANK_OR_POSITIVITY",raw_p=np.nan))
                    continue
                pt=point[pi,yi,hs];err=vals-pt
                stat=float(pt@np.linalg.solve(covariance,pt))
                statistics=np.sum(err*np.linalg.solve(covariance,err.T).T,axis=1)
                count=int(np.count_nonzero(statistics>=stat))
                jr.append(dict(p=p,outcome=y,window=name,horizons=json.dumps(hs),status="EVALUATED",reason="",
                    wald_statistic=stat,covariance_rank=rank,df=len(hs),covariance_min_eigenvalue=float(eigen.min()),
                    covariance_condition_number=float(np.linalg.cond(covariance)),raw_p=(1+count)/(TARGET+1),null_tail_count=count,
                    chi2_p_diagnostic_only=float(chi2.sf(stat,len(hs))),valid_draws=TARGET,
                    calibration="centered-bootstrap Wald plus-one; NOT chi-square primary p"))
                for a,ha in enumerate(hs):
                    for b,hb in enumerate(hs):jointcov.append(dict(p=p,outcome=y,window=name,h_a=ha,h_b=hb,covariance=float(covariance[a,b])))
    J=pd.DataFrame(jr)
    if J.status.eq("EVALUATED").all():J=adjust(jr,["outcome","p"])
    else:
        for (y,p),g in J.groupby(["outcome","p"]):
            if g.status.eq("EVALUATED").all():
                ids=g.index;J.loc[ids,"bh_q"]=multipletests(g.raw_p,method="fdr_bh")[1];J.loc[ids,"holm_p"]=multipletests(g.raw_p,method="holm")[1]
            else:J.loc[g.index,"family_adjustment_status"]="NOT EVALUATED: incomplete fixed 4-window family"
    save("lag_stage2_joint_windows.csv",J)
    save("lag_stage2_joint_window_covariances.csv",jointcov)
    return dict(attempted=attempted,effective=accepted,rejected=attempted-accepted)

from interface import PACKAGE
REFERENCE=PACKAGE/"reference"

def check_original_outputs():
    # Read-only reconstruction of saved Phase2B primary L12 scalar/joint outputs.
    paths=np.load(REFERENCE/"bootstrap/phase2b_bootstrap_paths_long_L12.npz",allow_pickle=False)
    period=read(REFERENCE/"statistics/lp_final_coefficients.csv")
    cumul=read(REFERENCE/"statistics/lp_cumulative_response.csv")
    hierarchy=read(REFERENCE/"statistics/price_hierarchy_tests.csv")
    joint=read(REFERENCE/"statistics/lp_joint_tests.csv")
    checks=[]
    saved_ref=[]
    cp=[]
    draws=[]
    for yi,y in enumerate(YV):
        mid=f"PRIMARY_{y}"
        b=period[period.outcome==y].sort_values("horizon").coefficient.to_numpy()
        path=paths[mid]
        assert path.shape==(TARGET,13) and np.isfinite(path).all()
        cp.append(np.cumsum(b));draws.append(np.cumsum(path,axis=1))
        for h in HS:
            row=cumul[(cumul.outcome==y)&(cumul.horizon==h)&(cumul.block_length==BLOCK)].iloc[0]
            test=scalar_interval(draws[-1][:,h],cp[-1][h])
            ok=np.allclose([test["ci_low"],test["ci_high"],test["raw_p"]],
                           [row.bootstrap_ci_low,row.bootstrap_ci_high,row.bootstrap_p],rtol=1e-11,atol=2e-12)
            assert ok
            checks.append(dict(check=f"original_cumulative_{y}_{h}",passed=ok))
        for window,hs in WINDOWS.items():
            C=np.atleast_2d(np.cov(path[:,hs].T,ddof=1));rank=np.linalg.matrix_rank(C)
            assert rank==len(hs) and np.linalg.eigvalsh(C).min()>0,"Original joint full rank gate failed"
            point=b[hs]
            stat=float(point@np.linalg.solve(C,point))
            errors=path[:,hs]-point
            ww=np.sum(errors*np.linalg.solve(C,errors.T).T,axis=1)
            p=(1+np.count_nonzero(ww>=stat))/(TARGET+1)
            row=joint[(joint.model==mid)&(joint.block_length==BLOCK)&(joint.window==window)].iloc[0]
            ok=np.allclose([stat,p],[row.wald_statistic,row.raw_p],rtol=2e-10,atol=2e-12)
            assert ok
            checks.append(dict(check=f"original_joint_{y}_{window}",passed=ok))
    for hi,H in enumerate(CH):
        for ci,(a,b) in enumerate(PAIRS):
            name=f"{YV[a]} minus {YV[b]}"
            row=hierarchy[(hierarchy.contrast==name)&(hierarchy.horizon==H)&(hierarchy.block_length==BLOCK)].iloc[0]
            test=scalar_interval(draws[a][:,H]-draws[b][:,H],cp[a][H]-cp[b][H])
            ok=np.allclose([test["ci_low"],test["ci_high"],test["raw_p"]],
                [row.bootstrap_ci_low,row.bootstrap_ci_high,row.raw_p],rtol=1e-11,atol=2e-12)
            assert ok
            checks.append(dict(check=f"original_stage_{CONTRASTS[ci]}_{H}",passed=ok))
            saved_ref.append(dict(H=H,contrast=CONTRASTS[ci],original_point=float(row.difference),original_ci_low=float(row.bootstrap_ci_low),
                original_ci_high=float(row.bootstrap_ci_high),original_raw_p=float(row.raw_p),original_bh_q=float(row.fdr_q),original_holm_p=float(row.holm_p),
                reference="Frozen original p2 full sample; original seed and L12, not paired to new independent stream"))
    save("lag_stage2_original_p2_stage_reference.csv",saved_ref)
    save("lag_stage2_original_inference_reconciliation.csv",checks)
    return checks
