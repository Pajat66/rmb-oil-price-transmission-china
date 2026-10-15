"""Immutable-rationale YoY alignment, OLS lag grids and HAC previews."""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']: os.environ[name]='1'
import warnings, hashlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from statsmodels.tsa.stattools import adfuller,kpss,acf
from statsmodels.stats.diagnostic import acorr_ljungbox,acorr_breusch_godfrey,het_breuschpagan,linear_reset
from statsmodels.stats.stattools import jarque_bera
from numpy.polynomial.legendre import legvander
from phase15_common import ROOT,REV,DATA,TABLES,AUDIT,LOGS,load_canonical,calendar_lag

Y=['fuel_power_inflation','ppi_inflation','cpi_inflation']
OIL='oil_rmb_yoy_pct'; IMPORT='import_unit_price_yoy_pct'; Q='import_quantity_yoy_pct'
MAPPING={OIL:'oil_rmb','brent_yoy_pct':'brent_usd','fx_yoy_pct':'cny_per_usd',
         IMPORT:'import_crude_oil_unit_price_yuan_per_kg',Q:'import_crude_oil_qty_10k_ton',
         'import_value_yoy_pct':'import_crude_oil_value_100m_rmb'}
WINDOWS={'long_core':('long','2000-01-01'),'short_refit':('short','2015-01-01'),
         'short_round1':('short','2016-07-01'),'short_round2':('short','2017-01-01'),
         'long_almon':('long','2000-07-01'),'short_almon':('short','2017-07-01')}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(z,name,folder=TABLES):
    z=z if isinstance(z,pd.DataFrame) else pd.DataFrame(z)
    z.to_csv(folder/name,index=False,encoding='utf-8-sig');return z
def sample_hash(z): return hashlib.sha256('|'.join(z.month.dt.strftime('%Y-%m')).encode()).hexdigest()

def aligned():
    raw={s:load_canonical(s) for s in ['long','short']}; result={};checks=[]
    for s,df in raw.items():
        z=df.copy()
        for out,price in MAPPING.items():
            if price not in df: continue
            if (df[price]<=0).any():raise ValueError(f'nonpositive log input {s}/{price}')
            prior=calendar_lag(df,price,12)
            z[out]=100*(np.log(df[price])-np.log(prior))
            # Independent month-key calendar lookup rather than positional shift.
            lookup=df.set_index(pd.PeriodIndex(df.month,freq='M'))[price]
            expected=np.array([100*(np.log(v)-np.log(lookup.loc[m-12])) if m-12 in lookup.index else np.nan
                               for m,v in zip(pd.PeriodIndex(df.month,freq='M'),df[price])])
            checks.append({'sample':s,'variable':out,'calendar_safe':np.allclose(z[out],expected,equal_nan=True,atol=1e-10),
                           'first_valid':z.loc[z[out].notna(),'month'].min().strftime('%Y-%m')})
        for y,index in zip(Y,['ppi_fuel_power_yoy','ppi_yoy','cpi_yoy']):z[y]=df[index]-100
        result[s]=z
    commoncols=['brent_usd','cny_per_usd','oil_rmb','ppi_fuel_power_yoy','ppi_yoy','cpi_yoy']
    a=raw['long'].set_index('month').loc[raw['short'].month,commoncols]
    b=raw['short'][commoncols]
    assert np.allclose(a.to_numpy(),b.to_numpy(),rtol=1e-10,atol=1e-8,equal_nan=True),'canonical overlap mismatch'
    # Price-history extension uses existing canonical observations; customs are NEVER extended/backfilled.
    sh=result['long'].copy(); lookup=result['short'].set_index('month')
    for c in [IMPORT,Q,'import_value_yoy_pct']:
        sh[c]=sh.month.map(lookup[c])
    save(result['long'],'long_sample_yoy_aligned.csv',DATA)
    save(sh[sh.month>='2015-01-01'].reset_index(drop=True),'short_sample_yoy_aligned.csv',DATA)
    save(checks,'phase2a9_calendar_change_checks.csv',AUDIT)
    return {'long':result['long'],'short':sh},raw,checks

