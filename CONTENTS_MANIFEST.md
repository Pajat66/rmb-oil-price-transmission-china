# v2.0.0 repository contents

This document and the linked [file manifest](metadata/public_file_manifest.csv), [licence register](licenses/FILE_LICENSES.csv), [checksum index](validation/checksums/files.json), [34-item manuscript index](metadata/manuscript_to_files.csv) and [SI mappings](metadata/si_file_mapping.csv) describe the fixed v2.0.0 snapshot at commit 96770433002895f72c94ac5548b9fcdea2f6d0ea. References below to "current" mean that snapshot, including its 18 Supporting Tables and three Supporting Figures. The main branch additionally includes [S1 Data](journal_submission/S1_Data.xlsx), bringing the current journal SI total to 22; see the [current material list](README.md#repository-guide). The historical indexes do not cover S1 Data or later documentation changes. The original scripts/verify_results.py checks the fixed snapshot and is not a verifier for these post-release additions.

| Directory | Contents |
|---|---|
| [figures](figures/) | Seven main figures in TIFF/PNG/SVG/EPS; included plotted statistics in figures/source |
| [tables](tables/) | Six CSV/XLSX main-table pairs |
| [journal_submission](journal_submission/) | 18 Supporting Tables and three Supporting Figures |
| [supporting_information](supporting_information/) | Frozen supporting workbooks, CSVs and archive mapping |
| [src](src/), [scripts](scripts/), [config](config/) | Scientific and plotting software, entry points and fixed configurations |
| [reference](reference/) | Frozen statistical outputs, bootstrap paths and sample/design registries |
| [data](data/) | Public-domain EXCHUS extract and scientific source metadata |
| [metadata](metadata/), [validation](validation/) | Captions, item/path mappings, export records and checksums |
| [docs](docs/), [licenses](licenses/) | Reproduction, data-access, validation, research-history and licence documentation |

## Checksums and provenance

The [checksum index](validation/checksums/files.json) covers every current file except itself and metadata/public_file_manifest.csv. The public manifest includes both index paths but intentionally leaves their target hashes and sizes empty, preserving the existing non-circular rule. All other rows contain actual byte sizes and SHA256 values. Git objects and administrative files are excluded. Git records the two indexes as ordinary versioned files and provides their historical identities.

The source_path and source_sha256 fields identify the input file at the preceding research-package commit, 0bb68d60cdb4251c13e620d119e06f58350d5852; these are provenance references, not current filesystem paths. New documentation has no baseline source hash. A byte-integrity check does not establish scientific replication.

See [figure reproduction](docs/FIGURE_REPRODUCTION.md), [validation scope](VALIDATION.md), [approved licence record](licenses/FINAL_LICENSE_APPROVAL.md) and [publication status](RELEASE_NOTES.md#publication-status). Original provider exports and complete mixed monthly inputs remain excluded. Historical commits and tags retain their earlier contents and licence boundaries; this inventory describes the current tree.
