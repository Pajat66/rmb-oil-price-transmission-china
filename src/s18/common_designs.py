"""Pure calendar/design construction for S18; does not fit or resample data."""
import numpy as np
import pandas as pd
from stage1_helpers import calendar,lookup
PSET=[1,2,3,4,6]
YS=['d_fuel_power_inflation','d_ppi_inflation','d_cpi_inflation']
SHOCK='dlog_oil_rmb'

def construct(frame):
    ix=calendar(frame)
    z=pd.DataFrame({'month':frame.month})
    for v in [SHOCK]+YS:
        z[v]=frame[v]
        for lag in range(1,7):z[f'{v}_lag{lag}']=lookup(frame,v,-lag)
    designs=[]
    for h in range(13):
        for y in YS:z[f'{y}_lead{h}']=lookup(frame,y,h)
        needed=[SHOCK]+[f'{v}_lag{lag}' for v in [SHOCK]+YS for lag in range(1,7)]+[f'{y}_lead{h}' for y in YS]
        valid=np.isfinite(z[needed].to_numpy(float)).all(axis=1)
        for pi,p in enumerate(PSET):
            for yi,y in enumerate(YS):
                cols=['const',SHOCK]+[f'{SHOCK}_lag{lag}' for lag in range(1,p+1)]+[f'{y}_lag{lag}' for lag in range(1,p+1)]
                X=np.column_stack([np.ones(valid.sum()),z.loc[valid,cols[1:]].to_numpy(float)])
                designs.append(dict(pi=pi,yi=yi,p=p,outcome=y,h=h,cols=cols,X=X,Y=z.loc[valid,f'{y}_lead{h}'].to_numpy(float),
                   valid=valid.copy(),ncalendar=len(ix),j=1,months=ix[valid].astype(str).tolist()))
    return designs
