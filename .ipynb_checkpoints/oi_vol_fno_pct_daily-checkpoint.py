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
        # Remove duplicates (keep first occurrence)
        df = df.drop_duplicates()
        dfs[name] = df

# Unpack
fii, fno, fuidx, fustk, oi, vol = dfs['fii'], dfs['fnototal'], dfs['fuidx'], dfs['fustk'], dfs['participant_oi'], dfs['participant_vol']

# --- Build TOTAL rows for fuidx ---
totals = fuidx.groupby("Date", as_index=False)[
    ["noofconsTrd","TrdQty","totTrdvalrsincrs","OIqtyasatendoftradinghrs"]
].sum()
totals["symbol"] = "TOTAL"

fuidx_with_total = pd.concat([fuidx, totals], ignore_index=True)
fuidx_with_total.sort_values(["Date","symbol"], ascending=False, inplace=True)

# --- Volume percentages (Index Futures) ---
fuidx_vol = vol[['Date', 'clienttype', 'fuidxlong','fuidxshort']].copy()

# Get TOTAL values per Date
totals_vol = fuidx_vol[fuidx_vol['clienttype'].str.upper() == 'TOTAL'][['Date','fuidxlong','fuidxshort']]
totals_vol = totals_vol.rename(columns={'fuidxlong':'total_long','fuidxshort':'total_short'})

# Merge back per Date
fuidx_vol = fuidx_vol.merge(totals_vol, on='Date', how='left')

# Calculate percentages per Date
fuidx_vol['fuidxlong_pct'] = (fuidx_vol['fuidxlong'] / fuidx_vol['total_long'] * 100).round(2)
fuidx_vol['fuidxshort_pct'] = (fuidx_vol['fuidxshort'] / fuidx_vol['total_short'] * 100).round(2)

# --- Add Index Futures values from fno ---
fno['product'] = fno['product'].str.strip()
idx_fut = fno[fno['product'] == 'Index Futures'][['Date','noofcons','Trdvalrscrs']]

fuidx_vol = fuidx_vol.merge(idx_fut, on='Date', how='left')

# Contract average value (lac)
fuidx_vol['conavg_lac'] = (fuidx_vol['Trdvalrscrs']*100 / fuidx_vol['noofcons']).round(3)

# Base calculations
fuidx_vol['Pbaselong_cr'] = (fuidx_vol['fuidxlong_pct'] / 100 * fuidx_vol['Trdvalrscrs']).round(2)
fuidx_vol['Pbaseshort_cr'] = (fuidx_vol['fuidxshort_pct'] / 100 * fuidx_vol['Trdvalrscrs']).round(2)

fuidx_vol['long_AvgbaseAmt_cr'] = (fuidx_vol['fuidxlong'] * fuidx_vol['conavg_lac']/100).round(3)
fuidx_vol['short_AvgbaseAmt_cr'] = (fuidx_vol['fuidxshort'] * fuidx_vol['conavg_lac']/100).round(3)

fuidx_pct_vol = fuidx_vol.copy()

# --- Open Interest percentages (Index Options) ---
opidx_oi = oi[['Date', 'clienttype', 'opidxcalllong','opidxcallshort', 'opidxputlong','opidxputshort']].copy()

# Get TOTAL values per Date
totals_oi = opidx_oi[opidx_oi['clienttype'].str.upper() == 'TOTAL'][[
    'Date','opidxcalllong','opidxcallshort','opidxputlong','opidxputshort'
]].rename(columns={
    'opidxcalllong':'totcall_long',
    'opidxcallshort':'totcall_short',
    'opidxputlong':'totput_long',
    'opidxputshort':'totput_short'
})

# Merge back per Date
opidx_oi = opidx_oi.merge(totals_oi, on='Date', how='left')

# Calculate percentages per Date
opidx_oi['opcalllong_pct']  = (opidx_oi['opidxcalllong'] / opidx_oi['totcall_long'] * 100).round(2)
opidx_oi['opcallshort_pct'] = (opidx_oi['opidxcallshort'] / opidx_oi['totcall_short'] * 100).round(2)
opidx_oi['opputlong_pct']   = (opidx_oi['opidxputlong'] / opidx_oi['totput_long'] * 100).round(2)
opidx_oi['opputshort_pct']  = (opidx_oi['opidxputshort'] / opidx_oi['totput_short'] * 100).round(2)

# --- Add Index Options values from fno ---
idx_op = fno[fno['product'] == 'Index Options'][['Date','noofcons','Trdvalrscrs']]
opidx_pct_oi = opidx_oi.merge(idx_op, on='Date', how='left')

# --- Reorder columns ---
volcol = ['Date', 'clienttype', 'fuidxlong', 'fuidxshort','fuidxlong_pct','fuidxshort_pct',
          'conavg_lac','Pbaselong_cr', 'Pbaseshort_cr', 'long_AvgbaseAmt_cr','short_AvgbaseAmt_cr',
          'noofcons', 'Trdvalrscrs']
opcol = ['Date', 'clienttype', 'opidxcalllong', 'opidxputshort','opidxputlong', 'opidxcallshort', 'opcalllong_pct',      'opputshort_pct','opputlong_pct', 'opcallshort_pct','noofcons', 'Trdvalrscrs']
         

fuidx_pct_vol = fuidx_pct_vol[volcol].drop_duplicates()
opidx_pct_oi = opidx_pct_oi[opcol].drop_duplicates()

# --- Save back to DB ---
with sqlite3.connect(db_path) as conn:
    fuidx_pct_vol.to_sql('fuidx_pct_vol', conn, if_exists='replace', index=False)
    opidx_pct_oi.to_sql('opidx_pct_oi', conn, if_exists='replace', index=False)
    conn.commit()

print("The Task Completed at ", datetime.now())
