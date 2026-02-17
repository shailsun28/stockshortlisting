import pandas as pd
from datetime import datetime
import sqlite3
import os 

print("The Task start at ", datetime.now())

BASE_DIR_db = "/home/shail/db"
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

# --- Load all tables into dictionary ---
with sqlite3.connect(db_path) as conn:
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
    dfs = {}
    for name in tables['name']:
        df = pd.read_sql_query(f'SELECT * FROM "{name}" ORDER BY Date DESC', conn)
        df = df.drop_duplicates()
        dfs[name] = df

# Unpack
fii, fno, fuidx, fustk, oi, vol = dfs['fii'], dfs['fnototal'], dfs['fuidx'], dfs['fustk'], dfs['participant_oi'], dfs['participant_vol']

# Column definitions
fuidx_col = ['Date', 'clienttype', 'fuidxlong', 'fuidxshort']
opidx_col = ['Date', 'clienttype', 'opidxcalllong', 'opidxputshort','opidxputlong', 'opidxcallshort']

def calc_pct(df, fuidx_col, opidx_col):
    """Calculate long/short percentages for futures index and options index."""
    # Futures Index
    fuidx = df[fuidx_col].copy()
    fuidx['fuidxlng_pct'] = round(fuidx['fuidxlong'] / (fuidx['fuidxlong'] + fuidx['fuidxshort']) * 100, 2)
    fuidx['fuidxsht_pct'] = round(fuidx['fuidxshort'] / (fuidx['fuidxlong'] + fuidx['fuidxshort']) * 100, 2)
    fuidx_pct = fuidx.loc[:, ['Date','clienttype'] + [c for c in fuidx.columns if c.endswith('_pct')]]

    # Options Index
    opidx = df[opidx_col].copy()
    opidx['TotOpLong'] = opidx['opidxcalllong'] + opidx['opidxputshort']
    opidx['TotOpShort'] = opidx['opidxputlong'] + opidx['opidxcallshort']
    opidx['opidxlng_pct'] = round((opidx['TotOpLong'] / (opidx['TotOpLong'] + opidx['TotOpShort'])) * 100, 2)
    opidx['opidxsht_pct'] = round((opidx['TotOpShort'] / (opidx['TotOpLong'] + opidx['TotOpShort'])) * 100, 2)
    opidx_pct = opidx.loc[:, ['Date','clienttype'] + [c for c in opidx.columns if c.endswith('_pct')]]

    # Merge
    return pd.merge(fuidx_pct, opidx_pct, on=['Date','clienttype'], how='inner')

# Apply to both oi and vol
oi_fnoidx_pct = calc_pct(oi, fuidx_col, opidx_col)
vol_fnoidx_pct = calc_pct(vol, fuidx_col, opidx_col)

print("The Task Completed Successfully at ", datetime.now())