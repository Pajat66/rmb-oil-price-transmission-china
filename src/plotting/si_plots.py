"""Source-exact S1-S3 scientific plotting helpers."""
from __future__ import annotations

import argparse

import csv

import hashlib

import json

from datetime import datetime

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates

import matplotlib.pyplot as plt

from matplotlib import font_manager

import numpy as np

from PIL import Image

from plos_figure_export import PLOS_DPI, PLOS_FONT_FAMILY, PLOS_MAX_BYTES, save_plos_figure

OUTCOMES = (
    ("d_fuel_power_inflation", "Fuel and power", "#176B8C"),
    ("d_ppi_inflation", "PPI", "#B06E21"),
    ("d_cpi_inflation", "CPI", "#755184"),
)

CONTRASTS = (
    ("d_fuel_power_inflation minus d_ppi_inflation", "Fuel - PPI", "#176B8C"),
    ("d_fuel_power_inflation minus d_cpi_inflation", "Fuel - CPI", "#B06E21"),
    ("d_ppi_inflation minus d_cpi_inflation", "PPI - CPI", "#755184"),
)

SOURCE_FIELDS = [
    "figure_id", "panel", "series", "outcome", "horizon", "x", "x_kind",
    "estimate", "ci_low", "ci_high", "ci_method", "source_table",
    "source_row_index", "source_row_key", "source_filter", "source_sha256",
    "x_field", "estimate_field", "ci_low_field", "ci_high_field", "N",
    "sample_start", "sample_end", "last_response_date", "window",
    "block_length", "maxlags", "quantity_order", "response_type",
]

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)

class FrozenSources:
    def __init__(self, root):
        self.root = root
        self.cache = {}

    def read(self, name):
        if name not in self.cache:
            path = self.root / "03_tables" / name
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.cache[name] = (rows, sha256(path))
        return self.cache[name]

    def select(self, name, filters, sort_key, expected_count=None):
        rows, digest = self.read(name)
        selected = [(i, row) for i, row in enumerate(rows)
                    if all(row[key] == str(value) for key, value in filters.items())]
        selected.sort(key=lambda item: sort_key(item[1]))
        if not selected:
            raise ValueError("No rows in {} for {}".format(name, filters))
        if expected_count is not None and len(selected) != expected_count:
            raise ValueError("{} {}: expected {} rows, found {}".format(
                name, filters, expected_count, len(selected)))
        return selected, digest

def record_points(store, figure_id, panel, series, source_table, selected,
                  digest, filters, key_fields, x_field, estimate_field,
                  ci_low_field, ci_high_field, ci_method, x_kind="horizon"):
    captured = []
    for index, row in selected:
        estimate, lo, hi = [row[field] for field in (estimate_field, ci_low_field, ci_high_field)]
        values = np.array([float(estimate), float(lo), float(hi)])
        if not np.isfinite(values).all() or float(lo) > float(hi):
            raise ValueError("Invalid estimate/interval in {} row {}".format(source_table, index))
        point = {field: "" for field in SOURCE_FIELDS}
        point.update({
            "figure_id": figure_id, "panel": panel, "series": series,
            "outcome": row.get("outcome", row.get("contrast", "")),
            "horizon": row.get("horizon", row.get("lag", "")),
            "x": row[x_field], "x_kind": x_kind,
            "estimate": estimate, "ci_low": lo, "ci_high": hi,
            "ci_method": ci_method, "source_table": source_table,
            "source_row_index": index,
            "source_row_key": json.dumps({key: row[key] for key in key_fields}, sort_keys=True),
            "source_filter": json.dumps(filters, sort_keys=True), "source_sha256": digest,
            "x_field": x_field, "estimate_field": estimate_field,
            "ci_low_field": ci_low_field, "ci_high_field": ci_high_field,
            "N": row.get("N", ""),
            "sample_start": row.get("sample_start", row.get("start", "")),
            "sample_end": row.get("sample_end", row.get("end", "")),
            "last_response_date": row.get("last_response_date", ""),
            "window": row.get("window", ""), "block_length": row.get("block_length", ""),
            "maxlags": row.get("maxlags", ""), "quantity_order": row.get("quantity_order", ""),
            "response_type": row.get("response_type", ""),
        })
        store.append(point)
        captured.append(point)
    return captured