def stationarity(frames):
    rows=[]; summary=[]
    domains={**WINDOWS,'long_full_valid':('long',None),'short_full_valid':('short','2015-01-01')}
    for window,(sample,start) in domains.items():
        df=frames[sample]
        if start:df=df[df.month>=pd.Timestamp(start)]
        for v in [OIL,'brent_yoy_pct','fx_yoy_pct']+Y+([IMPORT,Q,'import_value_yoy_pct'] if sample=='short' else []):
            # Trim leading missing history only; interior monthly gaps are never compressed.
            first=df[v].first_valid_index()
            z=df.loc[first:,['month',v]].copy() if first is not None else df.iloc[:0][['month',v]]
            valid=len(z)>=36 and not z[v].isna().any()
            values=z[v].to_numpy(dtype=float); ps={}
            for spec in ['c','ct']:
                for test in ['ADF','KPSS']:
                    row={'window':window,'sample':sample,'variable':v,'test':test,'deterministic':spec,
                         'series_N':len(z),'sample_start':z.month.min().strftime('%Y-%m') if len(z) else '',
                         'sample_end':z.month.max().strftime('%Y-%m') if len(z) else '',
                         'sample_hash':sample_hash(z) if len(z) else '',
                         'lag_rule':'AIC; maxlag12' if test=='ADF' else 'statsmodels auto','warnings':''}
                    if valid:
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter('always')
                            if test=='ADF': stat,p,lag,n,crit=adfuller(values,maxlag=12,regression=spec,autolag='AIC')[:5]
                            else:stat,p,lag,crit=kpss(values,regression=spec,nlags='auto');n=len(z)
                            row.update(statistic=stat,p_value=p,selected_lag=lag,effective_N=n,
                                       critical_1pct=crit.get('1%',np.nan),critical_5pct=crit['5%'],critical_10pct=crit['10%'],
                                       p_value_is_bound=test=='KPSS' and p in [.01,.10],
                                       warnings=' | '.join(str(w.message) for w in caught),test_status='TESTED')
                            ps[(test,spec)]=p
                    else:row.update(p_value=np.nan,test_status='UNTESTABLE_CALENDAR_OR_N')
                    rows.append(row)
            if valid:
                ac=ps[('ADF','c')]<.05;kc=ps[('KPSS','c')]>=.05
                ct=ps[('ADF','ct')]<.05 and ps[('KPSS','ct')]>=.05
                status='CLEAR' if ac and kc else 'BLOCKED' if not ac and not kc else 'BORDERLINE'
                summary.append({'window':window,'sample':sample,'variable':v,'N':len(z),
                                'start':z.month.min().strftime('%Y-%m'),'end':z.month.max().strftime('%Y-%m'),
                                'ADF_c_p':ps[('ADF','c')],'KPSS_c_p':ps[('KPSS','c')],
                                'ADF_ct_p':ps[('ADF','ct')],'KPSS_ct_p':ps[('KPSS','ct')],
                                'constant_consensus':ac and kc,'trend_consensus':ct,'trend_sensitivity':(ac and kc)!=ct,
                                'status':status})
            else:summary.append({'window':window,'sample':sample,'variable':v,'N':len(z),'status':'BLOCKED'})
    save(rows,'yoy_aligned_stationarity_full.csv');return save(summary,'yoy_aligned_stationarity_summary.csv')

def frame(df,y,orders,start,controls=()):
    z=df[['month',y]].copy()
    for x,p in orders.items():
        for j in range(p+1):z[f'{x}_lag{j}']=calendar_lag(df,x,j)
    for c in controls:
        if c.endswith('_lag1'):z[c]=calendar_lag(df,c[:-5],1)
        else:z[c]=df[c]
    z=z[z.month>=pd.Timestamp(start)].dropna().reset_index(drop=True)
    assert pd.PeriodIndex(z.month,freq='M').equals(pd.period_range(z.month.min(),z.month.max(),freq='M'))
    return z
def design(z,orders,controls=()):
    cols=[f'{x}_lag{j}' for x,p in orders.items() for j in range(p+1)]+list(controls)
    return sm.add_constant(z[cols].astype(float),has_constant='add')
def fit(z,y,X):return sm.OLS(z[y].astype(float),X).fit()
def metrics(f):return {'N':int(f.nobs),'k':len(f.params),'AIC':f.aic,'BIC':f.bic,'HQIC':f.info_criteria('hqic'),'adjusted_R2':f.rsquared_adj}

def grid(df,y,x,mid,maxp,window):
    sample,start=WINDOWS[window]; z=frame(df,y,{x:maxp},start);rows=[]
    for p in range(maxp+1):
        f=fit(z,y,design(z,{x:p}))
        rows.append({'model_id':mid,'sample':sample,'outcome':y,'shock':x,'p':p,'grid_max_p':maxp,
                     'window':window,'sample_start':z.month.min().strftime('%Y-%m'),'sample_end':z.month.max().strftime('%Y-%m'),
                     'sample_hash':sample_hash(z),'selection_criterion':'BIC_ONLY','quantity_in_selection':False,**metrics(f)})
    g=pd.DataFrame(rows); b=g.sort_values(['BIC','k','p'],kind='stable').iloc[0].to_dict()
    return g,b,z

