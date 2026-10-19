# Renminbi-denominated oil-price movements and inflation dynamics across China's price system

**The v2.0.0 research package is archived at [Version DOI 10.5281/zenodo.23388839](https://doi.org/10.5281/zenodo.23388839) and fixed at commit [`9677043`](https://github.com/Pajat66/rmb-oil-price-transmission-china/commit/96770433002895f72c94ac5548b9fcdea2f6d0ea).** The current main branch additionally provides S1 Data for separate PLOS ONE Supporting Information submission. The v2.0.0 tag, Release and Zenodo archive remain unchanged; historical release-status records retain their snapshot meaning.

The main analysis uses stationary local projections (p=2, h=0–12) for RMB oil-cost movements and changes in year-on-year Fuel/PPI/CPI inflation. Estimates describe conditional dynamic associations. The macro calendar is January 1998–February 2026 (338 months); Customs inputs span January 2015–February 2026 (134 months). RMB oil cost = Brent USD/barrel × CNY/USD; oil movements = 100 calendar log differences; inflation outcomes = adjacent changes in year-on-year indices minus 100. Missing months are preserved.

## Repository guide

| Material | Location |
|---|---|
| Seven main figures: TIFF / PNG / SVG / EPS | [Figures](figures/); [scripts, inputs and rendering](docs/FIGURE_REPRODUCTION.md) |
| Six main tables, CSV/XLSX pairs | [Tables](tables/) |
| 18 Supporting Tables, three Supporting Figures and one Supporting Data workbook | [22 journal SI files](journal_submission/); [S1 Data](journal_submission/S1_Data.xlsx); [v2.0.0 archive mapping](supporting_information/README.md) |
| Captions and 34 manuscript items | [Manuscript index](metadata/manuscript_to_files.csv); [captions](metadata/captions.json) |
| Observation sources and transformations | [Official sources](DATA_SOURCES.md); [access matrix](DATA_ACCESS_MATRIX.csv); [data dictionary](DATA_DICTIONARY.md); [data access](data/README.md); [figure observations](docs/FIGURE_DATA_ACCESS.md) |
| Software, frozen results and validation | [Python sources](src/); [entry points](scripts/); [saved results](reference/); [reproduction guide](REPRODUCTION_GUIDE.md); [validation scope](VALIDATION.md); [code coverage](docs/SCIENTIFIC_CODE_COVERAGE.md) |
| Citation and versions | [CITATION.cff](CITATION.cff); [change log](CHANGELOG.md); [release notes and publication status](RELEASE_NOTES.md); [research history](docs/HISTORY.md) |
| Licences | [LICENSE](LICENSE); [file licence register](licenses/FILE_LICENSES.csv); [approval record](licenses/FINAL_LICENSE_APPROVAL.md); [third-party exceptions](licenses/THIRD_PARTY_DATA.md) |
| File inventory and manuscript data statement | [Contents and checksum rules](CONTENTS_MANIFEST.md); [Data Availability text](docs/DATA_AVAILABILITY_FINAL.md); [journal policy context](docs/JOURNAL_POLICY_CHECK.md) |

## Observation access and reproduction limits

The [338-month EXCHUS extract](data/analysis_ready/fred_exchus_monthly.csv) is included under its upstream public-domain status with citation requested. Obtain EIA monthly RBRTE, NBS national monthly indices/activity and Customs HS27090000 observations through the official procedures, units and date windows in [DATA_SOURCES.md](DATA_SOURCES.md). Historical checksums identify the research vintage; later provider revisions must be documented. The archived v2.0.0 snapshot excludes EIA/NBS/Customs original exports, complete mixed monthly inputs and the historical 7,774-row Figure 2 observation source; third-party observations are not author-relicensed.

An additional [S1 Data workbook](journal_submission/S1_Data.xlsx) provides monthly analysis observations, variable transformations and Figure 2 supporting observations. This post-release addition to the GitHub main branch is intended for separate submission as PLOS ONE Supporting Information. It is not included in the archived v2.0.0 release or its [Zenodo Version DOI 10.5281/zenodo.23388839](https://doi.org/10.5281/zenodo.23388839). The historical 7,774-row Figure 2 source export is not separately redistributed. Provider terms continue to apply to third-party observations. The 34-item manuscript index and original SI mappings retain their v2.0.0 figure/table scope.

The earlier official Customs comparison covers 2015–2016: all 24 monthly quantities and 24 RMB amounts matched exactly. The remaining 110 months were not newly exported and compared; earlier 134-month local-validation evidence is separate. Exact historical-vintage reacquisition is unconfirmed. Figure 2 needs individual observations, including outliers, and the published calendar/sample rules. Its historical source-construction interface has an incomplete, untested portable binding; a redraw from the private frozen source does not establish fresh-data reconstruction.

Figures 1–7 were rendered from saved inputs on 2026-10-15. The repository includes 56 Python sources, frozen statistical outputs, six main-table pairs and 22 SI files: 18 Supporting Tables, three Supporting Figures and S1 Data. The [figure reproduction document](docs/FIGURE_REPRODUCTION.md) records scripts, inputs and the earlier figure checks. Full numerical and rendering execution from newly acquired data has not been verified. Earlier primary OLS/HAC checks and unperformed MBB/DWB/S18 procedures are distinguished in [VALIDATION.md](VALIDATION.md). Reference environment: Python 3.12.7 with [requirements](requirements.txt) and [Conda reference](environment.yml); Arial is not bundled.

The historical repository-integrity verifier is scoped to the fixed v2.0.0 snapshot and should be run against that release tag, rather than the post-release main branch containing S1 Data. Its snapshot-specific inventory and hash checks do not validate subsequent additions.

## Licences and citation

MIT applies to author-owned software, configuration and associated software documentation. CC BY 4.0 applies to author-original figures/captions, main and supporting tables and shareable generated statistical results. Third-party observations, notices and dependencies retain their own terms. [LICENSE](LICENSE) and the per-file register define these scopes; the historical MIT notice is preserved.

Author order: Xuehua Zhou; Baoping Zhang; Zhongfan Li; Yuechao Yao; Hanming Zhang; Huijuan Wang; Quanbo Yuan. Historical v1.1.0 has [Version DOI 10.5281/zenodo.22869727](https://doi.org/10.5281/zenodo.22869727); the existing [Concept DOI 10.5281/zenodo.20714251](https://doi.org/10.5281/zenodo.20714251) identifies the version family. Neither is a v2.0.0 Version DOI. [Zenodo metadata](.zenodo.json) uses Other (Open) for the mixed material and describes component scopes. Publication steps and the pending manuscript Data Availability insertion are recorded in [RELEASE_NOTES.md](RELEASE_NOTES.md#publication-status).
