"""Reconcile the 2026-10 private exports with the hash-bound historical readers."""
from datetime import datetime
from pathlib import Path
import csv
import json
import math
import re
import unicodedata

import numpy as np
import openpyxl
import pandas as pd
import xlrd

import raw_readers
from interface import PACKAGE, sha

END = "2026-10"
OLD_END = "2026-02"
START = {"long": "1998-01", "short": "2015-01"}
RAW = PACKAGE / "data/01_raw"
NEW = PACKAGE / "data/New"
EIA = "Europe Brent Spot Price FOB.xls"
FRED = "FRED.xlsx"
CPI = "核心 CPI 数据.xlsx"
PPI = "工业生产者出厂价格指数.xlsx"
PURCHASE = "工业生产者购进价格指数 (上年同月=100).xlsx"
IVA_MONTH = "规模以上工业增加值当月同比.xlsx"
IVA_CUM = "规模以上工业增加值累计同比.xlsx"
TRANSPORT = "交通通信细分类补充数据.xlsx"
CUSTOMS = "海关数据.csv"
NBS = "国家统计局"
GACC = "海关总署"
EIA_LINK = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RBRTE&f=M"
FRED_LINK = "https://fred.stlouisfed.org/data/EXCHUS"
NBS_LINK = "https://data.stats.gov.cn/"
CUSTOMS_LINK = "https://stats.customs.gov.cn/"
REGION = "全国"
INDEX = "同比指数，上年同月=100"
RATE = "%"
LOG = "100 对数点"
CPI_FIELDS = {
    "cpi_yoy": "居民消费价格指数",
    "cpi_transport_comm_yoy": "交通通信类居民消费价格指数",
    "core_cpi_proxy_yoy": "不包括食品和能源居民消费价格指数",
}
NBS_FIELDS = {
    CPI: {k: label + "(上年同月=100)" for k, label in CPI_FIELDS.items()},
    PPI: {"ppi_yoy": "工业生产者出厂价格指数(上年同月=100)"},
    PURCHASE: {
        "ppi_purchase_yoy": "工业生产者购进价格指数(上年同月=100)",
        "ppi_fuel_power_yoy": "燃料、动力类购进价格指数(上年同月=100)",
    },
    IVA_MONTH: {
        "indust_va_yoy": "规上工业增加值同比增长(%)",
        "indust_va_cum_yoy": "规上工业增加值累计增长(%)",
    },
}
QTY = "import_crude_oil_qty_10k_ton"
VAL = "import_crude_oil_value_100m_rmb"
UV = "import_crude_oil_unit_price_yuan_per_kg"
KG = "import_quantity_kg"
CNY = "import_value_cny"
BRENT = "Europe Brent Spot Price FOB (Dollars per Barrel)"
VERSION_CONFIG = PACKAGE / "config/monthly_update_202610.json"

# Publication values cross-read from the linked releases, used only as checks.
OFFICIAL = {
    "brent_usd": (123.93, EIA_LINK),
    "cny_per_usd": (6.6844, FRED_LINK),
    "cpi_yoy": (100.7, "https://www.stats.gov.cn/sj/zxfb/202611/t20261109_1965795.html"),
    "cpi_transport_comm_yoy": (105.5, "https://www.stats.gov.cn/sj/zxfb/202611/t20261109_1965844.html"),
    "core_cpi_proxy_yoy": (100.8, "https://www.stats.gov.cn/xxgk/jd/sjjd2020/202611/t20261109_1965796.html"),
    "ppi_yoy": (105.7, "https://www.stats.gov.cn/sj/zxfb/202611/t20261109_1965794.html"),
    "ppi_purchase_yoy": (107.9, "https://www.stats.gov.cn/sj/zxfb/202611/t20261109_1965794.html"),
    "ppi_fuel_power_yoy": (118.6, "https://www.stats.gov.cn/sj/zxfb/202611/t20261109_1965794.html"),
    "indust_va_yoy": (4.8, "https://www.stats.gov.cn/sj/zxfb/202611/t20261116_1965842.html"),
    "indust_va_cum_yoy": (5.3, "https://www.stats.gov.cn/sj/zxfb/202611/t20261116_1965844.html"),
}
IVA_FEB = "https://www.stats.gov.cn/sj/zxfbhjd/202603/t20260316_1962782.html"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def normalized(label):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(label)))


