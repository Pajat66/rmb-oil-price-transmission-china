"""Temporal strips, recursive ranges and formal p/q evidence from saved results."""
import os,statistics
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm
from matplotlib.patches import Rectangle

from visual_system import apply_style, text_geometry, OUTCOME_COLORS, PLUM, tint, panel_rule


W, H, DPI = 190., 220., 300


INK, TEAL, BLUE, GRAY, RULE = '#202729', '#24675F', '#74556F', '#87918E', '#DCE1DE'


OUTCOMES = ('d_fuel_power_inflation', 'd_ppi_inflation', 'd_cpi_inflation')


LABELS = dict(zip(OUTCOMES, ('Fuel', 'PPI', 'CPI')))


HORIZONS = (0, 3, 6, 12)


UNIT = 'percentage-point change in YoY inflation per one 100-times-log oil-price change (approximately 1%)'


TESTS = ('SUP_WALD', 'RECURSIVE_CUSUM', 'HANSEN')


def row_labels(ax, ys, pairs):
    ax.set_yticks(ys)
    ax.set_yticklabels([f'{LABELS[y]}  h={h}' for y,h in pairs],fontsize=8.5)
    ax.tick_params(axis='y',length=0,pad=8)
    for artist,(y,h) in zip(ax.get_yticklabels(),pairs):
        artist.set_color(OUTCOME_COLORS[LABELS[y]])