def select(df,y,x,mid,core=False):
    g,b,z=grid(df,y,x,mid,12 if core else 6,'long_core' if core or x in Y else 'short_round1')
    g['round']=1; first=b['p'];allg=[g]
    if not core and first==6:
        window='long_core' if x in Y else 'short_round2'
        ge,b,z=grid(df,y,x,mid,12,window);ge['round']=2;allg.append(ge)
    b.update(first_round_p=first,round=len(allg),boundary_status='UNRESOLVED' if b['p']==b['grid_max_p'] else 'RESOLVED')
    X=design(z,{x:int(b['p'])});return pd.concat(allg,ignore_index=True),b,z,X,fit(z,y,X)

def diagnostics(f,z,y,x,mid):
    a=acf(f.resid,nlags=24,fft=False);lb=acorr_ljungbox(f.resid,lags=[6,12,18,24],return_df=True)
    jb=jarque_bera(f.resid);bp=het_breuschpagan(f.resid,f.model.exog)
    reset=linear_reset(f,power=2,test_type='fitted',use_f=True)
    fitted=np.asarray(f.fittedvalues);curvature=np.corrcoef(f.resid,(fitted-fitted.mean())**2)[0,1]
    # Diagnose after selection; only the prespecified combined gross-mean screen can block.
    scaled=np.asarray(f.model.exog).copy(); scaled[:,1:]=(scaled[:,1:]-scaled[:,1:].mean(axis=0))/scaled[:,1:].std(axis=0,ddof=1)
    standardized_condition=float(np.linalg.cond(scaled))
    beta=np.asarray(f.params);X=np.asarray(f.model.exog); inv=np.linalg.pinv(X.T@X)
    influence=np.asarray(f.get_influence().hat_matrix_diag);resid=np.asarray(f.resid)
    delta=(X@inv)*(resid/(1-influence))[:,None]
    # Only shock regressors enter cumulative weights, excluding intercept/quantity controls.
    shockmask=np.array([1. if name.startswith(x+'_lag') else 0. for name in f.params.index])
    maximum_change=float(np.max(np.abs(delta@shockmask))*z[f'{x}_lag0'].std(ddof=1)/z[y].std(ddof=1))
    numeric=bool(np.isfinite(beta).all() and np.isfinite(f.cov_params()).all().all()
                 and np.linalg.matrix_rank(X)==X.shape[1] and standardized_condition<=1e8 and maximum_change<=.5)
    gross=bool(reset.pvalue<.001 and abs(curvature)>.30)
    s={'model_id':mid,'BG6_p':acorr_breusch_godfrey(f,nlags=6)[1],'BG12_p':acorr_breusch_godfrey(f,nlags=12)[1],
       'BP_stat':bp[0],'BP_p':bp[1],'JB_stat':jb[0],'JB_p':jb[1],'RESET_p':float(reset.pvalue),
       'residual_fitted_squared_correlation':curvature,'gross_mean_misspecification':gross,
       'raw_condition_number':f.condition_number,'standardized_condition_number':standardized_condition,
       'design_rank':np.linalg.matrix_rank(X),'k_over_N':X.shape[1]/len(z),
       'max_delete_one_sum_shift_sdY_per_sdX':maximum_change,'numerical_stability':numeric,
       'serial_gate_policy':'SERIAL_CORRELATION_HANDLED_BY_HAC'}
    rows=[]
    for j in range(1,25):
        rows.append({**s,'lag':j,'ACF':a[j],'reference_band':1.96/np.sqrt(len(z)),
                     'LB_stat':lb.loc[j,'lb_stat'] if j in lb.index else np.nan,
                     'LB_p':lb.loc[j,'lb_pvalue'] if j in lb.index else np.nan})
    s.update({f'LB{j}_p':float(lb.loc[j,'lb_pvalue']) for j in lb.index},ACF1=a[1],ACF12=a[12],ACF24=a[24])
    return rows,s

