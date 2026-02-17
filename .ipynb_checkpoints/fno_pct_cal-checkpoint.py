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
        df['Date'] = pd.to_datetime(df['Date'])
        dfs[name] = df

# Unpack
fii, fno, fuidx, fustk, oi, vol = dfs['fii'], dfs['fnototal'], dfs['fuidx'], dfs['fustk'], dfs['participant_oi'], dfs['participant_vol']

# Column definitions
fuidx_col = ['Date', 'clienttype', 'fuidxlong', 'fuidxshort']
opidx_col = ['Date', 'clienttype', 'opidxcalllong', 'opidxputshort','opidxputlong', 'opidxcallshort']
# Column Stock definitions
fustock_col = ['Date', 'clienttype', 'fustocklong', 'fustockshort']
opstock_col = ['Date', 'clienttype', 'opstockcalllong', 'opstockputshort','opstockputlong', 'opstockcallshort']

def calc_stock_pct(df, fustock_col, opstock_col):
    # --- Futures Index ---
    fustock = df[fustock_col].copy()
    fustock_pct = fustock[['Date','clienttype','fustocklong','fustockshort']]

    # --- Options Index ---
    opstock = df[opstock_col].copy()
    opstock['TotOpLong'] = opstock['opstockcalllong'] + opstock['opstockputshort']
    opstock['TotOpShort'] = opstock['opstockputlong'] + opstock['opstockcallshort']
    opstock_pct = opstock[['Date','clienttype','TotOpLong','TotOpShort']]

    # Merge futures + options
    merged = pd.merge(fustock_pct, opstock_pct, on=['Date','clienttype'], how='inner')

    # Extract TOTAL rows for each date
    totals = merged[merged['clienttype'] == 'TOTAL'].rename(columns={
        'fustocklong':'fustocklong_TOTAL',
        'fustockshort':'fustockshort_TOTAL',
        'TotOpLong':'TotOpLong_TOTAL',
        'TotOpShort':'TotOpShort_TOTAL'
    })[['Date','fustocklong_TOTAL','fustockshort_TOTAL','TotOpLong_TOTAL','TotOpShort_TOTAL']]

    # Join TOTAL values back to all rows
    merged = merged.merge(totals, on='Date', how='left')

    # --- Percentages relative to TOTAL row ---
    # Futures
    merged['fustocklng_pct'] = (merged['fustocklong'] / merged['fustocklong_TOTAL'] * 100).round(2)
    merged['fustocksht_pct'] = (merged['fustockshort'] / merged['fustockshort_TOTAL'] * 100).round(2)

    # Options
    merged['opstocklng_pct'] = (merged['TotOpLong'] / merged['TotOpLong_TOTAL'] * 100).round(2)
    merged['opstocksht_pct'] = (merged['TotOpShort'] / merged['TotOpShort_TOTAL'] * 100).round(2)

    # Final cleanup — sort descending by Date
    final = merged[['Date','clienttype',
                    'fustocklng_pct','fustocksht_pct',
                    'opstocklng_pct','opstocksht_pct']] \
            .sort_values(['Date','clienttype'], ascending=[False, True])

    return final


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
oi_fnoidx_pct['fuidxnet'] = oi_fnoidx_pct['fuidxlng_pct'] - oi_fnoidx_pct['fuidxsht_pct']
oi_fnoidx_pct['opidxnet'] = oi_fnoidx_pct['opidxlng_pct'] - oi_fnoidx_pct['opidxsht_pct']
vol_fnoidx_pct['fuidxnet'] = vol_fnoidx_pct['fuidxlng_pct'] - vol_fnoidx_pct['fuidxsht_pct']
vol_fnoidx_pct['opidxnet'] = vol_fnoidx_pct['opidxlng_pct'] - vol_fnoidx_pct['opidxsht_pct']

# Apply to Stock oi and vol
oi_fnostock_pct =  calc_stock_pct(oi, fustock_col, opstock_col)
vol_fnostock_pct =  calc_stock_pct(vol, fustock_col, opstock_col)
oi_fnostock_pct['fustocknet'] = oi_fnostock_pct['fustocklng_pct'] - oi_fnostock_pct['fustocksht_pct']
oi_fnostock_pct['opstocknet'] = oi_fnostock_pct['opstocklng_pct'] - oi_fnostock_pct['opstocksht_pct']
vol_fnostock_pct['fustocknet'] = vol_fnostock_pct['fustocklng_pct'] - vol_fnostock_pct['fustocksht_pct']
vol_fnostock_pct['opstocknet'] = vol_fnostock_pct['opstocklng_pct'] - vol_fnostock_pct['opstocksht_pct']


with sqlite3.connect(db_path) as conn:
    oi_fnoidx_pct.to_sql('fnoidx_pct_oi', conn, if_exists='replace', index=False)
    vol_fnoidx_pct.to_sql('fnoidx_pct_vol', conn, if_exists='replace', index=False)
    oi_fnostock_pct.to_sql('fnostk_pct_oi', conn, if_exists='replace', index=False)
    vol_fnostock_pct.to_sql('fnostk_pct_vol', conn, if_exists='replace', index=False)
    conn.commit()
print("The Task Completed Successfully at ", datetime.now())