def number(value, context, integer=False):
    if value is None or value == "":
        return np.nan
    if isinstance(value, str):
        if integer:
            require(re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)", value), f"{context}: {value!r}")
            return int(value.replace(",", ""))
        require(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value), f"{context}: {value!r}")
    require(not isinstance(value, bool), f"{context}: boolean")
    out = float(value)
    require(math.isfinite(out), f"{context}: nonfinite {value}")
    if integer:
        require(out.is_integer(), f"{context}: fractional count {value}")
        return int(out)
    return out


def months(values, context):
    result = []
    for value in values:
        if isinstance(value, datetime):
            require(value.tzinfo is None and value.day == 1, f"{context}: {value}")
            result.append(value.strftime("%Y-%m"))
            continue
        match = re.fullmatch(r"(\d{4})(?:年|-)?(\d{1,2})月?", str(value))
        require(match is not None, f"{context}: invalid date {value!r}")
        y, m = map(int, match.groups())
        result.append(datetime(y, m, 1).strftime("%Y-%m"))
    return result


def calendar(start, end):
    return pd.period_range(start, end, freq="M").astype(str)


def keyed(keys, values, context):
    index = pd.Index(keys, name="month")
    require(index.is_unique, f"{context}: duplicate keys {index[index.duplicated()].tolist()}")
    return pd.Series(values, index=index).sort_index()


def xlsx_rows(path):
    book = openpyxl.load_workbook(path, read_only=True, data_only=False)
    output = {}
    try:
        for sheet in book:
            rows = []
            for row in sheet.iter_rows():
                for cell in row:
                    require(cell.data_type not in {"e", "f"}, f"{path}:{sheet.title}:{getattr(cell, 'coordinate', '?')}: formula/error")
                rows.append(tuple(c.value for c in row))
            output[sheet.title] = rows
        return output, book.properties.created.isoformat(sep=" ") if book.properties.created else ""
    finally:
        book.close()


def profile(wide, file, sheet, field, values, date_format, unit, used):
    valid = values.dropna()
    wide.append({"file": file, "sheet": sheet, "raw_field": field, "date_format": date_format,
                 "unit": unit, "role": used, "calendar_n": len(values), "valid_n": len(valid),
                 "first_date": values.index.min(), "last_date": values.index.max(),
                 "first_valid": valid.index.min() if len(valid) else "",
                 "last_valid": valid.index.max() if len(valid) else "",
                 "missing_months": ";".join(values.index[values.isna()]),
                 "overlap_months": ";".join(values.index[values.index <= OLD_END])})


def nbs_export(path, profiles, selected):
    sheets, created = xlsx_rows(path)
    require(set(sheets) == {"Sheet1"}, f"{path}: unexpected sheets")
    rows = sheets["Sheet1"]
    require(rows[0][0] == "数据库：月度数据" and rows[2][0] == "指标", f"{path}: header")
    require(any("数据来源：国家统计局" == r[0] for r in rows), f"{path}: source")
    month_keys = months(rows[2][1:], str(path))
    indexed = {}
    skipped = []
    for row in rows[3:]:
        label = normalized(row[0])
        if not any(v is not None for v in row[1:]) and not label.endswith(("=100)", "(%)")):
            skipped.append(str(row[0]))
            continue
        require(label.endswith(("上年同月=100)", "(%)")), f"{path}: unexpected basis {label}")
        require(label not in indexed, f"{path}: duplicate indicator {label}")
        s = keyed(month_keys, [number(v, f"{path}:{row[0]}:{m}") for m, v in zip(month_keys, row[1:])], str(path))
        indexed[label] = s
        profile(profiles, path.name, "Sheet1", row[0], s, "YYYY年M月（横列）",
                RATE if label.endswith("(%)") else INDEX,
                selected.get(label, "核验重复副本" if path.name == IVA_CUM else "已审计，未入主表"))
    return indexed, {"sheets_dimensions": f"Sheet1 {len(rows)}×{len(rows[2])}",
                     "metadata": " | ".join([rows[0][0], rows[1][0]] + skipped),
                     "acquired": created + "（工作簿创建时间）"}


