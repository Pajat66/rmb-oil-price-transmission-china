# Renminbi-denominated oil-price movements and inflation dynamics across China's price system

**v2.0.0 — final preparation for the authorized GitHub main push; tagged Release and Zenodo archive pending.** The coauthors approved the revised materials, version and scoped MIT/CC BY 4.0 licences. This package supports a **new PLOS ONE manuscript**. Current preparation state: `READY_FOR_AUTHORIZED_GITHUB_MAIN_PUSH`. No new Version DOI has been assigned.

The revised main analysis uses stationary local projections (p=2, h=0–12) for RMB oil-cost movements and changes in year-on-year Fuel/PPI/CPI inflation. Estimates describe conditional dynamic associations. The macro calendar is January 1998–February 2026 (338 months); Customs inputs span January 2015–February 2026 (134 months). RMB oil cost = Brent USD/barrel × CNY/USD; oil movements = 100 calendar log differences; inflation outcomes = adjacent changes in year-on-year indices minus 100. Missing months are preserved.

## Start here

| Material | Location |
|---|---|
| Seven main figures: TIFF / PNG / SVG / EPS | [Figures](figures/); [visual redesign and QA](docs/FIGURE_REDESIGN_EXECUTIVE_SUMMARY.md); [Figure 2 source boundary](docs/FIGURE2_RELEASE_STATUS.md) |
| Six main tables, CSV/XLSX pairs | [Tables](tables/); [latest Word status](docs/MANUSCRIPT_RECONCILIATION.md) |
| 18 Supporting Tables and three Supporting Figures | [21 journal SI files](journal_submission/); [archive mapping](supporting_information/README.md) |
| Captions and 34 manuscript items | [Manuscript index](metadata/manuscript_to_files.csv); [captions](metadata/captions.json) |
| Necessary observations and transformations | [Official sources](DATA_SOURCES.md); [data access matrix](DATA_ACCESS_MATRIX.csv); [data dictionary](DATA_DICTIONARY.md); [data access](data/README.md); [figure observations](docs/FIGURE_DATA_ACCESS.md) |
| Software and frozen results | [Python sources](src/); [entry points](scripts/); [saved results](reference/); [reproduction guide](REPRODUCTION_GUIDE.md); [validation limits](VALIDATION.md) |
| Citation and version | [CITATION.cff](CITATION.cff); [change log](CHANGELOG.md); [release notes](RELEASE_NOTES.md); [history](docs/HISTORY.md) |
| Licence scopes | [LICENSE](LICENSE); [file licence register](licenses/FILE_LICENSES.csv); [third-party exceptions](licenses/THIRD_PARTY_DATA.md) |
| Manuscript and publication handoff | [Final Data Availability](docs/DATA_AVAILABILITY_FINAL.md); [remaining actions](docs/FINAL_AUTHOR_CHECKLIST.md); [publication sequence](docs/FINAL_RELEASE_HANDOFF.md) |

## Official observation access

The [EXCHUS extract](data/analysis_ready/fred_exchus_monthly.csv) is included under its upstream public-domain status with citation requested. Obtain EIA monthly RBRTE, NBS national monthly indices/activity and Customs HS27090000 observations through the exact official procedures, units and date windows in [DATA_SOURCES.md](DATA_SOURCES.md). Historical checksums identify the research vintage; later provider revisions must be documented. EIA/NBS/Customs original exports, complete mixed monthly inputs and the 7,774-row Figure 2 observation source are excluded and are not author-relicensed. Figure 2 requires the individual values, including outliers, transformed with the published calendar/sample rules.

The inherited Customs closure is precise: official self-service exports for 2015–2016 matched all 24 monthly quantities and 24 RMB amounts exactly. The remaining 110 months were not newly exported and compared; the earlier 134-month local-validation evidence is separate. No new Customs investigation is required by this release preparation. No concrete necessary observation lacking a documented provider route was identified.

## Licences and citation

MIT applies to author-owned software, configuration and associated software documentation. CC BY 4.0 applies to author-original figures/captions, main and supporting tables and shareable generated statistical results. Third-party data, notices and dependencies retain their own terms; [LICENSE](LICENSE) and the per-file register define the limits. The historical MIT notice is unchanged.

Author order: Xuehua Zhou; Baoping Zhang; Zhongfan Li; Yuechao Yao; Hanming Zhang; Huijuan Wang; Quanbo Yuan. Historical v1.1.0 has [Version DOI 10.5281/zenodo.22869727](https://doi.org/10.5281/zenodo.22869727); the existing [Concept DOI 10.5281/zenodo.20714251](https://doi.org/10.5281/zenodo.20714251) identifies the version family. Neither is a new v2.0.0 Version DOI. The existing active GitHub–Zenodo release integration is the sole archive route. [Root metadata](.zenodo.json) explicitly uses Other (Open) for this mixture and describes component scopes, avoiding an automatic blanket CC BY label.

## Evidence and remaining actions

The 2026-10-15 figure-only revision redraws all seven main figures from frozen inputs and synchronizes TIFF/PNG/SVG/EPS, the local submission copies and file indexes. All scientific data, estimates, saved bootstrap paths, six table pairs, 21 SI files and manuscript files remain unchanged. There are 56 Python sources, including the shared plotting visual system. No models, MBB/DWB/S18 or SI processing were rerun. [Redesign outputs](docs/FIGURE_REDESIGN_OUTPUTS.md), [formal scripts](docs/FIGURE_REDESIGN_SCRIPT_MAP.md) and [11-point QA](docs/FIGURE_REDESIGN_QA.md) describe this narrow update. Earlier scientific verification remains limited to its stated scope. The [reproduction guide](REPRODUCTION_GUIDE.md) discloses the untested full execution path and required legal inputs. Reference environment: Python 3.12.7 with versions in [requirements](requirements.txt) and [environment](environment.yml); Arial is not bundled.

Latest saved Word Table 2 Fuel h=12 is already `0.3072[0.1118, 0.5484]`; MathType objects remain present. The Data Availability heading is empty. After separate Release/Zenodo authorization and actual archive creation, fill the real Version DOI in the final statement and insert it manually in Word. Main tables stay in the manuscript; submit seven separate figures and 21 SI files as a new manuscript.
