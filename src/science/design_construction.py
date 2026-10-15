"""Pure frozen design construction. No estimation or reference array reads."""
import numpy as np
import pandas as pd
from phase15_common import calendar_lag, calendar_lead

YLIST=['d_fuel_power_inflation','d_ppi_inflation','d_cpi_inflation']
SHOCK='dlog_oil_rmb'

def build_design(df,y,shock,h,quantity=False,components=False):
    z=pd.DataFrame({'month':df.month,'response':calendar_lead(df,y,h),'const':1.,shock:df[shock]})
    cols=['const',shock]
    for x in (shock,y):
        for j in (1,2):
            c=f'{x}_lag{j}';z[c]=calendar_lag(df,x,j);cols.append(c)
    if quantity:
        z['dlog_import_quantity']=df.dlog_import_quantity;cols.append('dlog_import_quantity')
    if components:
        z=z.drop(columns=shock);cols.remove(shock)
        for x in ('dlog_brent','dlog_fx'): z[x]=df[x];cols.append(x)
    valid=z[['response']+cols].notna().all(axis=1).to_numpy()
    clean=z.loc[valid]
    assert np.all(np.diff(clean.index)==1), 'HAC must see contiguous monthly rows'
    X=clean[cols].to_numpy(float);Y=clean.response.to_numpy(float)
    return {'z':z,'cols':cols,'valid':valid,'X':X,'Y':Y,'ncalendar':len(df),'months':clean.month,'h':h,'y':y,'shock':shock,'j':cols.index(shock) if not components else None}

def build_link1(short):
    z=pd.DataFrame({'month':short.month,'dlog_import_unit_price':short.dlog_import_unit_price,'const':1.})
    cols=['const']
    for j in range(4):
        c=f'{SHOCK}_lag{j}';z[c]=calendar_lag(short,SHOCK,j);cols.append(c)
    valid=z.notna().all(axis=1).to_numpy()
    clean=z.loc[valid]
    return {'z':z,'cols':cols,'valid':valid,'X':clean[cols].to_numpy(float),
            'Y':clean.dlog_import_unit_price.to_numpy(float),'months':clean.month,
            'ncalendar':len(short),'h':0,'y':'dlog_import_unit_price','shock':SHOCK,'j':1}