def customs_rows(rows, context, profiles=None):
    header, *data = rows
    columns = ("数据年月", "商品编码", "商品名称", "第一数量", "第一计量单位",
               "第二数量", "第二计量单位", "人民币")
    require(tuple(header[:8]) == columns, f"{context}: header")
    require(len(header) in (8, 9) and all(len(r) == len(header) for r in data), f"{context}: ragged rows")
    if len(header) == 9:
        require(not header[8] and all(not r[8] for r in data), f"{context}: extra field")
    frame = pd.DataFrame([r[:8] for r in data], columns=columns)
    frame["month"] = months(frame["数据年月"], context)
    frame["商品编码"] = [number(v, f"{context}:HS", integer=True) for v in frame["商品编码"]]
    require(not frame.duplicated(["month", "商品编码"]).any(), f"{context}: duplicate month and HS")
    for source, dest in [("第一数量", KG), ("人民币", CNY)]:
        frame[dest] = [number(v, f"{context}:{m}:{source}", integer=True)
                       for m, v in zip(frame.month, frame[source])]
    crude = frame.loc[frame["商品编码"] == 27090000].set_index("month").sort_index()
    require((crude["第一计量单位"] == "千克").all() and
            (crude["商品名称"] == "石油原油及从沥青矿物提取的原油").all(),
            f"{context}: HS27090000 description or legal unit changed")
    require(not crude.empty and (crude[[KG, CNY]] > 0).all().all(), f"{context}: invalid quantity/amount")
    if profiles is not None:
        for hs, group in frame.groupby("商品编码"):
            group = group.set_index("month").sort_index()
            role = "纳入进口主表" if hs == 27090000 else "排除，商品编码不符"
            for raw, field, unit in [("第一数量", KG, "kg"), ("人民币", CNY, "CNY"),
                                     ("第二数量", "第二数量", "/".join(sorted(set(group["第二计量单位"]))))]:
                values = group[field]
                if field == "第二数量":
                    values = pd.Series([number(v, context, integer=True) for v in values], index=values.index)
                profile(profiles, context, "CSV", f"HS {hs} / {raw}", values, "YYYYMM", unit,
                        role if field != "第二数量" else "仅核验，未用于换算")
    return crude[[KG, CNY]], frame


def historical():
    contract = json.loads((PACKAGE / "config/raw_inputs.json").read_text(encoding="utf-8"))
    paths = {key: RAW / record["relative_path"] for key, record in contract["files"].items()}
    for key, path in paths.items():
        require(sha(path) == contract["files"][key]["sha256"], f"{path}: historical input SHA mismatch")
    previous = raw_readers.FILES
    try:
        raw_readers.FILES = paths
        long = raw_readers.build_long().set_index("month")
        short = raw_readers.build_master().set_index("month")
    finally:
        raw_readers.FILES = previous
    sheets, _ = xlsx_rows(paths["customs"])
    crude, raw_customs = customs_rows(next(iter(sheets.values())), str(paths["customs"]))
    require(crude.index.tolist() == list(calendar(START["short"], OLD_END)), "historical customs calendar")
    return long, short, crude, raw_customs, paths


