"""Source-format readers; inputs are supplied explicitly by the data interface."""
import re
from pathlib import Path
import pandas as pd
FILES={}

def ym_to_str(s):
    if pd.isna(s): return None
    s = str(s).strip()
    m = re.match(r"(\d{4})年(\d{1,2})月", s)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}"
    try: return pd.to_datetime(s).strftime("%Y-%m")
    except: return None

def read_wide_excel_xlsx(path: Path):
    df = pd.read_excel(path, header=None, engine="openpyxl")
    headers = df.iloc[2].tolist()
    df2 = df.iloc[3:].copy()
    df2.columns = headers
    return df2[df2["指标"].notna()].copy()

def read_wide_csv(path: Path):
    df = pd.read_csv(path, encoding="gbk", skiprows=2)
    return df[df["指标"].notna()].copy()

def extract_row(df, labels):
    if isinstance(labels, str): labels = [labels]
    for label in labels:
        row = df[df["指标"] == label]
        if not row.empty:
            row = row.iloc[0]
            out = []
            for col in df.columns[1:]:
                month = ym_to_str(col)
                if month is None: continue
                val = row[col]
                if pd.notna(val): out.append((month, val))
            return pd.DataFrame(out, columns=["month","value"]).sort_values("month")
    return pd.DataFrame(columns=["month","value"])

def build_long():
    months = pd.period_range("1998-01", "2026-02", freq="M").strftime("%Y-%m")
    master = pd.DataFrame({"month": months})

    # Brent
    eia = pd.read_csv(FILES["eia"], skiprows=4)
    eia["month"] = pd.to_datetime(eia["Month"], format="%b %Y").dt.strftime("%Y-%m")
    price_col = [c for c in eia.columns if c != "Month"][0]
    eia = eia[["month", price_col]].rename(columns={price_col:"brent_usd"})
    master = master.merge(eia, on="month", how="left")

    # FX
    fred = pd.read_excel(FILES["fred"], sheet_name="Monthly", engine="openpyxl")
    fred["month"] = pd.to_datetime(fred["observation_date"]).dt.strftime("%Y-%m")
    fred = fred[["month","EXCHUS"]].rename(columns={"EXCHUS":"cny_per_usd"})
    master = master.merge(fred, on="month", how="left")

    # Match the historical long workbook header before subsequent merges.
    master.insert(3, 'oil_rmb', master.brent_usd * master.cny_per_usd)

    # CPI (4 periods)
    cpi_dfs = {
        "98_15": read_wide_excel_xlsx(FILES["cpi_98_15"]),
        "16_20": read_wide_excel_xlsx(FILES["cpi_16_20"]),
        "21_25": read_wide_excel_xlsx(FILES["cpi_21_25"]),
        "26": read_wide_excel_xlsx(FILES["cpi_26"]),
    }
    labelsets = {
        "cpi_yoy": [["居民消费价格指数(上年同月=100)"]],
        "cpi_transport_comm_yoy": [
            ["交通和通讯类居民消费价格指数(上年同月=100)"],
            ["交通和通信类居民消费价格指数(上年同月=100)"],
            ["交通通信类居民消费价格指数(上年同月=100)"],
        ],
        "core_cpi_proxy_yoy": [["不包括食品和能源居民消费价格指数(上年同月=100)"]],
    }
    for out_col, alias_groups in labelsets.items():
        parts = []
        for df in cpi_dfs.values():
            found = pd.DataFrame(columns=["month","value"])
            for labels in alias_groups:
                found = extract_row(df, labels)
                if not found.empty: break
            if not found.empty: parts.append(found)
        if parts:
            series = pd.concat(parts, ignore_index=True).drop_duplicates("month", keep="first").sort_values("month")
            series = series.rename(columns={"value": out_col})
            master = master.merge(series, on="month", how="left")
        else:
            master[out_col] = pd.NA

    # PPI
    ppi_df = read_wide_csv(FILES["ppi"])
    ppip_df = read_wide_csv(FILES["ppi_purchase"])
    ppi = extract_row(ppi_df, "工业生产者出厂价格指数(上年同月=100)").rename(columns={"value":"ppi_yoy"})
    ppi_purchase = extract_row(ppip_df, "工业生产者购进价格指数(上年同月=100)").rename(columns={"value":"ppi_purchase_yoy"})
    ppi_fuel = extract_row(ppip_df, "燃料、动力类购进价格指数(上年同月=100)").rename(columns={"value":"ppi_fuel_power_yoy"})
    master = master.merge(ppi, on="month", how="left").merge(ppi_purchase, on="month", how="left").merge(ppi_fuel, on="month", how="left")

    # Industrial VA
    iva_df = read_wide_csv(FILES["iva"])
    iva_yoy = extract_row(iva_df, "规上工业增加值同比增长(%)").rename(columns={"value":"indust_va_yoy"})
    iva_cum = extract_row(iva_df, "规上工业增加值累计增长(%)").rename(columns={"value":"indust_va_cum_yoy"})
    master = master.merge(iva_yoy, on="month", how="left").merge(iva_cum, on="month", how="left")

    return master

