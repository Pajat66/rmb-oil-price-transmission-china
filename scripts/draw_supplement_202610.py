"""Draw the submitted S1–S3 stability paths from the sealed numerical tables."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

OUTCOMES = {"d_fuel_power_inflation": ("Fuel", "fuel"), "d_ppi_inflation": ("PPI", "ppi"),
            "d_cpi_inflation": ("CPI", "cpi")}
CONTRASTS = {
    "d_fuel_power_inflation minus d_ppi_inflation": ("Fuel − PPI", "fuel"),
    "d_fuel_power_inflation minus d_cpi_inflation": ("Fuel − CPI", "cpi"),
    "d_ppi_inflation minus d_cpi_inflation": ("PPI − CPI", "ppi"),
}
HORIZONS = (0, 3, 6, 12)
VINTAGE = "2026-10"


def csv(path):
    return pd.read_csv(path, float_precision="round_trip")


def same(left, right, keys, fields):
    joined = left.merge(right, on=keys, suffixes=("_a", "_b"), how="outer", indicator=True,
                        validate="one_to_one")
    assert joined._merge.eq("both").all()
    for key in fields:
        np.testing.assert_array_equal(joined[key + "_a"], joined[key + "_b"])


def path_table(directory, filename):
    data = csv(directory / filename)
    return data.loc[data.vintage.eq(VINTAGE)].copy()


def draw(ax, group, estimate, bounds, color, style):
    x = pd.to_datetime(group.end)
    assert len(x) == len(x.unique())
    assert (x == pd.date_range(x.min(), x.max(), freq="MS")).all()
    y = group[estimate].to_numpy()
    low, high = (group[v].to_numpy() for v in bounds)
    assert np.isfinite(np.c_[y, low, high]).all() and ((low <= y) & (y <= high)).all()
    style.interval_band(ax, color, x, low, high)
    style.zero_line(ax)
    line, = ax.plot(x, y, color=style.SERIES_COLORS[color], linewidth=1.2, zorder=3)
    np.testing.assert_array_equal(line.get_ydata(), y)
    ax.grid(axis="y", linewidth=.45, alpha=.5)
    ax.set_xticks(pd.to_datetime(["2010-01-01", "2015-01-01", "2020-01-01", "2025-01-01"]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(pd.Timestamp("2007-12-01"), pd.Timestamp("2027-02-01"))


def export(fig, output, name, style):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for label in fig.findobj(matplotlib.text.Text):
        if not label.get_visible() or not label.get_text().strip():
            continue
        bb = label.get_window_extent(renderer)
        assert label.get_fontsize() >= 8
        assert fig.bbox.contains(bb.x0, bb.y0) and fig.bbox.contains(bb.x1, bb.y1), label.get_text()
    paths = style.save_fig(fig, name, output, tiff=True, journal_profile="energies", submission=True)
    plt.close(fig)
    for key in ("preview", "tiff"):
        if key == "preview":
            with Image.open(paths["tiff"]) as im:
                im.save(paths["preview"], dpi=(600, 600))
        with Image.open(paths[key]) as im:
            assert im.mode == "RGB" and min(im.info["dpi"]) > 599
    if paths["submission"] not in (paths["preview"], paths["tiff"]):
        paths["submission"].unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--figure7", type=Path, required=True)
    parser.add_argument("--style", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.style))
    import paper_style as style
    assert style.apply_style_v2("energies", base_size=8.5) == "Arial"
    plt.rcParams["figure.constrained_layout.use"] = False
    plt.rcParams["figure.autolayout"] = False
    folder = args.validation / "stability"
    args.output.mkdir(parents=True, exist_ok=True)
    seal = json.loads((args.validation / "reproduction.json").read_text(encoding="utf-8"))
    seal_names = seal["output_hashes"]
    for name in ("rolling_lp_coefficients.csv", "recursive_lp_coefficients.csv",
                 "hierarchy_stability.csv", "phase2c_hierarchy_evidence_summary.csv",
                 "phase2c_recursive_endpoint_drift.csv", "structural_break_supwald.csv",
                 "parameter_stability_tests.csv"):
        path = folder / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == seal_names[f"stability/{name}"]
    bounds = ("hac_ci_low", "hac_ci_high")
    for number, kind in enumerate(("rolling", "recursive"), 1):
        data = path_table(folder, f"{kind}_lp_coefficients.csv")
        if kind == "rolling":
            data = data[data.window.eq(120)]
        assert len(data) == 2625 and data.maxlags.eq(12).all()
        comparison = csv(args.figure7 / f"figure7_{kind}_paths.csv")
        same(data, comparison, ["outcome", "horizon", "end"], ["coefficient", *bounds, "N", "last_response_date"])
        fig, axes = plt.subplots(4, 3, sharex=True, sharey="row", figsize=(7.05, 7.38))
        for row, horizon in enumerate(HORIZONS):
            for col, (key, (label, color)) in enumerate(OUTCOMES.items()):
                group = data[data.outcome.eq(key) & data.horizon.eq(horizon)].sort_values("end")
                assert len(group) == 224 - horizon and group.N.iloc[0] == 120
                assert group.end.iloc[-1] == (pd.Period(VINTAGE) - horizon).strftime("%Y-%m")
                ax = axes[row, col]
                draw(ax, group, "coefficient", bounds, color, style)
                if row == 0:
                    ax.set_title(label, color=style.SERIES_COLORS[color], weight="bold", pad=8)
                if col == 2:
                    ax.text(1.07, .5, f"h = {horizon}", transform=ax.transAxes, va="center", fontsize=8.5)
        title = "Rolling-window LP coefficients" if number == 1 else "Recursive LP coefficients"
        note = "120-month rolling windows" if number == 1 else "Expanding windows starting at 120 observations"
        fig.text(.105, .966, title, weight="bold", fontsize=11)
        fig.text(.105, .934, f"{note} · Pointwise 95% HAC12 intervals", fontsize=8.5)
        fig.supylabel("Estimated response (pp per ≈1% RMB oil-cost increase)", x=.025, fontsize=8.5)
        fig.supxlabel("Ending origin month", y=.045, fontsize=8.5)
        fig.set_layout_engine("none")
        fig.subplots_adjust(left=.115, right=.87, top=.875, bottom=.10, wspace=.22, hspace=.27)
        export(fig, args.output, f"Figure_S{number}", style)
        print(f"Figure S{number}: {len(data)} sealed paths matched Figure 7 sources.")
    contrasts = path_table(folder, "hierarchy_stability.csv")
    contrasts = contrasts[(contrasts.method == "rolling") & (contrasts.window == 120) &
                          (contrasts.horizon == 6) & (contrasts.response_type == "cumulative")]
    summary = path_table(folder, "phase2c_hierarchy_evidence_summary.csv")
    summary = summary[(summary.method == "rolling") & (summary.window == 120) &
                      (summary.horizon == 6) & (summary.response_type == "cumulative")].set_index("contrast")
    assert len(contrasts) == 654 and contrasts.maxlags.eq(12).all()
    fig, axes = plt.subplots(1, 3, sharey=True, figsize=(7.05, 3.15))
    for ax, (key, (label, color)) in zip(axes, CONTRASTS.items()):
        group = contrasts[contrasts.contrast.eq(key)].sort_values("end")
        assert len(group) == summary.loc[key, "n_windows"] == 218
        assert group.end.iloc[-1] == "2026-04"
        np.testing.assert_allclose((group.ci_low > 0).mean(), summary.loc[key, "fraction_ci_positive"])
        draw(ax, group, "estimate", ("ci_low", "ci_high"), color, style)
        ax.set_title(label, color=style.SERIES_COLORS[color], weight="bold", pad=8)
    fig.text(.105, .932, "Rolling paired cumulative contrasts at h = 6", weight="bold", fontsize=11)
    fig.text(.105, .866, "120-month windows · Paired pointwise 95% HAC12 intervals", fontsize=8.5)
    fig.supylabel("Cumulative difference\n(pp per ≈1% RMB oil-cost increase)", x=.015, fontsize=8.5)
    fig.supxlabel("Ending origin month", y=.064, fontsize=8.5)
    fig.set_layout_engine("none")
    fig.subplots_adjust(left=.145, right=.975, top=.739, bottom=.20, wspace=.22)
    export(fig, args.output, "Figure_S3", style)
    print("Figure S3: 654 sealed paired estimates and interval-direction summaries checked.")


if __name__ == "__main__":
    main()





