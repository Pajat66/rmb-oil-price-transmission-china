"""Data-only acceptance checks and eligibility audit for the October 2026 rebuild."""
from collections import Counter
from hashlib import sha256
from io import BytesIO
import subprocess

import numpy as np
import openpyxl
import pandas as pd

import monthly_update as u
from canonical_layer import build_oil_rmb
from design_construction import SHOCK, YLIST, build_design, build_link1
from phase15_common import calendar_lag, calendar_lead
from common_designs import construct
from transformation_layer import INFLATION, POSITIVE, transform

BASELINE_PRIVATE = u.PACKAGE.parent.parent / "rmb-oil-price-transmission-china"
SUBMITTED = u.PACKAGE.parent.parent / "PLOS_ONE_Final_Submission_20261019/S1_Data.xlsx"
S1_COPY = u.PACKAGE / "journal_submission/S1 Data.xlsx"
OPTIONAL = {"core_cpi_proxy_yoy", "indust_va_yoy", "indust_va_cum_yoy"}

# indicator, unit, old IDs, new file, meaning / downstream
VARIABLES = {
    "month": ("Month / Date / observation_date / 数据年月 / 指标横列日期", "公历月初", "", "", "所有设计的日历键"),
    "brent_usd": (u.BRENT, "USD/barrel", "eia", u.EIA, "主 LP、分项、Link1、稳定性、S15、S18 的上游；Fig 2"),
    "cny_per_usd": ("EXCHUS", "CNY/USD", "fred", u.FRED, "主 LP、分项、Link1、稳定性、S15、S18 的上游；Fig 2"),
    "oil_rmb": ("brent_usd × cny_per_usd", "CNY/barrel", "", "", "水平值 Table 3/S3；变换后用于 LP/Link1；Fig 2"),
    "cpi_yoy": (u.NBS_FIELDS[u.CPI]["cpi_yoy"], u.INDEX, "cpi_98_15;cpi_16_20;cpi_21_25;cpi_26", u.CPI, "总体 CPI 主 LP、终端 CPI、稳定性、S15、S18、Fig 2"),
    "cpi_transport_comm_yoy": ("交通和通讯/交通和通信/交通通信类居民消费价格指数(上年同月=100)", u.INDEX,
                               "cpi_98_15;cpi_16_20;cpi_21_25;cpi_26", u.CPI, "主表辅助字段；当前正式方程未读取"),
    "core_cpi_proxy_yoy": (u.NBS_FIELDS[u.CPI]["core_cpi_proxy_yoy"], u.INDEX, "cpi_21_25;cpi_26", u.CPI, "该列保存官方核心 CPI；当前正式方程未读取"),
    "ppi_yoy": (u.NBS_FIELDS[u.PPI]["ppi_yoy"], u.INDEX, "ppi", u.PPI, "PPI 主 LP、Link2、终端 CPI、稳定性、S15、S18、Fig 2"),
    "ppi_purchase_yoy": (u.NBS_FIELDS[u.PURCHASE]["ppi_purchase_yoy"], u.INDEX, "ppi_purchase", u.PURCHASE, "S2/S3 历史诊断、S1/Fig 2"),
    "ppi_fuel_power_yoy": (u.NBS_FIELDS[u.PURCHASE]["ppi_fuel_power_yoy"], u.INDEX, "ppi_purchase", u.PURCHASE, "Fuel 主 LP、Link2、终端 CPI、稳定性、S15、S18、Fig 2"),
    "indust_va_yoy": (u.NBS_FIELDS[u.IVA_MONTH]["indust_va_yoy"], u.RATE, "iva", u.IVA_MONTH, "S17 缺失核算、历史诊断；无正式 LP 控制项"),
    "indust_va_cum_yoy": (u.NBS_FIELDS[u.IVA_MONTH]["indust_va_cum_yoy"], u.RATE, "iva", u.IVA_MONTH, "Table 3/S3 历史滞后选择控制；S17；每年年初累计"),
    u.KG: ("第一数量；第一计量单位=千克；HS27090000", "kg", "customs", u.CUSTOMS, "S1 Data，数量源值及单位价值上游"),
    u.CNY: ("人民币；HS27090000", "CNY", "customs", u.CUSTOMS, "S1 Data，金额源值及单位价值上游"),
    u.QTY: (u.KG + " / 10^7", "万吨", "customs", u.CUSTOMS, "Link1、Link2 的数量敏感性；S2、Fig 2"),
    u.VAL: (u.CNY + " / 10^8", "亿元人民币", "customs", u.CUSTOMS, "单位价值上游，S2、Fig 2"),
    u.UV: (u.CNY + " / " + u.KG, "CNY/kg", "customs", u.CUSTOMS, "Link1 因变量；Link2/终端 CPI 冲击；S2、Fig 2"),
    "oil_rmb_source": ("canonical_layer.build_oil_rmb", "文本标签", "", "", "canonical 溯源标记，回归不读取"),
}
YOY = {
    "oil_rmb_yoy_pct": "oil_rmb", "brent_yoy_pct": "brent_usd", "fx_yoy_pct": "cny_per_usd",
    "import_unit_price_yoy_pct": u.UV, "import_quantity_yoy_pct": u.QTY, "import_value_yoy_pct": u.VAL,
}
for field, base in POSITIVE.items():
    VARIABLE = VARIABLES[base]
    VARIABLES[field] = (f"100 × [ln({base}_t) − ln({base}_(t−1))]", u.LOG, VARIABLE[2], VARIABLE[3],
                        VARIABLE[4] + ("；等同变量的月度运动" if base != "oil_rmb" else "；主模型当前冲击"))
