# Research Materials README

This folder contains the data, scripts, intermediate outputs, figures, tables, and reference materials prepared for a PLOS ONE manuscript on imported inflation, oil-price shocks, exchange-rate pass-through, and China-specific price dynamics. The project is organized as a reproducible research package: raw source files are preserved separately from cleaned analytical datasets, code is stored in script folders, and manuscript-ready outputs are collected under the results and paper-materials directories.

## Folder Structure

```text
Mainfiles/
  00_admin/              Project documentation, source logs, and variable dictionary
  01_raw/                Original source datasets downloaded or collected from public sources
  02_clean/              Cleaned monthly master datasets used for analysis
  03_scripts/            Python and R scripts for cleaning, analysis, tables, and figures
  04_results/            Cleaned outputs, diagnostics, regression tables, and final figures
  05_paper_materials/    Literature and reference files used during manuscript preparation
```

## 00_admin: Project Documentation

The `00_admin` directory contains the metadata needed to understand the provenance and construction of the analytical dataset.

- `source_log.xlsx` records the source file name, data provider, main variables, time coverage, unit of measurement, and processing notes for each raw dataset. It documents sources including EIA, FRED, the National Bureau of Statistics of China, China Customs, the World Bank commodity price data, and BIS effective exchange-rate backup series.
- `variable.xlsx` is the variable dictionary for the monthly master dataset. It maps each master-table field to its Chinese description, source file, original variable or column name, and transformation rule.

Important master variables documented in this folder include:

- `month`: monthly date key standardized to year-month format.
- `brent_usd`: Brent crude oil monthly average price in USD per barrel.
- `cny_per_usd`: RMB/USD exchange rate.
- `oil_rmb`: RMB-denominated oil price, computed as `brent_usd * cny_per_usd`.
- `cpi_yoy`: year-on-year CPI index.
- `cpi_transport_comm_yoy`: year-on-year transport and communication CPI index.
- `core_cpi_proxy_yoy`: proxy for core CPI, based on the index excluding food and energy.
- `ppi_yoy`: year-on-year producer price index.
- `ppi_purchase_yoy`: year-on-year industrial producer purchase price index.
- `ppi_fuel_power_yoy`: year-on-year fuel and power purchase price index.
- `import_crude_oil_qty_10k_ton`: crude-oil import volume, converted to ten-thousand tons.
- `import_crude_oil_value_100m_rmb`: crude-oil import value, converted to hundred-million RMB.
- `import_crude_oil_unit_price_yuan_per_kg`: crude-oil import unit value, computed as RMB value divided by physical quantity.
- `indust_va_yoy`: year-on-year growth of value added by industrial enterprises above designated size.
- `indust_va_cum_yoy`: cumulative year-on-year growth of industrial value added.
- `neer_backup`, `reer_backup`, and `brent_wb_backup`: backup cross-check series from BIS and World Bank sources.

## 01_raw: Original Source Data

The `01_raw` directory preserves the unprocessed or minimally processed source datasets. These files should be treated as the primary data archive and should not be overwritten during replication.

### `01_raw/01_eia_brent`

- `EIA_brent_usd_monthly_1987-latest_2026.3.22.csv`
- Source: U.S. Energy Information Administration.
- Main content: Europe Brent spot price, FOB, USD per barrel.
- Coverage recorded in the source log: May 1987 to February 2026.
- Processing note: the first four rows are descriptive metadata; the formal data table starts afterward.

### `01_raw/02_fx_pbc_fred`

- `FRED_exchus_cny_per_usd_monthly_1981-latest_2026.3.22.xlsx`
- Source: FRED.
- Main sheet: `Monthly`.
- Main variables: `observation_date` and `EXCHUS`.
- Coverage recorded in the source log: January 1981 to the latest available observation at download time.
- Used to construct the RMB/USD exchange-rate series.

### `01_raw/03_nbs_price`

This folder contains price and industrial-output series from the National Bureau of Statistics of China.

- CPI category files:
  - `98年-15年月度消费价格分类指数.xlsx`
  - `16年-20年月度消费价格分类指数.xlsx`
  - `21年-25年月度消费价格分类指数.xlsx`
  - `26年1-2月月度消费价格分类指数.xlsx`
- PPI files:
  - `98年-26年2月工业生产者出厂价格指数.csv`
  - `98年-26年2月工业生产者购入价格指数.csv`
- Industrial-output file:
  - `98年-26年2月规上工业增加值增长速度.csv`

These files are used to construct CPI, core-CPI proxy, transport and communication CPI, PPI, purchase-price, fuel-and-power purchase-price, and industrial value-added indicators. The CSV files use GBK encoding and are read by the scripts after skipping source-description rows.

