# Reproduction guide

Run from the repository root. Quick commands below were tested during assembly; they perform no fits/resamples. The earlier verified scientific environment and newly used quick-check runtime are distinct. Fresh installation and the full scientific chain were not run here.

## Quick verification

    python -B -X utf8 scripts/verify_results.py
    python -B -X utf8 scripts/reproduce_analysis.py plan
    python -B -X utf8 scripts/export_supplementary.py --output-dir ../new_si_copy
    python -B -X utf8 scripts/s18_stage3.py --stage1-dir reference/s18/S1 --stage2-dir reference/s18/S2 --output-dir ../new_s18_export

Previously verified: integrity, plan, 21-file frozen copy and CSV-based S18 Stage3 regeneration. Output directories must be new and external. Stage3 rebuilds the 8-sheet package from saved inferential CSVs, fixed fingerprints and empty OOXML layout; it does not estimate S18. The two checksum-index exceptions and their non-circular treatment are documented in [CONTENTS_MANIFEST.md](CONTENTS_MANIFEST.md).

The verifier checks payload inventory/SHA, relative links, 34-item mapping, 21 SI files, ZIP CRC, sheet/formula-cache counts, 39 frozen primary sample/HAC rules, 195 frozen S18 designs and 585 IC rows and Python syntax. An integrity PASS does not establish scientific reproduction or complete pending publication steps.

## Full scientific workflow

These are retained instructions, not a verified end-to-end recipe. Obtain lawful ten-file inputs under [contract](config/raw_inputs.json) and [source instructions](DATA_SOURCES.md). Use Python 3.12.7 with [requirements](requirements.txt) or the unsolved [Conda reference](environment.yml). The commands explicitly opt in to computation; they were not run during this documentation update:

    python -B -X utf8 scripts/reproduce_analysis.py prepare-data --allow-computation --raw-data-dir ../private_raw --work-dir ../new_scientific_work
    python -B -X utf8 scripts/reproduce_analysis.py main-lp --allow-computation --work-dir ../new_scientific_work
    python -B -X utf8 scripts/reproduce_analysis.py stability --allow-computation --work-dir ../new_scientific_work
    python -B -X utf8 scripts/s18_stage1.py --work-dir ../new_scientific_work --r3-authorized
    python -B -X utf8 scripts/s18_stage2.py --work-dir ../new_scientific_work --r3-authorized
    python -B -X utf8 scripts/s18_stage3.py --stage1-dir ../new_scientific_work/s18/stage1 --stage2-dir ../new_scientific_work/s18/stage2 --output-dir ../new_s18_outputs
    python -B -X utf8 scripts/assemble_tables.py --work-dir ../new_scientific_work
    python -B -X utf8 scripts/export_tables.py --source-dir ../new_scientific_work/03_final_tables --output-dir ../new_main_tables
    python -B -X utf8 scripts/export_tables.py --si --source-dir ../new_scientific_work/03_final_tables --output-dir ../new_si_tables

Preparation restores historical master XLSX boundaries, canonical CSVs, stationary variables and missing flags. No January interpolation or substitution of cumulative industrial growth is permitted. RMB_R3_WORKDIR is the retained environment-variable name for the explicit external work directory. main-lp includes primary/secondary LP, HAC and B5000 MBB; it is not an OLS-only quick command. stability includes DWB, rolling/recursive and S15. Existing receipts prevent silent overwrite.

Fixed policies: formal p=2, h=0–12, seed 20261004, B5000, blocks12/6/18. Bartlett HAC max(12, h+1), n/(n−k), use_t=False, normal inference; h=12 uses HAC13. S18 p=1/2/3/4/6 has the common 1998-08 sample, seed 2026101202, B5000, L12, separate shared-draw stream. DWB seed 2026100402, B5000, formal h=0/3/6. Rolling 96/120/144 and recursive initial 120 preserve descriptive h=12. JSON policy files retain full testing families and rules.

Historic S2/S3 source functions are identified in [code coverage](docs/SCIENTIFIC_CODE_COVERAGE.md). Their outputs are imported as historic references during table assembly rather than automatically re-estimated. Additional source modules had syntax/dependency review, not a scientific runtime verification.

## Figures and journal attachments

    python -B -X utf8 scripts/render_figures.py --figure 3 --source-dir ../rebuilt_figure_sources --statistics-dir ../new_scientific_work/03_tables --bootstrap-dir ../new_scientific_work/03_tables --output-dir ../new_figure3