for field, base in INFLATION.items():
    raw, _, ids, new, downstream = VARIABLES[base]
    VARIABLES[field] = (f"{base} − 100", "% 同比增速", ids, new, downstream)
    VARIABLES[f"d_{field}"] = (f"{field}_t − {field}_(t−1)", "百分点", ids, new, downstream)
for field, base in YOY.items():
    raw, _, ids, new, _ = VARIABLES[base]
    VARIABLES[field] = (f"100 × [ln({base}_t) − ln({base}_(t−12))]", u.LOG, ids, new,
                        "S2 对齐同比、Phase2A9 历史诊断")


def month_labels(dates):
    return pd.PeriodIndex(dates, freq="M").astype(str).tolist()


def canonical(frame, sample):
    frame = frame.reset_index()
    frame["month"] = pd.to_datetime(frame.month, format="%Y-%m")
    # Keep the historical long derived flag and the short source marker. The Excel
    # above stores calculated values in both samples.
    x = frame.drop(columns=["oil_rmb"]) if sample == "long" else frame
    return build_oil_rmb(x, sample)[0][[*frame, "oil_rmb_source"]]


def yoy(frame, long_frame=None):
    out = frame[["month"]].copy()
    for var, source in YOY.items():
        if source in frame:
            basis = long_frame if long_frame is not None and source in long_frame else frame
            movement = 100 * (np.log(basis[source]) - np.log(calendar_lag(basis, source, 12)))
            out[var] = frame.month.map(pd.Series(movement.to_numpy(), index=basis.month))
    return out


def classification(var, month, first):
    yyyy, mm = map(int, month.split("-"))
    if var == "core_cpi_proxy_yoy" and month < "2021-01":
        return "结构性", "原研究来源早期无可核验序列"
    if var in {"indust_va_yoy", "indust_va_cum_yoy"}:
        if yyyy >= 2005 and mm == 1 or var == "indust_va_yoy" and yyyy >= 2013 and mm == 2:
            return "结构性", "春节统计制度与发布规则"
        return "历史来源缺口", "冻结 NBS 文件缺值，保留待核"
    if var.startswith(("dlog_", "d_")) and first and month < first:
        return "结构性", "样本起点缺上月基数"
    if var in YOY and first and month < first:
        return "结构性", "样本起点缺上年同月基数"
    return "异常或未解释", "需排查来源与相邻基数"


