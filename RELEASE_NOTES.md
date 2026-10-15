# v2.0.0 release notes

The research package for **Renminbi-denominated oil-price movements and inflation dynamics across China's price system** is available on GitHub main. The research-package commit is 0bb68d60cdb4251c13e620d119e06f58350d5852. A subsequent documentation update consolidates figure instructions, removes superseded placeholders and refreshes status and file indexes without changing scientific files.

## Research package

The main design uses stationary local projections with p=2 and h=0–12 for RMB oil-cost log movements and calendar-month changes in year-on-year Fuel/PPI/CPI inflation. It replaces the earlier principal DLM/ARDL framing. Historical DLM diagnostics remain labelled in S3; estimates describe conditional dynamic associations.

The package contains seven main figures in TIFF/PNG/SVG/EPS, six main-table CSV/XLSX pairs, 18 Supporting Tables, three Supporting Figures, 56 Python sources and frozen statistical outputs. The 2026-10-15 figure revision used saved inputs without new model, bootstrap or SI computation. [Figure reproduction](docs/FIGURE_REPRODUCTION.md) and [validation scope](VALIDATION.md) distinguish frozen-input checks, earlier primary OLS/HAC verification and the untested full execution chain.

MIT covers author-owned software and associated documentation; CC BY 4.0 covers author-original figures, tables and shareable statistical outputs. Provider observations retain upstream terms. Only the attributed public-domain EXCHUS monthly extract is bundled. The earlier Customs comparison verified 24 months / 48 raw integer matches for 2015–2016; the other 110 months were not newly compared. Source-vintage and Figure 2 reconstruction limits remain in [data access](docs/FIGURE_DATA_ACCESS.md).

## Publication status

Current state: `GITHUB_MAIN_UPDATED_RELEASE_PENDING`. The revised package is on main. The v2.0.0 tag has not been created, its GitHub Release has not been published, a new Zenodo Version DOI has not been assigned, and the new PLOS ONE manuscript has not been submitted. Version, coauthor material consent and scoped licences are approved. Further tag/Release/Zenodo and journal actions require separate authorization.

The selected archive route is the existing GitHub–Zenodo release integration. Its release-event webhook was recorded active on 2026-10-15; that observation is not a guarantee of later ingestion. [Root Zenodo metadata](.zenodo.json) controls the archive description; [archive metadata and checks](docs/ZENODO_METADATA.json) additionally record pending identifiers, historical integration evidence and component rights. A parallel manual deposit is not part of the selected route.

When a release is separately authorized, set the actual release date and refresh affected indexes, publish against the reviewed commit, and inspect the resulting archive's title, seven-author order, version, exact file tree, mixed licence scopes and association with Concept DOI 10.5281/zenodo.20714251. Historical v1.1.0 Version DOI 10.5281/zenodo.22869727 must not be reused as the new Version DOI. Resolve any integration or record-family problem within the same route. Preserve released tag targets and archived files; later DOI citation updates may use a normal follow-up metadata commit.

The saved manuscript examined during package preparation already has Table 2 Fuel h=12 as `0.3072[0.1118, 0.5484]`. Its Data Availability heading was empty. After the actual archive exists, replace the sole DOI placeholder in [the statement](docs/DATA_AVAILABILITY_FINAL.md), insert it manually in Word, preserve MathType and record the saved file hash. The recorded OOXML check found 19 MathType objects; their presence does not certify visual rendering. The manuscript is outside this repository and is not edited by this documentation update.

For the later new PLOS ONE submission, the six main tables remain in Word; seven main figures and 21 SI files are separate uploads. Captions and item identities are mapped in [the manuscript index](metadata/manuscript_to_files.csv). Any journal-required disclosure of AI assistance must reflect actual use; documentation cleanup is not evidence about authorship or tool use.