Each figure needs actual rebuilt source CSVs and relevant statistics/coefficient paths. Complete source binding is not yet a one-command verified pipeline. Defaults use frozen references; a frozen redraw does not prove new estimates propagated. Figure6 requires short-sample bootstrap coefficient paths. Arial must be installed legally. For the tested frozen Figure2 redraw, supply --figure2-source /private/figure_2_source.csv; this existing 7774-row source is not redistributed. The historical --work-dir / --private-held-figure2 source-construction route is retained but was not run. Author-original graphic rights and observation-input rights remain separate. Main-figure exports now include 600-dpi RGB/LZW TIFF plus PNG/SVG/EPS; see [figure reproduction](docs/FIGURE_REPRODUCTION.md).

Use package_si.py for lossless S1–S17 sheet selection and s18_stage3.py for S18. Full table assembly still imports historical diagnostics. All frozen outputs and renderings must be compared after these boundaries are resolved. The numerical commands were not executed during package assembly or documentation cleanup.

## Observation vintage and verification boundary

Follow [official retrieval instructions](DATA_SOURCES.md) and [per-input statuses](metadata/data_source_status.csv). Current exports may differ in vintage/layout; do not silently replace historical inputs, hashes or masks. The integrity verifier excludes Git administrative files and reads current gates from RELEASE_STATUS.json. Its broader scientific-policy/SI checks were not rerun during documentation cleanup. The plotting revision used saved inputs, and the full computation commands above remain unverified end to end.

## Customs retrieval verified for 2015–2016

The author successfully used the official platform in a normal browser and supplied the two exports audited on October 14, 2026. The following records the tested selection specification; exact control positions and backend defaults were not independently replayed by the earlier review.

1. Open [Customs statistics](https://stats.customs.gov.cn/) from [Customs public services](https://online.customs.gov.cn/), then 数据查询.
2. Select imports (进口), RMB, monthly observations and January–December 2015. Repeat for January–December 2016. Select HS27090000. If HS27102000 is also exported, retain the original file and filter the research comparison to HS27090000 only.
3. For the intended national total, leave specific partner, trade-mode and registration-region selections unused and aggregate by month and commodity. Preserve the displayed conditions with each export. The available 2016 image shows empty trade-mode/registration fields; the partner selector and import/date controls are outside the image. These visibility limits do not reopen the completed numerical match.
4. Query and use 导出数据. Read the eight named fields with a legacy Chinese decoder such as strict GB18030. Parse the quoted RMB field's thousands commas without losing its integer value; ignore only the unnamed empty trailing CSV field. Do not use crude second quantity 0/unit `?` as barrels or litres.
5. Validate 201501–201512 and 201601–201612 at key YYYYMM + HS27090000. Compare quantity kilograms and RMB yuan as integers. Derive ten-thousand tonnes = kg / 10^7, hundred-million RMB = yuan / 10^8 and RMB/kg = yuan / kg with Decimal. Compare any saved floating ratios under the retained serialization policy rather than a loosened raw-value tolerance.

Result: `OFFICIAL_SELF_SERVICE_ACCESS_VERIFIED_2015_2016`, `OFFICIAL_MONTHLY_MATCH_VERIFIED_24_OF_24`. All 48 raw integer comparisons are exact; 24 raw ratios and scaled conversions agree, with only explained stored-unit-value precision. Use the historical input hash in [sources](DATA_SOURCES.md) to identify the research version. Keep newer exports private unless their redistribution terms have been confirmed. Document future revisions; preserve frozen data/results. The full 134-month fresh official comparison was not run.

## Reviewing the saved package

Start with [README](README.md), [the 34-item matrix](metadata/manuscript_to_files.csv), [main tables](tables/) and [21 SI files](journal_submission/). [Figure observations](docs/FIGURE_DATA_ACCESS.md) distinguishes included plotted statistics from underlying provider observations, including individual Figure 2 outliers. Earlier input/design and 39 OLS/HAC checks are separate from the unperformed full MBB/DWB/S18 pipeline; see [VALIDATION.md](VALIDATION.md). Version and component licences are approved. Current GitHub/tag/Release/DOI/submission status is recorded in [release notes](RELEASE_NOTES.md#publication-status).

## Figure 2 reconstruction boundary

See [the data access matrix](DATA_ACCESS_MATRIX.csv) and [static reconstruction review](DATA_SOURCES.md#final-data-access-transparency-review-2026-10-15). The ten-file historical SHA gate rejects changed download packaging/vintages. The Figure 2 build_sources route expects historical external CSV/registry layouts and 39 saved design CSVs; construct_designs.py emits NPZ and is not a verified drop-in source for those CSVs. Code specifies the observation transformations and masks, but fresh public-data recovery and portable source binding remain unverified. Neither a frozen-source redraw nor provider instructions establish that the excluded monthly observations are publicly deposited. No reconstruction was executed during the documentation update.
