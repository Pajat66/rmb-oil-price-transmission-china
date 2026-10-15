"""Period LP small multiples from unchanged saved statistics."""
import argparse

import csv

import hashlib

import io

import json

import re

from pathlib import Path

import xml.etree.ElementTree as ET

import numpy as np

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt

from matplotlib import font_manager

from matplotlib.lines import Line2D

from matplotlib.patches import Rectangle

from matplotlib.text import Text

from matplotlib.ticker import MaxNLocator, FormatStrFormatter

from PIL import Image

from visual_system import apply_style, OUTCOME_COLORS, OUTCOME_MARKERS, tint, panel_rule

STEM='figure_3_primary_lp_period_v1'

WIDTH,HEIGHT=190.,105.

INK,TEAL,PALE='#202729','#24675F','#E5E8E5'

OUTCOMES=[('d_fuel_power_inflation','Fuel'),('d_ppi_inflation','PPI'),('d_cpi_inflation','CPI')]

NUMERIC=['coefficient','hac_ci_low','hac_ci_high','raw_p','fdr_q','holm_p','hac_se']

FIELD_MAP={'estimate':'coefficient','ci_low':'hac_ci_low','ci_high':'hac_ci_high',
           'N':'N','raw_p':'raw_p','fdr_q':'fdr_q','holm_p':'holm_p'}

def draw(rows):
    font=font_manager.findfont('Arial',fallback_to_default=False)
    plt.rcParams.update({'font.family':'Arial','font.size':8.5,'svg.fonttype':'none','ps.fonttype':3,
        'pdf.fonttype':42,'axes.linewidth':.6,'axes.edgecolor':'#506774','axes.labelcolor':INK,
        'xtick.color':INK,'ytick.color':INK,'text.color':INK,'savefig.facecolor':'white'})
    apply_style()
    fig=plt.figure(figsize=(WIDTH/25.4,HEIGHT/25.4),dpi=300,facecolor='white')
    def txt(x,y,s,size=8.5,weight='normal',ha='left'):
        fig.text(x/WIDTH,1-y/HEIGHT,s,fontsize=size,fontweight=weight,ha=ha,va='center')
    txt(4,5,'Change in YoY inflation (percentage points) per 1-unit oil-cost change (≈1%)')
    txt(4,12,'Independent y-axis scales',8.5,'bold')
    fig.lines.append(Line2D([78/WIDTH,87/WIDTH],[1-12/HEIGHT]*2,transform=fig.transFigure,color=INK,linewidth=1.6))
    fig.lines.append(Line2D([82.5/WIDTH],[1-12/HEIGHT],transform=fig.transFigure,color=INK,marker='o',markersize=4))
    txt(89,12,'Point estimate')
    fig.patches.append(Rectangle((130/WIDTH,1-13.3/HEIGHT),6/WIDTH,2.6/HEIGHT,
        transform=fig.transFigure,facecolor=PALE,edgecolor='#819BA4',linewidth=.4))
    txt(138,12,'95% pointwise HAC CI')
    axes=[];plotted={};bounds={}
    for i,(y,label) in enumerate(OUTCOMES):
        d=[r for r in rows if r['outcome']==y]
        x=np.array([int(r['horizon']) for r in d]);estimate=np.array([float(r['estimate']) for r in d])
        lo=np.array([float(r['ci_low']) for r in d]);hi=np.array([float(r['ci_high']) for r in d])
        left=17+i*61
        color=OUTCOME_COLORS[label]; marker=OUTCOME_MARKERS[label]
        txt(left,21,'('+chr(65+i)+') '+label,10,'bold')
        panel_rule(fig,left/WIDTH,1-24/HEIGHT,45/WIDTH,color)
        ax=fig.add_axes([left/WIDTH,1-75/HEIGHT,45/WIDTH,48/HEIGHT]);axes.append(ax)
        # Opaque preblended tint equals a light translucent teal on white and
        # preserves consistent bands in EPS, which cannot encode transparency.
        band=ax.fill_between(x,lo,hi,facecolor=tint(color,.13),edgecolor='none',zorder=1)
        lowline,=ax.plot(x,lo,color=tint(color,.60),linewidth=.5,zorder=2)
        highline,=ax.plot(x,hi,color=tint(color,.60),linewidth=.5,zorder=2)
        line,=ax.plot(x,estimate,color=color,linewidth=1.6,marker=marker,markersize=4,
            markeredgecolor='white',markeredgewidth=.35,zorder=4)
        ax.axhline(0,color='#68716F',linewidth=.85,linestyle=(0,(3,3)),zorder=3)
        ax.set_xlim(-.35,12.35);span=max(hi.max(),0)-min(lo.min(),0)
        ax.set_ylim(min(lo.min(),0)-span*.08,max(hi.max(),0)+span*.08)
        ax.set_xticks(range(0,13,2));ax.yaxis.set_major_locator(MaxNLocator(nbins=5,steps=[1,2,2.5,5,10]))
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.3f' if i==2 else '%.2f'))
        ax.tick_params(labelsize=8.5,length=2.5,pad=3)
        for s in ['top','right']:ax.spines[s].set_visible(False)
        significant=np.array([r['bh_q_lt_005']=='True' for r in d])
        evidence=fig.add_axes([left/WIDTH,1-88/HEIGHT,45/WIDTH,4/HEIGHT])
        evidence.set_xlim(ax.get_xlim());evidence.set_ylim(-1,1);evidence.axis('off')
        marked=evidence.scatter(x[significant],np.zeros(significant.sum()),s=11,
            marker='s',facecolor=INK,edgecolor=INK,linewidths=.4)
        if not np.array_equal(line.get_ydata(),estimate) or not np.array_equal(lowline.get_ydata(),lo) or not np.array_equal(highline.get_ydata(),hi):
            raise ValueError('Plot arrays differ from source CSV '+y)
        vertices=set(map(tuple,band.get_paths()[0].vertices))
        if not all((float(a),float(b)) in vertices for a,b in list(zip(x,lo))+list(zip(x,hi))):
            raise ValueError('Ribbon vertices differ from source CSV '+y)
        if not np.array_equal(marked.get_offsets()[:,0],x[significant]):raise ValueError('BH marker coordinates mismatch '+y)
        if not (ax.get_ylim()[0]<lo.min() and ax.get_ylim()[1]>hi.max()):raise ValueError('Confidence limits clipped '+y)
        plotted[y]={'horizon':x.tolist(),'estimate':estimate.tolist(),'ci_low':lo.tolist(),'ci_high':hi.tolist(),
            'BH_marked_horizons':x[significant].tolist()}
        bounds[y]={'xlim':list(ax.get_xlim()),'ylim':list(ax.get_ylim()),'confidence_limits_inside_axis':True}
    txt(4,86,'BH\nq < 0.05',8.5)
    txt(100,94,'Horizon h (months)',9,ha='center')
    txt(4,102,"Squares: BH q < 0.05 within each outcome’s 13-horizon family")
    geometry=text_geometry(fig)
    return fig,{'font':'Arial','font_path':font,'canvas_mm':[WIDTH,HEIGHT],
        'geometry':geometry,'axis_bounds':bounds,'plotted_arrays':plotted,
        'band_export':'Opaque tint preblended on white; no EPS transparency flattening',
        'point_estimates_bounds_and_BH_markers_match_source':True}