def coverage(sample, frame, tier):
    months = pd.Series(month_labels(frame.month), index=frame.index)
    stats, detail = [], []
    for var, col in frame.items():
        valid = col.notna()
        first = months[valid].min() if valid.any() else ""
        last = months[valid].max() if valid.any() else ""
        counts = Counter()
        for month in months[~valid]:
            kind, reason = classification(var, month, first)
            counts[kind] += 1
            detail.append(dict(sample=sample, layer=tier, variable=var, month=month, kind=kind, reason=reason))
        stats.append(dict(sample=sample, layer=tier, variable=var, first_valid=first, last_valid=last,
                          calendar_n=len(col), valid_n=int(valid.sum()), missing_n=int((~valid).sum()),
                          missing_fraction=float((~valid).mean()),
                          structural_n=counts["结构性"], historical_n=counts["历史来源缺口"],
                          unexpected_n=counts["异常或未解释"], missing_months=";".join(months[~valid])))
    return stats, detail


def origin(var, month, paths):
    raw, _, ids, new, _ = VARIABLES[var]
    if ids.startswith("cpi_"):
        year = int(month[:4])
        ids = ("cpi_98_15" if year <= 2015 else "cpi_16_20" if year <= 2020
               else "cpi_21_25" if year <= 2025 else "cpi_26")
    return ";".join(paths[key].relative_to(u.PACKAGE).as_posix() for key in ids.split(";") if key) or "计算"


def overlap(history, rebuilt, observations, latest_customs, paths):
    records = []
    source = {**observations, u.KG: latest_customs[u.KG], u.CNY: latest_customs[u.CNY]}
    source[u.QTY] = source[u.KG] / 10**7
    source[u.VAL] = source[u.CNY] / 10**8
    source[u.UV] = source[u.CNY] / source[u.KG]
    source["oil_rmb"] = source["brent_usd"] * source["cny_per_usd"]
    for sample, old in history.items():
        new = rebuilt[sample]
        for var in old:
            for month, old_value in old[var].items():
                value = new.at[month, var]
                s = source.get(var)
                in_export = s is not None and month in s.index
                if not in_export and month < "2025-10":
                    continue
                raw_new = s.at[month] if in_export else np.nan
                published = pd.notna(raw_new)
                comparable = pd.notna(value) and pd.notna(old_value)
                delta = float(value - old_value) if comparable else np.nan
                changed = (abs(delta) > 1e-10) if comparable else (pd.isna(value) != pd.isna(old_value))
                if changed and var in {u.KG, u.CNY, u.QTY, u.VAL, u.UV}:
                    status = "采用新导出；差异成因未确认"
                elif changed and var == "oil_rmb":
                    status = "随 Brent/EXCHUS 新版输入重算"
                elif changed:
                    status = "采用同一指标新导出；差异成因未确认"
                elif published:
                    status = "新旧一致"
                elif pd.isna(value):
                    status = "原值为空，保留 NA"
                else:
                    status = "新导出无该值，保留旧源" if var != "oil_rmb" else "使用实际入表因子重算"
                path = VARIABLES[var][3]
                records.append(dict(sample=sample, month=month, variable=var, unit=VARIABLES[var][1],
                                    old_value=old_value, incoming_value=raw_new, final_value=value,
                                    delta_new_minus_old=delta, abs_delta=abs(delta),
                                    relative_pct=100 * delta / old_value if comparable and old_value != 0 else np.nan,
                                    changed=bool(changed), incoming_key_present=in_export,
                                    old_source=origin(var, month, paths),
                                    new_source=(f"data/New/{path}" if path else
                                                f"data/New/{u.EIA};data/New/{u.FRED}（缺期沿用旧源）"),
                                    decision=status))
    return pd.DataFrame(records)


