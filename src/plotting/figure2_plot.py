"""Coverage and distributions from a separately held, frozen plotting source."""
from pathlib import Path

import argparse

import hashlib

import io

import json

import re

import xml.etree.ElementTree as ET

import numpy as np

import pandas as pd

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt

from matplotlib import font_manager, cbook

from matplotlib.patches import Rectangle

from matplotlib.text import Text

from matplotlib.ticker import MaxNLocator

from PIL import Image

from visual_system import apply_style, OUTCOME_COLORS, tint, panel_rule, OCHRE, PLUM

STEM = 'figure_2_sample_characteristics'

WIDTH, HEIGHT = 190., 202.

INK, TEAL, GRAY = '#202729', '#24675F', '#E6E9EA'

STATES = {
    'observed': {'definition': 'Finite observation or eligible shock-origin month', 'fill': TEAL, 'hatch': None},
    'outside_coverage': {'definition': 'Calendar month outside the declared series coverage', 'fill': GRAY, 'hatch': None},
    'raw_missing': {'definition': 'Nonfinite level within declared coverage; never inferred from absence of a stored derived column', 'fill': '#B5473C', 'hatch': 'xx'},
    'transform_edge': {'definition': 'First difference unavailable because prior calendar-month level lies before coverage', 'fill': 'white', 'hatch': '////'},
    'lag_exclusion': {'definition': 'Current transformed values exist but required one/two-month lags are unavailable', 'fill': 'white', 'hatch': '////'},
    'lead_exclusion': {'definition': 'Outcome at origin plus horizon is beyond the observed calendar', 'fill': 'white', 'hatch': '////'},
}

RAW = [
    ('long', 'brent_usd', 'Brent crude-oil prices', 'USD/barrel'),
    ('long', 'cny_per_usd', 'CNY/USD exchange rate', 'CNY/USD'),
    ('long', 'oil_rmb', 'RMB-denominated oil cost', 'CNY/barrel'),
    ('long', 'ppi_fuel_power_yoy', 'Fuel', 'YoY index; previous year = 100'),
    ('long', 'ppi_yoy', 'PPI', 'YoY index; previous year = 100'),
    ('long', 'cpi_yoy', 'CPI', 'YoY index; previous year = 100'),
    ('short', 'import_crude_oil_value_100m_rmb', 'Crude-oil import values', '100 million CNY'),
    ('short', 'import_crude_oil_qty_10k_ton', 'Crude-oil import quantities', '10,000 tonnes'),
    ('short', 'import_crude_oil_unit_price_yuan_per_kg', 'Import unit values', 'CNY/kg'),
]

