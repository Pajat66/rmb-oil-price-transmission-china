# Data dictionary

Monthly dates form intact grids:1998-01–2026-02 long (338 rows), 2015-01–2026-02 customs (134 rows). Missing cells remain missing; lags/leads are constructed before exclusions, with no interpolation or adjacency compression. Source-file rights and hashes are in [Data sources](DATA_SOURCES.md).

| Variable | Meaning and source | Unit | Transformation and coverage | Use |
|---|---|---|---|---|
| month | Calendar month | Monthly date | Month-start date or YYYY-MM | All analyses |
| brent_usd | Europe Brent Spot Price FOB, EIA RBRTE; export credits Thomson Reuters | USD/barrel | Positive monthly level, long | Oil exposure, components, Figure2, S2 |
| cny_per_usd | FRED EXCHUS, Federal Reserve Board | CNY/USD | Monthly average NSA, long; increase means CNY depreciation | Oil exposure, components, Figure2 |
| oil_rmb | Brent×CNY/USD | CNY/barrel | Historical values preserved; blanks derived subject to identity check | Composite exposure, historical diagnostics |
| dlog_oil_rmb | Local-currency oil-price movement | 100 log points, approximate monthly percent change | 100[ln(P_t)−ln(P_t−1)], long | Primary LP, Link1, S15, S18 |
| dlog_brent, dlog_fx | Brent and FX movements | 100 log points | Corresponding100 calendar log differences, long | Components and current-coefficient equality tests |
| cpi_yoy | NBS CPI, previous-year same month=100 | Index | Long; not a price-level index | CPI, S2 |
| ppi_yoy | NBS producer ex-factory price index | YoY index, base100 | Long | PPI, S2 |
| ppi_purchase_yoy | NBS total producer purchase-price index | YoY index, base100 | Distinct from Fuel, long | Historical S2/S3 |
| ppi_fuel_power_yoy | NBS fuel-and-power purchase-price index | YoY index, base100 | Long | Fuel, S2 |
| cpi_inflation, ppi_inflation, ppi_purchase_inflation, fuel_power_inflation | Corresponding YoY index−100 | Percent YoY inflation | Long | Canonical and historical diagnostics |
| d_cpi_inflation, d_ppi_inflation, d_ppi_purchase_inflation, d_fuel_power_inflation | Adjacent-month change of YoY inflation | Percentage points | π_t−π_t−1; long first valid1998-02, 337 core observations | Formal LP, terminal CPI, Figure2, sensitivity |
| import_crude_oil_value_100m_rmb | China Customs HS27090000 crude-oil import value | 100million CNY | Customs calendar | Unit value, value diagnostics |
| import_crude_oil_qty_10k_ton | Customs crude-oil import quantity | 10, 000tonnes | Customs calendar | Unit value, quantity controls |
| import_crude_oil_unit_price_yuan_per_kg | Aggregate crude-oil import unit value | CNY/kg | 10×value(100m CNY)/quantity(10k tonnes) | Link1/2, terminal CPI |
| dlog_import_unit_price | Import unit-value movement | 100 log points | Calendar log difference; first valid2015-02 | Link1 dependent, Link2 exposure |
| dlog_import_quantity, dlog_import_value | Quantity/value movements | 100 log points | Corresponding calendar log differences, first valid2015-02 | Sensitivity, stationarity |
| indust_va_yoy | NBS monthly industrial value-added YoY growth | Percent | Observed monthly growth; January gaps retained | Historical diagnostics, S17; no primary industrial control |
| indust_va_cum_yoy | NBS cumulative industrial value-added YoY growth | Percent | Distinct cumulative series; not substituted for monthly growth | Historical S3, S17 |

The Customs ratio is an aggregate unit value, not a quality-adjusted market price. 100 log points approximate percent change; they are not exact arithmetic percent changes. LP coefficients measure percentage points of YoY-inflation change per one exposure unit.

Historic S2 aligned exposures use100[ln(P_t)−ln(P_t−12)] and original windows in src/science/phase2a9_core.py. They are historical diagnostic evidence. [S1 definitions](supporting_information/archive/csv/S1_Data_definitions.csv) and [S17](journal_submission/S17%20Table.xlsx) retain variable coverage and missingness.

Formal p2 starts1998-04, N=335−h. S18p1/2/3/4/6 starts1998-08, N=331−h. The initial2015-01 customs difference is missing because the prior month is outside its calendar. Equation-specific masks are in the [sample registry](supporting_information/archive/csv/S17_Final_sample_registry.csv) and [design seals](reference/registries/design_array_seals.json).

## Source/use and raw-unit clarification (R4B)

All ten inputs have verified official provenance and local hashes; research use and redistribution are separate in [source status](metadata/data_source_status.csv). Retain provider conditions when quoting observations. NBS onward licensing is restricted; EIA/Customs complete monthly sharing remains separately unresolved.

Customs workbook raw fields are 第一数量 in kg and 人民币 in CNY. Divide by 10^7 for 10,000 tonnes and by 10^8 for 100m CNY. Compute unit value as CNY/kg, equivalently 10 × canonical value/quantity. HS27102000 and incomplete secondary barrel fields do not enter the HS27090000 primary series. Acquisition and the 2015–2016 route are in [sources](DATA_SOURCES.md). These are documentation clarifications; no existing numerical value, variable or sample definition was changed.