def check_baseline(history, paths, add):
    profiles = []
    reference = {}
    objects = {
        "源长表": u.PACKAGE / "data/02_clean/monthly_master/master_monthly_long_1998_2026.xlsx",
        "源短表": u.PACKAGE / "data/02_clean/monthly_master/master_monthly_v1_filled_full_openpyxl.xlsx",
        "短表模板": u.PACKAGE / "data/02_clean/monthly_master/master_monthly_v1.xlsx",
        "已提交 S1": SUBMITTED,
        "仓库带空格 S1": S1_COPY,
    }
    for role, path in objects.items():
        if not path.is_file():
            add("基线存在 " + role, False, str(path))
            continue
        digest = u.sha(path)
        with path.open("rb") as stream:
            book = openpyxl.load_workbook(stream, read_only=True, data_only=True)
            for sheet in book:
                rows = list(sheet.values)
                header_row = 2 if sheet.title == "README" else 0
                header = rows[header_row] if len(rows) > header_row else ()
                body = rows[header_row + 1:]
                dated = sorted(str(r[0])[:7] for r in body if r[0] and str(r[0])[:4].isdigit())
                for i, title in enumerate(header):
                    if title is None:
                        continue
                    profiles.append(dict(role=role, path=path.relative_to(u.PACKAGE).as_posix() if u.PACKAGE in path.parents else
                                         "../../" + path.relative_to(u.PACKAGE.parent.parent).as_posix(),
                                         sha256=digest, sheet=sheet.title, rows=len(body), columns=len(header),
                                         first_month=min(dated, default=""), last_month=max(dated, default=""),
                                         variable=title, valid_n=sum(r[i] is not None and r[i] != "" for r in body),
                                         reader="openpyxl data_only", generated_by=(
                                             "原始 03_scripts/python/fill_master_monthly_long_openpyxl.py" if role == "源长表"
                                             else "原始 03_scripts/python/fill_master_monthly_v5_exactpaths.py" if role == "源短表"
                                             else "2026-10-19 S1 Data 生成流程；私有审计包 audit_evidence_20261019"
                                             if "S1" in role else "历史模板")))
            book.close()
    tracked = subprocess.check_output(["git", "--no-optional-locks", "show", "HEAD:journal_submission/S1_Data.xlsx"], cwd=u.PACKAGE)
    submitted_sha = u.sha(SUBMITTED)
    add("S1 提交归档、带空格文件及 Git blob 同一 SHA-256",
        sha256(tracked).hexdigest() == submitted_sha == u.sha(S1_COPY), submitted_sha)
    add("删除状态保持", not (u.PACKAGE / "journal_submission/S1_Data.xlsx").exists(),
        "工作树原路径应保持缺失；Git blob 只读核对")
    for sample, base in history.items():
        for kind in ("canonical", "transformed"):
            path = BASELINE_PRIVATE / f"05_revision/01_data/{sample}_sample_{kind}.csv"
            if not path.is_file():
                add(f"历史 {sample} {kind} 对照", False, str(path))
                continue
            old = pd.read_csv(path, parse_dates=["month"])
            current = canonical(base, sample)
            if kind == "transformed":
                current = transform(current)
            numeric = [col for col in old.select_dtypes("number") if col in current]
            match = list(old.month) == list(current.month) and bool(numeric) and np.allclose(
                old[numeric], current[numeric], rtol=1e-12, atol=1e-10, equal_nan=True)
            add(f"历史 {sample} {kind} 数值重建", match, f"{len(old)} 行，{len(numeric)} 个数值列")
            if kind == "transformed":
                reference[sample] = old
            for col in old:
                profiles.append(dict(role=f"历史模型 {sample} {kind}",
                                     path="../../" + path.relative_to(u.PACKAGE.parent.parent).as_posix(),
                                     sha256=u.sha(path), sheet="", rows=len(old), columns=len(old.columns),
                                     first_month=old.month.min().strftime("%Y-%m"), last_month=old.month.max().strftime("%Y-%m"),
                                     variable=col, valid_n=int(old[col].notna().sum()), reader="pandas.read_csv",
                                     generated_by="历史 05_revision Phase1/2A；现存镜像 data_interface.py / transformation_layer.py"))
    # Read S1 observed fields independently of canonical archives.
    def sheet_frame(sheet):
        return pd.read_excel(BytesIO(tracked), sheet_name=sheet, engine="openpyxl").set_index("month")
    submitted_long = sheet_frame("Monthly_338")
    submitted_short = sheet_frame("Customs_134")
    bindings = {
        "brent_usd": "brent_usd_per_bbl", "cny_per_usd": "cny_per_usd",
        "oil_rmb": "oil_rmb_cny_per_bbl", "ppi_fuel_power_yoy": "fuel_index_yoy",
        "ppi_yoy": "ppi_index_yoy", "cpi_yoy": "cpi_index_yoy", "ppi_purchase_yoy": "purchase_index_yoy",
    }
    if all(v in submitted_long for v in bindings.values()):
        add("已提交 S1 与长表原始重建数值对照",
            submitted_long.index.equals(history["long"].index)
            and np.allclose(submitted_long[list(bindings.values())], history["long"][list(bindings)], atol=1e-10, rtol=1e-12, equal_nan=True),
            "7 核心列，含历史公式缓存")
    else:
        add("已提交 S1 与长表原始重建数值对照", False, f"提交字段 {list(submitted_long)}")
    add("已提交 S1 与海关原始整数对照",
        submitted_short.index.equals(history["short"].index)
        and np.array_equal(submitted_short[[u.KG, u.CNY]], history["short"][[u.KG, u.CNY]]), "134 个月 × 2 原始整数列")
    return profiles, reference


