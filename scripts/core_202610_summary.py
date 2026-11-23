"""Exports for the October 2026 core comparison."""
from hashlib import sha256
import json

import numpy as np
import pandas as pd

KEYS = ["model", "horizon"]
LABELS = {"d_fuel_power_inflation": "Fuel", "d_ppi_inflation": "PPI", "d_cpi_inflation": "CPI"}
WORDING = {"ROBUST_ASSOCIATION": "稳健", "SUGGESTIVE_ASSOCIATION": "提示性", "NO_CLEAR_EVIDENCE": "证据不足"}


def primary_intervals(bundle):
    """Apply the frozen inference ledger rule to period and cumulative LP responses."""
    frames = []
    periods = bundle["period"]
    for is_cumulative in (False, True):
        prefix = "cumulative" if is_cumulative else "period"
        point = "cumulative_effect" if is_cumulative else "coefficient"
        result = bundle[prefix].copy()
        result["estimate"] = result[point]
        if is_cumulative:
            result = result.merge(periods[[*KEYS, "outcome", "shock", "N", "sample_start", "sample_end"]],
                                  on=KEYS, validate="one_to_one")
        bootstrap = bundle[prefix + "_boot"]
        sensitivity = bundle["cumulative_sensitivity" if is_cumulative else "sensitivity"]
        result = result.merge(bootstrap.loc[bootstrap.block_length.eq(12)].drop(columns=["outcome", point]),
                              on=KEYS, validate="one_to_one")
        for label, draws, lo, hi in [
            ("mbb", bootstrap, "bootstrap_ci_low", "bootstrap_ci_high"),
            ("hac", sensitivity, "hac_ci_low" if is_cumulative else "ci_low",
             "hac_ci_high" if is_cumulative else "ci_high"),
        ]:
            signs = draws.merge(result[[*KEYS, "estimate"]], on=KEYS, validate="many_to_one")
            signs["stable"] = ((signs[lo] > 0) | (signs[hi] < 0)) & (
                np.sign(signs[lo]) == np.sign(signs.estimate))
            stable = signs.groupby(KEYS).stable.all()
            result = result.merge(stable.rename(label + "_stable").reset_index(), on=KEYS, validate="one_to_one")
        stable = result.mbb_stable & result.hac_stable
        bootstrap_signal = (result.bootstrap_ci_low > 0) | (result.bootstrap_ci_high < 0)
        result["allowed_wording"] = np.select(
            [result.fdr_q.lt(.05) & stable, result.raw_p.lt(.05) | bootstrap_signal],
            ["ROBUST_ASSOCIATION", "SUGGESTIVE_ASSOCIATION"], default="NO_CLEAR_EVIDENCE")
        result["robustness_status"] = np.where(stable, "STABLE_HAC_AND_BLOCK_CI", "SENSITIVITY_OR_IMPRECISION")
        result["bh_reject_5pct"] = result.fdr_q.lt(.05)
        result["holm_reject_5pct"] = result.holm_p.lt(.05)
        result["response_end"] = (pd.PeriodIndex(result.sample_end, freq="M")
                                  + result.horizon.to_numpy()).astype(str)
        result["response_type"] = prefix
        result["claim_id"] = result.model + "_" + prefix + "_h" + result.horizon.astype(str)
        frames.append(result.drop(columns=point))
    return pd.concat(frames, ignore_index=True)


def stack(cases):
    return pd.concat([df.assign(scenario=name) for name, df in cases.items()], ignore_index=True)


def prior_deltas(table, indices, fields):
    """The first difference isolates revision, and the second isolates extension."""
    out = table.copy()
    out["comparison_to"] = out.scenario.map({"revised_overlap": "old", "full_new": "revised_overlap"})
    prior = out[["scenario", *indices, *fields]].rename(columns={
        "scenario": "comparison_to", **{field: field+"_prior" for field in fields}})
    out = out.merge(prior, on=["comparison_to", *indices], how="left", validate="many_to_one")
    for field in fields:
        out["delta_" + field] = out[field] - out.pop(field+"_prior")
    return out


def write_table(frame, folder, name):
    frame.to_csv(folder / name, index=False, encoding="utf-8-sig", lineterminator="\n")


