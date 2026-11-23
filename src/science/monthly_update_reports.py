"""Chinese, data-backed reports for the October 2026 private data release."""
import pandas as pd

import monthly_update as u


def mdtable(headers, records):
    def cell(v):
        return str(v).replace("|", r"\|").replace("\n", " ")
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *["| " + " | ".join(cell(x) for x in row) + " |" for row in records],
    ])


def dictionary(audit, paths, counts, historical, reference):
    records = []
    for name, (label, unit, ids, file, downstream) in audit.VARIABLES.items():
        for sample in ("long", "short"):
            row = counts[(counts["sample"] == sample) & (counts.variable == name)]
            if row.empty:
                continue
            current = row.iloc[0]
            if name in audit.YOY:
                previous = audit.yoy(audit.canonical(historical[sample], sample),
                                     audit.canonical(historical["long"], "long") if sample == "short" else None)
            elif name in historical[sample]:
                previous = audit.canonical(historical[sample], sample)
            else:
                previous = reference[sample]
            prior = previous.loc[previous[name].notna(), "month"] if name in previous else pd.Series(dtype="datetime64[ns]")
            historical_paths = "; ".join(paths[i].parent.name + "/" + paths[i].name for i in ids.split(";") if i)
            if name in {"oil_rmb", "dlog_oil_rmb"}:
                historical_paths = "详见 brent_usd 与 cny_per_usd"
            reader = "raw_readers.py → monthly_update.py"
            if name in audit.POSITIVE or name in audit.INFLATION or name.startswith("d_"):
                reader = "transformation_layer.transform"
            elif name in audit.YOY:
                reader = "monthly_update_audit.yoy；复用 phase15_common.calendar_lag"
            elif name == "oil_rmb_source":
                reader = "canonical_layer.build_oil_rmb"
            elif name in {"oil_rmb", u.QTY, u.VAL, u.UV}:
                reader = "monthly_update.reconcile"
            records.append(dict(variable=name, sample=sample, raw_field_or_formula=label, unit=unit,
                                frequency="月度", historical_span=(f"{prior.min():%Y-%m}–{prior.max():%Y-%m}" if len(prior) else ""),
                                historical_valid=len(prior), updated_first=current.first_valid, updated_last=current.last_valid,
                                updated_valid=int(current.valid_n), missing_n=int(current.missing_n),
                                historic_file_in_data_01_raw=historical_paths,
                                new_file_in_data_New=file if file else ("Brent × EXCHUS；见两输入" if name in {"oil_rmb","dlog_oil_rmb"} else ""),
                                transformation_or_reader=reader, actual_consumers=downstream))
    return pd.DataFrame(records)


