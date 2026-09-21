# Reproduction guide

## 1. System requirements

Use a fresh writable copy of the repository. Python scripts use Chinese filenames; Windows is the tested path context. The deposited result files are treated as reference outputs and should not be overwritten in the archival copy.

## 2. Python setup

Create an environment from `environment.yml`, or install `requirements.txt`. The recorded Python dependencies are pandas, NumPy, openpyxl, matplotlib, statsmodels, SciPy, scikit-learn, and Pillow.

## 3. R setup

R scripts use `tidyverse`, `readxl`, `ragg`, `scales`, `grid`, `dplyr`, `tidyr`, `ggplot2`, `vegan`, `stringr`, and `ggalluvial`. Install only the packages needed for the R script you plan to run.

## 4. Data sources

Confirm all raw files listed in `01_raw/README_DATA_SOURCES.md` are present. Do not alter raw inputs. The source log and variable dictionary are in `00_admin/`.

## 5. Ordered workflow

Run the following only in a copy where replacing generated outputs is intended.

| Step | Input | Script | Output |
| --- | --- | --- | --- |
| Build long master data | EIA, FRED, NBS files in `01_raw/` | `03_scripts/python/fill_master_monthly_long_openpyxl.py` | `02_clean/monthly_master/master_monthly_long_1998_2026.xlsx` |
| Build filled short master data | Short master plus EIA, FRED, NBS, and Customs files | `03_scripts/python/fill_master_monthly_v5_exactpaths.py` | `02_clean/monthly_master/master_monthly_v1_filled_full_openpyxl.xlsx` |
| Prepare analysis files | Long and filled short master datasets | `03_scripts/python/chapter2_preprocess_fixed_py38.py` | `04_results/chapter2/master_*`, missingness, continuity, and outlier-flag workbooks |
| Create final English figures | Appropriate chapter-2 output(s) | See figure-specific rows in `CONTENTS_MANIFEST.md` | `04_results/figures_english/` |
| Create chapter-6 result tables | Clean long and short chapter-2 files | `03_scripts/python/chapter6_tables_all_v2_fixed.py` | `04_results/chapter6/chapter6_tables.xlsx` |
| Create Supporting Information tables | Clean long/short files and long master auxiliary data | `03_scripts/python/export_supporting_information_tables.py` | `04_results/supporting_information/S1_Table.xlsx`, mapping CSV, and captions |
| Prepare PLOS figure copies | Final English figure files | `03_scripts/python/postprocess_plos_figures.py` | `04_results/figures_plos_submission/Fig*.tif` and a generated figure mapping CSV |

## 6. Expected outputs and verification

Use `CONTENTS_MANIFEST.md` for the manuscript-to-output link. The PLOS conversion map assigns the local-projection band to Fig10 and the Mantel graph to Fig11. `check_plos_figures.py` checks image format properties but writes a report into the submission-results directory, so run it only on a writable reproduction copy.

## 7. Supporting Information generation

The SI export script builds one workbook whose sheets are S1 Table through S8 Table. Their sources and models are recorded in `04_results/supporting_information/supporting_table_mapping.csv`; the deposited copy is assessed in `docs/repository_audit/SUPPORTING_INFORMATION_AUDIT.md`.

## 8. Known caveats

- This repository does not claim a one-command reproduction path.
- Some retained exploratory/older figure scripts write to `04_results/figures/`, while current English manuscript outputs are in `04_results/figures_english/`; see the manifest before choosing a script.
- Figure 1 has a deposited submission TIFF, but the code's PLOS mapping intentionally records no standalone technical-route source image. Its provenance needs manual confirmation.
- R execution is environment-dependent; this cleanup does not install R or rerun models.
