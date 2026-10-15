"""Verified local raw exports -> masters -> canonical -> stationary transformations.
No network fetch, source mutation, interpolation, or hidden vintage substitution.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from interface import PACKAGE,external_directory,sha

def prepare(raw_data_dir,work_dir,config_path=None):
    raw=external_directory(raw_data_dir,'raw data directory')
    work=external_directory(work_dir,'work directory',create=True)
    if work==raw or work.is_relative_to(raw) or raw.is_relative_to(work):
        raise ValueError('raw and work directories must be disjoint')
    import raw_readers as rr
    from transformation_layer import transform
    from canonical_layer import build_oil_rmb,write_master_source,read_historical_stage
    from phase15_common import load_canonical
    contract=json.loads(Path(config_path or PACKAGE/'config/raw_inputs.json').read_text(encoding='utf-8'))
    receipt=[]
    for key,record in contract['files'].items():
        p=(raw/record['relative_path']).resolve()
        if not p.is_relative_to(raw):raise ValueError('input escaped raw directory')
        actual=sha(p)
        if actual!=record['sha256']:
            raise ValueError(f'{key}: input SHA mismatch; EXACT_VINTAGE_UNVERIFIED. Reconciliation requires review.')
        rr.FILES[key]=p
        receipt.append(dict(key=key,relative_path=record['relative_path'],sha256=actual))
    long=rr.build_long();short=rr.build_master()
    folder=work/'01_data';folder.mkdir(parents=True,exist_ok=True)
    source_folder=work/'source_representation';source_folder.mkdir(parents=True,exist_ok=True)
    metadata=[]
    for name,df,start,n in [('long',long,'1998-01',338),('short',short,'2015-01',134)]:
        # Restore the actual historical XLSX -> cleaned XLSX -> canonical stages.
        # These independent workbooks contain only this run's rebuilt raw values.
        source_path=write_master_source(df,source_folder/f'{name}_master_source.xlsx',formula_oil=name=='long')
        historical=read_historical_stage(source_path,source_folder/f'{name}_master_clean.xlsx')
        if len(historical)!=n or not pd.to_datetime(historical.month).equals(pd.to_datetime(df.month)):
            raise ValueError('historical source serialization changed calendar or row order')
        if name=='short':
            df=pd.read_excel(source_path,engine='openpyxl')
        df['month']=pd.to_datetime(df.month).dt.to_period('M').dt.to_timestamp()
        ix=pd.PeriodIndex(df.month,freq='M')
        if len(df)!=n or not ix.equals(pd.period_range(start,'2026-02',freq='M')):raise ValueError('invalid monthly calendar')
        for c in df.columns.drop('month'):df[c]=pd.to_numeric(df[c],errors='raise')
        for c in ['brent_usd','cny_per_usd','oil_rmb']:
            if df[c].isna().any() or (df[c]<=0).any():raise ValueError('invalid observed core price '+c)
        if not np.allclose(df.oil_rmb,df.brent_usd*df.cny_per_usd,rtol=0,atol=1e-8):raise ValueError('oil units')
        if name=='short':
            expected=10*df.import_crude_oil_value_100m_rmb/df.import_crude_oil_qty_10k_ton
            if not np.allclose(expected,df.import_crude_oil_unit_price_yuan_per_kg,rtol=0,atol=1e-8):raise ValueError('customs units')
        df.to_csv(folder/f'{name}_master.csv',index=False,encoding='utf-8-sig')
        # Apply the original source.notna() rule before adding auxiliary controls.
        df,oil_report=build_oil_rmb(historical,name)
        if name=='short':
            df=df.merge(long[['month','indust_va_yoy','indust_va_cum_yoy']],on='month',how='left',validate='one_to_one')
        df.to_csv(folder/f'{name}_sample_canonical.csv',index=False,encoding='utf-8-sig')
        # Original transformation_layer.run reads the persisted canonical CSV.
        transformed=transform(load_canonical(name))
        transformed.to_csv(folder/f'{name}_sample_transformed.csv',index=False,encoding='utf-8-sig')
        flags=pd.DataFrame({'month':df.month})
        for c in df.columns.drop('month'):flags[c+'_missing']=df[c].isna()
        flags.to_csv(folder/f'{name}_missing_flags.csv',index=False,encoding='utf-8-sig')
        for c in ('indust_va_yoy','indust_va_cum_yoy'):
            metadata.append(dict(sample=name,variable=c,calendar_N=n,observed_N=int(df[c].notna().sum()),missing_N=int(df[c].isna().sum()),
                 missing_months=';'.join(df.loc[df[c].isna(),'month'].dt.strftime('%Y-%m')),primary_policy='Not imputed; no industrial control in formal LP',
                 control_issue='Monthly and cumulative growth are distinct series',limitation='Original missing months retained'))
    (work/'03_tables').mkdir(parents=True,exist_ok=True)
    pd.DataFrame(metadata).to_csv(work/'03_tables/industrial_missing_accounting.csv',index=False,encoding='utf-8-sig')
    (work/'input_receipt.json').write_text(json.dumps({'status':'LOCAL_INPUT_HASH_MATCH','public_reconstruction':'EXACT_VINTAGE_UNVERIFIED','files':receipt},indent=2),encoding='utf-8')
    return receipt
