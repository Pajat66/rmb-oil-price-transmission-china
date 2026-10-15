# Figure 1–7 正式脚本清单

主入口：[`scripts/render_figures.py`](../scripts/render_figures.py)。公共视觉规范：[`src/plotting/visual_system.py`](../src/plotting/visual_system.py)。入口只绘图，不执行模型拟合或重新抽样。

| 图 | 正式绘图模块 | 冻结输入 |
|---|---|---|
| Figure 1 | [figure1_plot.py](../src/plotting/figure1_plot.py) | `模块内流程图定义，无统计点数据` |
| Figure 2 | [figure2_plot.py](../src/plotting/figure2_plot.py) | `外部私有 figure_2_source.csv，7774行；未加入候选` |
| Figure 3 | [figure3_plot.py](../src/plotting/figure3_plot.py) | `figures/source/figure_3_primary_lp_period_source.csv` |
| Figure 4 | [figure4_plot.py](../src/plotting/figure4_plot.py) | `figures/source/figure_4_cumulative_contrasts_source.csv` |
| Figure 5 | [figure5_plot.py](../src/plotting/figure5_plot.py) | `figures/source/figure_5_brent_fx_components_source.csv` |
| Figure 6 | [figure6_plot.py](../src/plotting/figure6_plot.py) | `figures/source/figure_6_import_cost_innovative_source.csv + reference/statistics/mechanism_link1_final.csv + reference/bootstrap/phase2b_bootstrap_paths_short_L12.npz` |
| Figure 7 | [figure7_plot.py](../src/plotting/figure7_plot.py) | `figures/source/figure_7_temporal_stability_source.csv + figure_7_temporal_stability_recursive_summary.csv` |

调用示例（需 Arial，Python 3.12 和项目依赖；输出目录必须为空且位于候选之外）：

```text
python -B scripts/render_figures.py --figure 3 --output-dir /external/figure3
python -B scripts/render_figures.py --figure 2 --figure2-source /private/figure_2_source.csv --output-dir /external/figure2
```

Figure 6 仅读取已有5000条路径并沿用 Scott KDE、2048网格点及每 horizon 归一化高度，不重新 bootstrap。Figure 2 的历史 build_sources/--work-dir 兼容路线本轮未调用。

`export_figures.py` 保留为5–7的兼容入口；本轮四格式正式导出统一使用 render_figures.py。同路径旧视觉实现已被替代，可从已有 Git/历史 R4 候选追溯；未在当前候选添加旧版、draft 或临时脚本。科学估计模块及 SI 绘图模块未修改。