TRANS = [
    ('dlog_oil_rmb', 'RMB oil-cost change', 'oil_rmb', 'Approximate percentage change'),
    ('d_fuel_power_inflation', 'Fuel inflation change', 'ppi_fuel_power_yoy', 'Percentage-point change'),
    ('d_ppi_inflation', 'PPI inflation change', 'ppi_yoy', 'Percentage-point change'),
    ('d_cpi_inflation', 'CPI inflation change', 'cpi_yoy', 'Percentage-point change'),
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def monthhash(months):
    return hashlib.sha256('|'.join(months.strftime('%Y-%m')).encode()).hexdigest()

def same(a, b, name):
    if not np.allclose(np.asarray(a, float), np.asarray(b, float), rtol=1e-11, atol=1e-10, equal_nan=True):
        raise ValueError('Data mismatch: '+name)

def build_sources():
    # Historical source-construction compatibility; never needed for saved-source redraw.
    from phase15_common import REV, DATA
    inputs = {}
    def read(path, dates=False):
        inputs[str(path.relative_to(REV)).replace('\\', '/')] = digest(path)
        return pd.read_csv(path, parse_dates=['month'] if dates else None)
    frames, audit = {}, {'calendars': {}, 'transformations': {}, 'LP_design_checks': []}
    periods = {'long': ('1998-01', '2026-02'), 'short': ('2015-01', '2026-02')}
    for sample, (start, end) in periods.items():
        frames[sample] = {}
        calendar = pd.date_range(start, end, freq='MS')
        for layer in ('canonical', 'transformed'):
            d = read(DATA / (sample+'_sample_'+layer+'.csv'), True).set_index('month')
            if not d.index.equals(calendar) or d.index.has_duplicates:
                raise ValueError('Discontinuous/duplicated calendar: '+sample+' '+layer)
            frames[sample][layer] = d
        c, t = frames[sample]['canonical'], frames[sample]['transformed']
        # Confirm every carried-through canonical numeric column is unchanged.
        for v in c.select_dtypes(include=[np.number]).columns:
            same(c[v], t[v], sample+' carried '+v)
        if (c[['brent_usd','cny_per_usd','oil_rmb']].dropna() <= 0).any().any():
            raise ValueError('Nonpositive oil-price or FX level')
        same(c.oil_rmb, c.brent_usd*c.cny_per_usd, sample+' Brent x FX')
        if sample == 'short':
            same(c.import_crude_oil_unit_price_yuan_per_kg,
                 10*c.import_crude_oil_value_100m_rmb/c.import_crude_oil_qty_10k_ton,
                 'customs unit-value conversion')
        for v, label, raw, unit in TRANS:
            computed = 100*np.log(c[raw]).diff() if v.startswith('dlog') else (c[raw]-100).diff()
            same(t[v], computed, sample+' '+v)
            audit['transformations'][sample+'_'+v] = {
                'N': int(t[v].notna().sum()), 'first': t[v].first_valid_index().strftime('%Y-%m'),
                'last': t[v].last_valid_index().strftime('%Y-%m'),
                'formula': '100 * calendar log difference' if v.startswith('dlog') else 'calendar difference of YoY index minus 100',
                'units': unit}
        if sample == 'short':
            for v, raw in [('dlog_import_unit_price','import_crude_oil_unit_price_yuan_per_kg'),
                           ('dlog_import_quantity','import_crude_oil_qty_10k_ton'),
                           ('dlog_import_value','import_crude_oil_value_100m_rmb')]:
                same(t[v],100*np.log(c[raw]).diff(),v)
                audit['transformations'][sample+'_'+v] = {'N': int(t[v].notna().sum()), 'first': t[v].first_valid_index().strftime('%Y-%m'), 'last': t[v].last_valid_index().strftime('%Y-%m'), 'units':'Approximate percentage change'}
        audit['calendars'][sample] = {'start':start, 'end':end, 'months':len(calendar), 'continuous':True,
            'oil_identity_max_abs_difference': float((c.oil_rmb-c.brent_usd*c.cny_per_usd).abs().max())}
    # Macro levels on the overlap must agree; the first short-sample difference
    # intentionally lacks the previous month, unlike the long-sample difference.
    for v in ['brent_usd','cny_per_usd','oil_rmb','ppi_fuel_power_yoy','ppi_yoy','cpi_yoy']:
        same(frames['short']['canonical'][v], frames['long']['canonical'].loc[frames['short']['canonical'].index,v], 'overlap '+v)
    s1 = read(REV/'03_final_tables/S1_Data_definitions.csv').set_index('variable')
    for v, info in audit['transformations'].items():
        sample, variable = v.split('_',1)
        if variable in s1.index and (sample=='long' or variable.startswith('dlog_import')):
            row = s1.loc[variable]
            if int(row.observed_months) != info['N'] or row.observed_transformed_period != info['first']+' to '+info['last']:
                raise ValueError('S1 disagreement '+variable)
            if int(row.missing_months) != audit['calendars'][sample]['months']-info['N']:
                raise ValueError('S1 missing count disagreement '+variable)
    frame_registry = read(REV/'00_audit/phase2a_sample_frame_registry.csv').set_index('sample')
    for sample, key in [('long','CORE_TRANSMISSION_LONG'),('short','MECHANISM_SHORT')]:
        row = frame_registry.loc[key]; info = audit['calendars'][sample]
        if int(row.raw_N)!=info['months'] or row.raw_start!=info['start'] or row.raw_end!=info['end']:
            raise ValueError('Calendar registry disagreement '+sample)
    registry = read(REV/'03_final_tables/S17_Final_sample_registry.csv')
    grid = frames['long']['canonical'].index
    rows = []
    def record(panel, layer, sample, v, label, values, states, unit, path, formula, extra=None):
        values = values.reindex(grid)
        n = int((np.asarray(states)=='observed').sum())
        for i, month in enumerate(grid):
            row = {'panel': panel, 'layer': layer, 'sample': sample, 'variable':v, 'display_label':label,
                   'date':month.strftime('%Y-%m-%d'), 'value':values.iloc[i], 'units':unit,
                   'status':states[i], 'included':states[i]=='observed', 'valid_observation_count':n,
                   'source_file':str(path.relative_to(REV)).replace('\\','/'), 'source_sha256':digest(path),
                   'calculation':formula, 'filter':'status == observed', 'horizon_months':None,
                   'shock_value':None, 'shock_lag1':None, 'shock_lag2':None,
                   'outcome_lag1':None, 'outcome_lag2':None}
            if extra:
                for k, val in extra.items(): row[k] = val.iloc[i] if isinstance(val,pd.Series) else val
            rows.append(row)
    for sample,v,label,unit in RAW:
        values=frames[sample]['canonical'][v].reindex(grid)
        if not np.isfinite(values.dropna().to_numpy(float)).all():
            raise ValueError('Nonfinite raw observation '+v)
        inside=grid.isin(frames[sample]['canonical'].index)
        states=np.where(~inside,'outside_coverage',np.where(values.notna(),'observed','raw_missing'))
        record('A','raw_coverage',sample,v,label,values,states,unit,DATA/(sample+'_sample_canonical.csv'),
               'Brent USD/barrel * CNY/USD' if v=='oil_rmb' else '10 * import value / import quantity' if 'unit_price' in v else 'stored observation')
    t=frames['long']['transformed']
    for v,label,raw,unit in TRANS:
        states=np.where(t[v].notna(),'observed',np.where(grid==grid[0],'transform_edge','raw_missing'))
        for panel,layer in [('A','transformed_availability'),('B','distribution')]:
            record(panel,layer,'long',v,label,t[v],states,unit,DATA/'long_sample_transformed.csv',audit['transformations']['long_'+v]['formula'])
    masks={}
    # Rebuild design rows only, never call OLS/HAC/LP/MBB estimation.
    for y,_,_,unit in TRANS[1:]:
        for h in range(13):
            z=pd.DataFrame({'response':t[y].reindex(grid+pd.DateOffset(months=h)).to_numpy(),
                'const':1.,'dlog_oil_rmb':t.dlog_oil_rmb.to_numpy()},index=grid)
            for v in ['dlog_oil_rmb',y]:
                for lag in [1,2]:
                    z[v+'_lag'+str(lag)]=t[v].reindex(grid-pd.DateOffset(months=lag)).to_numpy()
            valid=z.notna().all(axis=1); clean=z.loc[valid]
            path=DATA/('phase2b_design_PRIMARY_'+y+'_h'+str(h)+'.csv')
            saved=read(path,True).set_index('month')
            if not saved.index.equals(clean.index) or list(saved.columns)!=list(clean.columns):
                raise ValueError('Saved LP design months/terms mismatch '+str(path))
            same(saved,clean,'LP design '+y+' h='+str(h))
            r=registry.loc[(registry.model=='PRIMARY_'+y)&(registry.horizon==h)]
            if len(r)!=1 or int(r.iloc[0].N)!=len(clean) or r.iloc[0].sample_hash!=monthhash(clean.index):
                raise ValueError('S17 N/calendar hash mismatch '+y+' '+str(h))
            audit['LP_design_checks'].append({'outcome':y,'horizon':h,'N':len(clean),
                'first':clean.index.min().strftime('%Y-%m'),'last':clean.index.max().strftime('%Y-%m'),
                'calendar_hash':monthhash(clean.index),'saved_design_and_S17_match':True})
            if h in [0,12]:
                masks[(y,h)]=valid
                current=t[['dlog_oil_rmb',y]].notna().all(axis=1)
                lagvalid=z[[c for c in z if '_lag' in c]].notna().all(axis=1)
                states=np.where(~current,'transform_edge',np.where(~lagvalid,'lag_exclusion',np.where(z.response.isna(),'lead_exclusion','observed')))
                record('A','LP_shock_origins','long','PRIMARY_'+y+'_h'+str(h),'Primary LP origins, h = '+str(h),
                       z.response,states,unit,DATA/'long_sample_transformed.csv','calendar-lead outcome and fixed two shock/two outcome lags; design only',
                       {'horizon_months':h,'shock_value':z.dlog_oil_rmb,'shock_lag1':z.dlog_oil_rmb_lag1,
                        'shock_lag2':z.dlog_oil_rmb_lag2,'outcome_lag1':z[y+'_lag1'],'outcome_lag2':z[y+'_lag2']})
    for h in [0,12]:
        if not all(masks[(TRANS[1][0],h)].equals(masks[(y,h)]) for y,_,_,_ in TRANS[1:]):
            raise ValueError('Outcome-specific origin patterns differ; cannot merge LP rows')
    audit['S1_note']='S1 missing_months includes the initial transformation edge; core raw series have no within-coverage missing values. No S1 edits made.'
    audit['legacy_count_note']='Older sample_count_checks.csv documents different level-model equations and is not the stationary primary LP registry; current S17 is authoritative.'
    audit['legacy_protection']='Original legacy files remain protected by the internal R2B baseline; no legacy numeric input is required to draw this figure.'
    return pd.DataFrame(rows),audit,inputs

def series(source,layer,v,panel='A'):
    d=source.loc[(source.panel==panel)&(source.layer==layer)&(source.variable==v)].copy()
    if d.date.duplicated().any() or len(d)!=len(pd.date_range('1998-01','2026-02',freq='MS')):
        raise ValueError('Source calendar error '+v)
    return d

def draw(source):
    font=font_manager.findfont('Arial',fallback_to_default=False)
    plt.rcParams.update({'font.family':'Arial','font.size':8.5,'text.color':INK,
        'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':'#506774',
        'axes.linewidth':.6,'svg.fonttype':'none','ps.fonttype':3,'pdf.fonttype':42,
        'hatch.linewidth':.45,'savefig.facecolor':'white'})
    apply_style()
    fig=plt.figure(figsize=(WIDTH/25.4,HEIGHT/25.4),dpi=300,facecolor='white')
    def txt(x,y,s,size=8.5,weight='normal',ha='left',color=INK):
        return fig.text(x/WIDTH,1-y/HEIGHT,s,fontsize=size,fontweight=weight,ha=ha,va='center',color=color)
    txt(4,6,'(A)',10,'bold');txt(15,6,'Sample availability and effective coverage',10,'bold')
    panel_rule(fig,4/WIDTH,1-10/HEIGHT,182/WIDTH,OCHRE)
    # True monthly bins: each bar is a union of adjacent calendar-month cells.
    ax=fig.add_axes([59/WIDTH,1-107/HEIGHT,117/WIDTH,93/HEIGHT])
    ax.set_xlim(0,338);ax.set_ylim(21.9,-.8)
    ax.set_yticks([]);ax.tick_params(axis='x',length=3,pad=3,labelsize=8.5)
    for s in ['top','right','left']:ax.spines[s].set_visible(False)
    dates=pd.date_range('1998-01','2026-02',freq='MS')
    years=['1998-01','2005-01','2010-01','2015-01','2020-01','2026-02']
    ticks=[dates.get_loc(pd.Timestamp(d))+.5 for d in years]
    ax.set_xticks(ticks);ax.set_xticklabels(['1998','2005','2010','2015','2020','2026'])
    for x in ticks[1:-1]:ax.axvline(x,color='#DCE1E3',linewidth=.5,zorder=0)
    countx=186
    txt(countx,13,'n',8.5,'bold',ha='right')
    def yfig(y):return 14+(y+.8)/22.7*93
    def heading(y,s):txt(4,yfig(y),s,8.5,'bold',color=INK)
    def strip(y,layer,v,label):
        d=series(source,layer,v);states=d.status.to_numpy();n=int(d.included.sum())
        observed_color = OCHRE if layer=='raw_coverage' and v.startswith('import_') else (
            OUTCOME_COLORS.get(label, PLUM if v=='cny_per_usd' else TEAL) if layer=='raw_coverage' else INK)
        changes=np.r_[0,np.flatnonzero(states[1:]!=states[:-1])+1,len(states)]
        for a,b in zip(changes[:-1],changes[1:]):
            st=STATES[states[a]]
            fill=observed_color if states[a]=='observed' else st['fill']
            ax.add_patch(Rectangle((a,y-.29),b-a,.58,facecolor=fill,hatch=st['hatch'],
                edgecolor='#506774' if st['hatch'] else fill,linewidth=.35,zorder=2))
        txt(4,yfig(y),label);txt(countx,yfig(y),str(n),ha='right')
        return n
    heading(0,'Macroeconomic levels / indices')
    for i,(_,v,label,_) in enumerate(RAW[:6]):strip(1+i,'raw_coverage',v,label)
    heading(7.6,'Customs levels')
    for i,(_,v,label,_) in enumerate(RAW[6:]):strip(8.6+i,'raw_coverage',v,label)
    heading(12.2,'After calendar-month transformation')
    pats=[series(source,'transformed_availability',v).status.tolist() for v,_,_,_ in TRANS]
    if not all(x==pats[0] for x in pats):raise ValueError('Cannot merge transformed availability')
    strip(13.2,'transformed_availability','dlog_oil_rmb','Four variables shown in (B)')
    heading(15,'Primary LP shock-origin months')
    strip(16,'LP_shock_origins','PRIMARY_d_fuel_power_inflation_h0','h = 0')
    strip(17,'LP_shock_origins','PRIMARY_d_fuel_power_inflation_h12','h = 12')
    txt(4,yfig(19),'No within-coverage missing values',8.5)
    # Exact boundaries reinforce short-series start and horizon-specific end.
    for date,y in [('2015-01',11.45),('2025-02',18.3)]:
        ax.text(dates.get_loc(pd.Timestamp(date))+.5,y,date,ha='center',va='center',fontsize=8.5,color=INK)
    txt(59,116,'Calendar year (January 1998–February 2026)',8.5)
    legend_y=123
    for x,w,label,state in [(4,3,'Available','observed'),(46,3,'Outside series coverage','outside_coverage'),(115,3,'Transform / lag / lead exclusion','lag_exclusion')]:
        st=STATES[state]
        fig.patches.append(Rectangle((x/WIDTH,1-(legend_y+1.3)/HEIGHT),w/WIDTH,2.6/HEIGHT,
            transform=fig.transFigure,facecolor=st['fill'],edgecolor='#506774',linewidth=.4,hatch=st['hatch']))
        txt(x+5,legend_y,label,8.5)
    txt(4,134,'(B)',10,'bold');txt(15,134,'Distributions of transformed variables',10,'bold')
    panel_rule(fig,4/WIDTH,1-138/HEIGHT,182/WIDTH,TEAL)
    stats={}
    for i,(v,label,_,unit) in enumerate(TRANS):
        col,row=i%2,i//2;x=8+col*96; top=142+row*29
        d=series(source,'distribution',v,'B');values=d.loc[d.included,'value'].to_numpy(float)
        txt(x,top,label+'  (n = '+str(len(values))+')',9,'bold')
        bx=fig.add_axes([x/WIDTH,1-(top+14)/HEIGHT,78/WIDTH,9/HEIGHT])
        stat=cbook.boxplot_stats(values,whis=1.5)[0]
        color=OUTCOME_COLORS.get(label.split(' inflation')[0],INK)
        stats[v]={k:float(stat[k]) for k in ['q1','med','q3','whislo','whishi']}
        stats[v].update({'N':len(values),'min':float(values.min()),'max':float(values.max()),
            'outlier_count':len(stat['fliers']),'outliers':stat['fliers'].tolist(),
            'quartile_method':'NumPy linear percentiles','whisker_rule':'Most extreme observed values within 1.5 IQR of Q1/Q3','units':unit})
        bx.axvline(0,color='#7A858B',linewidth=.7,linestyle=(0,(3,3)),zorder=0)
        bx.bxp([stat],vert=False,widths=.65,showfliers=True,patch_artist=True,
            boxprops={'facecolor':tint(color,.16),'edgecolor':color,'linewidth':.9},
            medianprops={'color':INK,'linewidth':1.5},whiskerprops={'color':color,'linewidth':.9},
            capprops={'color':color,'linewidth':.9},flierprops={'marker':'o','markersize':3,
                'markerfacecolor':'white','markeredgecolor':color,'markeredgewidth':.65})
        lo,hi=values.min(),values.max();pad=(hi-lo)*.08
        bx.set_xlim(min(lo-pad,0),max(hi+pad,0));bx.set_ylim(.4,1.6);bx.set_yticks([])
        bx.xaxis.set_major_locator(MaxNLocator(nbins=4,min_n_ticks=3))
        bx.tick_params(axis='x',labelsize=8.5,length=3,pad=2)
        for s in ['top','right','left']:bx.spines[s].set_visible(False)
        txt(x+39,top+24,unit,8.5,ha='center')
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    extents=[];errors=[]
    undrawn_ticks=set()
    for axis in fig.axes:
        for artist in axis.get_xticklabels():
            if not axis.get_xlim()[0]<=artist.get_position()[0]<=axis.get_xlim()[1]:
                undrawn_ticks.add(artist)
    for artist in fig.findobj(Text):
        if not artist.get_visible() or not artist.get_text() or artist in undrawn_ticks:continue
        # Only drawn ticks: Matplotlib also retains ticks outside x limits.
        if artist.axes and artist in artist.axes.get_xticklabels():
            if not artist.axes.get_xlim()[0]<=artist.get_position()[0]<=artist.axes.get_xlim()[1]:continue
        b=artist.get_window_extent(renderer)
        if b.width==0 or b.height==0:continue
        if not 8<=artist.get_fontsize()<=12:errors.append('Font outside 8–12 pt: '+artist.get_text())
        if b.x0<0 or b.y0<0 or b.x1>fig.bbox.width or b.y1>fig.bbox.height:errors.append('Clipped: '+artist.get_text())
        extents.append((b,artist.get_text()))
    for i,(a,sa) in enumerate(extents):
        for b,sb in extents[i+1:]:
            if min(a.x1,b.x1)-max(a.x0,b.x0)>1 and min(a.y1,b.y1)-max(a.y0,b.y0)>1:
                errors.append('Text overlap: '+sa+' / '+sb)
    if errors:raise ValueError('\n'.join(errors))
    return fig,stats,{'font':'Arial','font_path':font,'font_range_pt':[8.5,10],
        'canvas_mm':[WIDTH,HEIGHT],'text_objects_checked':len(extents),'geometry_errors':errors}
