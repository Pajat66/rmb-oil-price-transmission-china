# Validation scope

Distributed statistics are frozen author outputs. Validation described here is inherited from the recorded checks below; private logs, observed design matrices and residual arrays are not distributed. The documentation cleanup checks only files, hashes, links, licence coverage, metadata and Git state. It does not rerun the broader repository verifier, scientific computations, figure rendering or SI generation.

## Earlier input and primary-model checks

All ten locally held raw files matched the historical SHA contract. Earlier reconstruction validated master/canonical/stationary data and designs. Formal p=2 origins begin in 1998-04, with N=335 at h=0 and N=323 at h=12, without substituting the S18 common sample. Local hash equality proves integrity, not external availability of the historical vintage or redistribution rights.

Earlier Windows execution verified 39/39 primary OLS and 39/39 HAC models. Of 21,879 numerical comparisons, 20,795 had zero error and 1,084 had nonzero differences within abs(new−reference) <= 1e-10 + 1e-9 × abs(reference). There were zero tolerance failures and zero significance/CI-zero changes. Evidence comprised 3,003 saved historical CSV comparisons, 17,472 original-code/frozen-data reconstructions and 1,404 independent Bartlett sandwich elements. The 39 cumulative points and available OLS/HAC cumulative inference were checked with horizon-specific samples; h=12 uses HAC13.

Historical full beta, residual, RSS and covariance snapshots were not saved. Full arrays were recomputed with original author functions and an independent HAC check, not compared against nonexistent snapshots. Direct saved-CSV comparisons concern the available oil coefficients and inference fields. Earlier S18 checks covered 195 designs and 585 information-criterion rows; S18 Stage1/2 were not re-estimated during packaging.

Reference environment: Python 3.12.7, NumPy 1.26.4, pandas 2.2.2, SciPy 1.13.1, statsmodels 0.14.2, MKL 2023.1, one thread. Fresh installation and the directory/CLI adapters have no full scientific end-to-end test. [Code coverage](docs/SCIENTIFIC_CODE_COVERAGE.md) distinguishes implemented functions from actual execution evidence.

## Tables, SI and manuscript checks

Earlier package checks covered 34 mapped manuscript items, 21 journal attachments and 44 SI sheets. S3 has five sheets and 526 data rows; S18 has eight sheets and 762 formulas. OOXML values, types, styles, relationships and formula-cache presence were inspected, with no missing formula-cache elements or error cells in the recorded SI check. Native Excel opening/recalculation of all attachments was not performed; cache presence does not establish recalculation. CSV-based S18 Stage3 export was checked separately without estimating S18.

Excel absPath directory metadata was removed from the 17 split S1–S17 workbooks and their archive during earlier packaging. Other OOXML parts, including worksheet values/formulas/caches, styles, shared strings and table definitions, retained their bytes; whole-file hashes changed for that documented privacy transformation. Subsequent package checks found no private paths in SI XML/relationships. The current cleanup does not edit these files.

The recorded main-table review comprised 175 identifier/unit/sample or displayed-numeric checks: 174 matched and one historical Table 2 Fuel h=12 lower-bound display differed. The latest saved Word examined during preparation already shows `0.3072[0.1118, 0.5484]`; the earlier `0.1119` display issue is closed. That saved manuscript SHA256 is b76c073dd9275f33ae9f30032bd6d4631921064997cc1dd8d21ac40b3a3b42e3. Its 19 MathType OLE objects were present in OOXML; no new visual assessment of every equation was performed. The Data Availability heading was empty and still requires manual insertion after the real Version DOI exists. These are dated manuscript observations, not a live synchronization guarantee.

## Figures and observation access

All seven main figures were visually redrawn from saved inputs on 2026-10-15. [Figure reproduction](docs/FIGURE_REPRODUCTION.md) records the source/script mapping, formats, value/coordinate checks, Figure 6 horizon binding and final-size visual checks. Earlier statements that main-figure bytes were unchanged apply to checks before that revision. The figure revision did not alter observations, numerical results, bootstrap paths, scientific estimation modules, tables, SI or manuscript. A frozen redraw does not verify propagation from new estimates.

The official Customs comparison covered all 24 months in 2015–2016, with 48 exact raw quantity/RMB integer matches. The other 110 months were not newly acquired and compared; historical 134-month local validation is a separate evidence stratum. [Data sources](DATA_SOURCES.md), [the access matrix](DATA_ACCESS_MATRIX.csv) and [Figure 2 access limits](docs/FIGURE_DATA_ACCESS.md) retain the source-vintage, redistribution and portable-reconstruction limits. Source provenance does not prove retrospective browser actions or complete current-vintage availability.

## Unperformed procedures

Full main MBB distribution/interval/family comparison, DWB re-estimation, S18 Stage1/2 re-estimation, complete secondary numerical comparison and rebuilding all figures from fresh estimates remain unperformed in the release preparation. Saved coefficient paths do not establish a new bootstrap verification. Historical S2/S3 adapter modules received syntax/dependency review without numerical reruns; table assembly imports their frozen diagnostics. Full graph-source rebinding, fresh installation, complete historical-vintage reacquisition, native Excel recalculation, online NAAS checking and journal-system upload remain unverified.

Later packaging and documentation checks concern inventory, SHA256, relative links, licence scope, identity metadata and unchanged protected files. They do not extend the scientific evidence above. No claim of all-results verification, independent full reproduction or journal-policy acceptance is made. Version and scoped licences are approved; the remaining publication status is recorded in [RELEASE_STATUS.json](RELEASE_STATUS.json) and [release notes](RELEASE_NOTES.md#publication-status).