def export(folder, primary, link1, link2, link1_dates, gate, hashes, environment, policy):
    lp = {k: primary_intervals(v) for k, v in primary.items()}
    left, right = lp.values()
    numeric = ["estimate", "N", "hac_se", "hac_ci_low", "hac_ci_high", "raw_p", "fdr_q",
               "holm_p", "bootstrap_se", "bootstrap_ci_low", "bootstrap_ci_high", "bootstrap_p",
               "valid_draws", "failed_draws", "hac_z"]
    for frame in (left, right):
        frame["hac_z"] = frame.estimate / frame.hac_se
    carry = ["sample_start", "sample_end", "response_end", "bh_reject_5pct", "holm_reject_5pct",
             "allowed_wording", "robustness_status", *numeric]
    keys = ["outcome", *KEYS, "response_type"]
    paired = left[keys + carry].merge(right[keys + carry], on=keys, suffixes=("_old", "_new"),
                                    validate="one_to_one")
    for field in ("estimate", "N", "hac_se", "bootstrap_se"):
        paired["delta_" + field] = paired[field+"_new"] - paired[field+"_old"]
    paired["hac_se_pct_change"] = 100 * paired.delta_hac_se / paired.hac_se_old
    paired["bh_decision_changed"] = paired.bh_reject_5pct_old.ne(paired.bh_reject_5pct_new)
    paired["robustness_class_changed"] = paired.allowed_wording_old.ne(paired.allowed_wording_new)
    write_table(paired, folder, "primary_lp_comparison.csv")
    joint = stack({k: v["joint"] for k, v in primary.items()})
    write_table(joint, folder, "primary_joint_tests.csv")

    dated = {}
    for scenario, table in link1.items():
        dated[scenario] = table.assign(sample_start=link1_dates[scenario][0], sample_end=link1_dates[scenario][1])
        matrix = dated[scenario]
        matrix["bh_reject_5pct"] = matrix.fdr_q.lt(.05)
        matrix["holm_reject_5pct"] = matrix.holm_p.lt(.05)
    link1_table = prior_deltas(stack(dated), ["model", "maxlags", "record_type", "term"],
                               ["coefficient", "hac_se", "wald_chi2", "N"])
    write_table(link1_table, folder, "customs_link1.csv")

    link2_summary = {k: primary_intervals(v) for k, v in link2.items()}
    link2_table = prior_deltas(stack(link2_summary), [*KEYS, "response_type"], ["estimate", "hac_se", "N"])
    write_table(link2_table, folder, "customs_link2.csv")
    eligibility = stack({k: v["eligibility"] for k, v in link2.items()})
    write_table(eligibility, folder, "link2_half_sample_eligibility.csv")

    sensitivity = []
    for sample, cases in [("primary", primary), ("link2", link2)]:
        for scenario, bundle in cases.items():
            for name, response in [("sensitivity", "period"), ("cumulative_sensitivity", "cumulative"),
                                   ("period_boot", "period"), ("cumulative_boot", "cumulative")]:
                method = "MBB" if name.endswith("_boot") else "HAC"
                frame = bundle[name].rename(columns={"coefficient": "estimate", "cumulative_effect": "estimate",
                                                     "hac_ci_low": "ci_low", "hac_ci_high": "ci_high",
                                                     "bootstrap_ci_low": "ci_low", "bootstrap_ci_high": "ci_high"})
                sensitivity.append(frame.assign(sample=sample, scenario=scenario, method=method, response_type=response))
    sensitivities = pd.concat(sensitivity, ignore_index=True)
    write_table(sensitivities, folder, "inference_sensitivity.csv")
    (folder / "核心实验结果.md").write_text(report(paired, joint, link1_table, link2_table, eligibility, gate,
                                                  sensitivities), encoding="utf-8")
    receipt = dict(baseline="PASS", frozen_comparisons=int(gate.compared.sum()),
                   frozen_fields=len(gate), frozen_failures=0, frozen_tolerance={"rtol": 1e-8, "atol": 1e-10},
                   bootstrap_p_absolute_tolerance=5e-14, inputs_and_code_sha256=hashes,
                   environment=environment, policy=policy,
                   recovered_from_source="customs revision replaces Jan/Feb 2026 amounts and quantities on the fixed old calendar",
                   outputs_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir())})
    (folder / "reproduction.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")


