# v2.0.0 repository contents

The [file manifest](metadata/public_file_manifest.csv) lists every current public file, its category and scoped licence. The [licence register](licenses/FILE_LICENSES.csv) covers the same paths. The [34-item manuscript index](metadata/manuscript_to_files.csv) maps seven main figures, six main tables, 18 Supporting Tables and three Supporting Figures. [SI mappings](metadata/si_file_mapping.csv) describe the 21 journal attachments and their archive sources.

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
