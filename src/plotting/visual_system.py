"""Shared manuscript-size visual grammar; presentation only, no estimation."""
import numpy as np
import hashlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text

INK = '#202729'
SECONDARY = '#566166'
RULE = '#DCE1DE'
GRID = '#EDF0ED'
NEUTRAL = '#87918E'
TEAL = '#24675F'
PLUM = '#74556F'
OCHRE = '#96732D'
OUTCOME_COLORS = {'Fuel': TEAL, 'PPI': PLUM, 'CPI': OCHRE}
OUTCOME_MARKERS = {'Fuel': 'o', 'PPI': 'D', 'CPI': '^'}

def tint(hex_color, weight=.15):
    rgb=np.array([int(hex_color[i:i+2],16) for i in (1,3,5)])
    return '#'+''.join(f'{int(round(x)):02X}' for x in (255*(1-weight)+rgb*weight))

def apply_style():
    font=font_manager.findfont('Arial',fallback_to_default=False)
    plt.rcParams.update({'font.family':'Arial','font.size':8.5,'text.color':INK,
        'axes.labelsize':9,'axes.labelcolor':INK,'axes.titlesize':10,
        'axes.edgecolor':NEUTRAL,'axes.linewidth':.65,'axes.facecolor':'white',
        'xtick.color':SECONDARY,'ytick.color':SECONDARY,
        'xtick.labelsize':8.5,'ytick.labelsize':8.5,
        'figure.facecolor':'white','savefig.facecolor':'white',
        'svg.fonttype':'none','svg.hashsalt':'main-figures-visual-redesign-20261015',
        'pdf.fonttype':42,'ps.fonttype':42,'hatch.linewidth':.45,
        'axes.unicode_minus':True,'axes.grid':False})
    return font

def text_geometry(fig, overlaps=True):
    """Reject actual visible text clipping/overlap at delivery dimensions."""
    fig.canvas.draw();renderer=fig.canvas.get_renderer();skip=set();visible=[];errors=[]
    for ax in fig.axes:
        if not ax.axison:
            skip.update(ax.get_xticklabels()+ax.get_yticklabels())
            skip.update([ax.xaxis.label,ax.yaxis.label,ax.xaxis.get_offset_text(),ax.yaxis.get_offset_text()])
        else:
            for t in ax.get_xticklabels():
                if not min(ax.get_xlim())<=t.get_position()[0]<=max(ax.get_xlim()): skip.add(t)
            for t in ax.get_yticklabels():
                if not min(ax.get_ylim())<=t.get_position()[1]<=max(ax.get_ylim()): skip.add(t)
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text() or t in skip: continue
        b=t.get_window_extent(renderer)
        if not b.width or not b.height: continue
        if not 8<=t.get_fontsize()<=12: errors.append('Font outside 8–12 pt: '+t.get_text())
        if b.x0<-.5 or b.y0<-.5 or b.x1>fig.bbox.width+.5 or b.y1>fig.bbox.height+.5:
            errors.append('Clipped: '+t.get_text())
        visible.append((b,t))
    if overlaps:
        for i,(a,ta) in enumerate(visible):
            for b,tb in visible[i+1:]:
                if min(a.x1,b.x1)-max(a.x0,b.x0)>1 and min(a.y1,b.y1)-max(a.y0,b.y0)>1:
                    errors.append('Text overlap: '+ta.get_text()+' / '+tb.get_text())
    if errors: raise ValueError('\n'.join(errors))
    return {'visible_text_objects':len(visible),'font_range_pt':[
        min(t.get_fontsize() for _,t in visible),max(t.get_fontsize() for _,t in visible)],
        'clipping_or_text_overlap_errors':errors}

def panel_rule(fig,x,y,width,color):
    from matplotlib.lines import Line2D
    fig.lines.append(Line2D([x,x+width],[y,y],transform=fig.transFigure,
        color=color,lw=1.0,solid_capstyle='butt'))

def evidence_digest(fig):
    """Digest data coordinates only, independent of color, weight and text geometry.

    Used to compare unchanged chart forms against the previous formal scripts.
    Figure 5's rotated axes are instead checked against its explicit source rows.
    """
    h=hashlib.sha256();counts={'axes':len(fig.axes),'lines':0,'collections':0,'rectangles':0}
    def add(a):
        a=np.asarray(a,dtype='<f8');h.update(str(a.shape).encode());h.update(a.tobytes())
    from matplotlib.patches import Rectangle
    for ax in fig.axes:
        add(ax.get_xlim());add(ax.get_ylim())
        for line in ax.lines:
            add(line.get_xdata());add(line.get_ydata());counts['lines']+=1
        for col in ax.collections:
            counts['collections']+=1
            if col.get_array() is not None: add(col.get_array())
            add(col.get_offsets())
            for path in col.get_paths(): add(path.vertices)
        for p in ax.patches:
            if isinstance(p,Rectangle):
                add([p.get_x(),p.get_y(),p.get_width(),p.get_height()]);counts['rectangles']+=1
    return {'sha256':h.hexdigest(),'objects':counts}
