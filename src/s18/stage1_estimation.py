"""S18 Stage1 scientific construction and checks extracted from frozen implementation."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2,norm
from statsmodels.stats.multitest import multipletests
from stage1_helpers import calendar,lookup,month_hash,array_hash
from phase15_common import REV
from phase2b_core import build,hac
PSET=[1,2,3,4,6]
HS=list(range(13))
WH=[0,1,3,6,12]
YS=["d_fuel_power_inflation","d_ppi_inflation","d_cpi_inflation"]
LABEL=dict(zip(YS,["Fuel","PPI","CPI"]))
SHOCK="dlog_oil_rmb"
INPUTS=["01_data/long_sample_canonical.csv","01_data/long_sample_transformed.csv"]
OUT=REV/"s18/stage1"
def path_out(name):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);return path
def save(name,rows):
    (rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)).to_csv(path_out(name),index=False,encoding="utf-8-sig")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def log(text):print(text,flush=True)
def selected_original_functions():return {"build":build,"hac":hac}
def estimate():
    checks = []

    def check(name, passed, detail=""):
        checks.append(dict(check=name, passed=bool(passed), detail=str(detail)))
        if not passed:
            save("lag_sensitivity_qa.csv", checks)
            raise RuntimeError(f"QA FAIL: {name} {detail}")

    log("ESTIMATION_BEGIN: authorized R3 only")
    d = pd.read_csv(REV / INPUTS[1], parse_dates=["month"], float_precision="round_trip")
    c = pd.read_csv(REV / INPUTS[0], parse_dates=["month"], float_precision="round_trip")
    ix = calendar(d)
    check("intact_input_calendar", calendar(c).equals(ix), f"{ix.min()}..{ix.max()}, N={len(ix)}")
    logoil = pd.DataFrame(dict(month=c.month, log=np.log(c.oil_rmb)))
    regenerated = {SHOCK:100*(logoil.log.to_numpy()-lookup(logoil, "log", -1))}
    for y, source in zip(YS, ["ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"]):
        f = pd.DataFrame(dict(month=c.month, inflation=c[source]-100))
        regenerated[y] = f.inflation.to_numpy()-lookup(f, "inflation", -1)
    for var, values in regenerated.items():
        check(f"canonical_transform_{var}", np.allclose(values, d[var], rtol=0, atol=2e-12, equal_nan=True),
              f"maximum error={np.nanmax(np.abs(values-d[var])):.17g}; use saved full precision transformed input")
    z = pd.DataFrame(dict(month=d.month))
    for variable in [SHOCK]+YS:
        z[variable] = d[variable]
        for lag in range(1, 7):
            z[f"{variable}_lag{lag}"] = lookup(d, variable, -lag)
    for y in YS:
        for h in HS:
            z[f"{y}_lead{h}"] = lookup(d, y, h)
    original = selected_original_functions()
    saved = pd.read_csv(REV / "03_tables/lp_final_coefficients.csv", float_precision="round_trip")
    registry = pd.read_csv(REV / "00_audit/phase2b_primary_model_registry.csv")
    modelrows, sample_rows, membership, parameter_rows, waldrows, baseline_rows = [], [], [], [], [], []
    for h in HS:
        required = [SHOCK]+[f"{v}_lag{l}" for v in [SHOCK]+YS for l in range(1,7)]+[f"{y}_lead{h}" for y in YS]
        valid = np.isfinite(z[required].to_numpy(float)).all(axis=1)
        months = ix[valid].astype(str).tolist()
        mh = month_hash(months)
        check(f"common_calendar_h{h}", len(months)>14 and not pd.PeriodIndex(months,freq="M").has_duplicates and
              pd.PeriodIndex(months,freq="M").equals(pd.period_range(months[0],months[-1],freq="M")), f"N={len(months)}")
        for order, month in enumerate(months):
            membership.append(dict(horizon=h, row_order=order, shock_origin_month=month, sample_sha256=mh))
        monthfile = f"months/h{h}.txt"
        path_out(monthfile).write_text("\n".join(months)+"\n", encoding="utf-8")
        for y in YS:
            response = z.loc[valid, f"{y}_lead{h}"].to_numpy(float)
            for p in PSET:
                cols = ["const", SHOCK]+[f"{SHOCK}_lag{l}" for l in range(1,p+1)]+[f"{y}_lag{l}" for l in range(1,p+1)]
                clean = z.loc[valid, ["month"]+[v for v in cols if v!="const"]].copy()
                clean["const"] = 1.0
                X = clean[cols].to_numpy(float)
                n, k = X.shape
                rank = np.linalg.matrix_rank(X)
                check(f"full_rank_{LABEL[y]}_h{h}_p{p}", rank==k==2+2*p and len(set(cols))==k and not any("lead" in v for v in cols))
                f = sm.OLS(response, X).fit()
                bw = max(12, h+1)
                r = f.get_robustcov_results(cov_type="HAC", maxlags=bw, kernel="bartlett", use_correction=True, use_t=False)
                V = np.asarray(r.cov_params())
                check(f"finite_hac_{LABEL[y]}_h{h}_p{p}", np.isfinite(V).all() and np.all(np.diag(V)>0) and np.isfinite(f.params).all())
                CI = r.conf_int(alpha=0.05)
                designhash = hashlib.sha256(json.dumps(cols,separators=(",",":")).encode()+bytes.fromhex(mh)+bytes.fromhex(array_hash(X))).hexdigest()
                responsehash = array_hash(response)
                equationhash = hashlib.sha256(bytes.fromhex(designhash)+bytes.fromhex(responsehash)).hexdigest()
                fn = f"designs/{LABEL[y]}_h{h}_p{p}.csv"
                design = pd.DataFrame(X, columns=cols)
                design.insert(0, "response", response)
                design.insert(0, "month", months)
                save(fn, design)
                base = dict(outcome=y, outcome_label=LABEL[y], horizon=h, p=p, N=n,
                            sample_start=months[0], sample_end=months[-1], k=k,
                            design_columns=json.dumps(cols), design_rank=int(rank), design_condition_number=float(np.linalg.cond(X)),
                            sample_sha256=mh, X_sha256=array_hash(X), design_sha256=designhash,
                            response_sha256=responsehash, equation_sha256=equationhash,
                            design_file=fn, design_file_sha256=sha(OUT/fn), maxlags=bw,
                            kernel="Bartlett", small_sample_correction=True, use_t=False,
                            hac_correction_factor=n/(n-k), role="SENSITIVITY")
                row = dict(base, coefficient=float(f.params[1]), hac_se=float(r.bse[1]),
                           hac_ci_low=float(CI[1,0]), hac_ci_high=float(CI[1,1]), raw_p=float(r.pvalues[1]),
                           RSS=float(f.ssr), log_likelihood=float(f.llf), AIC=float(f.aic), BIC=float(f.bic),
                           HQIC=float(f.info_criteria("hqic")), adjusted_R2=float(f.rsquared_adj))
                modelrows.append(row)
                sample_rows.append(dict(base, months_file=monthfile, months_file_sha256=sha(OUT/monthfile)))
                for j, term in enumerate(cols):
                    parameter_rows.append(dict(outcome=y,horizon=h,p=p,term=term,coefficient=float(f.params[j]),
                         hac_se=float(r.bse[j]),hac_ci_low=float(CI[j,0]),hac_ci_high=float(CI[j,1]),raw_p=float(r.pvalues[j])))
                save(f"covariances/{LABEL[y]}_h{h}_p{p}.csv", pd.DataFrame(V,columns=cols).assign(term=cols)[["term"]+cols])
                if p>2 and h in WH:
                    extra = [f"{v}_lag{l}" for v in [SHOCK,y] for l in range(3,p+1)]
                    R = np.zeros((len(extra),k))
                    for j, term in enumerate(extra):
                        R[j,cols.index(term)] = 1.0
                    q = len(extra)
                    C = R@V@R.T
                    eigen = np.linalg.eigvalsh(C)
                    cr = np.linalg.matrix_rank(C)
                    rr = np.linalg.matrix_rank(R)
                    identified = rr==cr==q and np.all(eigen>0) and np.allclose(C,C.T,rtol=1e-12,atol=1e-12)
                    check(f"wald_identifiable_{LABEL[y]}_h{h}_p{p}", identified, f"rank R={rr}, rank C={cr}, df={q}, min eig={eigen.min()}")
                    b = R@f.params
                    W = float(b@np.linalg.solve(C,b))
                    save(f"restrictions/{LABEL[y]}_h{h}_p{p}.csv",pd.DataFrame(R,columns=cols).assign(restricted_term=extra)[["restricted_term"]+cols])
                    waldrows.append(dict(outcome=y,outcome_label=LABEL[y],horizon=h,p=p,N=n,k=k,
                        restriction_terms=json.dumps(extra),restriction_count=q,restriction_rank=int(rr),restricted_covariance_rank=int(cr),
                        restricted_covariance_min_eigenvalue=float(eigen.min()),restricted_covariance_condition_number=float(np.linalg.cond(C)),
                        wald_statistic=W,df=q,raw_p=float(chi2.sf(W,q)),maxlags=bw,correction_factor=n/(n-k),
                        sample_sha256=mh,design_sha256=designhash,reference="chi-square",status="IDENTIFIED"))
                if p==2:
                    o = original["build"](d,y,SHOCK,h)
                    of = o["fit"]
                    oh = original["hac"](of,bw)
                    sr = saved[(saved.outcome==y)&(saved.horizon==h)]
                    check(f"saved_baseline_unique_{LABEL[y]}_h{h}",len(sr)==1)
                    sr = sr.iloc[0]
                    oldmonths = o["months"].dt.strftime("%Y-%m").tolist()
                    check(f"baseline_saved_result_{LABEL[y]}_h{h}", int(of.nobs)==sr.N and
                        np.allclose([of.params[1],oh.bse[1],oh.pvalues[1]], [sr.coefficient,sr.hac_se,sr.raw_p], rtol=1e-10,atol=2e-12))
                    dr = pd.read_csv(REV/f"01_data/phase2b_design_PRIMARY_{y}_h{h}.csv",float_precision="round_trip")
                    check(f"baseline_original_design_{LABEL[y]}_h{h}",o["cols"]==cols and np.allclose(dr[cols],o["X"],rtol=0,atol=2e-12) and
                        np.allclose(dr.response,o["Y"],rtol=0,atol=2e-12) and pd.to_datetime(dr.month).dt.strftime("%Y-%m").tolist()==oldmonths)
                    rg = registry[(registry.model==f"PRIMARY_{y}")&(registry.horizon==h)].iloc[0]
                    check(f"baseline_registry_{LABEL[y]}_h{h}", rg.sample_hash==month_hash(oldmonths) and rg.terms==";".join(cols))
                    positions = [oldmonths.index(m) for m in months]
                    removed = [m for m in oldmonths if m not in set(months)]
                    check(f"only_start_truncation_{LABEL[y]}_h{h}",oldmonths[positions[0]:]==months and all(m<months[0] for m in removed) and
                        np.array_equal(o["X"][positions],X) and np.array_equal(o["Y"][positions],response), f"removed={removed}")
                    baseline_rows.append(dict(outcome=y,outcome_label=LABEL[y],horizon=h,original_N=int(of.nobs),common_N=n,
                        original_start=oldmonths[0],common_start=months[0],end=months[-1],removed_months=json.dumps(removed),
                        original_sample_sha256=month_hash(oldmonths),common_sample_sha256=mh,
                        original_coefficient=float(sr.coefficient),common_coefficient=float(f.params[1]),coefficient_delta=float(f.params[1]-sr.coefficient),
                        original_hac_se=float(sr.hac_se),common_hac_se=float(r.bse[1]),original_raw_p=float(sr.raw_p),common_raw_p=float(r.pvalues[1])))
        log(f"h={h} complete; origin {months[0]}..{months[-1]}, N={len(months)}, 15 equations")
    period = pd.DataFrame(modelrows)
    check("195_unique_equations",len(period)==195 and not period.duplicated(["outcome","horizon","p"]).any())
    check("all_outcomes_all_p_common_h_months",period.groupby("horizon").sample_sha256.nunique().eq(1).all())
    save("lp_lag_period_hac.csv",period)
    save("lp_lag_all_parameters_hac.csv",parameter_rows)
    save("lag_sensitivity_sample_registry.csv",sample_rows)
    save("lag_sensitivity_sample_months.csv",membership)
    criteria = []
    winners = []
    for (y,h), g in period.groupby(["outcome","horizon"],sort=False):
        check(f"ic_comparable_{LABEL[y]}_h{h}",g.N.nunique()==g.sample_sha256.nunique()==g.response_sha256.nunique()==1)
        ref = g[g.p==2].iloc[0]
        for criterion in ["AIC","BIC","HQIC"]:
            minimum = float(g[criterion].min())
            optimal = sorted(g.loc[g[criterion]==minimum,"p"].astype(int).tolist())
            for rr in g.to_dict("records"):
                criteria.append(dict(outcome=y,outcome_label=LABEL[y],horizon=h,p=rr["p"],N=rr["N"],k=rr["k"],
                    sample_sha256=rr["sample_sha256"],criterion=criterion,value=rr[criterion],minimum=minimum,
                    delta_to_min=rr[criterion]-minimum,delta_vs_p2=rr[criterion]-ref[criterion],optimal_p=json.dumps(optimal),
                    is_minimum=rr["p"] in optimal,likelihood_type="Gaussian OLS working likelihood; NOT HAC IC"))
            winners.append(dict(outcome=y,outcome_label=LABEL[y],horizon=h,criterion=criterion,
                optimal_p=optimal[0],all_optimal_p=json.dumps(optimal),minimum=minimum,
                optimal_minus_p2=minimum-ref[criterion],p2_delta_to_min=ref[criterion]-minimum))
    save("lp_lag_information_criteria.csv",criteria)
    save("lp_lag_ic_winners.csv",winners)
    w = pd.DataFrame(waldrows)
    check("45_unique_identified_wald",len(w)==45 and not w.duplicated(["outcome","horizon","p"]).any() and w.status.eq("IDENTIFIED").all())
    for y, ids in w.groupby("outcome").groups.items():
        check(f"wald_family_{LABEL[y]}",len(ids)==15)
        w.loc[ids,"bh_q"] = multipletests(w.loc[ids,"raw_p"], method="fdr_bh")[1]
        w.loc[ids,"holm_p"] = multipletests(w.loc[ids,"raw_p"], method="holm")[1]
        w.loc[ids,"family"] = y+"_15_extra_lag_tests"
        w.loc[ids,"family_size"] = 15
    w["reject_bh_05"] = w.bh_q<0.05
    w["reject_holm_05"] = w.holm_p<0.05
    save("lp_lag_extra_terms_wald.csv",w)
    cum = period.sort_values(["outcome","p","horizon"])[["outcome","outcome_label","p","horizon","N","sample_start","sample_end","coefficient"]].copy()
    cum["cumulative_point_estimate"] = cum.groupby(["outcome","p"]).coefficient.cumsum()
    cum["interpretation"] = "DESCRIPTIVE_ONLY; sum of horizon-specific coefficients; no joint inference"
    save("lp_lag_cumulative_point_estimates.csv",cum)
    differences = []
    for (p,h), g in cum.groupby(["p","horizon"]):
        vals = g.set_index("outcome").cumulative_point_estimate
        for a,b in [(YS[0],YS[1]),(YS[0],YS[2]),(YS[1],YS[2])]:
            differences.append(dict(p=int(p),horizon=int(h),contrast=f"{LABEL[a]}–{LABEL[b]}",outcome_a=a,outcome_b=b,
                point_a=float(vals[a]),point_b=float(vals[b]),difference=float(vals[a]-vals[b]),
                interpretation="DESCRIPTIVE_ONLY; direct point difference; NOT a paired test"))
    save("lp_lag_descriptive_stage_differences.csv",differences)
    ref = pd.DataFrame(baseline_rows).sort_values(["outcome","horizon"])
    ref["original_cumulative_point"] = ref.groupby("outcome").original_coefficient.cumsum()
    ref["common_cumulative_point"] = ref.groupby("outcome").common_coefficient.cumsum()
    ref["cumulative_delta"] = ref.common_cumulative_point-ref.original_cumulative_point
    savedcum = pd.read_csv(REV/"03_tables/lp_cumulative_response.csv",float_precision="round_trip")
    for row in ref.itertuples():
        values = savedcum[(savedcum.outcome==row.outcome)&(savedcum.horizon==row.horizon)].cumulative_effect
        check(f"baseline_cumulative_matches_{LABEL[row.outcome]}_h{row.horizon}",len(values)==3 and np.allclose(values,row.original_cumulative_point,rtol=1e-12,atol=1e-12))
    save("lp_lag_p2_baseline_comparison.csv",ref)
    save("lag_sensitivity_qa.csv",checks)
    return period
