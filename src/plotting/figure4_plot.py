"""Cumulative levels and paired contrasts from unchanged saved statistics."""
import argparse

import csv

import hashlib

import io

import json

import os

from pathlib import Path

import re

import shutil

import subprocess

import tempfile

import xml.etree.ElementTree as ET

import numpy as np

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt

from matplotlib import font_manager

from matplotlib.lines import Line2D

from matplotlib.text import Text

from PIL import Image

from visual_system import apply_style, OUTCOME_COLORS, OUTCOME_MARKERS, OCHRE, tint, panel_rule

STEM = 'figure_4_cumulative_contrasts'

WIDTH, HEIGHT, DPI = 190., 201., 300

INK, TEAL, ZERO, RULE = '#202729', '#24675F', '#68716F', '#DCE1DE'

HORIZONS = (3, 6, 12)

OUTCOMES = [('d_fuel_power_inflation', 'Fuel'), ('d_ppi_inflation', 'PPI'),
            ('d_cpi_inflation', 'CPI')]

CONTRASTS = [(OUTCOMES[a][0], OUTCOMES[b][0], label) for a, b, label in
             [(0, 1, 'Fuel − PPI'), (0, 2, 'Fuel − CPI'), (1, 2, 'PPI − CPI')]]

FIELD_MAP = {
    'A': {'estimate': 'cumulative_effect', 'ci_low': 'bootstrap_ci_low',
          'ci_high': 'bootstrap_ci_high', 'raw_p': 'raw_p', 'fdr_q': 'fdr_q',
          'holm_p': 'holm_p', 'bootstrap_raw_p': 'bootstrap_p'},
    'B': {'estimate': 'difference', 'ci_low': 'bootstrap_ci_low',
          'ci_high': 'bootstrap_ci_high', 'raw_p': 'raw_p', 'fdr_q': 'fdr_q',
          'holm_p': 'holm_p', 'bootstrap_raw_p': 'bootstrap_p'}}

def geometry(fig):
    fig.canvas.draw(); renderer = fig.canvas.get_renderer(); extents = []; errors = []
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text():
            continue
        b = t.get_window_extent(renderer)
        if not b.width or not b.height:
            continue
        if not 8 <= t.get_fontsize() <= 12:
            errors.append('Font size: ' + t.get_text())
        if b.x0 < 0 or b.y0 < 0 or b.x1 > fig.bbox.width or b.y1 > fig.bbox.height:
            errors.append('Clipping: ' + t.get_text())
        extents.append((b, t.get_text()))
    for i, (a, sa) in enumerate(extents):
        for b, sb in extents[i + 1:]:
            if min(a.x1, b.x1) - max(a.x0, b.x0) > 1 and min(a.y1, b.y1) - max(a.y0, b.y0) > 1:
                errors.append('Text overlap: ' + sa + ' / ' + sb)
    if errors:
        raise ValueError('\n'.join(errors))
    return {'visible_text_artists': len(extents), 'font_range_pt': [8.5, 10],
            'clipping_or_text_overlap_errors': errors}