### `01_raw/04_customs_trade`

- `15年-26年2月月度原油进口量值数据.xlsx`
- Source: China Customs.
- Main content: monthly crude-oil import quantity and RMB value.
- Main filtering rule: commodity code `27090000`.
- The scripts convert raw quantity and value into ten-thousand tons, hundred-million RMB, and unit import price in RMB per kilogram.

### `01_raw/05_backup_bis_worldbank`

This folder contains backup and cross-check files rather than the main analytical source series.

- `(back_up)CMO-Historical-Data-Monthly.xlsx`: World Bank commodity price data.
- `China's Nominal Effective Exchange Rate.xlsx`: BIS nominal effective exchange-rate backup.
- `China's real effective exchange rate.xlsx`: BIS real effective exchange-rate backup.

These files are useful for validation, robustness checks, or alternative specifications, but the main Brent and bilateral exchange-rate series are constructed from the EIA and FRED files.

## 02_clean: Cleaned Master Data

The `02_clean/monthly_master` directory contains the cleaned monthly datasets used as the basis for analysis.

- `master_monthly_v1.xlsx`: short-sample master dataset with 13 columns.
- `master_monthly_v1_filled_full_openpyxl.xlsx`: filled short-sample master dataset generated from the raw files and written with `openpyxl`.
- `master_monthly_long_1998_2026.xlsx`: long monthly master dataset covering the broader 1998-2026 period, with 12 columns.

The master files consolidate energy-price, exchange-rate, price-index, import, and industrial-output variables into a common monthly panel. The long dataset supports coverage checks and descriptive analysis, while the short filled dataset supports models requiring the variables available from the later customs-import period.

## 03_scripts: Reproducible Code

The `03_scripts` directory contains Python and R scripts. The Python scripts are stored under `03_scripts/python`; R scripts are stored under `03_scripts/R`.

### Main Data-Construction Scripts

- `fill_master_monthly_long_openpyxl.py`: constructs the long master dataset `02_clean/monthly_master/master_monthly_long_1998_2026.xlsx` from raw source files.
- `fill_master_monthly_v5_exactpaths.py`: constructs the filled short-sample master dataset `master_monthly_v1_filled_full_openpyxl.xlsx`, using exact source-file paths and `openpyxl` output formatting.
- `chapter2_preprocess_fixed_py38.py`: cleans the long and short master datasets, checks month continuity, summarizes missing values, flags IQR outliers without deleting them, and writes chapter-2 analysis-ready outputs.

### Figure Scripts

The figure scripts generate descriptive, correlation, dynamic-effect, mechanism, robustness, and local-projection visuals. Most final English-language figures are exported to `04_results/figures_english` as both PNG and TIFF files.

Representative scripts include:

- `fig2_1_3d_coverage_terrain.py` and `03_scripts/R/fig2-1.R`: sample coverage and data-availability visualization.
- `plot_chapter2_trend_fixed_py38_3plus2.py`: standardized trend and LOWESS visualization.
- `fig3_2_corr_heatmap_bar.py`: correlation matrix and bar visualization.
- `fig3_3_rolling_corr_group.py`: rolling-correlation visualization.
- `fig4_1_dlm_path.py`: distributed-lag model path analysis and coefficient export.
- `fig4_2_cumulative_effect_group.py`: cumulative-effect visualization.
- `fig4_3_3d_effect_compare.py`: comparative 3D dynamic-effect visualization.
- `fig5_1_mechanism_path.py`, `fig5_2_mechanism_mirror.py`, and `fig5_3_mechanism_bubble_heatmap.py`: mechanism-path and mechanism-strength visuals.
- `fig6_1_phase_heatmap.py`, `03_scripts/R/fig6_1_mantel_network_bubble.R`, `fig6_2_lp_irf_band.py`, and `fig6_3_path_sem_style.py`: phase heterogeneity, Mantel/network-style visualization, local-projection impulse-response bands, and path-style summary graphics.

### Table and Robustness Scripts

- `chapter6_tables_all_v2_fixed.py` generates robustness, heterogeneity, local-projection, path-effect, and variable-importance tables.
- The final table workbook is stored at `04_results/chapter6/chapter6_tables.xlsx`.
- `export_supporting_information_tables.py` generates the English-language Supporting Information workbook for submission. It writes `04_results/supporting_information/S1_Table.xlsx`, `supporting_table_mapping.csv`, and `suggested_supporting_information_captions.txt`.
- The Supporting Information export script fills blank long-sample `oil_rmb` values as `brent_usd * cny_per_usd` during export, excludes the supplementary `core_cpi_proxy_yoy` series from the core unit-root-test sheets, and aligns S6 with the manuscript Table 4 6-period DLM specification using `indust_va_cum_yoy` as the industrial value-added control.