def build_master():
    months = pd.period_range("2015-01", "2026-02", freq="M").strftime("%Y-%m")
    master = pd.DataFrame({"month": months})

    # 1) Brent
    eia = pd.read_csv(FILES["eia"], skiprows=4)
    eia["month"] = pd.to_datetime(eia["Month"], format="%b %Y").dt.strftime("%Y-%m")
    price_col = [c for c in eia.columns if c != "Month"][0]
    eia = eia[["month", price_col]].rename(columns={price_col: "brent_usd"})
    master = master.merge(eia, on="month", how="left")

    # 2) Exchange rate
    fred = pd.read_excel(FILES["fred"], sheet_name="Monthly", engine="openpyxl")
    fred["month"] = pd.to_datetime(fred["observation_date"]).dt.strftime("%Y-%m")
    fred = fred[["month", "EXCHUS"]].rename(columns={"EXCHUS": "cny_per_usd"})
    master = master.merge(fred, on="month", how="left")

    # 3) CPI
    cpi_dfs = {
        "cpi_98_15": read_wide_excel_xlsx(FILES["cpi_98_15"]),
        "cpi_16_20": read_wide_excel_xlsx(FILES["cpi_16_20"]),
        "cpi_21_25": read_wide_excel_xlsx(FILES["cpi_21_25"]),
        "cpi_26": read_wide_excel_xlsx(FILES["cpi_26"]),
    }

    labelsets = {
        "cpi_yoy": [
            ["居民消费价格指数(上年同月=100)"],
        ],
        "cpi_transport_comm_yoy": [
            ["交通和通讯类居民消费价格指数(上年同月=100)"],
            ["交通和通信类居民消费价格指数(上年同月=100)"],
            ["交通通信类居民消费价格指数(上年同月=100)"],
        ],
        "core_cpi_proxy_yoy": [
            ["不包括食品和能源居民消费价格指数(上年同月=100)"],
        ],
    }

    for out_col, alias_groups in labelsets.items():
        parts = []
        for _, df in cpi_dfs.items():
            found = pd.DataFrame(columns=["month", "value"])
            for labels in alias_groups:
                found = extract_row(df, labels)
                if not found.empty:
                    break
            if not found.empty:
                parts.append(found)
        if parts:
            series = pd.concat(parts, ignore_index=True).drop_duplicates("month", keep="first").sort_values("month")
            series = series.rename(columns={"value": out_col})
            master = master.merge(series, on="month", how="left")
        else:
            master[out_col] = pd.NA

    # 4) PPI
    ppi_df = read_wide_csv(FILES["ppi"])
    ppi_purchase_df = read_wide_csv(FILES["ppi_purchase"])

    ppi = extract_row(ppi_df, "工业生产者出厂价格指数(上年同月=100)").rename(columns={"value": "ppi_yoy"})
    ppi_purchase = extract_row(ppi_purchase_df, "工业生产者购进价格指数(上年同月=100)").rename(columns={"value": "ppi_purchase_yoy"})
    ppi_fuel = extract_row(ppi_purchase_df, "燃料、动力类购进价格指数(上年同月=100)").rename(columns={"value": "ppi_fuel_power_yoy"})

    master = master.merge(ppi, on="month", how="left")
    master = master.merge(ppi_purchase, on="month", how="left")
    master = master.merge(ppi_fuel, on="month", how="left")

    # 5) Customs crude-oil import data
    customs = pd.read_excel(FILES["customs"], engine="openpyxl")
    customs["商品编码"] = pd.to_numeric(customs["商品编码"], errors="coerce")
    crude = customs[customs["商品编码"] == 27090000].copy()
    crude["month"] = pd.to_datetime(crude["数据年月"].astype(str), format="%Y%m").dt.strftime("%Y-%m")
    crude["import_crude_oil_qty_10k_ton"] = pd.to_numeric(crude["第一数量"], errors="coerce") / 1e7
    crude["import_crude_oil_value_100m_rmb"] = pd.to_numeric(crude["人民币"], errors="coerce") / 1e8
    crude["import_crude_oil_unit_price_yuan_per_kg"] = (
        pd.to_numeric(crude["人民币"], errors="coerce") / pd.to_numeric(crude["第一数量"], errors="coerce")
    )
    crude = crude[[
        "month",
        "import_crude_oil_qty_10k_ton",
        "import_crude_oil_value_100m_rmb",
        "import_crude_oil_unit_price_yuan_per_kg",
    ]]
    master = master.merge(crude, on="month", how="left")

    # 6) Derived variables
    master["oil_rmb"] = master["brent_usd"] * master["cny_per_usd"]

    ordered_cols = [
        "month",
        "brent_usd",
        "cny_per_usd",
        "oil_rmb",
        "cpi_yoy",
        "cpi_transport_comm_yoy",
        "core_cpi_proxy_yoy",
        "ppi_yoy",
        "ppi_purchase_yoy",
        "ppi_fuel_power_yoy",
        "import_crude_oil_qty_10k_ton",
        "import_crude_oil_value_100m_rmb",
        "import_crude_oil_unit_price_yuan_per_kg",
    ]
    return master[ordered_cols]