def validate_values(base, transformed, aligned, add):
    for sample, frame in base.items():
        n = {"long": 346, "short": 142}[sample]
        add(f"{sample} 月历", len(frame) == n and list(frame.index) == list(u.calendar(u.START[sample], u.END)),
            f"{u.START[sample]}–{u.END}，{len(frame)} 月")
        finite = all(pd.api.types.is_numeric_dtype(frame[var]) and np.isfinite(frame[var].dropna()).all() for var in frame)
        add(f"{sample} 数值类型与有限性", finite, "源解析检查非法字符、错误、空格、非法日期和重复键")
        required = frame.drop(columns=list(OPTIONAL))
        holes = [(m, col) for col in required for m in required.index[required[col].isna()]]
        add(f"{sample} 核心变量完整性", not holes, str(holes) if holes else "核心列全日历有值")
        nonpositive = {c: frame[c][frame[c] <= 0].index.tolist() for c in required if (frame[c] <= 0).any()}
        add(f"{sample} 价格、指数、数量及金额取值域", not nonpositive, str(nonpositive) if nonpositive else "正值")
        add(f"{sample} RMB 油价独立验算",
            all(abs(row.oil_rmb - row.brent_usd * row.cny_per_usd) <= 1e-10 for row in frame.itertuples()),
            "USD/barrel × CNY/USD")
        tx, ya = transformed[sample], aligned[sample]
        for var, source in POSITIVE.items():
            if source in frame:
                expected = 100 * np.log(frame[source].to_numpy() / frame[source].shift(1).to_numpy())
                add(f"{sample} {var}", np.allclose(expected, tx[var], atol=1e-10, rtol=0, equal_nan=True),
                    "独立比值取对数；日历 t−1")
        for var, source in INFLATION.items():
            expected = frame[source] - 100
            add(f"{sample} {var} 与差分",
                np.allclose(expected, tx[var], atol=1e-12, rtol=0, equal_nan=True)
                and np.allclose(frame[source].diff(), tx[f"d_{var}"], atol=1e-12, rtol=0, equal_nan=True),
                "指数减 100；相邻同比增速相减（百分点）")
        for var, source in YOY.items():
            basis = base["long"] if source in base["long"] else frame
            if var in ya:
                add(f"{sample} {var}",
                    np.allclose(
                        (100*np.log(basis[source]/basis[source].shift(12))).reindex(frame.index), ya[var],
                                atol=1e-10, rtol=0, equal_nan=True), "独立 t/t−12 对数比")
        add(f"{sample} 对数分解恒等式",
            np.allclose(tx.dlog_oil_rmb, tx.dlog_brent+tx.dlog_fx, atol=1e-10, rtol=0, equal_nan=True),
            "合成冲击等于 Brent 与 FX 分项对数月变动之和")
    short, long = base["short"], base["long"]
    add("长短表共同字段一致", short[list(long)].equals(long.loc[u.START["short"]:]), "相同月份、值和缺失掩码")
    add("海关数量、金额单位及比值独立验算",
        all(float(short.at[m, u.QTY]) == int(short.at[m, u.KG])/10000000
            and float(short.at[m, u.VAL]) == int(short.at[m, u.CNY])/100000000
            and abs(short.at[m, u.UV] - 10*short.at[m, u.VAL]/short.at[m, u.QTY]) < 1e-12
            for m in short.index), "kg→万吨；元→亿元；CNY/kg=10×亿元/万吨")
    expected_core = u.calendar("2021-01", u.END).tolist()
    add("核心 CPI 的实际覆盖", long.core_cpi_proxy_yoy.dropna().index.tolist() == expected_core,
        f"{len(expected_core)} 个值，早期保留 NA")
    jan, feb = long.loc["2026-01"], long.loc["2026-02"]
    add("2026 年工业增加值发布口径",
        pd.isna(jan.indust_va_yoy) and pd.isna(feb.indust_va_yoy) and pd.isna(jan.indust_va_cum_yoy)
        and feb.indust_va_cum_yoy == 6.3, f"1 月空缺；2 月累计 6.3%、当月空缺。{u.IVA_FEB}")
    for var, (expected, link) in u.OFFICIAL.items():
        add(f"2026-10 官网页交叉核对 {var}", abs(long.at[u.END, var] - expected) < 1e-10, f"{expected}；{link}")
    add("海关 2026-10 及累计量额的发布舍入核对",
        round(short.loc[u.END, u.QTY], 1) == 4193.8 and round(short.loc[u.END, u.VAL], 1) == 2308.2
        and round(short.loc["2026-01":, u.QTY].sum(), 1) == 39989.5
        and round(short.loc["2026-01":, u.VAL].sum(), 1) == 17631.3,
        "仅用于印证量级和全国进口方向，公开全国表转载的一位小数；https://www.gotohui.com/trade/list/191970.html")


