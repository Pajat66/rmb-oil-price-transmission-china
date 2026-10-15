"""Lag waterfall and complete saved-bootstrap density family; no resampling."""
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

from visual_system import apply_style, OUTCOME_COLORS, OCHRE, tint, panel_rule


W, H, DPI = 190., 210., 300


INK, TEAL, BLUE, RULE, ZERO = '#202729', '#24675F', '#566166', '#DCE1DE', '#68716F'


HORIZONS = tuple(range(13))  # Complete set; no significance-based selection.


KDE_RULE, GRID_N, RIDGE_HEIGHT = 'scott', 2048, .60


def plot(source, drawsets, kdes, lags, total):
    font = font_manager.findfont('Arial', fallback_to_default=False)
    os.environ['SOURCE_DATE_EPOCH'] = '1791580800'
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 8.5, 'text.color': INK,
        'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK, 'axes.edgecolor': ZERO,
        'axes.linewidth': .65, 'svg.fonttype': 'none', 'svg.hashsalt': 'figure6-innovative-v1',
        'ps.fonttype': 3, 'pdf.fonttype': 42, 'savefig.facecolor': 'white', 'axes.unicode_minus': True})
    apply_style()
    fig = plt.figure(figsize=(W/25.4, H/25.4), facecolor='white')
    fig.text(.08, .965, '(A) Arithmetic decomposition of distributed-lag coefficients', fontsize=10, weight='bold')
    fig.text(.08, .940, 'RMB oil-price change to customs import unit-value change', fontsize=9)
    panel_rule(fig,.08,.928,.88,OCHRE)
    ax = fig.add_axes([.105, .753, .86, .171])
    beta = lags.coefficient.to_numpy()
    running = np.r_[0., np.cumsum(beta)]
    for i, b in enumerate(beta):
        ax.bar(i, b, bottom=running[i], width=.55,
            color=OCHRE if b >= 0 else 'white', edgecolor=INK, linewidth=.6,
            hatch=None if b >= 0 else '///', zorder=3)
        ax.plot([i+.275, i+1-.275], [running[i+1]]*2, color=ZERO, linewidth=.65, zorder=2)
    ax.bar(4, total.coefficient, bottom=0, width=.55, color=INK, edgecolor=INK, linewidth=.6)
    ax.errorbar(4, total.coefficient, yerr=[[total.coefficient-total.hac_ci_low], [total.hac_ci_high-total.coefficient]],
        fmt='none', color=INK, capsize=5, linewidth=1.2, zorder=5)
    ax.axhline(0, color=ZERO, lw=.8)
    labels = [f'Lag {i}\n{b:+.3f}\n[{lo:.3f}, {hi:.3f}]' for i, b, lo, hi in zip(range(4), beta, lags.hac_ci_low, lags.hac_ci_high)]
    labels += [f'Lag-sum association\n{total.coefficient:.3f}\n[{total.hac_ci_low:.3f}, {total.hac_ci_high:.3f}]']
    ax.set_xticks(range(5), labels, fontsize=8.5)
    ax.tick_params(axis='x', length=0, pad=6)
    ax.set_yticks([0, .25, .5, .75, 1.], ['0.00', '0.25', '0.50', '0.75', '1.00'])
    ax.set_ylabel('Coefficient units', fontsize=9, labelpad=5)
    ax.set_ylim(-.005, 1.02); ax.set_xlim(-.6, 4.65)
    ax.spines[['top', 'right', 'bottom']].set_visible(False)
    fig.text(.105, .670, 'Brackets: 95% HAC CIs for individual coefficients / lag sum', fontsize=8.5)
    fig.text(.105, .646, 'Bar positions show arithmetic sums; no causal decomposition', fontsize=8.5)
    fig.text(.08, .608, '(B) Fuel bootstrap distributions', fontsize=10, weight='bold')
    fig.text(.555, .608, '(C) PPI bootstrap distributions', fontsize=10, weight='bold')
    panel_rule(fig,.08,.601,.39,OUTCOME_COLORS['Fuel'])
    panel_rule(fig,.555,.601,.39,OUTCOME_COLORS['PPI'])
    fig.text(.08, .584, 'Different horizontal scales; all horizons h = 0–12', fontsize=9, weight='bold')
    ranges = {}
    for outcome, left in [('Fuel', .105), ('PPI', .580)]:
        color=OUTCOME_COLORS[outcome]
        a = fig.add_axes([left, .107, .330, .446])
        # CSV also contains the Link-1 label "sum_0_3", making this whole
        # column textual. Restore the original numeric horizon correspondence;
        # never pair h=1's saved density with h=10's estimate/interval.
        rr = source[source.outcome == outcome].sort_values('lag_or_horizon', key=lambda s:s.astype(int))
        assert rr.lag_or_horizon.astype(int).tolist()==list(HORIZONS)
        lows = [drawsets[(outcome, h)].min()-4*np.sqrt(kdes[(outcome, h)].covariance[0, 0]) for h in HORIZONS]
        highs = [drawsets[(outcome, h)].max()+4*np.sqrt(kdes[(outcome, h)].covariance[0, 0]) for h in HORIZONS]
        lo, hi = float(min(lows)), float(max(highs))
        # Round OUTWARD; all raw extrema and four bandwidths of KDE tails retained.
        step = .5 if outcome == 'Fuel' else .2
        lo, hi = np.floor(lo/step)*step, np.ceil(hi/step)*step
        x = np.linspace(lo, hi, GRID_N)
        a.axvline(0, color=ZERO, lw=.8, linestyle=(0, (3, 3)), zorder=2)
        for h, row in zip(HORIZONS, rr.itertuples()):
            base = 12-h
            kde = kdes[(outcome, h)]
            den = kde(x)
            height = RIDGE_HEIGHT*den/den.max()
            a.fill_between(x, base, base+height, color=tint(color,.12), zorder=1)
            a.plot(x, base+height, color=color, lw=.85, zorder=2)
            # Independent interval below the density baseline, true saved endpoints.
            yy = base-.13
            a.plot([row.ci_low, row.ci_high], [yy, yy], color=color, lw=1., zorder=4)
            a.vlines([row.ci_low, row.ci_high], yy-.08, yy+.08, color=color, lw=.8, zorder=4)
            a.plot(row.estimate, yy, 'o', color=INK, markersize=4., zorder=5)
            a.text(1.04, yy, f'{row.estimate:.3f}'.replace('-', '−'), transform=a.get_yaxis_transform(),
                ha='left', va='center', fontsize=8.5, clip_on=False)
        a.text(1.04, 13.02, 'Estimate', transform=a.get_yaxis_transform(), fontsize=8.5, ha='left')
        a.set_yticks([12-h-.13 for h in HORIZONS], [str(h) for h in HORIZONS])
        a.set_ylabel('Horizon h (months)', fontsize=9, labelpad=5)
        a.set_xlim(lo, hi); a.set_ylim(-.57, 13.02)
        ticks = np.arange(lo, hi+.001, step)
        a.set_xticks(ticks)
        a.set_xticklabels([f'{v:.1f}'.replace('-', '−') for v in ticks], fontsize=8.5)
        a.tick_params(axis='y', length=0, pad=5)
        a.tick_params(axis='x', length=3, pad=4)
        a.spines[['top', 'right', 'left']].set_visible(False)
        ranges[outcome] = [float(lo), float(hi)]
    fig.text(.52, .070, 'Cumulative association (percentage points per ≈1% import unit-value change)',
        ha='center', fontsize=9)
    fig.legend(handles=[Line2D([], [], marker='o', linestyle='none', color=INK, markersize=4, label='Point estimate'),
        Line2D([], [], color=TEAL, lw=1, marker='|', markersize=6, label='95% pointwise MBB percentile CI')],
        loc='lower center', bbox_to_anchor=(.52, .026), ncol=2, frameon=False, fontsize=8.5,
        handlelength=2, columnspacing=2)
    fig.text(.52, .012, '5,000 saved draws; Scott KDE; density heights normalized within each horizon', ha='center', fontsize=8.5)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    text_boxes, errors = [], []
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text():
            continue
        b = t.get_window_extent(renderer)
        if b.width == 0 or b.height == 0:
            continue
        if t.get_fontsize() < 8 or t.get_fontsize() > 12:
            errors.append('Font outside venue range: '+t.get_text())
        if b.x0 < 0 or b.y0 < 0 or b.x1 > fig.bbox.width or b.y1 > fig.bbox.height:
            errors.append('Clipped: '+t.get_text())
        text_boxes.append({'text': t.get_text(), 'font_pt': t.get_fontsize(), 'bounds_px_at_100dpi': list(b.bounds)})
    assert not errors, errors
    return fig, dict(font='Arial', font_resolved_path=font, width_mm=W, height_mm=H,
        horizon_source_mapping=[{'outcome':o,'horizon':int(r.lag_or_horizon),
            'estimate':float(r.estimate),'ci_low':float(r.ci_low),'ci_high':float(r.ci_high)}
            for o in ('Fuel','PPI') for r in source[source.outcome==o].sort_values('lag_or_horizon',key=lambda s:s.astype(int)).itertuples()],
        text_range_pt=[min(t['font_pt'] for t in text_boxes), max(t['font_pt'] for t in text_boxes)],
        text_bounds=text_boxes, clipping_errors=errors, axis_ranges=ranges,
        density_height_rule='normalize each density to peak 0.60; heights not comparable',
        kde_rule=KDE_RULE, kde_grid_points=GRID_N, raw_tail_trimming=False)