def incoming():
    files = {p.relative_to(NEW).as_posix() for p in NEW.rglob("*") if p.is_file()
             and p.suffix.lower() in {".xlsx", ".xls", ".xlsm", ".xlsb", ".csv", ".tsv", ".ods"}}
    config = json.loads(VERSION_CONFIG.read_text(encoding="utf-8"))
    require(config["vintage"] == END and config["historical_end"] == OLD_END, "version calendar mismatch")
    expected = config["new_sha256"]
    require(files == set(expected), f"data/New: unexpected/missing inputs {sorted(files ^ set(expected))}")
    for file, digest in expected.items():
        require(sha(NEW / file) == digest, f"data/New/{file}: input vintage hash differs")
    profiles, metadata, observations = [], {}, {}
    b = xlrd.open_workbook(NEW / EIA)
    require(b.sheet_names() == ["Contents", "Data 1"], "EIA: sheet names")
    contents, raw = b.sheets()
    require(contents.row_values(6)[1:5] == ["Data 1", BRENT, 1.0, "Monthly"], "EIA: indicator/frequency")
    require(raw.row_values(1) == ["Sourcekey", "RBRTE"] and raw.row_values(2) == ["Date", BRENT], "EIA: code/unit")
    dates = [xlrd.xldate_as_datetime(raw.cell_value(i, 0), b.datemode) for i in range(3, raw.nrows)]
    brent = keyed(months([d.replace(day=1) for d in dates], EIA), [number(raw.cell_value(i, 1), EIA) for i in range(3, raw.nrows)], EIA)
    observations["brent_usd"] = brent
    profile(profiles, EIA, "Data 1", BRENT, brent, "Excel 日期序号（月内日期映射到月初）", "USD/barrel", "brent_usd")
    metadata[EIA] = {"sheets_dimensions": f"Contents {contents.nrows}×{contents.ncols}; Data 1 {raw.nrows}×{raw.ncols}",
                     "metadata": "RBRTE；Contents 月频；Data 1 前三行为导航、序列代码和列头",
                     "acquired": str(contents.cell_value(contents.nrows-1, 5)) + "（文件内时间）"}
    sheets, created = xlsx_rows(NEW / FRED)
    doc, raw = sheets["README"], sheets["Monthly"]
    require(set(sheets) == {"README", "Monthly"} and tuple(raw[0]) == ("observation_date", "EXCHUS"), "FRED: header")
    require(any(r[0] == "EXCHUS" and "Chinese Yuan Renminbi to One U.S. Dollar, Monthly, Not Seasonally Adjusted" in r[1]
                for r in doc), "FRED: unit/frequency")
    fx = keyed(months([r[0] for r in raw[1:]], FRED), [number(r[1], FRED) for r in raw[1:]], FRED)
    observations["cny_per_usd"] = fx
    profile(profiles, FRED, "Monthly", "EXCHUS", fx, "Excel 日期", "CNY/USD", "cny_per_usd")
    metadata[FRED] = {"sheets_dimensions": f"README {len(doc)}×{len(doc[0])}; Monthly {len(raw)}×2",
                      "metadata": " | ".join(x for r in doc for x in r if isinstance(x, str)),
                      "acquired": next(r[0] for r in doc if str(r[0]).startswith("File Created:"))}
    for file, mapping in NBS_FIELDS.items():
        observed, metadata[file] = nbs_export(NEW / file, profiles, {v: k for k, v in mapping.items()})
        for key, label in mapping.items():
            observations[key] = observed[label]
    aux, metadata[IVA_CUM] = nbs_export(NEW / IVA_CUM, profiles, {})
    for key, label in NBS_FIELDS[IVA_MONTH].items():
        require(aux[label].equals(observations[key]), f"industrial exports conflict for {key}")
    _, metadata[TRANSPORT] = nbs_export(NEW / TRANSPORT, profiles, {})
    csv_text = (NEW / CUSTOMS).read_text(encoding="gb18030")
    rows = list(csv.reader(csv_text.splitlines(), strict=True))
    customs, raw_customs = customs_rows(rows, CUSTOMS, profiles)
    metadata[CUSTOMS] = {"sheets_dimensions": f"CSV {len(rows)}×{len(rows[0])}",
                        "metadata": "GB18030；空尾列；无进出口、伙伴、贸易方式或地区筛选字段。作者提供的进口导出。",
                        "acquired": "下载时间无内嵌元数据；2026-11-20 已取得"}
    require(list(customs.index) == list(calendar("2026-01", END)), "customs update calendar")
    return observations, customs, raw_customs, profiles, metadata


def reconcile(old, new, old_customs, new_customs):
    long = old.reindex(calendar(START["long"], END))
    long.index.name = "month"
    for variable, series in new.items():
        # A blank incoming field does not supersede a previous observed value.
        # Current and historical source documentation defines these structural industrial blanks.
        if variable == "indust_va_yoy":
            require(pd.isna(series.loc["2026-02"]) and "2026-01" not in series.index,
                    "2026-01/02 monthly IVA requires review; publication is Jan–Feb combined")
        observed = series.dropna().reindex(long.index).dropna()
        long.loc[observed.index, variable] = observed
    long["oil_rmb"] = long.brent_usd * long.cny_per_usd
    raw = old_customs.reindex(calendar(START["short"], END))
    raw.index.name = "month"
    raw.loc[new_customs.index, [KG, CNY]] = new_customs[[KG, CNY]]
    raw = raw.astype("int64")
    short = long.loc[START["short"]:].copy()
    short[QTY] = raw[KG] / 10**7
    short[VAL] = raw[CNY] / 10**8
    short[UV] = raw[CNY] / raw[KG]
    short[[KG, CNY]] = raw
    return {"long": long, "short": short}