def outliers(transformed):
    rows = []
    for sample, frame in transformed.items():
        changes = {col: frame[col] for col in frame if col.startswith(("dlog_", "d_"))}
        for col in sorted(OPTIONAL | {"cpi_transport_comm_yoy"}):
            if col in frame:
                changes[col] = frame[col].diff()
        for col, s in changes.items():
            med = s.median()
            mad = (s-med).abs().median()
            if not mad or pd.isna(mad):
                continue
            z = 0.6744897501960817 * (s-med) / mad
            for i in z.index[z.abs() > 3.5]:
                rows.append(dict(sample=sample, variable=col, month=frame.at[i, "month"].strftime("%Y-%m"),
                                 movement=s.at[i], center=med, mad=mad, robust_z=z.at[i],
                                 method="相邻月变动；稳健 Z；|Z|>3.5", decision="保留原值"))
    return pd.DataFrame(rows)


def summarize_design(rows, model, sample, frame, d, before, notes="", lead=None):
    h = d["h"]
    current, old = month_labels(d["months"]), month_labels(before["months"])
    months = pd.PeriodIndex(current, freq="M")
    end = str(months[-1] + (h if lead is None else lead)) if len(months) else ""
    rows.append(dict(model=model, sample=sample, h=h, y=d["y"], shock=d["shock"],
                     required_terms=";".join(d["cols"]), old_n=len(old), old_start=min(old, default=""),
                     old_end=max(old, default=""), n=len(current), start=min(current, default=""),
                     end=max(current, default=""), last_response_month=end,
                     added_origins=len(set(current)-set(old)),
                     newly_observed_origin_count=sum(m > u.OLD_END for m in current),
                     dropped_origins=len(set(old)-set(current)), gaps=len(pd.period_range(months[0], months[-1], freq="M"))-len(months) if len(months) else 0,
                     date_sha256=sha256("|".join(current).encode()).hexdigest(), notes=notes))
    return rows[-1]


