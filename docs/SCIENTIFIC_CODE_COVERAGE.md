# Scientific code coverage

Code retains its working src/science, src/s18, src/plotting layout to preserve imports. No statistical function was removed for cosmetic directory renaming. Phase identifiers name historic source provenance; they do not define the main study design.

| Function | Implementations | Actual validation boundary | Deliverables |
|---|---|---|---|
| Raw/master/canonical | raw_readers.py, canonical_layer.py, data_interface.py | Earlier R3A-Fix real reconstruction/design checks; no R4A reconstruction | Tables1, S1, S17, all monthly designs |
| Stationary/calendar design | transformation_layer.py, phase15_common.py, design_construction.py | Earlier R3A-Fix and R3B1 true-design checks | Primary39, components, Customs, S18 |
| OLS/HAC/cumulative covariance | phase2b_core.py, main_estimation.py, inference_ledger.py | Earlier primary 39 OLS/HAC real verification; cumulative available HAC checked; secondary full comparison not done | Figures3–6, Tables2–5, S4–S12 |
| MBB/paired tests/shares | phase2b_core.py, main_estimation.py, inference_ledger.py | Frozen outputs retained; no new full B5000 run | S5–S7, S11, S12, S16, Figures4/6 |
| Components/Customs Link1 | phase2b_diagnostics.py | Source syntax/dependencies and frozen output QA; not a new secondary fit | Figure5/6, Tables4/5, S8–S11 |
| DWB/stability/windows | phase2c_core.py, phase2c_windows.py, stability_estimation.py, stability_summary.py | Frozen results only; no new DWB or rolling/recursive re-estimation | Figure7, Table6, S13/S14, S1–S3Figs |
| S15 | s15_diagnostics.py | Frozen adverse diagnostics retained; no new fit | S15 Table |
| S18 stages | stage1_estimation.py, stage2_estimation.py, stage2_kernels.py, csv_payload.py | Earlier195 design verification; stages1/2 not rerun; Stage3 CSV export checked in R4A | S18 Table |
| Historical S2/S3 | stationarity_analysis.py, phase2a_stationarity.py, phase2a9_core.py, table3_lag_selection.py, model_core.py, phase2a_models.py, phase2a5_core.py | Additional originals syntax/function-AST reviewed; historical data adapter untested numerically | S2three sheets, S3 five sheets526rows |
| Figure/table/SI export | src/plotting/*, xlsx_export.py, table_assembly.py, scripts/export_tables.py, package_si.py, s18_stage3.py | Frozen copy, SI package and non-estimation exports; complete new-estimate rendering not verified | All figures/tables/SI |

Directory protection, quick/dry-run and checksum-path adapters changed execution plumbing only. OLS/HAC/MBB/DWB/S18 numerical function bodies match their copied sources. Additional S2/S3 modules restore unique historical-diagnostic coverage; their adapter was not numerically rerun. Private Word, Codex configuration, Node installation and temporary audit logs are not computation inputs.

Full table assembly copies historic diagnostic CSVs rather than re-estimating S2/S3. Full graph-source rebinding is not a verified automatic chain. These are disclosed pipeline limits, not missing frozen evidence. No ARDL bounds/ECM generator is automatically appended.
