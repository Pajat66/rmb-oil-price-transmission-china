# Official data sources, use and acquisition

Source evidence reviewed 2026-10-14; licence/access documentation updated 2026-10-15. All ten retained source files are `OFFICIAL_SOURCE_VERIFIED` and `LOCAL_FILE_HASH_VERIFIED`. Earlier README, source_log, variable metadata, first-version Table 1/S1, and current Table 1/S1/S17 provide cumulative evidence. Lack of a dated download screenshot does not invalidate that provenance. Full byte-identical historical reacquisition is a separate question and was not repeated here.

[Per-input status](metadata/data_source_status.csv) records independent judgments. `REDISTRIBUTION_UNRESOLVED` never cancels verified origin. `RESEARCH_USE_EVIDENCED` for EIA/Customs describes supported scholarly use of officially disseminated statistics, not a verified private-data licence; FRED/NBS have explicit provider use terms.

## Input register

Paths are relative to an externally held raw directory. [Raw input contract](config/raw_inputs.json) retains exact expected filenames/hashes and was not edited. No provider raw export is added by this review.

| ID | Historical file | Coverage | SHA256 |
|---|---|---|---|
| `eia` | `01_eia_brent/EIA_brent_usd_monthly_1987-latest_2026.3.22.csv` | 1987-05–2026-02; study 1998-01–2026-02 | `2cf214d4194bae4486f26fe7a152439a847bd96a3fddb11d7697484f1383e03d` |
| `fred` | `02_fx_pbc_fred/FRED_exchus_cny_per_usd_monthly_1981-latest_2026.3.22.xlsx` | 1981-01 onward; study 1998-01–2026-02 | `6e71150a0559ffa71781a2c905d26daa45f939145b78545d20e8ee029a260136` |
| `cpi_98_15` | `03_nbs_price/98年-15年月度消费价格分类指数.xlsx` | 1998-01–2015-12 | `256fbf7171ce3adc9fa790f2c5ce5f28230ebcf18cec521a0e213655915b12cb` |
| `cpi_16_20` | `03_nbs_price/16年-20年月度消费价格分类指数.xlsx` | 2016-01–2020-12 | `18e94d7fc0ae88c5c71f302a8ba6db570f49da778a83795f59784a960015aff3` |
| `cpi_21_25` | `03_nbs_price/21年-25年月度消费价格分类指数.xlsx` | 2021-01–2025-12 | `e51f677e5bff02c56c4de152ab2b8ace512ad1bd8b15847b1ea0ee9dfd003c75` |
| `cpi_26` | `03_nbs_price/26年1-2月月度消费价格分类指数.xlsx` | study extension 2026-01–2026-02; file also retains overlapping months | `ec4be3293aea3c8e0107cbef08d432a105f77ad53d82622fd6db819321aef4d5` |
| `ppi` | `03_nbs_price/98年-26年2月工业生产者出厂价格指数.csv` | 1998-01–2026-02 | `030163d41bcf91c996ab3bb277b38b689b15e4fd82fb2084a28529c2fc4c661a` |
| `ppi_purchase` | `03_nbs_price/98年-26年2月工业生产者购入价格指数.csv` | 1998-01–2026-02 | `399daa3f59e88e2ab606227846fcffe3a4482008e9cbceb0192a940c00d312b6` |
| `iva` | `03_nbs_price/98年-26年2月规上工业增加值增长速度.csv` | 1998-01–2026-02 calendar; monthly 290 and cumulative 304 nonmissing | `c624ff1c473e2822958cdb9fbbe6bd7aac826315819bb738fcc6d922d481a386` |
| `customs` | `04_customs_trade/15年-26年2月月度原油进口量值数据.xlsx` | 2015-01–2026-02; 134 HS27090000 observations | `7f5118ac984400a80fe6253d92412ca971e17975774f77ba86e964d4f6617a06` |

The old source_log uses `.xls` names for four CPI files; actual registered files are `.xlsx`. Its combined 1998–2026 description is a family span, not the coverage of every CPI file. Actual export headers and current construction code govern. A filename containing 2026 does not exclude overlapping earlier columns.

## EIA Brent

Use [Europe Brent Spot Price FOB, RBRTE monthly](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RBRTE&f=M), not a futures price or a weekly/daily substitution. Select monthly frequency, download the series history, retain USD per barrel and the official monthly means; retain May 1987–February 2026 if reconstructing the historical file, then the code selects January 1998–February 2026 for this study. The original CSV contains four metadata rows before its Month/price header, the exact URL, a local time-of-day string and a Thomson Reuters source credit. Its filename/export metadata are not a proven full download date.

