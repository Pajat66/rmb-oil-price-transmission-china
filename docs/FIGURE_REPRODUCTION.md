# Main-figure reproduction

Figures 1–7 are rendered by [scripts/render_figures.py](../scripts/render_figures.py), with shared typography and visual settings in [visual_system.py](../src/plotting/visual_system.py). This entry point reads saved inputs and does not fit models or draw new bootstrap samples. The included plotted statistics support reproducing the saved figures; re-estimation requires the underlying monthly observations and the workflows in [REPRODUCTION_GUIDE.md](../REPRODUCTION_GUIDE.md).

## Scripts and saved inputs

| Figure | Plotting module | Input paths, relative to repository root |
|---|---|---|
| 1 | [figure1_plot.py](../src/plotting/figure1_plot.py) | Workflow definitions in the module; no empirical point dataset |
| 2 | [figure2_plot.py](../src/plotting/figure2_plot.py) | Separately held figure_2_source.csv, 7,774 rows; excluded provider observations |
| 3 | [figure3_plot.py](../src/plotting/figure3_plot.py) | [figure_3_primary_lp_period_source.csv](../figures/source/figure_3_primary_lp_period_source.csv) |
| 4 | [figure4_plot.py](../src/plotting/figure4_plot.py) | [figure_4_cumulative_contrasts_source.csv](../figures/source/figure_4_cumulative_contrasts_source.csv) |
| 5 | [figure5_plot.py](../src/plotting/figure5_plot.py) | [figure_5_brent_fx_components_source.csv](../figures/source/figure_5_brent_fx_components_source.csv) |
| 6 | [figure6_plot.py](../src/plotting/figure6_plot.py) | [figure_6_import_cost_innovative_source.csv](../figures/source/figure_6_import_cost_innovative_source.csv); [mechanism_link1_final.csv](../reference/statistics/mechanism_link1_final.csv); [phase2b_bootstrap_paths_short_L12.npz](../reference/bootstrap/phase2b_bootstrap_paths_short_L12.npz) |
| 7 | [figure7_plot.py](../src/plotting/figure7_plot.py) | [figure_7_temporal_stability_source.csv](../figures/source/figure_7_temporal_stability_source.csv); [figure_7_temporal_stability_recursive_summary.csv](../figures/source/figure_7_temporal_stability_recursive_summary.csv) |

## Rendering commands and formats

Use the reference Python 3.12.7 environment and [requirements](../requirements.txt). Arial must be installed under its applicable terms; it is not bundled. Run from the repository root. Each output directory must be new, empty and outside the repository. The commands are instructions; they were not rerun during documentation cleanup.

```text
python -B -X utf8 scripts/render_figures.py --figure 1 --output-dir ../figure1_output
python -B -X utf8 scripts/render_figures.py --figure 2 --figure2-source ../private_inputs/figure_2_source.csv --output-dir ../figure2_output
python -B -X utf8 scripts/render_figures.py --figure 3 --output-dir ../figure3_output
python -B -X utf8 scripts/render_figures.py --figure 4 --output-dir ../figure4_output
python -B -X utf8 scripts/render_figures.py --figure 5 --output-dir ../figure5_output
python -B -X utf8 scripts/render_figures.py --figure 6 --output-dir ../figure6_output
python -B -X utf8 scripts/render_figures.py --figure 7 --output-dir ../figure7_output
```

The entry point accepts --source-dir, --statistics-dir and --bootstrap-dir to bind alternative saved inputs. Defaults read the included frozen references. For new estimates, all relevant paths must be rebound and checked; the full fresh-estimate-to-figure chain remains unverified. [export_figures.py](../scripts/export_figures.py) retains a compatibility interface for Figures 5–7; render_figures.py is the four-format main-figure entry point.

Each main figure has figures/Figure N.tif, .png, .svg and .eps. The seven supplied TIFFs are single-frame RGB/LZW at 600 dpi; PNGs are 300 dpi previews; SVG/EPS retain vector elements. Canvas width is 190 mm and heights are 105–220 mm. The PNG width rounds to 2,244 pixels, so inferred physical resolution can be approximately 299.99 dpi. [Export metadata](../metadata/figure_export_status.json) records output hashes/sizes/dimensions, frozen-input and script hashes, runtime versions and earlier checks. A render_receipt.json is written to the external output directory.

## Figure 2 access boundary

The saved redraw used an excluded 7,774-row monthly source. It preserved calendar masks, counts, transformed values, quartiles, whiskers and all outliers. Its author-original graphic is covered by the approved CC BY 4.0 scope; the underlying mixed provider observations are not author-relicensed.

Obtain EIA RBRTE, FRED EXCHUS, NBS national monthly indices/activity and Customs HS27090000 through [DATA_SOURCES.md](../DATA_SOURCES.md) and [the access matrix](../DATA_ACCESS_MATRIX.csv). [FIGURE_DATA_ACCESS.md](FIGURE_DATA_ACCESS.md) specifies the 338/134-month calendars, calendar differences, missing-value rules and equation eligibility. Individual observations are necessary; the TIFF and boxplot summaries are not substitutes.

The historical --work-dir / --private-held-figure2 source-construction route was not executed during the figure revision. It expects historical canonical/transformed CSV layouts, S1/S17/frame registries and 39 saved primary design CSVs. The separate design-construction entry point emits NPZ, so the portable binding to that CSV interface is incomplete and untested. The ten-file input SHA gate rejects different packaging or vintages. Exact historical-vintage reacquisition and fresh public-data reconstruction have not been demonstrated. The earlier official Customs comparison covered 24 months in 2015–2016; the remaining 110 months were not newly compared.

## Figure 6 horizon binding

The source column lag_or_horizon contains both numeric horizons and the Link-1 label sum_0_3. After selecting Fuel or PPI, the plotting module converts the horizon keys to integers, sorts them numerically and asserts the complete 0–12 sequence. It binds each saved point estimate and interval to the matching (outcome, horizon) bootstrap density, avoiding lexical order such as 0, 1, 10, 11, 12, 2.

The entry point reads MECH2 outcome coefficient arrays of shape (5000, 13), cumulatively sums along the horizon axis and checks the 2.5%/97.5% quantiles against the source intervals with absolute tolerance 1e-14. It uses the saved draws, Scott KDE, 2,048 grid points and within-horizon peak normalization; density heights are not comparable across horizons. Panel A uses the quantity_order=-1, maxlags=12 Link-1 records. No new bootstrap is performed.

## Recorded checks and limits

The 2026-10-15 figure revision compared frozen inputs and plotted values/coordinates: Figure 2 boxplot statistics and outliers; Figures 3, 4 and 7 coordinate fingerprints; Figure 5's 24 points, 48 interval endpoints and 39 equality-test q/status cells; and Figure 6's 26 horizon-specific estimate/interval/density bindings. Figure 1 retained the data/sample/variable pipeline, separate Customs branch, primary LP, supplementary analyses, HAC/MBB/FDR-Holm/DWB inference and conditional-association interpretation. These checks concern diagram content and saved-result rendering, not new model validation.

The earlier review also checked vector/file properties, clipping and text overlap, and all seven figures at their final physical size in colour, grayscale and an approximate deuteranopia preview. Arial text was 8–10 pt and TIFFs were at most 2.65 MB. Numerical data, saved bootstrap paths, scientific estimation modules, tables, SI and manuscript were unchanged by that figure revision. No fresh-data model estimates, MBB/DWB/S18 reruns, online NAAS review or journal-system upload were performed. Documentation cleanup repeats only path/link/licence/hash checks. [VALIDATION.md](../VALIDATION.md) records the separate inherited scientific evidence and remaining limits.