### Software Dependencies

The scripts use standard Python scientific-computing packages and R plotting packages.

Python dependencies observed in the scripts include:

- `pandas`
- `numpy`
- `openpyxl`
- `matplotlib`
- `statsmodels`
- `scipy`
- `scikit-learn`

R dependencies observed in the scripts include:

- `tidyverse`
- `readxl`
- `ragg`
- `scales`
- `grid`

Some scripts use absolute Windows paths pointing to this project directory. If the project is moved, update the `ROOT`, `PROJECT_ROOT`, `DATA_FILE`, or related path definitions before re-running the workflow.

## 04_results: Analytical Outputs

The `04_results` directory contains processed data, diagnostics, manuscript tables, and final English-language figures.

### `04_results/chapter2`

This directory contains data-quality and analysis-ready outputs generated by `chapter2_preprocess_fixed_py38.py`.

- `master_long_clean_v1.xlsx`: cleaned long-sample dataset.
- `master_short_clean_v1.xlsx`: cleaned short-sample dataset.
- `master_long_plot_ready.xlsx`: long dataset with plotting transformations.
- `master_short_plot_ready.xlsx`: short dataset with plotting transformations.
- `missing_summary.xlsx`: missing-value counts and ratios by variable and dataset.
- `continuity_long.xlsx` and `continuity_short.xlsx`: checks for missing months in the long and short datasets.
- `outlier_flag_long.xlsx` and `outlier_flag_short.xlsx`: IQR-based outlier flags by month and variable. These flags are diagnostic; observations are not deleted by default.

### `04_results/chapter6`

- `chapter6_tables.xlsx`: workbook containing robustness and mechanism-related tables.

Observed sheets include:

- `表6-1 替代变量稳健性`: alternative-variable robustness checks.
- `表6-2 替代模型稳健性`: alternative-model robustness checks.
- `表6-3 阶段异质性`: stage or phase heterogeneity analysis.
- `表6-4 LP摘要`: local-projection summary.
- `附表 LP全响应`: full local-projection responses.
- Additional sheets generated by the fixed script may include direct path effects, indirect path effects, and variable-contribution rankings.

### `04_results/supporting_information`

This directory contains the manuscript Supporting Information tables prepared for PLOS ONE submission.

- `S1_Table.xlsx`: English-language Supporting Information workbook with eight sheets named `S1 Table` through `S8 Table`.
- `supporting_table_mapping.csv`: source and model mapping for each Supporting Information sheet.
- `suggested_supporting_information_captions.txt`: suggested captions and notes for the Supporting Information files.

The current SI workbook sheets are:

- `S1 Table`: variable names, abbreviations, units, sources, and derivations.
- `S2 Table`: descriptive statistics for the long sample. The exported `oil_rmb` series is filled from `brent_usd * cny_per_usd` if the stored cleaned long-sample column is blank.
- `S3 Table`: descriptive statistics for the short sample.
- `S4 Table`: ADF unit-root tests for level series in the core long-sample variables.
- `S5 Table`: ADF unit-root tests for first-differenced core long-sample variables. The supplementary `core_cpi_proxy_yoy` series is not included in S4-S5 because it is not a core ARDL premise variable.
- `S6 Table`: cumulative lag effects of the RMB-denominated oil price. This sheet uses the manuscript Table 4 specification: a 6-period DLM with `oil_rmb` lags 0-6 and `indust_va_cum_yoy` as the industrial value-added control. The lag 0-3 cumulative effects align with the manuscript values for fuel and power purchase prices, PPI, and CPI.
- `S7 Table`: impacts of the RMB-denominated oil price on the crude oil import unit price. It reports both the baseline DLM and the same model controlling for crude oil import quantity, supporting the statement that the result remains essentially unchanged after adding import quantity.
- `S8 Table`: impacts of crude oil import costs and upstream/midstream prices on CPI YoY. It reports lag terms, cumulative lag effects, significance, sample size, and adjusted R-squared for CPI transmission models.

### `04_results/figures_english`

This directory contains manuscript-ready English-language figures. PNG files are suitable for quick review; TIFF files are high-resolution publication files.

Current final figure files include:

- `fig2_1_sample_coverage_english`: sample-coverage figure.
- `fig2_2_standardized_trend_lowess_english`: standardized trend and LOWESS figure.
- `fig3_2_correlation_matrix_bar_english`: correlation matrix with bar-style summary.
- `fig3_3_rolling_correlation_english`: rolling-correlation figure.
- `fig4_1_dlm_path_english`: distributed-lag path figure.
- `fig4_1_dlm_path_coefficients_english.xlsx`: coefficient table supporting Figure 4.1.
- `fig4_2_cumulative_effect_english`: cumulative-effect figure.
- `fig4_3_3d_effect_compare_english`: 3D comparison of dynamic effects.
- `fig5_2_mechanism_3dbar_english`: 3D mechanism-strength bar figure.
- `fig6_1_mantel_network_bubble_english`: Mantel/network-bubble figure.
- `fig6_2_lp_irf_band_english`: local-projection impulse-response-band figure.

Most TIFF files are exported at high resolution and are therefore large. This is expected for journal-submission graphics.

## 05_paper_materials: Manuscript Reference Materials

The `05_paper_materials/Refference` directory contains literature and reference documents used during manuscript preparation. It includes Chinese and English PDF files on:

- imported inflation,
- oil-price shocks,
- exchange-rate pass-through,
- RMB exchange-rate pass-through,
- China-specific inflation dynamics,
- monetary-policy responses,
- VAR, structural VAR, local-projection, and quantile-regression evidence,
- BIS, ECB, NBER, ScienceDirect, MDPI, and other academic or institutional sources.

The folder also contains `参考文献.txt`, a working bibliography file. Because this file may use a local text encoding, verify character encoding before copying entries directly into a manuscript or reference manager.

## Suggested Reproduction Workflow

Run the workflow from the project root after confirming that all raw files are present in `01_raw`.

1. Review metadata:
   - Open `00_admin/source_log.xlsx` to confirm data provenance and coverage.
   - Open `00_admin/variable.xlsx` to confirm variable definitions and transformations.

2. Rebuild cleaned master datasets:
   - Run `03_scripts/python/fill_master_monthly_long_openpyxl.py` to rebuild the long monthly dataset.
   - Run `03_scripts/python/fill_master_monthly_v5_exactpaths.py` to rebuild the filled short monthly dataset.

3. Generate cleaned analysis-ready outputs:
   - Run `03_scripts/python/chapter2_preprocess_fixed_py38.py`.
   - Confirm that outputs are written to `04_results/chapter2`.

4. Generate figures:
   - Run the relevant Python and R figure scripts in `03_scripts/python` and `03_scripts/R`.
   - Confirm that final English-language graphics are written to `04_results/figures_english`.

5. Generate robustness and mechanism tables:
   - Run `03_scripts/python/chapter6_tables_all_v2_fixed.py`.
   - Confirm that `04_results/chapter6/chapter6_tables.xlsx` is updated.

6. Generate Supporting Information tables:
   - Run `03_scripts/python/export_supporting_information_tables.py`.
   - Confirm that `04_results/supporting_information/S1_Table.xlsx`, `supporting_table_mapping.csv`, and `suggested_supporting_information_captions.txt` are updated.
   - Close the Excel workbook before re-running the script on Windows; an open `S1_Table.xlsx` file can prevent overwrite.

7. Prepare files for journal submission:
   - Use TIFF figures from `04_results/figures_english` for high-resolution submission graphics.
   - Use PNG files for internal review, presentations, or quick manuscript drafting.
   - Use `04_results/supporting_information/S1_Table.xlsx` as the submission Supporting Information table workbook.
   - Use `04_results/chapter6/chapter6_tables.xlsx` and supporting coefficient workbooks as internal table sources and robustness outputs.

## Notes for PLOS ONE Submission

- Raw data and derived datasets are separated to preserve traceability.
- The data dictionary and source log support transparent reporting of variable definitions and source provenance.
- Cleaned datasets and diagnostic files allow reviewers to inspect missingness, continuity, and outlier flags.
- Supporting Information tables are consolidated in `04_results/supporting_information/S1_Table.xlsx` with sheet names matching S1-S8 captions.
- Figures are provided in both review-friendly PNG format and high-resolution TIFF format.
- The scripts are suitable for reproducibility but may require path adjustment if the folder is moved to another machine.
- Python bytecode cache folders such as `__pycache__` are generated artifacts and are not required for replication or journal submission.
- Literature PDFs are provided for manuscript-preparation context. Redistribution should follow the copyright and licensing conditions of the original publishers.

## Encoding and Path Notes

Several source files and script comments use Chinese file names or Chinese text. On Windows, run scripts in an environment that handles UTF-8 and GBK encodings correctly. The NBS CSV files are read using GBK encoding in the current scripts, while Excel files are read using `openpyxl`.

If the repository is shared with reviewers or collaborators, preserve the directory structure shown above. The scripts rely on the relative organization of `01_raw`, `02_clean`, `03_scripts`, and `04_results`, and several scripts currently contain hard-coded project-root paths.