def verify_exports(folder):
    expected = {
        "primary_lp_comparison.csv": 78, "primary_joint_tests.csv": 72,
        "customs_link1.csv": 162, "customs_link2.csv": 312, "link2_half_sample_eligibility.csv": 78,
        "inference_sensitivity.csv": 2808,
    }
    for name, rows in expected.items():
        frame = pd.read_csv(folder / name)
        if len(frame) != rows:
            raise RuntimeError(f"{name}: expected {rows}, observed {len(frame)}")
    lp = pd.read_csv(folder / "primary_lp_comparison.csv")
    if not lp.delta_N.eq(8).all() or not lp.response_end_new.eq("2026-10").all():
        raise RuntimeError("Primary horizon sample expansion differs from the audited calendar")
    for file, base, horizon in [("customs_link1.csv", 130, False), ("customs_link2.csv", 131, True)]:
        result = pd.read_csv(folder / file)
        expected_old = base - result.horizon if horizon else base
        expected_n = expected_old + result.scenario.eq("full_new").astype(int)*8
        if not result.N.eq(expected_n).all():
            raise RuntimeError(f"{file}: scenario sample counts changed unexpectedly")
    halves = pd.read_csv(folder / "link2_half_sample_eligibility.csv")
    restricted = halves.loc[halves.horizon.isin([11, 12])]
    if not restricted.status.eq("SKIPPED_PAIRED_HALF_N_BELOW60").all():
        raise RuntimeError("Link2 half-sample cutoff was not applied")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |",
                      *["| " + " | ".join(map(str, row)) + " |" for row in rows]])


def test_counts(paired):
    rows = []
    for (outcome, meaning), group in paired.groupby(["outcome", "response_type"], sort=False):
        old, new = [int(group[f"bh_reject_5pct_{v}"].sum()) for v in ("old", "new")]
        robust_old, robust_new = [int(group[f"allowed_wording_{v}"].eq("ROBUST_ASSOCIATION").sum())
                                  for v in ("old", "new")]
        gained = ", ".join(map(str, group.loc[~group.bh_reject_5pct_old & group.bh_reject_5pct_new, "horizon"]))
        lost = ", ".join(map(str, group.loc[group.bh_reject_5pct_old & ~group.bh_reject_5pct_new, "horizon"]))
        rows.append((LABELS[outcome], "逐期" if meaning == "period" else "累计", f"{old} → {new}",
                     f"{robust_old} → {robust_new}", gained or "—", lost or "—"))
    return table(["价格", "响应", "BH 拒绝期数", "稳健期数", "新增拒绝 h", "原拒绝、新未拒绝 h"], rows)