def plot(source,summary,formal):
    font_manager.findfont('Arial',fallback_to_default=False)
    plt.rcParams.update({'font.family':'Arial','font.size':8.5,'text.color':INK,
        'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':GRAY,
        'axes.linewidth':.65,'xtick.labelsize':8.5,'ytick.labelsize':8.5,
        'svg.fonttype':'none','ps.fonttype':3,'pdf.fonttype':42,
        'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
    apply_style()
    fig=plt.figure(figsize=(W/25.4,H/25.4),dpi=100)
    fig.text(.055,.982,'(A) Rolling temporal coefficient strips',fontsize=10,fontweight='bold',va='top')
    fig.text(.055,.959,'120-month windows; h=0, 3, 6, 12; all 2,529 estimates; pointwise HAC12 uncertainty',va='top')
    panel_rule(fig,.055,.944,.89,TEAL)
    ax=fig.add_axes([.18,.710,.64,.229])
    months=pd.period_range('2008-03','2026-02',freq='M')
    cmap=LinearSegmentedColormap.from_list('plum_white_teal',[(0,PLUM),(.5,'#FAFBF9'),(1,OUTCOME_COLORS['Fuel'])],N=256)
    norm=TwoSlopeNorm(vmin=-.08,vcenter=0,vmax=.08)
    roll=source[(source.diagnostic_type=='rolling')&(source.window_length==120)]
    color_arrays=[]
    for yy,(y,h) in zip(RPOS,ROWS):
        g=roll[(roll.outcome==y)&(roll.horizon==h)].sort_values('displayed_date')
        x=pd.PeriodIndex(g.displayed_date,freq='M').asi8-months.asi8[0]
        polys=[[(xx-.5,yy-.31),(xx+.5,yy-.31),(xx+.5,yy+.31),(xx-.5,yy+.31)] for xx in x]
        coll=PolyCollection(polys,array=g.estimate.to_numpy(float),cmap=cmap,norm=norm,edgecolors='none',antialiased=False)
        ax.add_collection(coll); color_arrays.append((coll,g.estimate.to_numpy(float)))
        neg=g.estimate.to_numpy(float)<0
        ax.hlines(np.full(neg.sum(),yy),x[neg]-.24,x[neg]+.24,color=INK,lw=.65)
        posci=g.ci_low.to_numpy(float)>0; negci=g.ci_high.to_numpy(float)<0
        ax.hlines(np.full(posci.sum(),yy-.40),x[posci]-.5,x[posci]+.5,color=INK,lw=.9)
        ax.hlines(np.full(negci.sum(),yy+.40),x[negci]-.5,x[negci]+.5,color=INK,lw=.9)
        if len(g)<len(months):
            ax.add_patch(Rectangle((len(g)-.5,yy-.31),len(months)-len(g),.62,
                facecolor='#EDF0F2',edgecolor=GRAY,hatch='////',lw=.25))
        frac=((g.ci_low<=0)&(g.ci_high>=0)).mean()
        ax.text(1.07,yy,f'{100*frac:.1f}%',transform=ax.get_yaxis_transform(),ha='center',va='center')
    ax.text(1.07,1.055,'CI includes 0',transform=ax.transAxes,ha='center',fontsize=8.5)
    for yy in (3.75,8.25):ax.axhline(yy,color=RULE,lw=.6)
    ax.set_xlim(-.5,len(months)-.5);ax.set_ylim(12.8,-.75);row_labels(ax,RPOS,ROWS)
    ticks=[0]+[months.get_loc(pd.Period(f'{year}-01')) for year in (2012,2016,2020,2024,2026)]
    ax.set_xticks(ticks);ax.set_xticklabels(['2008','2012','2016','2020','2024','2026'])
    ax.get_xticklabels()[0].set_ha('left');ax.get_xticklabels()[-1].set_ha('right')
    ax.set_xlabel('Rolling-window end date (shock-origin month)',labelpad=5)
    for s in ('left','top','right'):ax.spines[s].set_visible(False)
    cbax=fig.add_axes([.18,.648,.64,.011])
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cbax,orientation='horizontal',ticks=[-.08,-.04,0,.04,.08])
    cb.solids.set_rasterized(False)
    cb.outline.set_linewidth(.5);cb.ax.tick_params(length=2,pad=2)
    cb.set_label('Period coefficient (pp per approximately 1% oil-price change)',labelpad=2)
    fig.text(.055,.601,'Central ticks: negative estimate. Upper/lower rails: 95% CI wholly above/below 0.',fontsize=8.5)
    fig.text(.055,.585,'No rail: CI includes 0. Hatched tail: no horizon-valid estimate. Fractions are descriptive.',fontsize=8.5)
    # All saved recursion points determine the range, while full temporal paths remain in S2.
    fig.text(.055,.555,'(B) Recursive endpoints and ranges (same units as A)',fontsize=10,fontweight='bold')
    fig.text(.055,.536,'Gray span: observed point-estimate range, not a CI. Initial N=120.',fontsize=8.5)
    panel_rule(fig,.055,.550,.89,OUTCOME_COLORS['PPI'])
    bx=fig.add_axes([.18,.337,.41,.195])
    for yy,(y,h) in zip(RPOS,ROWS):
        r=summary[(summary.outcome==y)&(summary.horizon==h)].iloc[0]
        color=OUTCOME_COLORS[LABELS[y]]
        bx.hlines(yy,r.path_min,r.path_max,color=GRAY,lw=2.2,zorder=1)
        bx.vlines([r.path_min,r.path_max],yy-.17,yy+.17,color=GRAY,lw=.7)
        bx.plot(r.initial_estimate,yy,'o',mfc='white',mec=INK,ms=4.6,mew=.9,zorder=3)
        bx.plot(r.final_estimate,yy,'D',mfc=color,mec='white',ms=4.8,mew=.45,zorder=4)
        bx.text(1.24,yy,f'{r.initial_estimate:+.4f}'.replace('-','−'),transform=bx.get_yaxis_transform(),ha='right',va='center')
        bx.text(1.59,yy,f'{r.final_estimate:+.4f}'.replace('-','−'),transform=bx.get_yaxis_transform(),ha='right',va='center')
        bx.text(1.87,yy,f'{int(r.N_final)}',transform=bx.get_yaxis_transform(),ha='right',va='center')
    for x,t in ((1.24,'Initial'),(1.59,'Final'),(1.87,'Final N')):bx.text(x,1.02,t,transform=bx.transAxes,ha='right')
    bx.plot(1.05,1.045,'o',mfc='white',mec=INK,ms=4.6,mew=.9,transform=bx.transAxes,clip_on=False)
    bx.plot(1.43,1.045,'D',mfc=TEAL,mec=INK,ms=4.2,mew=.5,transform=bx.transAxes,clip_on=False)
    bx.set_xlim(-.035,.065);bx.set_ylim(12.8,-.75);row_labels(bx,RPOS,ROWS)
    bx.axvline(0,color=GRAY,ls='--',lw=.8,zorder=0)
    bx.set_xticks([-.03,0,.03,.06])
    for s in ('left','top','right'):bx.spines[s].set_visible(False)
    fig.text(.055,.299,'Fuel h12: Δ=−0.057899; 95% paired CI [−0.090910, −0.024887]; Holm p=0.002348.',fontsize=8.5)
    fig.text(.055,.274,'(C) Formal parameter-stability tests',fontsize=10,fontweight='bold')
    fig.text(.055,.253,'5,000 null-imposed dependent-wild draws; every saved formal horizon (0, 3, 6)',fontsize=8.5)
    panel_rule(fig,.055,.269,.89,PLUM)
    pairs=[(y,h) for y in OUTCOMES for h in (0,3,6)]
    ys=[i+(i//3)*.45 for i in range(9)]
    formal_marks=[]
    for col,(test,title) in enumerate(zip(TESTS,('sup-Wald','CUSUM','Hansen'))):
        cx=fig.add_axes([.18+col*.275,.065,.225,.155])
        for yy,(y,h) in zip(ys,pairs):
            r=formal[(formal.test==test)&(formal.outcome==y)&(formal.horizon==h)].iloc[0]
            cx.hlines(yy,r.bootstrap_p,r.fdr_q,color=RULE,lw=1)
            cx.plot(r.bootstrap_p,yy,'o',mfc='white',mec=INK,ms=4.3,mew=.9,zorder=3)
            cx.plot(r.fdr_q,yy,'D',mfc=PLUM,mec='white',ms=4.2,mew=.4,zorder=4)
            formal_marks.append([test,y,h,float(r.bootstrap_p),float(r.fdr_q)])
        cx.set_title(title,fontsize=9,pad=4,loc='left')
        cx.axvline(.05,color=GRAY,ls='--',lw=.8,zorder=0)
        cx.set_xlim(-.045,1.045);cx.set_ylim(9.35,-.6);cx.set_xticks([0,.5,1])
        if col==0:row_labels(cx,ys,pairs)
        else:cx.set_yticks([])
        for s in ('left','top','right'):cx.spines[s].set_visible(False)
    fig.text(.055,.030,'Open circles: bootstrap p. Diamonds: BH q. Dashed line: 0.05; separate nine-test families.',fontsize=8.5)
    fig.text(.055,.014,'Nonrejection does not prove constancy; maximizing dates are not confirmed breaks. S13–S14 Tables.',fontsize=8.5)
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    bounds=[]
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text():continue
        box=t.get_window_extent(renderer)
        # Matplotlib retains invisible off-scale ticks: audit only actual canvas text.
        if box.x1<0 or box.x0>fig.bbox.width or box.y1<0 or box.y0>fig.bbox.height:continue
        assert t.get_fontsize()>=8, t.get_text()
        assert box.x0>=-.5 and box.y0>=-.5 and box.x1<=fig.bbox.width+.5 and box.y1<=fig.bbox.height+.5, 'Clipped: '+t.get_text()
        bounds.append({'text':t.get_text(),'fontsize':t.get_fontsize(),'bounds_px_at_100dpi':list(box.bounds)})
    for c,a in color_arrays:
        assert np.array_equal(np.asarray(c.get_array()),a)
        assert np.max(np.abs(a))<.08
    return fig,dict(text_bounds=bounds,min_font_pt=min(t['fontsize'] for t in bounds),
        geometry=text_geometry(fig),
        coefficient_colormap={'negative':PLUM,'zero':'#FAFBF9','positive':OUTCOME_COLORS['Fuel'],'vmin':-.08,'vcenter':0,'vmax':.08,
            'shared_for_all_rows':True,'clipped_values':0,'negative_point_redundancy':'central black ticks'},
        formal_plotted_marks=formal_marks,width_mm=W,height_mm=H,
        recursive_glyph_range='actual min/max of all saved point estimates; not uncertainty; no intermediate point omitted from range')


ROWS = [(y, h) for y in OUTCOMES for h in HORIZONS]
RPOS = [i + (i//4)*.5 for i in range(12)]