def design_audit(old, new, add):
    registry = pd.read_csv(u.PACKAGE / "reference/registries/phase2b_primary_model_registry.csv")
    registry = registry.loc[registry.horizon.notna()].set_index(["model", "horizon"])
    rows, agreement = [], []
    args = []
    for y in YLIST:
        args.append((f"PRIMARY_{y}", "long", y, SHOCK, False, False))
        args.append((f"COMPONENTS_{y}", "long", y, SHOCK, False, True))
    for x in YLIST[:2]:
        args.append((f"TERMINAL_{x}", "long", YLIST[2], x, False, False))
        for q in (False, True):
            args.append((f"MECH2_{x}_quantity{int(q)}", "short", x, "dlog_import_unit_price", q, False))
    args.append(("TERMINAL_dlog_import_unit_price", "short", YLIST[2], "dlog_import_unit_price", False, False))
    for model, sample, y, x, q, comp in args:
        for h in range(13):
            before = build_design(old[sample], y, x, h, quantity=q, components=comp)
            design = build_design(new[sample], y, x, h, quantity=q, components=comp)
            row = summarize_design(rows, model, sample, new[sample], design, before,
                                   "当前分项替换合成项；保留合成滞后" if comp else "会计口径；滞后 1、2，响应 t+h")
            if (model, h) in registry.index:
                r = registry.loc[(model, h)]
                date_sha = sha256("|".join(month_labels(before["months"])).encode()).hexdigest()
                agreement.append(len(before["Y"]) == r.N and ";".join(before["cols"]) == r.terms and date_sha == r.sample_hash)
            add_month = row["n"] - row["old_n"]
            u.require(add_month == 8 and row["gaps"] == 0, f"{model} h={h}: missing extension")
    add("历史正式 LP 日期、列、N 和已保存月份哈希", len(agreement) == 130 and all(agreement),
        f"{sum(agreement)}/{len(agreement)}；对照冻结 registry")
    add("新版正式 LP 与分项每期完整", all(row["added_origins"] == 8 and row["dropped_origins"] == 0 for row in rows),
        f"{len(rows)} 个纯设计/资格掩码，基于已有 build_design")
    old_short, new_short = old["short"], new["short"]
    b, d = build_link1(old_short), build_link1(new_short)
    summarize_design(rows, "MECH1_OIL_IMPORT_p3", "short", new_short, d, b, "原 Link1 油冲击 0..3")
    for q in (0, 1):
        uses = []
        for frame, actual in [(old_short,b), (new_short,d)]:
            design = {**actual, "cols": actual["cols"].copy()}
            eligible = actual["valid"].copy()
            for lag in range(q+1):
                eligible &= calendar_lag(frame, "dlog_import_quantity", lag).notna().to_numpy()
                design["cols"].append(f"dlog_import_quantity_lag{lag}")
            design["months"] = frame.loc[eligible, "month"]
            uses.append(design)
        summarize_design(rows, f"MECH1_QUANTITY_q{q}", "short", new_short, uses[1], uses[0],
                         "同一 Link1 样本，额外数量 0..q")
    s18_old, s18_new = construct(old["long"]), construct(new["long"])
    for b, d in zip(s18_old,s18_new):
        d = dict(d, y=d["outcome"], shock=SHOCK)
        summarize_design(rows, f"S18_p{d['p']}_{d['outcome']}", "long", new["long"], d, b,
                         "每个 h 三个因变量、p=1/2/3/4/6 共用 pmax=6 的日历")
    add("S18 共同样本", len(s18_new) == 195 and all(len(d["months"]) == 339-d["h"] for d in s18_new),
        "195 个设计；N=339−h；纯 common_designs.construct")
    for y in YLIST:
        designs = [build_design(frame, y, SHOCK, 0) for frame in (old["long"], new["long"])]
        for leads in ((1,), (2,), (3,), (1, 2, 3)):
            masks = []
            placebo = len(leads) > 1
            for design in designs:
                z = design["z"].loc[design["valid"]].reset_index(drop=True)
                future = pd.concat([calendar_lead(z, SHOCK, j) for j in leads], axis=1)
                masks.append(dict(design, months=z.loc[future.notna().all(axis=1), "month"], h=max(leads),
                                  y=y if placebo else f"{SHOCK}_lead{max(leads)}",
                                  cols=design["cols"] + ([f"oil_lead{j}" for j in leads] if placebo else [y])))
            model = f"S15_PLACEBO_{y}" if placebo else f"S15_REVERSE_{y}"
            summarize_design(rows, model, "long", new["long"], masks[1], masks[0],
                             "未来油价 1..3 同时入式；单项和联合检验共用" if placebo else "未来油价逐期作响应",
                             lead=0 if placebo else max(leads))
    add("模型输入核对无月历空洞", all(r["gaps"] == 0 for r in rows), f"{len(rows)} 条资格记录")
    return pd.DataFrame(rows)