def report(paired, joint, link1, link2, eligibility, gate, sensitivities):
    focus = paired.loc[paired.horizon.isin([0, 3, 6, 12])]
    point = table(["价格", "响应", "h", "N 旧→新", "系数旧→新", "新 MBB 95% 区间", "新 HAC SE", "BH q 旧→新"],
                  [(LABELS[r.outcome], "逐期" if r.response_type == "period" else "累计", r.horizon,
                    f"{r.N_old} → {r.N_new}", f"{r.estimate_old:.4f} → {r.estimate_new:.4f}",
                    f"[{r.bootstrap_ci_low_new:.4f}, {r.bootstrap_ci_high_new:.4f}]",
                    f"{r.hac_se_new:.4f}", f"{r.fdr_q_old:.4g} → {r.fdr_q_new:.4g}")
                   for r in focus.itertuples()])
    windows = joint.loc[joint.block_length.eq(12) & joint.window.isin(["short", "medium"])]
    joint_rows = windows.pivot(index=["outcome", "window"], columns="scenario", values="fdr_q").reset_index()
    jt = table(["价格", "窗口", "旧 BH q", "新 BH q"],
               [(LABELS[r.outcome], "h0–3" if r.window == "short" else "h4–6", f"{r.old:.4g}", f"{r.full_new:.4g}")
                for r in joint_rows.itertuples()])
    names = {"old": "冻结旧版", "revised_overlap": "仅替换 1–2 月量额", "full_new": "完整新版"}
    one = link1.loc[link1.model.eq("MECH1_quantity-1") & link1.maxlags.eq(12)
                    & link1.record_type.eq("cumulative")]
    lt = table(["场景", "N", "Link1 累计系数", "HAC 95% 区间", "前一场景差"],
               [(names[r.scenario], r.N, f"{r.coefficient:.4f}", f"[{r.hac_ci_low:.4f}, {r.hac_ci_high:.4f}]",
                 "—" if pd.isna(r.delta_coefficient) else f"{r.delta_coefficient:+.4f}") for r in one.itertuples()])
    two = link2.loc[link2.model.str.endswith("quantity0") & link2.response_type.eq("cumulative")
                    & link2.horizon.isin([3, 6])]
    l2 = table(["价格", "h", "冻结旧值", "仅更新重叠月", "完整新版", "修订 Δ", "扩样 Δ", "全版 BH q"],
               [(LABELS[y], h, f"{a.loc['old','estimate']:.4f}", f"{a.loc['revised_overlap','estimate']:.4f}",
                 f"{a.loc['full_new','estimate']:.4f}", f"{a.loc['revised_overlap','delta_estimate']:+.4f}",
                 f"{a.loc['full_new','delta_estimate']:+.4f}", f"{a.loc['full_new','fdr_q']:.4g}")
                for (y, h), group in two.groupby(["outcome", "horizon"], sort=False)
                for a in [group.set_index("scenario")]])
    end = eligibility.loc[eligibility.scenario.eq("full_new") & eligibility.horizon.isin([11, 12])].drop_duplicates("horizon")
    halves = "、".join(f"h={r.horizon} 为 {r.first_half_n}/{r.second_half_n}" for r in end.itertuples())
    worst = gate.groupby("dataset").max_abs_error.max()
    failed = int(sensitivities.failed_draws.fillna(0).sum())
    return f"""# 核心实证复现与重估 · 2026 年 10 月

## 旧版复现通过

以冻结至 2026-02 的 338 月长样本和 134 月海关样本重跑估计。主 LP 39 个逐期系数和样本、三种区块长度的逐期及累计区间、36 个路径联合检验、Link1 54 行及主 HAC 协方差、Link2 冻结结果均通过回归核对。共比较 {int(gate.compared.sum()):,} 个值，零失败。主 LP 逐期字段最大绝对差 {worst['primary_period']:.2g}，累计字段 {worst['primary_cumulative']:.2g}，主 LP 联合检验字段 {worst['primary_joint']:.2g}，Link1 字段 {worst['Link1']:.2g}。

保留原先的 0–12 期、冲击及因变量 1–2 阶滞后、Bartlett HAC、原带宽与小样本修正、5,000 次非循环移动区块 Bootstrap、L=12/6/18、种子 20261004、同样本组共享抽样以及原 BH/Holm 检验族。逐期及累计分别校正。稳健分类还要求原有 HAC 和区块长度敏感性区间保持方向。LP 的模型×期×响应类型×抽样设定失效计数合计 {failed}。

## 新版主 LP

同口径历史段的原模型变量一致，新增 8 月使各期限均增加 8 个有效起点。累计响应等于各期系数之和，累计行 N 指该行最后一期的有效数。单位为人民币 Brent 变动 1 对数点对应同比通胀变化的百分点。区间为原 L=12 的逐点 95% Bootstrap 百分位区间，BH q 据原 HAC 族内校正。

{point}

{test_counts(paired)}

h0–3 和 h4–6 的整段零响应联合检验如下。q 值来自原移动区块的中心化 Wald 校准，对每个结果变量的四个窗口校正。

{jt}

## 海关三场景

重叠场景保持旧日历和非海关字段，只替换 2026-01 和 02 的 HS27090000 数量及金额，按原定义重算单位价值和对数变动。重叠场景减冻结旧版为修订差，完整新版减重叠场景为扩样差。CSV 导出的查询筛选及修订原因仍有待证实。差值是同口径点估计分解。

Link1 固定原始 0–3 阶油价冲击规格，以下为四个系数之和的主 HAC 结果。

{lt}

Link2 以下列无当期数量控制的累计响应为例，数量敏感性保存在完整表。新版两半最低 60 月的原规则下，{halves}，两侧比较均跳过。各期全样本 Link2 仍符合自身样本条件。

{l2}

逐期和累计结果见 [主 LP 对照](primary_lp_comparison.csv)、[窗口联合检验](primary_joint_tests.csv)、[Link1 三场景](customs_link1.csv)、[Link2 三场景](customs_link2.csv)、[Link2 分段资格](link2_half_sample_eligibility.csv)及[原推断敏感性](inference_sensitivity.csv)。[输入、版本和输出封签](reproduction.json)记录本轮复建配置。
"""
