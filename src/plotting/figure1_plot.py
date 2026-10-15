"""Research workflow: independent macro/customs lanes and primary-design branches."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from visual_system import apply_style, text_geometry, INK, SECONDARY, RULE, TEAL, PLUM, OCHRE, tint

WIDTH, HEIGHT = 190., 204.
TEXTS, BOXES, SEGMENTS = [], {}, []

def text(ax,x,y,value,size=8.5,weight='normal',color=INK,owner=None,ha='left'):
    t=ax.text(x,y,value,fontsize=size,fontweight=weight,color=color,ha=ha,
              va='center',linespacing=1.45,zorder=4)
    TEXTS.append((t,owner));return t

def box(ax,key,x,y,w,h,title,lines,color=TEAL,primary=False,inference=None):
    BOXES[key]=(x,y,w,h)
    ax.add_patch(Rectangle((x,y),w,h,fc='white',ec=color if primary else RULE,
                           lw=1.2 if primary else .7,zorder=2))
    ax.add_patch(Rectangle((x,y),1.2,h,fc=color,ec='none',zorder=3))
    text(ax,x+3.5,y+5,title,9.5,'bold',owner=key)
    for i,s in enumerate(lines): text(ax,x+3.5,y+11+i*4.5,s,owner=key)
    if inference:
        iy=y+h-11.5
        ax.add_patch(Rectangle((x+1.4,iy),w-1.6,11.2,fc=tint(PLUM,.07),ec='none',zorder=3))
        for i,s in enumerate(inference): text(ax,x+3.5,iy+3.3+i*4.5,s,8.0,color=PLUM,owner=key)

def path(ax,points,primary=False,arrow=True):
    color=TEAL if primary else SECONDARY
    lw=1.7 if primary else .9
    for a,b in zip(points[:-1],points[1:]):
        SEGMENTS.append((a,b))
        ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=lw,zorder=1,solid_capstyle='butt')
    if arrow:
        ax.add_patch(FancyArrowPatch(points[-2],points[-1],arrowstyle='-|>',
            mutation_scale=12 if primary else 9.5,lw=lw,color=color,
            shrinkA=0,shrinkB=0,zorder=3))

def make_figure():
    TEXTS.clear();BOXES.clear();SEGMENTS.clear();font=apply_style()
    fig=plt.figure(figsize=(WIDTH/25.4,HEIGHT/25.4),dpi=300)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,WIDTH),ylim=(HEIGHT,0));ax.axis('off')
    text(ax,6,5,'01  Data and samples',10,'bold',TEAL)
    box(ax,'macro',6,12,112,23,'Macroeconomic data',[
        '1998-01–2026-02  ·  338 months',
        'EIA Brent  ·  FRED CNY/USD  ·  NBS Fuel / PPI / CPI'])
    box(ax,'customs_data',130,12,54,23,'Customs data',[
        '2015-01–2026-02  ·  134 months','RMB values / quantities'],color=OCHRE)
    text(ax,6,43,'02  Calendar and variables',10,'bold',TEAL)
    box(ax,'macro_variables',6,50,112,28,'Monthly calendar; missing values retained',[
        'RMB oil cost = Brent × CNY/USD',
        'Log changes  ·  ΔYoY inflation  ·  ADF / KPSS'])
    box(ax,'customs_variables',130,50,54,28,'Import unit value',[
        'Value / quantity (unit-scaled)',
        'Log changes: unit value / quantity'],color=OCHRE)
    text(ax,6,86,'03  Primary analysis',10,'bold',TEAL)
    text(ax,130,86,'Additional analysis',10,'bold',OCHRE)
    box(ax,'primary',6,93,112,34,'Stationary local projections',[
        'Fuel / PPI / CPI  ·  h = 0–12  ·  fixed lag controls'],primary=True,
        inference=['Period: HAC  ·  Cumulative: pairs MBB','Pointwise intervals  ·  BH-FDR / Holm'])
    box(ax,'customs',130,93,54,34,'Import-cost associations',[
        'Link 1: stationary DL','Link 2: stationary LP · Fuel/PPI'],color=OCHRE,
        inference=['Link 1: HAC','Link 2: HAC + pairs MBB'])
    text(ax,6,136,'04  Comparisons and assessment',10,'bold',TEAL)
    box(ax,'comparisons',6,145,54,31,'Price-stage comparisons',[
        'Period / cumulative associations',
        'Paired contrasts  ·  joint tests',
        'Descriptive response shares'])
    box(ax,'components',68,145,54,31,'Brent / FX components',[
        'Current components  ·  equality',
        'Common controls  ·  collinearity',
        'HAC tests'],color=PLUM)
    box(ax,'robustness',130,145,54,31,'Robustness and stability',[
        'Rolling / recursive',
        'HAC / MBB / quantity sensitivity',
        'Placebo / reverse-predictive',
        'Formal: dependent-wild bootstrap'],color=SECONDARY)
    path(ax,[(62,35),(62,50)],True);path(ax,[(157,35),(157,50)])
    path(ax,[(62,78),(62,93)],True);path(ax,[(181,78),(181,93)])
    path(ax,[(118,70),(124,70),(124,101),(130,101)])
    # Parallel branches from the primary design, never serial dependencies.
    path(ax,[(95,127),(95,140)],primary=True,arrow=False)
    path(ax,[(33,140),(157,140)],arrow=False)
    for x in (33,95,157): path(ax,[(x,140),(x,145)],primary=x==33)
    for x in (33,95,157): path(ax,[(x,176),(x,182)],arrow=False)
    path(ax,[(33,182),(188,182)],arrow=False)
    path(ax,[(184,117),(188,117),(188,182)],arrow=False)
    path(ax,[(95,182),(95,188)],True)
    BOXES['limits']=(6,188,178,13)
    ax.add_patch(Rectangle((6,188),178,13,fc=tint(TEAL,.07),ec=TEAL,lw=.7,zorder=2))
    text(ax,95,192,'Magnitude  ·  timing  ·  uncertainty  ·  temporal variation',9.5,'bold',owner='limits',ha='center')
    text(ax,95,197.5,'Conditional dynamic associations; no identified causal effects',8.5,owner='limits',ha='center')
    return fig,ax,font

def check_geometry(fig,ax):
    qa=text_geometry(fig);fig.canvas.draw();r=fig.canvas.get_renderer()
    for t,owner in TEXTS:
        b=t.get_window_extent(r).transformed(ax.transData.inverted())
        l,rr=min(b.x0,b.x1),max(b.x0,b.x1);top,bt=min(b.y0,b.y1),max(b.y0,b.y1)
        for a,c in SEGMENTS:
            if a[0]==c[0] and l<a[0]<rr and min(max(a[1],c[1]),bt)>max(min(a[1],c[1]),top):
                raise AssertionError('Connector crosses text: '+t.get_text())
            if a[1]==c[1] and top<a[1]<bt and min(max(a[0],c[0]),rr)>max(min(a[0],c[0]),l):
                raise AssertionError('Connector crosses text: '+t.get_text())
        if owner:
            b=t.get_window_extent(r).transformed(ax.transData.inverted());x,y,w,h=BOXES[owner]
            assert min(b.x0,b.x1)>=x+1.5 and max(b.x0,b.x1)<=x+w-1.5, 'Box width: '+t.get_text()
            assert min(b.y0,b.y1)>=y and max(b.y0,b.y1)<=y+h, 'Box height: '+t.get_text()
    qa.update({'text_objects':len(TEXTS),'word_count':sum(len(t.get_text().split()) for t,_ in TEXTS),
        'connectors':'orthogonal; primary fan-out; independent Customs lane',
        'main_arrow_pt':1.7,'main_arrow_head_scale':12,
        'scientific_graph':'macro→primary; macro+customs→import-cost; primary→comparisons/components/robustness; outputs→interpretation',
        'formal_stability_inference':'dependent-wild bootstrap'})
    return qa
