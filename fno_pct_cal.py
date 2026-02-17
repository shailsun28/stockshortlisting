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
    # --- Futures Index ---
    fuidx = df[fuidx_col].copy()
    fuidx_pct = fuidx[['Date','clienttype','fuidxlong','fuidxshort']]

    # --- Options Index ---
    opidx = df[opidx_col].copy()
    opidx['TotOpLong'] = opidx['opidxcalllong'] + opidx['opidxputshort']
    opidx['TotOpShort'] = opidx['opidxputlong'] + opidx['opidxcallshort']
    opidx_pct = opidx[['Date','clienttype','TotOpLong','TotOpShort']]

    # Merge futures + options
    merged = pd.merge(fuidx_pct, opidx_pct, on=['Date','clienttype'], how='inner')

    # Extract TOTAL rows for each date
    totals = merged[merged['clienttype'] == 'TOTAL'].rename(columns={
        'fuidxlong':'fuidxlong_TOTAL',
        'fuidxshort':'fuidxshort_TOTAL',
        'TotOpLong':'TotOpLong_TOTAL',
        'TotOpShort':'TotOpShort_TOTAL'
    })[['Date','fuidxlong_TOTAL','fuidxshort_TOTAL','TotOpLong_TOTAL','TotOpShort_TOTAL']]

    # Join TOTAL values back to all rows
    merged = merged.merge(totals, on='Date', how='left')

    # --- Percentages relative to TOTAL row ---
    # Futures
    merged['fuidxlng_pct'] = (merged['fuidxlong'] / merged['fuidxlong_TOTAL'] * 100).round(2)
    merged['fuidxsht_pct'] = (merged['fuidxshort'] / merged['fuidxshort_TOTAL'] * 100).round(2)

    # Options
    merged['opidxlng_pct'] = (merged['TotOpLong'] / merged['TotOpLong_TOTAL'] * 100).round(2)
    merged['opidxsht_pct'] = (merged['TotOpShort'] / merged['TotOpShort_TOTAL'] * 100).round(2)

    # Final cleanup — sort descending by Date
    final = merged[['Date','clienttype',
                    'fuidxlng_pct','fuidxsht_pct',
                    'opidxlng_pct','opidxsht_pct']] \
            .sort_values(['Date','clienttype'], ascending=[False, True])

    return final


# Apply to both oi and vol
oi_fnoidx_pct = calc_pct(oi, fuidx_col, opidx_col)
vol_fnoidx_pct = calc_pct(vol, fuidx_col, opidx_col)

print("The Task Completed Successfully at ", datetime.now())