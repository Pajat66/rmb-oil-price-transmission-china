"""Brent/FX component small multiples and the unchanged 39 equality restrictions."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
from visual_system import apply_style, text_geometry, INK, SECONDARY, RULE, TEAL, PLUM, OUTCOME_COLORS, tint, panel_rule

WIDTH,HEIGHT,DPI=190.,216.,300
OUTCOMES=[('d_fuel_power_inflation','Fuel'),('d_ppi_inflation','PPI'),('d_cpi_inflation','CPI')]
DISPLAY_HORIZONS=(0,3,6,12)

def draw(rows):
    font=apply_style();fig=plt.figure(figsize=(WIDTH/25.4,HEIGHT/25.4),dpi=DPI)
    def txt(x,y,s,size=8.5,weight='normal',ha='left',color=INK):
        return fig.text(x/WIDTH,1-y/HEIGHT,s,fontsize=size,fontweight=weight,ha=ha,va='center',color=color)
    txt(5,6,'(A) Current component coefficients',10,'bold')
    txt(5,13,'95% pointwise HAC CIs; independent vertical scales in all six plots')
    for term,left,color,marker,filled,title in [('brent',27,TEAL,'o',True,'Brent'),('fx',115,PLUM,'D',False,'FX (CNY/USD)')]:
        txt(left,23,title,9.5,'bold',color=color)
        panel_rule(fig,left/WIDTH,1-26/HEIGHT,68/WIDTH,color)
    plotted=[];bounds={};matrix=[]
    for i,(y,label) in enumerate(OUTCOMES):
        top=31+34*i
        txt(5,top+9,label,9.5,'bold',color=OUTCOME_COLORS[label])
        selected=[r for r in rows if r['outcome']==y and r['panel_A_displayed']=='True']
        assert [int(r['horizon']) for r in selected]==list(DISPLAY_HORIZONS)
        for term,left,color,marker,filled in [('brent',27,TEAL,'o',True),('fx',115,PLUM,'D',False)]:
            estimates=np.array([float(r['beta_'+term]) for r in selected])
            lo=np.array([float(r[term+'_ci_low']) for r in selected]);hi=np.array([float(r[term+'_ci_high']) for r in selected])
            minimum,maximum=min(lo.min(),0),max(hi.max(),0);span=maximum-minimum
            limits=(minimum-.09*span,maximum+.09*span)
            ax=fig.add_axes([left/WIDTH,1-(top+22)/HEIGHT,68/WIDTH,22/HEIGHT])
            ax.axhline(0,color=SECONDARY,lw=.75,ls=(0,(3,3)),zorder=0)
            e=ax.errorbar(DISPLAY_HORIZONS,estimates,yerr=[estimates-lo,hi-estimates],
                fmt=marker,ms=4.8,mfc=color if filled else 'white',mec=color,mew=.9,
                ecolor=color,elinewidth=.9,capsize=3,capthick=.8,lw=0,zorder=3)
            ax.set_xlim(-1.1,13.1);ax.set_ylim(limits)
            ax.set_xticks(DISPLAY_HORIZONS)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3,steps=[1,2,2.5,5,10]))
            decimals=3 if label=='CPI' and term=='brent' else (2 if term=='brent' else 1)
            ticks=ax.yaxis.get_majorticklocs();ticks=ticks[(ticks>=limits[0])&(ticks<=limits[1])]
            ax.set_yticks(ticks,[f'{v:.{decimals}f}'.replace('-','−') for v in ticks])
            ax.tick_params(length=2.4,pad=2.5)
            for s in ('top','right'):ax.spines[s].set_visible(False)
            assert np.array_equal(e.lines[0].get_xdata(),DISPLAY_HORIZONS)
            assert np.array_equal(e.lines[0].get_ydata(),estimates)
            segments=e.lines[2][0].get_segments()
            for j,r in enumerate(selected):
                assert np.array_equal(segments[j][:,1],[lo[j],hi[j]])
                assert limits[0]<lo[j]<hi[j]<limits[1]
                plotted.append({'outcome':y,'horizon':int(r['horizon']),'component':term,
                    'estimate':estimates[j],'ci_low':lo[j],'ci_high':hi[j]})
            bounds[label+'_'+term]=list(limits)
    txt(105,137,'Horizon h (months)',9,ha='center')
    txt(5,145,'Change in YoY inflation (percentage points) per ≈1% monthly component change')
    txt(5,157,'(B) Equality restrictions across all 13 horizons',10,'bold')
    txt(5,165,'Horizon h',weight='bold')
    centers=[38+h*11.6 for h in range(13)]
    for h,x in enumerate(centers):txt(x,165,str(h),ha='center')
    for i,(y,label) in enumerate(OUTCOMES):
        yy=175+i*11
        txt(5,yy+1.2,label,9,'bold',color=OUTCOME_COLORS[label])
        fig.lines.append(Line2D([33/WIDTH,184/WIDTH],[1-(yy+7)/HEIGHT]*2,
            transform=fig.transFigure,color=RULE,lw=.45))
        for r in (r for r in rows if r['outcome']==y):
            x=centers[int(r['horizon'])];rejected=r['equality_bh_rejected']=='True'
            fig.lines.append(Line2D([x/WIDTH],[1-(yy-1)/HEIGHT],transform=fig.transFigure,
                marker='s',ms=3.5,mfc=INK if rejected else 'white',mec=SECONDARY,mew=.7,ls='none'))
            txt(x,yy+3.6,f'{float(r["equality_bh_q"]):.3f}',8.5,ha='center')
            matrix.append({'outcome':y,'horizon':int(r['horizon']),
                'saved_equality_BH_q':float(r['equality_bh_q']),'filled_rejection_square':rejected})
    assert not any(r['filled_rejection_square'] for r in matrix), 'Frozen equality results changed'
    txt(5,211,'Open squares: not rejected (BH q ≥ 0.05); numbers show equality-test BH q')
    return fig,{'font':'Arial','font_path':font,'canvas_mm':[WIDTH,HEIGHT],
        'geometry':text_geometry(fig),'component_axis_bounds':bounds,
        'plotted_component_arrays':plotted,'restriction_matrix':matrix,
        'displayed_component_estimates':24,'restriction_cells':39,'BH_rejection_squares':0,
        'all24_points_48_CI_endpoints_and39_restriction_cells_match_source':True,
        'layout':'vertical interval small multiples; ordered horizon coordinates; no connecting lines'}
