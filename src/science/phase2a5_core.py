"""Phase 2A.5 stationary dynamic-lag grids and prespecified Almon sensitivities."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from numpy.polynomial.legendre import legvander
from statsmodels.stats.diagnostic import acorr_breusch_godfrey, acorr_ljungbox, het_breuschpagan
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from statsmodels.tsa.stattools import acf

from phase15_common import DATA, TABLES, calendar_lag, write_csv

LONG_Y=["d_fuel_power_inflation","d_ppi_inflation"]
SHOCK_LONG="dlog_oil_rmb"
SHOCK_MECH="dlog_import_unit_price"


def load(sample):
    z=pd.read_csv(DATA/f"{sample}_sample_transformed.csv")
    z.month=pd.to_datetime(z.month)
    periods=pd.PeriodIndex(z.month,freq="M")
    if z.month.duplicated().any() or not periods.equals(pd.period_range(periods.min(),periods.max(),freq="M")):
        raise ValueError("transformed canonical months are not continuous")
    return z


def lagged(df,y,x,max_r,max_p,extra=()):
    z=df[["month",y]].copy()
    for i in range(1,max_r+1):
        z[f"{y}_lag{i}"]=calendar_lag(df,y,i)
    for j in range(max_p+1):
        z[f"{x}_lag{j}"]=calendar_lag(df,x,j)
    for name in extra:
        z[name]=df[name]
    return z


def common_sample(z,y,x,max_r,max_p,extra=()):
    needed=["month",y]
    needed += [f"{y}_lag{i}" for i in range(1,max_r+1)]
    needed += [f"{x}_lag{j}" for j in range(max_p+1)]
    needed += list(extra)
    # holdback is max lag; row at that position can still have the initial
    # transformed-value NA. Drop it once, before the entire candidate grid.
    c=z.iloc[max(max_r,max_p):][needed].dropna().copy()
    months=pd.PeriodIndex(c.month,freq="M")
    if not months.equals(pd.period_range(months.min(),months.max(),freq="M")):
        raise ValueError("common sample has interior calendar missingness")
    return c


def cols(y,x,r,p):
    return [f"{y}_lag{i}" for i in range(1,r+1)]+[f"{x}_lag{j}" for j in range(p+1)]


def ols(data,y,predictors):
    return sm.OLS(data[y].astype(float),sm.add_constant(data[predictors].astype(float),has_constant="add")).fit()


def metrics(f):
    return {"N":int(f.nobs),"k":len(f.params),"AIC":f.aic,"BIC":f.bic,
            "HQIC":f.info_criteria("hqic"),"RSS":float(np.sum(f.resid**2)),
            "adjusted_R2":f.rsquared_adj}


def diag(f,max_acf=12):
    residual=np.asarray(f.resid)
    a=acf(residual,nlags=max_acf,fft=False)
    lb=acorr_ljungbox(residual,lags=[6,12],return_df=True)
    bg6=acorr_breusch_godfrey(f,nlags=6)
    bg12=acorr_breusch_godfrey(f,nlags=12)
    bp=het_breuschpagan(residual,f.model.exog)
    jb=jarque_bera(residual)
    out={f"residual_ACF_lag{j}":float(a[j]) for j in range(1,max_acf+1)}
    out.update({"Ljung_Box_lag6_stat":float(lb.loc[6,"lb_stat"]),"Ljung_Box_lag6_p":float(lb.loc[6,"lb_pvalue"]),
                "Ljung_Box_lag12_stat":float(lb.loc[12,"lb_stat"]),"Ljung_Box_lag12_p":float(lb.loc[12,"lb_pvalue"]),
                "Breusch_Godfrey_lag6_LM":float(bg6[0]),"Breusch_Godfrey_lag6_p":float(bg6[1]),
                "Breusch_Godfrey_lag12_LM":float(bg12[0]),"Breusch_Godfrey_lag12_p":float(bg12[1]),
                "Durbin_Watson":float(durbin_watson(residual)),
                "Breusch_Pagan_LM":float(bp[0]),"Breusch_Pagan_p":float(bp[1]),
                "Jarque_Bera_stat":float(jb[0]),"Jarque_Bera_p":float(jb[1])})
    return out


def grid(df,sample,y,x,rmax,pmax):
    z=lagged(df,y,x,rmax,pmax)
    c=common_sample(z,y,x,rmax,pmax)
    rows=[]
    for r in range(rmax+1):
        for p in range(pmax+1):
            f=ols(c,y,cols(y,x,r,p))
            rows.append({"sample":sample,"dependent_variable":y,"shock":x,
                         "r":r,"p":p,"holdback":max(rmax,pmax),
                         "common_start":c.month.min().strftime("%Y-%m"),
                         "common_end":c.month.max().strftime("%Y-%m"),**metrics(f)})
    g=pd.DataFrame(rows)
    assert g.N.nunique()==1 and g.common_start.nunique()==1
    return g,c


def select_bic(g):
    return g.sort_values(["BIC","k","r","p"],kind="stable").iloc[0]


def almon_basis(L,degree):
    return legvander(np.linspace(-1,1,L+1),degree)


def almon_design(c,y,x,r,L,degree):
    basis=almon_basis(L,degree)
    out=c[["month",y]+[f"{y}_lag{i}" for i in range(1,r+1)]].copy()
    shock=c[[f"{x}_lag{j}" for j in range(L+1)]].to_numpy()
    for m in range(degree+1):
        out[f"{x}_poly{m}"]=shock@basis[:,m]
    return out,[f"{y}_lag{i}" for i in range(1,r+1)]+[f"{x}_poly{m}" for m in range(degree+1)]


def fit_almon(c,y,x,r,L,degree):
    z,features=almon_design(c,y,x,r,L,degree)
    f=ols(z,y,features)
    theta=np.array([f.params[f"{x}_poly{m}"] for m in range(degree+1)])
    beta=almon_basis(L,degree)@theta
    return z,features,f,beta


def almon_grid(df,sample,y,x,r,L_values,degrees,holdback):
    z=lagged(df,y,x,r,holdback)
    c=common_sample(z,y,x,r,holdback)
    rows=[]; coefficients=[]
    for L in L_values:
        for d in degrees:
            zz,features,f,beta=fit_almon(c,y,x,r,L,d)
            row={"sample":sample,"dependent_variable":y,"shock":x,"r":r,"L":L,"degree":d,
                 "holdback":holdback,"common_start":c.month.min().strftime("%Y-%m"),
                 "common_end":c.month.max().strftime("%Y-%m"),**metrics(f),
                 "coefficient_sum":float(beta.sum()),"impact_effect":float(beta[0]),
                 "basis":"Legendre polynomial in normalized lag j/L"}
            rows.append(row)
            coefficients += [{"sample":sample,"dependent_variable":y,"shock":x,"r":r,"L":L,"degree":d,
                              "lag":j,"shock_coefficient":float(b),"selected_BIC":False} for j,b in enumerate(beta)]
    g=pd.DataFrame(rows)
    assert g.N.nunique()==1
    return g,pd.DataFrame(coefficients),c


def simple_diagnostics(df,sample,y,x):
    z=lagged(df,y,x,0,18)
    c=common_sample(z,y,x,0,18)
    rows=[]
    for p in (2,6,12,18):
        f=ols(c,y,cols(y,x,0,p))
        rows.append({"sample":sample,"dependent_variable":y,"shock":x,"p":p,"r":0,
                     "common_start":c.month.min().strftime("%Y-%m"),"common_end":c.month.max().strftime("%Y-%m"),
                     **metrics(f),**diag(f)})
    return pd.DataFrame(rows)


def run_initial():
    long,short=load("long"),load("short")
    simple=[]; long_grids=[];extended=[];selected=[]; long_diag=[];almon_grids=[];almon_coef=[]
    for y in LONG_Y:
        simple.append(simple_diagnostics(long,"long",y,SHOCK_LONG))
        simple.append(simple_diagnostics(short,"short",y,SHOCK_MECH))
        g,c=grid(long,"long",y,SHOCK_LONG,6,24)
        long_grids.append(g)
        best=select_bic(g)
        boundary="NO_BOUNDARY"
        if int(best.p)==24:
            ge,ce=grid(long,"long",y,SHOCK_LONG,6,36)
            extended.append(ge)
            best=select_bic(ge)
            boundary="PERSISTENT_LAG_BOUNDARY" if int(best.p)==36 else "RESOLVED_BY_0_36"
            c=ce
        r,p=int(best.r),int(best.p)
        f=ols(c,y,cols(y,SHOCK_LONG,r,p))
        selected.append({"model_id":f"LONG_DYNAMIC_{y}","sample":"long","dependent_variable":y,
                         "shock":SHOCK_LONG,"r":r,"p":p,"boundary_status":boundary,
                         "sample_start":c.month.min().strftime("%Y-%m"),"sample_end":c.month.max().strftime("%Y-%m"),
                         **metrics(f)})
        long_diag.append({"model_id":f"LONG_DYNAMIC_{y}","sample":"long","dependent_variable":y,
                          "shock":SHOCK_LONG,"r":r,"p":p,"boundary_status":boundary,**metrics(f),**diag(f)})
        ga,ca,ac=almon_grid(long,"long",y,SHOCK_LONG,r,(6,12,18,24),(2,3,4),24)
        chosen=select_bic(ga.rename(columns={"L":"p"}).assign(r=r))
        L,d=int(chosen.p),int(chosen.degree)
        ca["selected_BIC"]=(ca.L==L)&(ca.degree==d)
        almon_grids.append(ga);almon_coef.append(ca)
    write_csv(pd.concat(simple,ignore_index=True),"simple_dlm_dynamic_diagnostics.csv")
    write_csv(pd.concat(long_grids,ignore_index=True),"long_dynamic_dlm_grid.csv")
    if extended:
        write_csv(pd.concat(extended,ignore_index=True),"long_dynamic_dlm_extended_grid.csv")
    else:
        pd.DataFrame(columns=long_grids[0].columns).to_csv(TABLES/"long_dynamic_dlm_extended_grid.csv",index=False)
    write_csv(pd.DataFrame(selected),"long_dynamic_dlm_selected.csv")
    write_csv(pd.DataFrame(long_diag),"long_dynamic_dlm_diagnostics.csv")
    write_csv(pd.concat(almon_grids,ignore_index=True),"almon_lag_grid_long.csv")
    write_csv(pd.concat(almon_coef,ignore_index=True),"almon_lag_coefficients_long.csv")
    return pd.DataFrame(selected)


if __name__=="__main__":
    print(run_initial().to_string(index=False))
