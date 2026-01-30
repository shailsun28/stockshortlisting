import requests
import pandas as pd
import io, zipfile
from datetime import datetime, timedelta
import sqlite3
import os 
import re

BASE_DIR_db = "/home/shail/db"
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

# Connect to SQLite
conn = sqlite3.connect(db_path)

# Get list of all tables
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
table_names = tables['name'].tolist()

# Dictionary to hold DataFrames
dfs = {}

for name in table_names:
    try:
        query = f'SELECT * FROM "{name}" ORDER BY Date DESC'
        df = pd.read_sql_query(query, conn)
        dfs[name] = df
        print(f"Loaded table: {name}, rows: {len(df)}")
    except Exception as e:
        print(f"Skipped table {name} due to error: {e}")

conn.close()
fii = dfs['fii']
fno = dfs['fnototal']
fuidx = dfs['fuidx']
fustk = dfs['fustk']
oi = dfs['participant_oi']
vol = dfs['participant_vol']


# Select only the relevant columns from vol
fuidx_vol = vol[['Date', 'clienttype', 'fuidxlong','fuidxshort']].copy()

# Get TOTAL values for the same Date
mask_total = fuidx_vol['clienttype'].str.upper() == 'TOTAL'
total_long = fuidx_vol.loc[mask_total, 'fuidxlong'].values[0]
total_short = fuidx_vol.loc[mask_total, 'fuidxshort'].values[0]

# Calculate percentages
fuidx_vol['fuidxlong_pct'] = (fuidx_vol['fuidxlong'] / total_long * 100).round(3)
fuidx_vol['fuidxshort_pct'] = (fuidx_vol['fuidxshort'] / total_short * 100).round(3)

# --- Dynamically get total_val and totvolavg from fno ---
# Merge fuidx_vol with fno to bring in Index Futures values for the same Date
fno['product'] = fno['product'].str.strip()
idx_fut = fno[fno['product'] == 'Index Futures'][['Date','noofcons','Trdvalrscrs']]

# Join on Date
fuidx_vol = fuidx_vol.merge(idx_fut, on='Date', how='left')

# total_val = Trdvalrscrs (in crores)
#fuidx_vol['Trdvalrscrs'] = fno['Trdvalrscrs']

# totvolavg = Trdvalrscrs / noofcons (crores per contract), rounded to 3 decimals
fuidx_vol['conavg_lac'] = (fuidx_vol['Trdvalrscrs']*100 / fuidx_vol['noofcons']).round(3)

# Calculate Pbaselong_cr and Pbaseshort_cr using dynamic total_val
fuidx_vol['Pbaselong_cr'] = (fuidx_vol['fuidxlong_pct'] / 100 * fuidx_vol['Trdvalrscrs']).round(3)
fuidx_vol['Pbaseshort_cr'] = (fuidx_vol['fuidxshort_pct'] / 100 * fuidx_vol['Trdvalrscrs']).round(3)

# Calculate AvgbaseAmt_cr using dynamic totvolavg
fuidx_vol['long_AvgbaseAmt_cr'] = (fuidx_vol['fuidxlong'] * fuidx_vol['conavg_lac']/100).round(3)
fuidx_vol['short_AvgbaseAmt_cr'] = (fuidx_vol['fuidxshort'] * fuidx_vol['conavg_lac']/100).round(3)

fuidx_vol.head()