def window_audit(ready):
    """Count contiguous monthly eligibility for the Phase 2C rules without fitting."""
    rows = []
    for y in YLIST:
        primary = ready.loc[ready.model == f"PRIMARY_{y}"]
        for r in primary.loc[primary.h.isin([0, 3, 6, 12])].itertuples():
            for method, width in (("recursive", 120), ("rolling", 120), ("rolling", 96), ("rolling", 144)):
                rows.append(dict(model=r.model, h=r.h, method=method, width=width,
                                 old_n=r.old_n-width+1, new_n=r.n-width+1, last_origin=r.end,
                                 detail="窗口数；递归从首个窗口开始增长"))
            if r.h != 12:
                def count(n, tightest_n):
                    start = max(int(np.ceil(.15*n)), 60)
                    end = min(int(np.floor(.85*n)), tightest_n-60)
                    return max(0, end-start+1)
                rows.append(dict(model=r.model, h=r.h, method="sup-Wald candidate grid", width=None,
                                 old_n=count(r.old_n, primary.old_n.min()), new_n=count(r.n, primary.n.min()),
                                 last_origin=r.end, detail="候选分割个数；15% trim，各 h 两侧各至少 60"))
    mechanisms = ready.loc[ready.model.isin([f"MECH2_{y}_quantity0" for y in YLIST[:2]]
                                           + ["MECH1_OIL_IMPORT_p3"])]
    for model, group in mechanisms.groupby("model"):
        h0 = group.loc[group.h == 0].iloc[0]
        for r in group.itertuples():
            rows.append(dict(model=model, h=r.h, method="rolling", width=60, old_n=r.old_n-59,
                             new_n=r.n-59, last_origin=r.end, detail="窗口数"))
            split, old_split = h0.n//2, h0.old_n//2
            split_month = str(pd.Period(h0.start, freq="M") + split-1)
            eligibility = ("可运行；每侧至少 60" if min(split, r.n-split) >= 60 else "第二侧少于 60，按原规则跳过")
            for side, old_n, n in [("first", old_split, split), ("second", r.old_n-old_split, r.n-split)]:
                rows.append(dict(model=model, h=r.h, method=f"half: {side}", width=None,
                                 old_n=old_n, new_n=n, last_origin=split_month if side == "first" else r.end,
                                 detail=f"在各自 h0 样本的中位日期分割；{eligibility}"))
    return pd.DataFrame(rows)


def historical_table3(old, new):
    """Reproduce only lag_frame's complete-case selection for the Table 3 DLM."""
    rows = []
    for label, frame in (("old", old), ("new", new)):
        for outcome in ("ppi_fuel_power_yoy", "ppi_yoy", "cpi_yoy"):
            for p in range(13):
                for mode, cap in (("varying", p), ("fixed pmax12", 12)):
                    valid = frame[outcome].notna() & frame.indust_va_cum_yoy.notna()
                    for lag in range(cap+1):
                        valid &= frame.oil_rmb.shift(lag).notna()
                    months = frame.index[valid]
                    rows.append(dict(vintage=label, outcome=outcome, p=p, sample_mode=mode,
                                     required_terms=f"oil_rmb lags 0..{p}; indust_va_cum_yoy at t",
                                     start=months[0], end=months[-1], eligible_n=len(months),
                                     excluded=";".join(frame.index[~valid])))
    return pd.DataFrame(rows)

