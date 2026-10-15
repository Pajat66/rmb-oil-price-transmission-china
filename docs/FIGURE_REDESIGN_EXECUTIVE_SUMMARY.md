# Figure 1–7 图件重设计执行总结

日期：2026-10-15。范围：仅视觉重设计、正式文件及本地候选同步；没有执行科研重估或发布。

## 正式基准与定位

本轮以 `R5_release_staging/rmb-oil-price-transmission-china/` 为当前正式仓库候选；投稿副本为其同级 `submission_package/main_figures/`。R4C/R4B/R3 目录、旧原始工作仓库及旧归档均为历史材料，未作为替换目标。图号和 `metadata/captions.json` 原样保留。

## 完成的重设计

| 图 | 旧图主要问题 | 正式改动 |
|---|---|---|
| 1 | 密集文字、细箭头、长外绕线、主支线层级接近 | 宏观/Customs 两通道；主 LP 明确突出；三项评估并行分流；推断标签与解释边界分层；短正交线及明显箭头 |
| 2 | 覆盖条与分布同色，箱体/离群点层级偏弱 | 按变量/样本区分覆盖条；强化箱体、中位数与完整离群点；以细规则线区分 A/B，保留原有真实月度分箱和箱线图 |
| 3 | 三个 outcome 配色重复，点与带层级不足 | Fuel/PPI/CPI 固定颜色与圆/菱/三角标记；较细区间边线、克制带色、强化估计线与零线；保留独立纵轴 |
| 4 | 两类比较辨识度不足，与图5相似 | 横向分组区间图；A 用 outcome 编码，B 用赭色菱形表示直接对比；统一零线与数字列对齐 |
| 5 | 与图4同为横向森林图，组件差别不够直接 | 两组件列 × 三 outcome 行的纵向区间小图；真实 horizon 位置、独立纵轴；实心圆/空心菱形；完整保留39格 equality q 矩阵 |
| 6 | 新颖图式已有，但瀑布/密度/区间识别层次偏弱 | 保留瀑布及26条脊线；赭色区分 lag 分解，Fuel/PPI 稳定配色；细密度轮廓、独立点/区间与清晰面板规则线 |
| 7 | 三类稳定性信息和解释文字视觉权重接近 | 系数条保留正负冗余编码；递归范围与初末点分层；正式 p/q 用空心圆/实心菱形；三模块标题规则线及 outcome 标签一致 |

Figure 1 的英文/数字词项从 **203 减为 156（减少 23.2%）**，文本对象由51减为41。主箭头线宽0.7→1.7 pt，箭头头部尺度6.5→12。连接线穿字检查为0；独立 Customs 支线和 primary 直接分支逻辑保留。原图详细措辞由方法文稿和保留的源代码历史承担，正文及 caption 未自动改写。图内仍有数据/样本/变量、主 LP、补充分析、HAC/MBB/FDR-Holm/DWB 及条件关联解释边界。

统一系统：Arial；面板10 pt、轴标签9 pt、刻度/图例8.5 pt，流程推断标签最低8 pt。白底、细结构线、明确零线；Fuel `#24675F`、PPI `#74556F`、CPI `#96732D`，辅以形状/位置/空实编码。配色按语义变化，避免七图同一蓝色模板。

## 数据对应关系保护

Figure 6 的混合 CSV 列含 `sum_0_3`，直接读取后 horizon 为字符串。QA 拦截了绘图接口按字典序排列的错误预览；正式脚本恢复冻结图和源表的数值 horizon 0–12 对应，并检查26组点/区间与密度行的绑定。没有改变研究数据排序定义、任何估计或置信区间，也没有重抽样。

## 已同步文件

- `figures/Figure 1–7.tif` 及对应 `.png/.svg/.eps`，共28个正式输出。
- 同级 `submission_package/main_figures/Fig1–7.tif`，与仓库 TIFF 逐字节一致。
- `src/plotting/figure1_plot.py` 至 `figure7_plot.py`、`visual_system.py`；入口 `scripts/render_figures.py`；兼容入口说明 `scripts/export_figures.py`。
- `metadata/figure_index.json`、`manuscript_to_files.csv`、`figure_export_status.json`、`public_file_manifest.csv`、`validation/checksums/files.json`、投稿 `upload_manifest.csv`、必要 README/图件说明/许可路径索引。
- 现有本地 `rmb-oil-price-transmission-china-v2.0.0-prepared.zip` 及其既有外部校验索引一并刷新；没有创建发布版本、提交 Git 或操作外部服务。

## 明确未改动

冻结数据及统计结果 CSV、NPZ/bootstrap 路径、科学估计模块、模型/样本/分组定义、显著性与结论、Table/SI 全部内容、正文 DOCX/PDF、caption 注册与图号均未改动。私有 Figure 2 月度源、QA 截图/裁剪/色弱模拟、内部脚本和 render receipts 均未加入公开候选。旧 R5 Git tree/diff 报告是重设计前快照，Git 原有暂存区保持原状。
