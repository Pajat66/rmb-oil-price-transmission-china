# Raw data sources

Raw source files are preserved as originally collected and should not be modified during reproduction.

| Provider | Original file(s) | Variable(s) | Unit / coverage | Purpose and processing notes |
| --- | --- | --- | --- | --- |
| EIA | `01_eia_brent/EIA_brent_usd_monthly_1987-latest_2026.3.22.csv` | `brent_usd` | USD per barrel; source coverage starts in 1987 | Monthly Brent price. The first four rows are source metadata before the data table. |
| FRED | `02_fx_pbc_fred/FRED_exchus_cny_per_usd_monthly_1981-latest_2026.3.22.xlsx` | `cny_per_usd` | CNY per USD; monthly sheet | Used with Brent to construct `oil_rmb`. |
| NBS China | `03_nbs_price/*.xlsx` and `*.csv` | CPI, PPI, purchase-price, fuel/power purchase-price, industrial value added | Monthly; manuscript sample uses 1998-01 to 2026-02 | CSV inputs are GBK-encoded and have source-description rows skipped by construction scripts. |
| China Customs | `04_customs_trade/15年-26年2月月度原油进口量值数据.xlsx` | Import quantity and RMB value | Monthly, 2015-01 to 2026-02 | Commodity code 27090000 is used to construct quantity, value, and import unit price. |
| BIS | `05_backup_bis_worldbank/China's Nominal Effective Exchange Rate.xlsx`; `China's real effective exchange rate.xlsx` | Effective exchange-rate backups | As supplied | Backup/cross-check material only where applicable. |
| World Bank | `05_backup_bis_worldbank/(back_up)CMO-Historical-Data-Monthly.xlsx` | Commodity-price backup | As supplied | Backup/cross-check material only where applicable. |

Provider licensing, access, and reuse conditions remain applicable to these files.