def write(text, report, audit, tables, candidate, records, ready):
    revisions = records.loc[records.changed & (records["sample"] == "short") &
                            records.variable.isin([u.KG, u.CNY, u.UV])]
    unit_comp = mdtable(("月份", "指标", "单位", "旧值", "新版", "新版减旧版", "相对差异"), [
        (r.month, r.variable, r.unit, f"{r.old_value:,.10g}" if r.variable == u.UV else f"{r.old_value:,.0f}",
         f"{r.final_value:,.10g}" if r.variable == u.UV else f"{r.final_value:,.0f}",
         f"{r.delta_new_minus_old:+,.10g}" if r.variable == u.UV else f"{r.delta_new_minus_old:+,.0f}", f"{r.relative_pct:+.6f}%")
        for r in revisions.itertuples()
    ])
    text(report / "DATA_REVISION_COMPARISON.md", f"""# 2026-10 数据对账

## 重叠期

[逐月逐字段对账](overlap_comparison.csv)有 {len(records)} 行，覆盖两套样本内的新旧文件重叠、2025-10—2026-02 指定窗口及差异传递到旧版模型变换的单元格。incoming_value 是新文件值或根据新文件因子算出的值。final_value 是本轮入表值。新版减旧版保留符号，绝对差为其绝对值，相对差为 (新版−旧版)/旧版×100%，零分母和缺数留空。

- EIA RBRTE 在研究日历内 338 个旧月与新版一致。FRED 的新导出从 2026-01 起，两个重叠月一致。
- PPI、总购进及燃料动力从 2025-10 起有 5 个重叠月。全国 CPI、交通通信和核心 CPI 工作簿的说明行写 2025-10 起，实际列头从 2026-01 开始，两个重叠月均一致。2025-10—12 CPI 三列保留历史值。
- 两个工业工作簿包含同一当月、累计指标。新旧同时有值的重叠月份，当月指标 3 个，累计指标 4 个，逐值一致。2026-02 当月为空、累计 6.3%。2026-01 在新工作簿无日期列，两项均保留 NA。[国家统计局 1—2 月发布]({u.IVA_FEB})
- 海关 CSV 从 2026-01 起，故 2025-10—12 沿用旧值。数量、金额、单位价值的重叠差异出现在 2026-01/02。详表包含原始 kg/CNY 以及转换后的万吨/亿元和相关月度对数变动。

{unit_comp}

## 海关取舍依据

旧工作簿和新 CSV 对齐 HS27090000、品名、YYYYMM、第一计量单位千克、人民币金额与月×商品唯一键。新文件 20 条明细，原油 10 条，每月一条。第二计量单位桶仅做核验；剔除另 10 条 HS27102000。两个重叠月的 HS27102000 原始数量与金额四个值完全一致。对 2026-10 及 1—10 月合计的新量额，换算舍入后与公开全国进口表的转载一致。此项只用于方向和全国合计量级的旁证。[海关查询入口]({u.CUSTOMS_LINK}) · [总量旁证](https://www.gotohui.com/trade/list/191970.html)

依据作者说明的官方进口导出、历史进口定义和上述核对，更新了 HS27090000 在 2026-01 和 02 的量额，旧值留在对账表。CSV 未携带查询方向、贸易伙伴、贸易方式、登记地域选择或修订日志。无法判定差额由修订、统计时点或其他查询因素造成，标记为**未确认差异**。若需将差额定性为官方修订，可核对原导出的查询凭证或发布方修订说明。
""")
    coverage = tables["variable_coverage"]
    key_names = ["brent_usd","cny_per_usd","oil_rmb",*u.CPI_FIELDS,"ppi_yoy","ppi_purchase_yoy","ppi_fuel_power_yoy",
                 "indust_va_yoy","indust_va_cum_yoy",u.KG,u.CNY,u.UV]
    key_coverage = coverage.loc[coverage.variable.isin(key_names) & (coverage.layer == "model")]
    summary = mdtable(("样本", "变量", "首月", "末月", "有效", "缺失", "结构性", "历史来源缺口"), [
        (r.sample, r.variable, r.first_valid, r.last_valid, r.valid_n, r.missing_n, r.structural_n, r.historical_n)
        for r in key_coverage.itertuples()
    ])
    selected = tables["outlier_flags"]
    recent = selected.loc[(selected["sample"] == "long") & (selected.month > u.OLD_END) &
                          selected.variable.isin(["dlog_brent", "dlog_oil_rmb"])]
    outlier_md = mdtable(("月份", "字段", "变动（100 对数点）", "稳健 Z"), [
        (r.month, r.variable, f"{r.movement:.2f}", f"{r.robust_z:.2f}") for r in recent.itertuples()
    ])
    official = mdtable(("变量", "2026-10 证据值", "发布方来源"), [
        (key, value, f"[数据发布]({link})") for key, (value, link) in u.OFFICIAL.items()
    ])
    text(report / "DATA_QUALITY_REPORT.md", f"""# 数据质量审计 · 2026-10

长表 1998-01—2026-10，346 月 × {len(candidate['long'].columns) + 1} 列。短表 2015-01—2026-10，142 月 × {len(candidate['short'].columns) + 1} 列。列数含 month；短表增加两列工业指标及两列原始量额，保留旧短表全部变量。主表 month 是无时区 Excel 月初日期，缺值为空，数据列均为存储数值。

- [逐项自动验收与状态](DATA_PIPELINE_VALIDATION.md) · [全部变量覆盖与缺失比例](variable_coverage.csv) · [逐月缺失原因](missing_months.csv)
- [原始文件的工作表、行列、元数据、来源和 SHA-256](../../manifests/2026-10/SOURCE_LEDGER.csv) · [逐指标的原始列名、数据行、单位、日期、交集和有效值](raw_new_profile.csv)
- [历史快照逐文件、工作表、变量、维度和有效数](baseline_inventory.csv) · [差异报告](DATA_REVISION_COMPARISON.md)

## 关键字段覆盖

{summary}

核心 CPI 沿用仓库列名 core_cpi_proxy_yoy，值来自全国扣除食品和能源指数。早于 2021-01 的月份无原研究来源值。工业当月同比是实际增长率，累计同比按年内累计；2005 年及以后 1 月、2013 年及以后 2 月当月缺口按已知发布制度标注。更早或其他月份的源文件空缺列为历史来源缺口，保留核验空间。两份最新工业文件都无 2026-02 当月的 23。2011 年调查规模门槛和行业分类说明随原始脚注保留。[国家统计局关于 2005 年发布制度调整](https://www.stats.gov.cn/zs/tjwh/tjkw/tjqk/zgxxb/202510/P020251013338528565175.pdf)

交通通信的历史指标跨统计分类名称变化，沿用原代码明确的全国总类标签映射。2026 年官方 CPI 基期轮换记录在发布附注。交通通信细分类补充表六项已逐项检查。PPI、购进及燃料动力均为上年同月=100，主模型先减 100 得同比百分比，再作相邻月差，响应单位是百分点。 [统计局 CPI 发布及附注](https://www.stats.gov.cn/sj/zxfbhjd/202611/t20261109_1965795.html)

## 2026-10 发布值交叉核验

{official}

## 异常波动

对月份相邻变动，计算稳健 Z = 0.67449×(值−中位数)/MAD，标记 |Z|>3.5。长短样本分别取自身中位数和 MAD。未为这些标记改值。见[逐项异常标记](outlier_flags.csv)。

{outlier_md}

Brent 与人民币油价 2026 年显著变动依据实际月度数据。海关单位价值反映实际进口组合的合计比值，量值及报价冲击在机制模型中用途不同。正式样本可用性见[模型准备报告](MODEL_INPUT_READINESS.md)。
""")
    readiness = ready.loc[ready.model.isin(["PRIMARY_d_fuel_power_inflation", "MECH2_d_fuel_power_inflation_quantity1",
                       "MECH1_OIL_IMPORT_p3", "S18_p6_d_fuel_power_inflation"]) & ready.h.isin([0,3,6,12])]
    last_months = mdtable(("模型", "h", "旧 N", "新 N", "首个起点", "最后冲击起点", "最后响应月", "新增加起点", "2026-03 后新增起点"), [
        (r.model, r.h, r.old_n, r.n, r.start, r.end, r.last_response_month, r.added_origins, r.newly_observed_origin_count)
        for r in readiness.itertuples()
    ])
    text(report / "MODEL_INPUT_READINESS.md", f"""# 模型输入与下一轮运行顺序

## 已验证的读入

原模型的数据层实际读取新版 [canonical/transformed CSV](../../processed/2026-10/01_data/)，沿用原列名和日历查找。两份 XLSX 为数值主表，模型入口读取的是 CSV。已经运行原 build_design、build_link1 和 S18 common_designs.construct 计算列、滞后和响应资格，无估计量或重抽样。见[模型逐期变量、样本日期、N、月份哈希](model_input_eligibility.csv)。

- 主模型 Fuel/PPI/CPI 使用 dlog_oil_rmb，滞后 1、2 的冲击和各自因变量，响应为各同比通胀差分 t+h。油价和 FX 分解使用当期 dlog_brent 与 dlog_fx，同时保留合成冲击滞后。合成冲击单位 100 对数点，未经 Z 标准化。
- Link1 使用进口单位价值的月度对数变动，解释变量为人民币 Brent 的当月及滞后 1—3；数量敏感性 q=0 或 q=1。Link2 对 Fuel 和 PPI 分别用进口单位价值冲击，另有当期进口数量变动规格。终端 CPI 用进口单位价值或 Fuel/PPI 变化作为各自冲击。
- S18 在同一 h 使用 pmax=6 的有效日历，同时覆盖三种响应和 p=1/2/3/4/6。历史 S2 对齐同比使用 100×log(t/t−12)，短样本的 Brent 和汇率同比可使用长样本早期基数，海关三项只从 2016-01 起可算同比。支持性旧 Table 3/S3 的累计工业增加值仍有真实缺口。BIS NEER、BIS REER、World Bank Brent 未绑定当前正式模型或备选方程的数据入口。
- 稳定性主模型沿用逐期设计；h=0/3/6 的正式断点网格，h=0/3/6/12 的递归/滚动，窗口 120/96/144 月。短样本的机制诊断保持自己的窗口约束。S15 在 h=0 设计上加未来油价 1—3 期，正向各项和联合检验共用三前导样本；反向预测按前导分别核算。

{last_months}

每个 h 的全样本资格比旧版多 8 个起点，其中一部分是旧日期因新增响应而获得资格。h=12 主 LP 最后起点是 2025-10，其对应响应才是 2026-10。期别与累计路径也需遵守各自的共同资格条件。

[稳定性窗口和分段资格](stability_window_eligibility.csv)记录滚动、递归窗口数、断点候选数及机制两侧 N。新版 Link2 固定 h=0 中位日期分段后，h=11/12 的后段仍小于 60，原规则跳过两侧比较；全样本及滚动窗口有可用数据。[Table 3 历史规格](historical_table3_eligibility.csv)记录三类价格、各滞后阶数、固定与可变样本以及缺失月份。

## 阻塞和后续运行顺序

1. **确认两套数据基线和新增配置。** 旧版对照使用 [baseline_inventory.csv](baseline_inventory.csv)、冻结原始哈希、reference/registries/design_array_seals.json、旧统计结果与 SI。原 prepare-data 固定 338/134 月，并限制外部路径和冻结原始哈希。为扩样另设有日期和场景的外部工作目录，复制本次 01_data 专用 CSV，以本版本哈希绑定新版，保留旧密封。src/science/interface.py 的 prepare_designs 会对旧 X/Y seal 作精确比较，需新增明确的新入口/模式和独立的新设计回执。scripts/construct_designs.py 还要求旧六对象 data-gate 结构，不能把本次输出清单冒充该回执。
2. **复核设计和对照策略。** 在原始旧版、旧终点加新版来源两套 2026-02 子样本，以及全样本 2026-10 数据上比对变量、日历、列序与掩码。先比较旧版复现的月份、N、X/Y 封签或可解释的序列化差异。对海关分别比较旧/新两个重叠月带来的差分变化，再在相同来源规则下比较八个月扩样效应。主模型 h=0—12 用相同模型定义逐期对比。
3. **后续经授权运行估计及推断。** src/science/main_estimation.py、phase2b_core.py、phase2b_diagnostics.py、inference_ledger.py。先主 LP/Link1/Link2/终端 CPI/分项，后 HAC 与累计路径协方差、共同月历 moving-block bootstrap 和配对层级比较。冻结设定主 HAC max(12,h+1)、替代 max(6,h+1) 与 12+h，MBB 5,000 次、L=12/6/18、seed=20261004。按原 policy JSON 逐族复核 BH-FDR、Holm、有效重抽样数、配对有效样本和各自校正判定。保存 raw p、调整 p、CI、N，核对显著性阈值、各 horizon 方向和跨层响应差值。旧冻结回归核对只在旧版要求相等；新样本的 N、日期、系数和统计结论应由新证据产生。
4. **后续稳定性与 S18。** src/science/stability_estimation.py 从正式主 LP CSV 设计读取，依赖主 LP 写出的逐期设计与 Link1 设计、phase2c 策略。依次完成断点/参数检验、窗口和机制稳定性、S15、汇总；断点为依赖型 wild Bootstrap，和主 LP MBB 是不同的推断环节。将固定日期的锚点与原意核对。scripts/s18_stage1.py → scripts/s18_stage2.py → scripts/s18_stage3.py，Stage1 的旧 p2 注册及系数对照须区分“旧版复现”和“同一新版样本比较”；Stage2 核对设计和共同抽样，Stage3 当前固定模板假定 5,000 尝试且零拒绝，须按实际执行报告绑定。先确认 IC、共同样本、配对检验族、修正量及抽样记录，再导出 S18。
5. **后续表件、SI、图件。** scripts/assemble_tables.py + src/science/table_assembly.py → scripts/export_tables.py，依赖新的统计 CSV、canonical/transformed、注册和政策。Table 1 有旧终点的脚注，Table 6 有固定旧判定。S1 变量定义及 S17 需重新派生样本与缺失统计；S2/S3 在组表时导入历史诊断证据，决定是否保留历史范围或另行按原规格重估。scripts/export_supplementary.py 是冻结复制入口；scripts/package_si.py 按元数据拆表，须明确绑定新版原件。S1 Data 已提交工作簿包含数据和 Figure 2 支持页，另行交付新版时保留原证据和必要权限。核对 metadata/si_file_mapping.csv、metadata/table_input_mapping.json 与实际表名。核对 Figure 2 缺失、样本长度与分布，Figure 3–7 的系数/区间/校正/窗口与同版 CSV、NPZ；先校验源再导出外部新文件。

## Figure 1–7 数据血缘

| 图件 | 程序、统计产物和适配 |
| --- | --- |
| 1 | 当前 main 实际来自作者修订 PDF（metadata/figure1_canva_validation_20261104.json）。历史工程绘图为 src/plotting/figure1_plot.py。工作流无回归输入，如图面日期、样本量或设计标注受影响则同步核对。 |
| 2 | src/plotting/figure2_plot.py。冻结出图源为私有 7,774 行 figure_2_source.csv（外部历史 05_revision/04_final_figures 等路径），不同于提交 S1 的 5,070 行 Fig2_observations。构造新源需本版 canonical/transformed、S1/S17、样本注册及 39 个主 LP 设计 CSV。当前构造和绘图固定 338/134、2026-02 等，且 construct_designs.py 输出 NPZ，须重绑格式和日期。 |
| 3 | src/plotting/figure3_plot.py ← figures/source/figure_3_primary_lp_period_source.csv ← 主 LP 时点系数、HAC/MBB 区间及多重检验。 |
| 4 | src/plotting/figure4_plot.py ← figure_4_cumulative_contrasts_source.csv ← 累计路径和配对层级检验，联合使用相同重抽样。 |
| 5 | src/plotting/figure5_plot.py ← figure_5_brent_fx_components_source.csv ← lp_composite_components.csv、分项相等限制及协方差诊断。 |
| 6 | src/plotting/figure6_plot.py ← figure_6_import_cost_innovative_source.csv、mechanism_link1_final.csv、phase2b_bootstrap_paths_short_L12.npz ← Link1/Link2 及进口单位价值数据。 |
| 7 | src/plotting/figure7_plot.py ← figure_7_temporal_stability_source.csv、figure_7_temporal_stability_recursive_summary.csv ← 稳定性、共同端点及递归/滚动结果。代码有至 2026-02 的固定轴和固定起点。 |

scripts/render_figures.py 的 source/statistics/bootstrap 默认指向冻结参考。替换数据源时逐一核验绑定，沿用 docs/visualization/FIGURE_STYLE_GUIDE.md、VISUAL_REFERENCES.md 和论文单位。下一轮需重新评估上中下游响应层级、持续期、分项约束、进口机制和时间稳定性。当前结果只确认可用数据与样本。
""")
    text(report / "REPRODUCE_202610.md", """# 复建和验证 2026-10 数据

在仓库根目录运行。已核对环境 Python 3.8.6、pandas 2.0.3、numpy 1.24.4、openpyxl 3.1.5、xlrd 2.0.2。xlrd 负责 EIA 的二进制 XLS。日志、输出和源码哈希见 [manifest](../../manifests/2026-10/PIPELINE_MANIFEST.json)。

~~~powershell
python -B -X utf8 scripts/rebuild_monthly_202610.py
python -B -X utf8 scripts/rebuild_monthly_202610.py --check
~~~

第一次命令将冻结读取器、2026-10 源读取、对账、数值输出、独立公式校验和原设计的资格检查在两个临时目录完整运行。通过后发布本期文件。第二条命令仅比较在隔离目录重建的文件哈希与当前产物。CSV 和 XLSX 的日期、排序、字段、数值和精度配置为固定值。跨库版本如需逐字节复现，先对齐运行库。

更新期文件哈希位于 [monthly_update_202610.json](../../../config/monthly_update_202610.json)，字段映射位于 [monthly_update.py](../../../src/science/monthly_update.py)，冻结历史路径/哈希位于 [raw_inputs.json](../../../config/raw_inputs.json)。9 份输入的范围和说明在 [来源台账](../../manifests/2026-10/SOURCE_LEDGER.csv)。本地验收会读取上层投稿目录的已提交 S1、历史工作区的 canonical/transformed CSV 和 Git 中有删档记录的 S1 blob，保留工作区原始布局。若更换数据文件或改变统计口径，先审查目标月份、单位、键结构、官方核验值和政策，再开启新版本。

新版主表、最接近正式入口的 canonical/transformed、Phase2A9 同比兼容 CSV 位于 [processed/2026-10](../../processed/2026-10/)。运行步骤只执行数据重建和纯设计检查。本地生成文件含来源观测，沿用项目已有的私有数据保管范围。
""")


def validation_report(checks, counts):
    table = mdtable(("状态", "检查项", "证据"), [(r["status"], r["check"], r["detail"]) for r in checks])
    return f"""# 数据管线自动验收

**PASS {counts['PASS']} · WARNING {counts['WARNING']} · FAIL {counts['FAIL']}**

两次隔离运行验证同一快照的可复现性。断言覆盖原始结构、数值、日历、覆盖、单位、独立公式、实际文件读回和模型设计掩码。结果表的每行是一项检查。资料性 WARNING 说明差异原因未确证、历史缺失和未来执行路径约束。任何 FAIL 均阻止发布计算完成的版本。详见 [机器可读记录](validation_checks.csv) 和 [运行说明](REPRODUCE_202610.md)。

{table}
"""

