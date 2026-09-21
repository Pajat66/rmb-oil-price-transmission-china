# Replication Package: Transmission of RMB-Denominated Oil Price Shocks to China’s Price System

This repository contains the data, code, analytical outputs, and supporting materials for the manuscript: “Transmission of RMB-denominated oil price shocks to China’s price system.” It examines how an RMB-denominated oil price—constructed from Brent crude oil and the RMB/USD exchange rate—transmits through crude-oil import costs, PPI, CPI, and related Chinese price indicators.

## Overview

The study combines a long monthly macroeconomic sample (1998-01 to 2026-02) with a shorter customs-import sample (2015-01 to 2026-02). It evaluates the transmission of external energy-cost shocks into China’s price system, with particular attention to crude-oil import costs, the fuel-and-power purchase price index, PPI, and CPI.

## Paper

**Title:** Transmission of RMB-denominated oil price shocks to China’s price system

**Authors:** Xuehua Zhou, Baoping Zhang, Zhongfan Li, Yuechao Yao, Hanming Zhang, Huijuan Wang, and Quanbo Yuan
**Replication archive DOI:** [10.5281/zenodo.20714252](https://doi.org/10.5281/zenodo.20714252)

## Data availability and provenance

Raw source files are preserved under `01_raw/` as originally collected and must not be modified during reproduction. Provider terms continue to govern third-party data.

| Provider | Repository source material | Primary role |
| --- | --- | --- |
| U.S. Energy Information Administration (EIA) | `01_raw/01_eia_brent/` | Brent crude-oil price |
| Federal Reserve Economic Data (FRED) | `01_raw/02_fx_pbc_fred/` | RMB/USD exchange rate |
| National Bureau of Statistics of China | `01_raw/03_nbs_price/` | CPI, PPI, purchase-price and industrial-output series |
| General Administration of Customs of China | `01_raw/04_customs_trade/` | Crude-oil import quantity and value |
| Bank for International Settlements (BIS) | `01_raw/05_backup_bis_worldbank/` | Backup exchange-rate series where applicable |
| World Bank commodity-price data | `01_raw/05_backup_bis_worldbank/` | Backup/cross-check commodity-price data where applicable |

See `00_admin/README_METADATA.md` and `01_raw/README_DATA_SOURCES.md` for file-level documentation.

## Main variables

Core variables include `brent_usd`, `cny_per_usd`, `oil_rmb`, `cpi_yoy`, `ppi_yoy`, `ppi_purchase_yoy`, `ppi_fuel_power_yoy`, `import_crude_oil_qty_10k_ton`, `import_crude_oil_value_100m_rmb`, `import_crude_oil_unit_price_yuan_per_kg`, `indust_va_yoy`, and `indust_va_cum_yoy`. Definitions, source mapping, and transformations are documented in `00_admin/variable.xlsx` and `00_admin/README_METADATA.md`.

## Methods represented in the deposited code and manuscript

The materials cover distributed-lag models (DLM), ARDL/bounds testing, stepwise mechanism regressions, cumulative lag effects, alternative-variable robustness checks, stage heterogeneity analysis, local projections, and Mantel correlation analysis. This package does not add methods or analyses beyond the submitted manuscript.

## Repository structure

```text
00_admin/             Source log, variable dictionary, and metadata notes
01_raw/               Preserved source data
02_clean/             Cleaned/master analytical datasets
03_scripts/python/    Python construction, analysis, export, and figure scripts
03_scripts/R/         R figure scripts
04_results/           Existing analytical outputs and submission-ready graphics
05_paper_materials/   Working bibliography/reference materials (not needed to run code)
```

## Software requirements

Python dependencies are listed in `requirements.txt`; a Conda environment specification is in `environment.yml`. R package requirements are listed in `REPRODUCTION_GUIDE.md`. The scripts use Chinese filenames and selected raw CSV files are read as GBK, so use an environment with appropriate Windows/UTF-8/GBK support when needed.

## Quick reproduction guide

There is intentionally no one-command reproduction wrapper: several scripts overwrite existing analytical outputs if run in place. Work on a fresh copy of the repository, then follow the ordered, input–script–output workflow in `REPRODUCTION_GUIDE.md`.

1. Inspect `00_admin/` and confirm all files in `01_raw/` are present.
2. Rebuild master files with the two `fill_master_*.py` scripts.
3. Run `chapter2_preprocess_fixed_py38.py` to create analysis-ready files.
4. Run only the figure/table/SI scripts needed for the target item.
5. Use `CONTENTS_MANIFEST.md` to verify the relevant manuscript item and output.

## Manuscript, outputs, and Supporting Information

`CONTENTS_MANIFEST.md` records the verified manuscript–data–script–output mapping and flags entries that need manual confirmation. Figure 10 is the local-projection dynamic-response band and Figure 11 is the Mantel correlation graph. The repository Supporting Information workbook was cross-checked against the submitted Supporting Information package for sheet order, populated cells, formulas, and header content. The current SI workbook is `04_results/supporting_information/S1_Table.xlsx`, with sheets `S1 Table` through `S8 Table`.

## License and citation

Repository-authored code is released under the MIT License; see `LICENSE`. The MIT License applies only to repository-authored code and documentation and does not override third-party data-provider terms. Third-party source datasets and literature remain subject to their original providers’ terms, licenses, and policies. Cite this package using `CITATION.cff` and the DOI above.

## Contact

For questions about the study or deposited materials, contact the corresponding author named in the manuscript.
