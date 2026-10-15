"""Stationary Phase 2A point estimates; no inferential model selection."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from phase15_common import AUDIT, TABLES, calendar_lag, calendar_lead, write_csv
from transformation_layer import run as transform_run

OUTCOMES = ["d_fuel_power_inflation", "d_ppi_inflation", "d_cpi_inflation"]
SHOCK = "dlog_oil_rmb"


def design(df, y, orders, holdback, start=None, end=None, controls=()):
    """Create every lag on full calendar first, then apply dates and drop NA."""
    if df.month.duplicated().any() or not pd.PeriodIndex(df.month, freq="M").equals(
            pd.period_range(df.month.min(), df.month.max(), freq="M")):
        raise ValueError("non-contiguous calendar")
    z = df[["month", y]].copy()
    cols = []
    for x, p in orders.items():
        for j in range(p + 1):
            name = f"{x}_lag{j}"
            z[name] = calendar_lag(df, x, j)
            cols.append(name)
    for x in controls:
        z[x] = df[x]
        cols.append(x)
    z = z.iloc[holdback:]
    if start is not None:
        z = z.loc[z.month >= pd.Timestamp(start)]
    if end is not None:
        z = z.loc[z.month <= pd.Timestamp(end)]
    z = z[["month", y] + cols].dropna()
    if len(z) <= len(cols) + 5:
        raise ValueError(f"model too large for sample: {y} {orders}")
    return z, cols


def fit(z, y, cols):
    return sm.OLS(z[y].astype(float), sm.add_constant(z[cols].astype(float), has_constant="add")).fit()


def fit_record(model_id, sample, y, orders, z, fit_result, shock=None, policy="none", role=""):
    row = {"model_id": model_id, "sample": sample, "dependent_variable": y,
           "regressors": ";".join(orders), "lag_orders": ";".join(f"{k}:{v}" for k,v in orders.items()),
           "control_policy": policy, "role": role, "N": len(z), "n_parameters": len(fit_result.params),
           "start": z.month.min().strftime("%Y-%m"), "end": z.month.max().strftime("%Y-%m"),
           "AIC": fit_result.aic, "BIC": fit_result.bic, "HQIC": fit_result.info_criteria("hqic"),
           "adjusted_R2": fit_result.rsquared_adj}
    coefficients = [{**row, "term": term, "coefficient": float(value)}
                    for term, value in fit_result.params.items()]
    cumulative = None
    if shock:
        terms = [f"{shock}_lag{j}" for j in range(orders[shock] + 1)]
        cumulative = {**row, "shock": shock, "cumulative_effect": float(fit_result.params[terms].sum()),
                      "lag_terms": ";".join(terms)}
    return row, coefficients, cumulative


def grid(df, sample, y, shock, maxlag, common_holdback=None):
    # Every transformed input begins with a calendar first-difference NA.
    # Hold back one extra month so p=maxlag has the same N as p=0.
    hold = maxlag + 1 if common_holdback is None else common_holdback
    rows = []
    fits = {}
    for p in range(maxlag + 1):
        z, cols = design(df, y, {shock:p}, hold)
        f = fit(z,y,cols)
        rows.append({"sample":sample,"dependent_variable":y,"shock":shock,"p":p,
                     "common_holdback":hold,"N":len(z),"n_parameters":len(f.params),
                     "start":z.month.min().strftime("%Y-%m"),"end":z.month.max().strftime("%Y-%m"),
                     "AIC":f.aic,"BIC":f.bic,"HQIC":f.info_criteria("hqic")})
        fits[p]=(z,f)
    return pd.DataFrame(rows),fits


def recommend(rows):
    """BIC first, tie within 2 BIC units resolved to fewer lags."""
    best = rows.BIC.min()
    return int(rows.loc[rows.BIC <= best + 2].sort_values("p").iloc[0].p)


def rolling_origin_error(z, y, cols, n_test=24):
    """Expanding-window, genuine one-step forecasts over last 24 observations."""
    errors=[]
    for i in range(len(z)-n_test,len(z)):
        prior=z.iloc[:i]
        fitted=fit(prior,y,cols)
        future=sm.add_constant(z.iloc[[i]][cols].astype(float),has_constant="add")
        errors.append(float(z.iloc[i][y])-float(fitted.predict(future).iloc[0]))
    return float(np.sqrt(np.mean(np.square(errors)))),float(np.mean(np.abs(errors)))


def run(frames=None):
    frames = transform_run() if frames is None else frames
    long, short = frames["long"], frames["short"]
    all_coeff, all_cum, sample_rows = [], [], []
    primary_grid, sensitivity_grid, summaries = [], [], []
    selected = {}
    for y in OUTCOMES:
        g12, _ = grid(long,"long",y,SHOCK,12)
        g18, _ = grid(long,"long",y,SHOCK,18)
        primary_grid.append(g12); sensitivity_grid.append(g18)
        p12, p18 = recommend(g12), recommend(g18)
        selected[y]=p12
        summaries.append({"dependent_variable":y,"AIC_0_12":int(g12.loc[g12.AIC.idxmin()].p),
                          "BIC_0_12":int(g12.loc[g12.BIC.idxmin()].p),
                          "HQIC_0_12":int(g12.loc[g12.HQIC.idxmin()].p),
                          "AIC_0_18":int(g18.loc[g18.AIC.idxmin()].p),
                          "BIC_0_18":int(g18.loc[g18.BIC.idxmin()].p),
                          "HQIC_0_18":int(g18.loc[g18.HQIC.idxmin()].p),
                          "benchmark_p":p12,"sensitivity_BIC_recommendation":p18,
                          "benchmark_policy":"BIC within 2 then parsimony on 0..12; no p-value selection",
                          "boundary_flag":bool(p12==12 or p18>12)})
    write_csv(pd.concat(primary_grid,ignore_index=True),"long_dlm_lag_grid_0_12.csv")
    write_csv(pd.concat(sensitivity_grid,ignore_index=True),"long_dlm_lag_grid_0_18_sensitivity.csv")
    write_csv(pd.DataFrame(summaries),"long_dlm_lag_summary.csv")

    for sample,df in [("long",long),("short",short)]:
        cc=[];cu=[]
        for y,p in selected.items():
            z,cols=design(df,y,{SHOCK:p},p)
            f=fit(z,y,cols)
            mid=f"{sample.upper()}_DLM_{y}"
            row,c,cum=fit_record(mid,sample,y,{SHOCK:p},z,f,SHOCK,role="PRIMARY_CANDIDATE" if sample=="long" else "ROBUSTNESS_CANDIDATE")
            sample_rows.append(row);cc+=c;cu.append(cum)
        write_csv(pd.DataFrame(cc),f"{sample}_dlm_coefficients_preHAC.csv")
        write_csv(pd.DataFrame(cu),f"{sample}_dlm_cumulative_effects_preHAC.csv")
        all_coeff+=cc;all_cum+=cu

    # Composite and component equations are nested on exactly the same months.
    comparisons, restrictions=[] ,[]
    for y,p in selected.items():
        zc,xc=design(long,y,{SHOCK:p},p)
        zu,xu=design(long,y,{"dlog_brent":p,"dlog_fx":p},p)
        if not zc.month.reset_index(drop=True).equals(zu.month.reset_index(drop=True)):
            raise AssertionError("component sample mismatch")
        fc,fu=fit(zc,y,xc),fit(zu,y,xu)
        R=np.zeros((p+1,len(fu.params)))
        for j in range(p+1):
            R[j,fu.params.index.get_loc(f"dlog_brent_lag{j}")]=1
            R[j,fu.params.index.get_loc(f"dlog_fx_lag{j}")]=-1
        w=fu.f_test(R)
        restrictions.append({"dependent_variable":y,"p":p,"N":len(zu),"restrictions":p+1,
                             "Wald_F_conventional":float(w.fvalue),"p_value_descriptive_only":float(w.pvalue),
                             "df_num":float(w.df_num),"df_denom":float(w.df_denom),
                             "null":"beta_brent_j = beta_fx_j for every j=0..p",
                             "covariance":"conventional; HAC deferred to Phase 2B"})
        for label,f,z,orders,shock in [("C_COMPOSITE",fc,zc,{SHOCK:p},SHOCK),
                                        ("U_COMPONENTS",fu,zu,{"dlog_brent":p,"dlog_fx":p},None)]:
            row,c,cum=fit_record(f"{label}_{y}","long",y,orders,z,f,shock,
                                 role="ROBUSTNESS_CANDIDATE" if label=="U_COMPONENTS" else "PRIMARY_CANDIDATE")
            row["representation"]=label
            row["CV_method"]="expanding origin one-step, last 24 calendar months"
            row["CV_RMSE"],row["CV_MAE"]=rolling_origin_error(z,y,xc if label=="C_COMPOSITE" else xu)
            comparisons.append(row)
            sample_rows.append(row);all_coeff+=c
            if cum: all_cum.append(cum)
    write_csv(pd.DataFrame(comparisons),"composite_components_comparison.csv")
    write_csv(pd.DataFrame(restrictions),"composite_restriction_tests.csv")

    # Customs link 1. Fixed N across candidate p and volume sensitivities.
    g1,_=grid(short,"short","dlog_import_unit_price",SHOCK,12)
    write_csv(g1,"mechanism_link1_lag_selection.csv")
    p1=recommend(g1)
    mechanism={}
    y="dlog_import_unit_price"
    z,cols=design(short,y,{SHOCK:p1},p1)
    f=fit(z,y,cols)
    row,c,cum=fit_record("MECH1_OIL_IMPORT","short",y,{SHOCK:p1},z,f,SHOCK,role="SECONDARY_CANDIDATE")
    mechanism["link1"]=p1;sample_rows.append(row);all_coeff+=c;all_cum.append(cum)
    write_csv(pd.DataFrame(c),"mechanism_link1_preHAC.csv")
    vol=[]
    for q in (0,1):
        orders={SHOCK:p1,"dlog_import_quantity":q}
        z,cols=design(short,y,orders,max(p1,q))
        f=fit(z,y,cols)
        row,c,cum=fit_record(f"MECH1_VOLUME_q{q}","short",y,orders,z,f,SHOCK,
                             policy=f"quantity log change lags 0..{q}",role="ROBUSTNESS_CANDIDATE")
        sample_rows.append(row);all_coeff+=c;all_cum.append(cum);vol+=c
    write_csv(pd.DataFrame(vol),"mechanism_link1_volume_control_preHAC.csv")

    # Mechanism link 2, same 0..12 grid and BIC rule.
    for y,tag in [("d_fuel_power_inflation","fuel"),("d_ppi_inflation","ppi")]:
        shock="dlog_import_unit_price"
        g,_=grid(short,"short",y,shock,12)
        g18,_=grid(short,"short",y,shock,18)
        p=recommend(g)
        z,cols=design(short,y,{shock:p},p)
        f=fit(z,y,cols)
        row,c,cum=fit_record(f"MECH2_{tag.upper()}","short",y,{shock:p},z,f,shock,role="SECONDARY_CANDIDATE")
        sample_rows.append(row);all_coeff+=c;all_cum.append(cum)
        rows=[{**r,"record_type":"coefficient","selected_p":p} for r in c]
        rows += [{**r,"record_type":"lag_grid","selected_p":p} for r in g.to_dict("records")]
        rows += [{**r,"record_type":"lag_grid_0_18_sensitivity","selected_p":p,
                  "sensitivity_BIC_p":recommend(g18)} for r in g18.to_dict("records")]
        orders={shock:p,"dlog_import_quantity":0}
        zv,cv=design(short,y,orders,p)
        fv=fit(zv,y,cv)
        rv,cc,cm=fit_record(f"MECH2_{tag.upper()}_VOLUME","short",y,orders,zv,fv,shock,
                            policy="quantity log change contemporaneous",role="ROBUSTNESS_CANDIDATE")
        sample_rows.append(rv);all_coeff+=cc;all_cum.append(cm)
        rows += [{**r,"record_type":"volume_sensitivity","selected_p":p} for r in cc]
        write_csv(pd.DataFrame(rows),f"mechanism_link2_{tag}_preHAC.csv")
        mechanism[f"link2_{tag}"]=p

    # CPI terminal link: individual BIC lag search, then their prespecified joint equation.
    terminal=[];term_orders={}
    y="d_cpi_inflation"
    for x in ["dlog_import_unit_price","d_fuel_power_inflation","d_ppi_inflation"]:
        g,_=grid(short,"short",y,x,6)
        p=recommend(g);term_orders[x]=p
        z,cols=design(short,y,{x:p},p)
        f=fit(z,y,cols)
        row,c,cum=fit_record(f"TERMINAL_{x}","short",y,{x:p},z,f,x,role="SECONDARY_CANDIDATE")
        sample_rows.append(row);all_coeff+=c;all_cum.append(cum)
        terminal += [{**r,"record_type":"individual_lag_grid"} for r in g.to_dict("records")]
        terminal += [{**r,"record_type":"individual_coefficient"} for r in c]
    z,cols=design(short,y,term_orders,max(term_orders.values()))
    f=fit(z,y,cols)
    row,c,_=fit_record("TERMINAL_JOINT","short",y,term_orders,z,f,role="SECONDARY_CANDIDATE")
    sample_rows.append(row);all_coeff+=c
    terminal += [{**r,"record_type":"joint_coefficient"} for r in c]
    write_csv(pd.DataFrame(terminal),"terminal_link_models_preHAC.csv")

    write_csv(pd.DataFrame(sample_rows),"phase2a_sample_registry.csv",folder=AUDIT)
    write_csv(pd.DataFrame(all_coeff),"phase2a_all_coefficients_preHAC.csv")
    write_csv(pd.DataFrame(all_cum),"phase2a_all_cumulative_preHAC.csv")
    return selected,mechanism,term_orders,pd.DataFrame(sample_rows)


if __name__ == "__main__":
    print(run()[:3])