The [EIA notes](https://www.eia.gov/dnav/pet/TblDefs/pet_pri_spt_tbldef2.asp) identify Refinitiv/LSEG today and explain that monthly values are computed by EIA as unweighted daily closing-price averages. This does not overwrite the historical Thomson Reuters attribution. The [reuse policy](https://www.eia.gov/about/copyrights_reuse.php) broadly allows EIA information use/distribution while excepting protected private contributions. It supports documented statistical research; it is not a series-specific clearance to republish the historical CSV or every transformed observation. Those two redistribution modes remain unresolved. The author's independently drawn scientific figure is assessed separately.

## FRED / Federal Reserve Board EXCHUS

Open [EXCHUS](https://fred.stlouisfed.org/series/EXCHUS), set 1998-01-01 through 2026-02-01 and download monthly observations. Units are Chinese yuan per one US dollar, not the inverse; frequency is monthly, not seasonally adjusted. The publisher is the Board of Governors under G.5. Monthly data are averages of available daily observations; do not average an already monthly series again.

The series-level Public Domain: Citation Requested tag and [Board copyright notice](https://www.federalreserve.gov/disclaimer.htm) support research and observation sharing. The site-wide graph copyright banner does not replace the series-specific status. The included [extract](data/analysis_ready/fred_exchus_monthly.csv) retains the previously matched 338 observations. Cite the Board, EXCHUS, FRED, series URL and actual retrieval date when known; do not invent that date. This review did not repeat the 338-value comparison or substitute current observations.

## National Bureau of Statistics of China

Open [National Data](https://data.stats.gov.cn/) via the [NBS statistics site](https://www.stats.gov.cn/), choose monthly national data (月度数据), and select the exact indicators below with the complete January 1998–February 2026 calendar. Export in supported year/date batches if the portal limits the requested window. Preserve Chinese labels, units, original missing cells and any overlapping columns; the existing construction program handles the historical file layout.

| Study series | Exact export indicator | Unit and handling |
|---|---|---|
| CPI | 居民消费价格指数(上年同月=100) | YoY index, previous-year same month=100; join the four historical CPI periods |
| PPI | 工业生产者出厂价格指数(上年同月=100) | YoY index, not month-on-month or cumulative PPI |
| Total purchase price | 工业生产者购进价格指数(上年同月=100) | YoY index; needed for retained S2/S3 diagnostics |
| Fuel | 燃料、动力类购进价格指数(上年同月=100) | YoY index; distinct from total purchase price |
| Monthly industrial activity | 规模以上工业增加值同比增长 (original header may abbreviate to 规上工业增加值同比增长(%)) | Percent; 290 nonmissing observations in the current retained calendar |
| Cumulative industrial activity | 规模以上工业增加值累计增长 (original header may abbreviate to 规上工业增加值累计增长(%)) | Percent; 304 nonmissing; never substitute for missing monthly growth |

The original exports record database/time/indicator names. Original query IDs are not saved, and are not invented here. Labels, national monthly scope, dates and units provide an operational selection specification; a numerical query code is not itself a licensing prerequisite. A different contemporary export/vintage needs a documented comparison rather than relabelling it as the frozen file. This review inspected the exports and official instructions; it did not execute an interactive full-window re-download.

[NBS terms](https://www.stats.gov.cn/wzgl/202302/t20230217_1912857.html) explicitly permit downloading and using published statistics. They support reasonable, good-faith, free public quotation/reproduction with prominent NBS attribution and the NBS URL, subject to listed exceptions and preservation of meaning. They prohibit unauthorized onward authorization. Thus qualified unchanged quotation is conditionally permitted; putting NBS content under a new MIT/CC BY licence is restricted. Applicability of those terms to a complete computed monthly analysis table and its downstream reuse remains unresolved, rather than all NBS research use being unresolved. The selected provider-access delivery is recorded in [data delivery](data/README.md). NBS contact for scope clarification: info@stats.gov.cn, from the official terms.

## General Administration of Customs: HS27090000

Earlier source_log/variable metadata and Table 1/S1 identify monthly crude-oil imports from Customs. The retained historical workbook covers January 2015–February 2026, 134 HS27090000 observations; its registered SHA256 is `7f5118ac984400a80fe6253d92412ca971e17975774f77ba86e964d4f6617a06`. Its OOXML created/modified metadata are March 22, 2026 save clues, not proof of the original download date. Retain this research version. Select only HS27090000, 石油原油及从沥青矿物提取的原油. HS27102000 is another oil product and is excluded. 第一数量 is kilograms; 人民币 is yuan under the retained research definitions and conversion code. Secondary quantity/unit fields are incomplete and do not enter the study.

On October 14, 2026, the earlier comparison independently read the author's two newly supplied official-platform CSV exports. Year identification came from 数据年月. Each CSV contains 24 rows: 12 HS27090000 and 12 HS27102000 monthly observations. There are no duplicate month/HS keys, missing crude months or annual/subtotal rows. Both exports use a legacy Chinese encoding compatible with GB2312/GBK/GB18030; strict GB18030 parsing preserves quoted RMB thousands separators and an empty trailing field. Crude secondary quantity is 0 with a literal `?` unit marker and is not used. Original CSV bytes and the one supplied screenshot remain outside this public candidate.

All 24 crude-oil months, January 2015–December 2016, match the historical workbook exactly: 24 quantity integers and 24 RMB-amount integers, 48 comparisons with zero differences. Quantity / 10^7, RMB / 10^8 and RMB / kilograms were independently recalculated; the saved unit values differ only within the documented 16-significant-digit/binary64 serialization boundary. The newly calculated annual totals are 335,482,810,731 kg and RMB 832,597,383,483 for 2015, and 381,006,947,967 kg and RMB 771,121,789,669 for 2016.

The scoped statuses are `OFFICIAL_SELF_SERVICE_ACCESS_VERIFIED_2015_2016` and `OFFICIAL_MONTHLY_MATCH_VERIFIED_24_OF_24`. Acquisition was performed by the author using a normal browser, and the numerical audit was independent. The single 2016 screenshot directly shows the official platform name and stats.customs.gov.cn hostname, RMB and kilogram result columns, HS27090000/27102000, monthly 201601–201603 rows and 导出数据. Its first three crude rows match the supplied 2016 CSV. The import selector, full date window, partner selector and total-result count are outside the image. No 2015 screenshot was supplied. Trade-mode and registration-location fields show no specific subgroup selection (`NO_SPECIFIC_SUBGROUP_FILTER_DISPLAYED`); blank displayed fields do not independently establish every backend aggregation default.

Use [Customs statistics](https://stats.customs.gov.cn/) through [Customs public services](https://online.customs.gov.cn/). The author-tested selection specification is imports (进口), monthly observations, January–December 2015 and January–December 2016 separately, HS8=27090000, RMB amounts and first legal quantity in kilograms. For the intended national series avoid specific partner, trade-mode and registration-region filters and group by month and commodity. These are the documented retrieval settings, not reconstructed historical clicks. The national-import interpretation is supported by historical source/variable records, the author's flow/no-subgroup explanation, the 24-month exact match and the earlier annual crosscheck against the [2025 NBS yearbook national import table for 2024](https://www.stats.gov.cn/sj/ndsj/2025/html/C11-07.jpg): 55,323.1920435 ten-thousand tonnes and RMB 231,353,156.9382 ten-thousand yuan round to its published totals. That annual crosscheck was not repeated during the 24-month comparison and does not establish backend defaults for all years.

Follow the [tested selection and validation procedure](REPRODUCTION_GUIDE.md). An additional service application is not a prerequisite for the already acquired 2015–2016 observations. The [official statistical-service guide](https://online.customs.gov.cn/static/pages/guides/002029004002/002029004002.html) remains a fallback for a future unavailable vintage or a specific permission question. Earlier automated portal-access failures do not negate the author's successful exports. No service request has been sent by this review.

The other 110 months, January 2017–February 2026, were not newly exported and compared in C2. They retain the historical 134-month local-validation evidence; the uncovered full-calendar re-download comparison is not evidence of unreliable provenance. No claim of a fresh 134/134 official-monthly match is made. A later source revision must be compared and documented rather than replacing the historical input silently. Official obtainability and the author's right to redistribute raw files or full monthly derivatives remain separate: redistribution is unresolved, and no new third-party raw export or internal screenshot is included here.

## Conversion and vintage boundary

Keep raw inputs private and run only the retained construction code when scientific execution is separately authorized: [reproduction guide](REPRODUCTION_GUIDE.md). oil_rmb = Brent × EXCHUS; kilograms / 10^7 = 10,000 tonnes; CNY / 10^8 = 100 million CNY; import unit value = CNY / kilograms = 10 × value(100m CNY) / quantity(10,000 tonnes). Inflation is YoY index minus 100; stationary outcomes are adjacent calendar-month differences. Log movements are 100 times calendar log differences. Preserve reporting gaps, pre-sample dates and equation-specific lag/lead eligibility. Current source values may have been revised; no such replacement is made here.

## Final data-access transparency review (2026-10-15)

[DATA_ACCESS_MATRIX.csv](DATA_ACCESS_MATRIX.csv) lists every historical input, its observation range, official acquisition route, historical file SHA256, actual included materials and object-specific redistribution limits. It contains metadata, not the excluded observations. The public EXCHUS extract is the only deposited upstream monthly observation dataset. Existing original graphics and generated statistics are separate author contributions. No provider licence is expanded.

Static inspection finds code for constructing the Figure 2 values, calendar masks and outliers from the documented official series. It does not establish exact reconstruction from current public downloads: the preparation interface enforces ten historical whole-file hashes and historical layouts, whereas provider revisions or a differently packaged export fail that gate. The Figure 2 compatibility route also expects canonical/transformed CSVs, S1/S17/frame-registry files in an external historical layout and 39 saved primary design CSVs. Public registries/code describe these objects, but the separate design-construction entry point emits NPZ, so an end-to-end portable binding to that CSV interface is incomplete and untested. The tested frozen redraw instead uses an excluded 7774-row private plotting source.

No specific necessary monthly observation has been demonstrated to be irretrievably unavailable. Exact historical-vintage availability is unconfirmed, including the 110 Customs months not newly reacquired in the earlier check; raw/full-monthly-derivative redistribution remains unresolved for the listed EIA/NBS/Customs objects. Official routes and code specifications are not a claim that those observations are deposited or that fresh-data Figure 2 recovery has passed. This review did not download data, rebuild samples, execute models or redraw figures.
