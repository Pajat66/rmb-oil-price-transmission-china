# Renminbi-denominated oil-price movements and inflation dynamics across China's price system

**v2.0.0 research package available on the main branch; tagged release and Zenodo archiving pending.** The revised research package was pushed in commit [`0bb68d6`](https://github.com/Pajat66/rmb-oil-price-transmission-china/commit/0bb68d60cdb4251c13e620d119e06f58350d5852). Current status: `GITHUB_MAIN_UPDATED_RELEASE_PENDING`. The v2.0.0 tag, GitHub Release and new Zenodo Version DOI do not yet exist; the new PLOS ONE manuscript has not been submitted. The coauthors approved the revised materials, version and scoped MIT/CC BY 4.0 licences.

The main analysis uses stationary local projections (p=2, h=0–12) for RMB oil-cost movements and changes in year-on-year Fuel/PPI/CPI inflation. Estimates describe conditional dynamic associations. The macro calendar is January 1998–February 2026 (338 months); Customs inputs span January 2015–February 2026 (134 months). RMB oil cost = Brent USD/barrel × CNY/USD; oil movements = 100 calendar log differences; inflation outcomes = adjacent changes in year-on-year indices minus 100. Missing months are preserved.

## Repository guide

| Material | Location |
|---|---|
| Seven main figures: TIFF / PNG / SVG / EPS | [Figures](figures/); [scripts, inputs and rendering](docs/FIGURE_REPRODUCTION.md) |
| Six main tables, CSV/XLSX pairs | [Tables](tables/) |
| 18 Supporting Tables and three Supporting Figures | [21 journal SI files](journal_submission/); [archive mapping](supporting_information/README.md) |
| Captions and 34 manuscript items | [Manuscript index](metadata/manuscript_to_files.csv); [captions](metadata/captions.json) |
| Observation sources and transformations | [Official sources](DATA_SOURCES.md); [access matrix](DATA_ACCESS_MATRIX.csv); [data dictionary](DATA_DICTIONARY.md); [data access](data/README.md); [figure observations](docs/FIGURE_DATA_ACCESS.md) |
| Software, frozen results and validation | [Python sources](src/); [entry points](scripts/); [saved results](reference/); [reproduction guide](REPRODUCTION_GUIDE.md); [validation scope](VALIDATION.md); [code coverage](docs/SCIENTIFIC_CODE_COVERAGE.md) |
| Citation and versions | [CITATION.cff](CITATION.cff); [change log](CHANGELOG.md); [release notes and publication status](RELEASE_NOTES.md); [research history](docs/HISTORY.md) |
| Licences | [LICENSE](LICENSE); [file licence register](licenses/FILE_LICENSES.csv); [approval record](licenses/FINAL_LICENSE_APPROVAL.md); [third-party exceptions](licenses/THIRD_PARTY_DATA.md) |
| File inventory and manuscript data statement | [Contents and checksum rules](CONTENTS_MANIFEST.md); [Data Availability text](docs/DATA_AVAILABILITY_FINAL.md); [journal policy context](docs/JOURNAL_POLICY_CHECK.md) |

## Observation access and reproduction limits

The [338-month EXCHUS extract](data/analysis_ready/fred_exchus_monthly.csv) is included under its upstream public-domain status with citation requested. Obtain EIA monthly RBRTE, NBS national monthly indices/activity and Customs HS27090000 observations through the official procedures, units and date windows in [DATA_SOURCES.md](DATA_SOURCES.md). Historical checksums identify the research vintage; later provider revisions must be documented. EIA/NBS/Customs original exports, complete mixed monthly inputs and the 7,774-row Figure 2 observation source are excluded and are not author-relicensed.

The earlier official Customs comparison covers 2015–2016: all 24 monthly quantities and 24 RMB amounts matched exactly. The remaining 110 months were not newly exported and compared; earlier 134-month local-validation evidence is separate. Exact historical-vintage reacquisition is unconfirmed. Figure 2 needs individual observations, including outliers, and the published calendar/sample rules. Its historical source-construction interface has an incomplete, untested portable binding; a redraw from the private frozen source does not establish fresh-data reconstruction.

Figures 1–7 were rendered from saved inputs on 2026-10-15. The repository includes 56 Python sources, frozen statistical outputs, six main-table pairs and 21 SI files. The [figure reproduction document](docs/FIGURE_REPRODUCTION.md) records scripts, inputs and the earlier figure checks. Full numerical and rendering execution from newly acquired data has not been verified. Earlier primary OLS/HAC checks and unperformed MBB/DWB/S18 procedures are distinguished in [VALIDATION.md](VALIDATION.md). Reference environment: Python 3.12.7 with [requirements](requirements.txt) and [Conda reference](environment.yml); Arial is not bundled.

## Licences and citation

MIT applies to author-owned software, configuration and associated software documentation. CC BY 4.0 applies to author-original figures/captions, main and supporting tables and shareable generated statistical results. Third-party observations, notices and dependencies retain their own terms. [LICENSE](LICENSE) and the per-file register define these scopes; the historical MIT notice is preserved.

Author order: Xuehua Zhou; Baoping Zhang; Zhongfan Li; Yuechao Yao; Hanming Zhang; Huijuan Wang; Quanbo Yuan. Historical v1.1.0 has [Version DOI 10.5281/zenodo.22869727](https://doi.org/10.5281/zenodo.22869727); the existing [Concept DOI 10.5281/zenodo.20714251](https://doi.org/10.5281/zenodo.20714251) identifies the version family. Neither is a v2.0.0 Version DOI. [Zenodo metadata](.zenodo.json) uses Other (Open) for the mixed material and describes component scopes. Publication steps and the pending manuscript Data Availability insertion are recorded in [RELEASE_NOTES.md](RELEASE_NOTES.md#publication-status).