def preview(f,mid,x):
    covs={'OLS':np.asarray(f.cov_params()),'HC3':np.asarray(f.get_robustcov_results(cov_type='HC3').cov_params())}
    for h in [6,12,18]:covs[f'HAC{h}']=np.asarray(f.get_robustcov_results(cov_type='HAC',maxlags=h,use_correction=True,use_t=False).cov_params())
    names=f.params.index.tolist();beta=f.params.to_numpy();w=np.array([float(t.startswith(x+'_lag')) for t in names]);total=float(w@beta)
    rows=[{'model_id':mid,'term':t,'coefficient':beta[j],'mean_terms':';'.join(names),
           'HAC_kernel':'Bartlett','small_sample_correction':True,'N':int(f.nobs),
           **{k+'_SE':float(np.sqrt(v[j,j])) for k,v in covs.items()}} for j,t in enumerate(names)]
    sums=[]
    for k,v in covs.items():
        var=float(w@v@w);se=np.sqrt(max(var,0))
        sums.append({'model_id':mid,'covariance':k,'cumulative_effect':total,'variance':var,'SE':se,
                     'CI95_lower':total-norm.ppf(.975)*se,'CI95_upper':total+norm.ppf(.975)*se,
                     'diagonal_only_variance':float(np.sum(w*w*np.diag(v))),
                     'cross_covariance_contribution':var-float(np.sum(w*w*np.diag(v))),
                     'N':int(f.nobs),'mean_terms':';'.join(names),'CI_reference':'normal asymptotic; unadjusted',
                     'inferential_role':'preview; formal admissibility determined by registry'})
    return rows,sums,covs

def gate(r,s,station,variables,role='core'):
    st=station[(station.window==r['window'])&station.variable.isin(variables)]
    reasons=[]
    if len(st)!=len(variables) or not st.status.eq('CLEAR').all():
        reasons.append('STATIONARITY_NOT_CLEAR: '+','.join(f'{v.variable}={v.status}' for _,v in st.iterrows()))
    if r['boundary_status']!='RESOLVED':reasons.append('LAG_BOUNDARY_UNRESOLVED')
    if not s['numerical_stability']:reasons.append('NUMERICAL_OR_INFLUENCE_INSTABILITY')
    if s['gross_mean_misspecification']:reasons.append('GROSS_MEAN_MISSPECIFICATION')
    if s['k_over_N']>.20:reasons.append('PARAMETER_COUNT_UNREASONABLE')
    return ('BLOCKED' if reasons else 'CLEARED_FOR_PHASE2B'),'; '.join(reasons+['SERIAL_CORRELATION_HANDLED_BY_HAC'])

def almon(df,y,x,mid,window):
    sample,start=WINDOWS[window];z=frame(df,y,{x:18},start);rows=[];coeff=[]
    for L in [12,18]:
        for degree in [2,3]:
            B=legvander(np.linspace(-1,1,L+1),degree)
            X=pd.DataFrame(z[[f'{x}_lag{j}' for j in range(L+1)]].to_numpy()@B,columns=[f'lag_poly{k}' for k in range(degree+1)])
            X=sm.add_constant(X,has_constant='add');f=fit(z,y,X)
            beta=B@f.params.iloc[1:].to_numpy();v=f.get_robustcov_results(cov_type='HAC',maxlags=12,use_correction=True,use_t=False).cov_params()
            w=np.r_[0,B.sum(axis=0)];var=float(w@v@w);se=np.sqrt(max(var,0));total=float(beta.sum())
            aid=f'{mid}_ALMON_L{L}_D{degree}'
            rows.append({'model_id':aid,'parent_model':mid,'sample':sample,'outcome':y,'shock':x,'L':L,'degree':degree,
                         'sample_start':z.month.min().strftime('%Y-%m'),'sample_end':z.month.max().strftime('%Y-%m'),
                         'sample_hash':sample_hash(z),'selection_role':'prespecified sensitivity; no promotion of boundary base',
                         **metrics(f),'cumulative_effect':total,'HAC12_SE':se,'HAC12_CI_lower':total-norm.ppf(.975)*se,
                         'HAC12_CI_upper':total+norm.ppf(.975)*se,'status':'ROBUSTNESS_ONLY'})
            coeff += [{'model_id':aid,'lag':j,'coefficient':v} for j,v in enumerate(beta)]
    return rows,coeff

def cv(z,y,X,mid,variant):
    rows=[]
    for i in range(len(z)-24,len(z)):
        f=fit(z.iloc[:i],y,X.iloc[:i]);pred=float(f.predict(X.iloc[[i]]).iloc[0]);actual=float(z[y].iloc[i])
        rows.append({'model_id':mid,'variant':variant,'month':z.month.iloc[i].strftime('%Y-%m'),
                     'train_N':i,'actual':actual,'prediction':pred,'error':actual-pred})
    e=np.array([r['error'] for r in rows]);return {'CV_RMSE':np.sqrt(np.mean(e*e)),'CV_MAE':np.mean(abs(e)),'CV_folds':24},rows