def draw_band(ax, points, color, marker=True):
    if points[0]["x_kind"] == "month":
        x = np.array([mdates.date2num(datetime.strptime(p["x"], "%Y-%m")) for p in points])
    else:
        x = np.array([float(p["x"]) for p in points])
    y = np.array([float(p["estimate"]) for p in points])
    lo = np.array([float(p["ci_low"]) for p in points])
    hi = np.array([float(p["ci_high"]) for p in points])
    ax.fill_between(x, lo, hi, color=color, alpha=0.17, linewidth=0)
    ax.plot(x, y, color=color, linewidth=1.25,
            marker="o" if marker else None, markersize=2.5)
    ax.axhline(0, color="#3B4248", linewidth=0.85, linestyle=(0, (4, 3)), zorder=1)
    ax.grid(axis="y", color="#D6D9DC", linewidth=0.5, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#80858A")
    ax.spines["bottom"].set_color("#80858A")
    ax.tick_params(length=2.5, width=0.6, colors="#33383D")
    ax.set_axisbelow(True)
    if points[0]["x_kind"] == "month":
        first, last = x[0], x[-1]
        year_first = datetime.strptime(points[0]["x"], "%Y-%m").year
        year_last = datetime.strptime(points[-1]["x"], "%Y-%m").year
        dates = [first] + [mdates.date2num(datetime(year, 1, 1))
                           for year in range(year_first + 1, year_last, 5)] + [last]
        # Boundaries always remain visible; interior labels stay calendar-spaced.
        margin = (last - first) * 0.22
        dates = [dates[0]] + [d for d in dates[1:-1]
                              if d - first > margin and last - d > margin] + [dates[-1]]
        ax.set_xticks(dates)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.set_xlim(first, last)
        labels = ax.get_xticklabels()
        labels[0].set_ha("left")
        labels[-1].set_ha("right")
    else:
        ax.set_xticks(x)
        ax.set_xlim(x[0] - 0.2, x[-1] + 0.2)

def layout(fig, title, subtitle, note, bottom=0.24, top=0.76):
    fig.suptitle(title, x=0.07, y=0.97, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.07, 0.89, subtitle, ha="left", va="top", fontsize=8.5, color="#414A51")
    fig.text(0.07, 0.035, note, ha="left", va="bottom", fontsize=8, color="#414A51")
    fig.subplots_adjust(left=0.085, right=0.98, bottom=bottom, top=top, wspace=0.2, hspace=0.42)

def save_bundle(root, figure_id, designation, fig, source, title, caption, manifest):
    destination = root / "04_final_figures"
    destination.mkdir(parents=True, exist_ok=True)
    stem = "figure_" + figure_id
    data_path = destination / (stem + "_source.csv")
    write_csv(data_path, source, SOURCE_FIELDS)
    export_result = save_plos_figure(fig, destination / (stem + ".tif"), preview_png=True)
    plt.close(fig)
    script = Path(__file__).resolve()
    font_path = Path(font_manager.findfont(PLOS_FONT_FAMILY, fallback_to_default=False))
    provenance = []
    seen = set()
    for point in source:
        marker = (point["source_table"], point["source_filter"])
        if marker not in seen:
            seen.add(marker)
            provenance.append({"source_table": marker[0], "source_filter": json.loads(marker[1]),
                               "source_sha256": point["source_sha256"]})
    for suffix in (".png", ".tif"):
        path = destination / (stem + suffix)
        with Image.open(path) as rendered:
            width, height = rendered.size
            dpi = rendered.info.get("dpi", (PLOS_DPI, PLOS_DPI))
            frames = getattr(rendered, "n_frames", 1)
            mode = rendered.mode
            image_format = rendered.format
            compression = rendered.info.get("compression", "")
        if suffix == ".tif" and (path.stat().st_size > PLOS_MAX_BYTES or frames != 1
                                 or mode not in ("RGB", "L")
                                 or min(dpi) < PLOS_DPI):
            raise ValueError("PLOS export check failed: " + str(path))
        manifest.append({
            "figure_id": figure_id, "designation": designation, "title": title,
            "file": path.relative_to(root).as_posix(), "format": image_format,
            "dpi_x": round(dpi[0], 3), "dpi_y": round(dpi[1], 3),
            "width_px": width, "height_px": height,
            "width_inches": round(width / dpi[0], 4), "height_inches": round(height / dpi[1], 4),
            "file_size_bytes": path.stat().st_size, "file_sha256": sha256(path),
            "mode": mode, "frames": frames, "compression": compression,
            "font": PLOS_FONT_FAMILY, "font_file": font_path.name,
            "font_sha256": sha256(font_path), "font_min_pt": 8, "font_max_pt": 12,
            "script": "02_scripts/final_figures/plot_final_figures.py",
            "script_sha256": sha256(script),
            "export_helper": "02_scripts/final_figures/plos_figure_export.py",
            "export_helper_sha256": sha256(script.with_name("plos_figure_export.py")),
            "source_data": data_path.relative_to(root).as_posix(),
            "source_data_sha256": sha256(data_path), "plotted_points": len(source),
            "source_tables": ";".join(sorted({p["source_table"] for p in source})),
            "source_filters": json.dumps(provenance, sort_keys=True),
            "source_row_keys": "source_data.source_row_key + zero-based source_row_index",
            "no_smoothing": True, "zero_line": True, "significance_stars": False,
            "export_warning": export_result["warning"], "caption": caption,
        })
    return {"figure_id": figure_id, "title": title, "designation": designation, "caption": caption}

def rolling_hierarchy(root, frozen, figure_id, horizon, designation, manifest):
    source = []
    fig, axes = plt.subplots(1, 3, figsize=(7.35, 3.9), sharey=True)
    table = "hierarchy_stability.csv"
    for panel, (ax, (contrast, label, color)) in enumerate(zip(axes, CONTRASTS)):
        filters = {"method": "rolling", "window": "120", "horizon": str(horizon),
                   "response_type": "cumulative", "contrast": contrast}
        selected, digest = frozen.select(table, filters, lambda r: r["end"])
        points = record_points(source, figure_id, chr(65 + panel), label, table, selected,
                               digest, filters, ["method", "window", "horizon", "response_type", "contrast", "end"],
                               "end", "estimate", "ci_low", "ci_high",
                               "95% paired cross-outcome/horizon Bartlett HAC12 pointwise CI", "month")
        draw_band(ax, points, color, marker=False)
        ax.set_title(chr(65 + panel) + "  " + label, loc="left", fontsize=10, pad=9)
        ax.set_xlabel("Window-ending origin month", labelpad=7)
    axes[0].set_ylabel("Estimated cumulative difference", labelpad=6)
    title = "Rolling price-stage contrasts at h = " + str(horizon)
    layout(fig, title, "120-month windows; all monthly endpoints retained. Bands: paired pointwise 95% HAC12 CI.",
           "Common response-difference scale; frozen paired cross-equation and cross-horizon covariance.\nRetrospective origin windows; overlapping windows are dependent and are not repeated independent tests.",
           bottom=0.25, top=0.76)
    caption = "Frozen Phase2C rolling cumulative price-stage differences at h=" + str(horizon) + " in every available 120-month window. Pointwise 95% intervals use paired cross-equation and cross-horizon Bartlett HAC12 covariance. The same origin months are used within each contrast and cumulative horizon. Windows are retrospective: forward outcomes may extend beyond their ending origin month. Overlapping windows are dependent, so interval frequencies are descriptive and do not constitute independent repeated tests or simultaneous stability proof. The three panels use a common y-axis."
    return save_bundle(root, figure_id, designation, fig, source, title, caption, manifest)

def stability_grid(root, frozen, figure_id, recursive, manifest):
    source = []
    fig, axes = plt.subplots(3, 4, figsize=(10.6, 8.3), sharey="col")
    table = "recursive_lp_coefficients.csv" if recursive else "rolling_lp_coefficients.csv"
    for row_no, (outcome, label, color) in enumerate(OUTCOMES):
        for col_no, horizon in enumerate((0, 3, 6, 12)):
            filters = {"outcome": outcome, "horizon": str(horizon)}
            if not recursive:
                filters["window"] = "120"
            selected, digest = frozen.select(table, filters, lambda r: r["end"])
            panel = chr(65 + row_no * 4 + col_no)
            points = record_points(source, figure_id, panel, label, table, selected,
                                   digest, filters,
                                   ["outcome", "horizon", "end_date"] if recursive else ["outcome", "horizon", "window", "end"],
                                   "end", "coefficient", "hac_ci_low", "hac_ci_high",
                                   "95% Bartlett HAC12 pointwise CI", "month")
            ax = axes[row_no, col_no]
            draw_band(ax, points, color, marker=False)
            ax.set_title(panel + "  " + label + ", h = " + str(horizon), loc="left", fontsize=9, pad=8)
            if col_no == 0:
                ax.set_ylabel("Estimated response (pp)", labelpad=5)
            if row_no == 2:
                ax.set_xlabel("Ending origin month", labelpad=7)
    title = "Recursive LP period responses" if recursive else "Rolling LP period responses"
    layout(fig, title, "All outcomes and Phase2C summary horizons h = 0, 3, 6, 12; bands: pointwise 95% HAC12 intervals.",
           ("Expanding windows begin at 120 observations. Fuel h = 12 endpoint drift is retained (SI Table S14).\n" if recursive else "All 120-month rolling windows retained. 96/144-month sensitivities remain in SI Table S14.\n") +
           "Common y-axis within each horizon column. Retrospective origin windows; confidence intervals are not simultaneous.",
           bottom=0.13, top=0.81)
    caption = "Frozen Phase2C " + ("expanding recursive" if recursive else "120-month rolling") + " period LP coefficients for all three outcomes and all four prespecified stability summary horizons (h=0,3,6,12). Every monthly endpoint is retained with its pointwise Bartlett HAC12 95% interval. These stability-window intervals follow the Phase2C fixed-HAC12 convention, including h12; they do not replace Phase2B full-sample HAC13 inference at h12. Panels within a horizon column have a common y-axis scale. Origin windows are retrospective and forward outcomes may extend beyond their ending origin month. " + ("Fuel h12 drift and its paired endpoint comparison remain explicitly visible and are reported in SI Table S14; absence of corrected drift for other outcomes is not an equivalence test." if recursive else "Overlapping rolling windows are dependent; displayed fractions and signs are descriptive rather than repeated independent tests. The 96/144-month sensitivity results remain in the supporting tables.")
    return save_bundle(root, figure_id, "SI", fig, source, title, caption, manifest)