def text_geometry(fig):
    fig.canvas.draw();renderer=fig.canvas.get_renderer();errors=[];extents=[];undrawn=set()
    for ax in fig.axes:
        if not ax.axison:
            undrawn.update(ax.get_xticklabels()+ax.get_yticklabels())
            undrawn.update([ax.xaxis.label,ax.yaxis.label,ax.xaxis.get_offset_text(),ax.yaxis.get_offset_text()])
            continue
        for a in ax.get_xticklabels():
            if not min(ax.get_xlim())<=a.get_position()[0]<=max(ax.get_xlim()):undrawn.add(a)
        for a in ax.get_yticklabels():
            if not min(ax.get_ylim())<=a.get_position()[1]<=max(ax.get_ylim()):undrawn.add(a)
    for artist in fig.findobj(Text):
        if not artist.get_visible() or not artist.get_text() or artist in undrawn:continue
        b=artist.get_window_extent(renderer)
        if not b.width or not b.height:continue
        if not 8<=artist.get_fontsize()<=12:errors.append('Font outside 8–12 pt: '+artist.get_text())
        if b.x0<0 or b.y0<0 or b.x1>fig.bbox.width or b.y1>fig.bbox.height:errors.append('Clipped: '+artist.get_text())
        extents.append((b,artist.get_text()))
    for i,(a,sa) in enumerate(extents):
        for b,sb in extents[i+1:]:
            if min(a.x1,b.x1)-max(a.x0,b.x0)>1 and min(a.y1,b.y1)-max(a.y0,b.y0)>1:
                errors.append('Text overlap: '+sa+' / '+sb)
    if errors:raise ValueError('\n'.join(errors))
    return {'checked_text_objects':len(extents),'font_range_pt':[8.5,10],'clipping_or_text_overlap_errors':errors}