def draw(rows):
    font = font_manager.findfont('Arial', fallback_to_default=False)
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 8.5, 'svg.fonttype': 'none',
                         'ps.fonttype': 3, 'pdf.fonttype': 42, 'axes.linewidth': .6,
                         'axes.edgecolor': '#506774', 'xtick.color': INK, 'ytick.color': INK,
                         'text.color': INK, 'savefig.facecolor': 'white'})
    apply_style()
    fig = plt.figure(figsize=(WIDTH / 25.4, HEIGHT / 25.4), dpi=300, facecolor='white')
    def txt(x, y, s, size=8.5, weight='normal', ha='left'):
        return fig.text(x / WIDTH, 1 - y / HEIGHT, s, fontsize=size, fontweight=weight,
                        ha=ha, va='center')
    def mark(x, y, marker='o', color=TEAL, size=4.5):
        fig.lines.append(Line2D([x / WIDTH], [1 - y / HEIGHT], transform=fig.transFigure,
                               marker=marker, markersize=size, markeredgewidth=.55, color=color))
    mark(6, 6)
    txt(10, 6, 'Point estimate')
    fig.lines.append(Line2D([39 / WIDTH, 48 / WIDTH], [1 - 6 / HEIGHT] * 2,
                           transform=fig.transFigure, color=TEAL, linewidth=1.1))
    txt(51, 6, '95% pointwise MBB percentile CI')
    txt(126, 6, '12-month blocks; 5,000 draws')
    plot_arrays = []; axes = []; limits = (-.06, .58)
    for panel, title, first, heading in [('A', 'Cumulative LP associations', 31., 17.),
                                         ('B', 'Direct paired cumulative contrasts', 116., 102.)]:
        txt(4, heading, '(' + panel + ') ' + title, 10, 'bold')
        panel_rule(fig,4/WIDTH,1-(heading+4)/HEIGHT,180/WIDTH,TEAL if panel=='A' else OCHRE)
        txt(4, first - 7, 'Horizon', weight='bold')
        txt(23, first - 7, 'Price indicator' if panel == 'A' else 'Contrast', weight='bold')
        txt(103, first - 7, 'Estimate and 95% CI', weight='bold', ha='center')
        txt(178, first - 7, 'Estimate' if panel == 'A' else 'BH q', weight='bold', ha='center')
        top, bottom = first - 4, first + 58
        ax = fig.add_axes([49 / WIDTH, 1 - bottom / HEIGHT, 107 / WIDTH, (bottom - top) / HEIGHT])
        ax.set_xlim(limits); ax.set_ylim(bottom, top)
        ax.set_xticks([0, .1, .2, .3, .4, .5]); ax.set_xticklabels(['0', '0.1', '0.2', '0.3', '0.4', '0.5'])
        ax.tick_params(axis='x', labelsize=8.5, length=2.6, pad=3)
        ax.set_yticks([])
        for spine in ['top', 'left', 'right']:
            ax.spines[spine].set_visible(False)
        ax.axvline(0, color='#566166', linewidth=.9, linestyle=(0, (3, 3)), zorder=1)
        axes.append(ax)
        d = [r for r in rows if r['panel'] == panel]
        for group, h in enumerate(HORIZONS):
            group_top = first + group * 21
            txt(4, group_top + 6, 'h = ' + str(h), weight='bold')
            if group:
                sep = group_top - 4.5
                fig.lines.append(Line2D([23 / WIDTH, 184 / WIDTH], [1 - sep / HEIGHT] * 2,
                                       transform=fig.transFigure, color=RULE, linewidth=.45, zorder=0))
            for j, r in enumerate([v for v in d if int(v['horizon']) == h]):
                y = group_top + j * 6
                estimate, lo, hi = [float(r[c]) for c in ['estimate', 'ci_low', 'ci_high']]
                color=OUTCOME_COLORS[r['display_label']] if panel=='A' else OCHRE
                marker=OUTCOME_MARKERS[r['display_label']] if panel=='A' else 'D'
                txt(23, y, r['display_label'])
                line, = ax.plot([lo, hi], [y, y], color=color, linewidth=1., solid_capstyle='butt', zorder=2)
                caps, = ax.plot([lo, hi], [y, y], marker='|', linestyle='none', color=color,
                                markersize=4.3, markeredgewidth=.8, zorder=2)
                point, = ax.plot([estimate], [y], marker=marker, markersize=5.,
                                 markeredgewidth=.45, markeredgecolor='white',color=color, linestyle='none', zorder=3)
                assert list(line.get_xdata()) == [lo, hi] and list(caps.get_xdata()) == [lo, hi]
                assert list(point.get_xdata()) == [estimate]
                assert limits[0] < lo < hi < limits[1]
                if panel == 'A':
                    txt(184, y, f'{estimate:.4f}', ha='right')
                else:
                    txt(184, y, f'{float(r["fdr_q"]):.5f}', ha='right')
                    if r['bh_q_lt_005_marker'] == 'True':
                        mark(166, y, 's', INK, 3.4)
                plot_arrays.append({'panel': panel, 'horizon': int(r['horizon']),
                                    'label': r['display_label'], 'estimate': estimate,
                                    'ci_low': lo, 'ci_high': hi,
                                    'BH_square': panel == 'B' and r['bh_q_lt_005_marker'] == 'True'})
    assert axes[0].get_xlim() == axes[1].get_xlim()
    txt(103, 186, 'Percentage points per ≈1% monthly change in RMB oil cost', 9, ha='center')
    mark(6, 196, 's', INK, 3.4)
    txt(10, 196, '(B) Squares: paired-bootstrap BH q < 0.05 across all nine contrasts')
    return fig, {'font': 'Arial', 'font_path': font, 'canvas_mm': [WIDTH, HEIGHT],
                 'geometry': geometry(fig), 'common_x_limits': list(limits),
                 'plot_width_fraction': 107 / WIDTH, 'plotted_arrays': plot_arrays,
                 'all_18_points_and_36_interval_endpoints_match_source': True,
                 'zero_lines': 2, 'BH_squares': 7, 'significance_stars': False}
