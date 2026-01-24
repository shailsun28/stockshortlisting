import pandas as pd
import os
import requests
import sqlite3
from pandas import json_normalize
from datetime import datetime

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

# --- CONFIGURATION ---
DB_PATH = os.path.join(BASE_DIR_db, "growth_nse_db.db")
MAIN_URL = 'https://www.nseindia.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': MAIN_URL
}

# --- DATE SETUP ---
now = datetime.now()
curr_mn = now.strftime('%b')  # e.g., 'Jan'
curr_yr_short = now.strftime('%y')  # e.g., '26'
curr_yr_long = now.strftime('%Y')   # e.g., '2026'
today_str = now.strftime('%Y-%b-%d') # e.g., '2026-Jan-08'

def get_data(session, url):
    """Helper to fetch and normalize JSON data"""
    resp = session.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    df = json_normalize(data['data'], sep='_')
    return df.loc[:, (df != 0).any(axis=0)] # Drop all-zero columns

print(f"Task Started: {now}")
session = requests.Session()

try:
    # 1. Initialize Session
    session.get(MAIN_URL, headers=HEADERS)

    # --- PART A: CASH MARKET (CM) ---
    print(f"Fetching CM data for {curr_mn}...")
    #cm_api = f'www.nseindia.com{curr_mn}&year={curr_yr_short}'
    cm_api = f'https://www.nseindia.com/api/historicalOR/cm/tbg/daily?month={curr_mn}&year={curr_yr_short}'
    print (cm_api)
    cm_df = get_data(session, cm_api)
    
    cm_renaming = {
        'data_F_TIMESTAMP':'date',
        'data_CDT_NOS_OF_SECURITY_TRADES': 'Trdstocks',
        'data_CDT_NOS_OF_TRADES': 'NoTrades',
        'data_CDT_TRADES_QTY': 'Tvol',
        'data_CDT_TRADES_VALUES' : 'Tval'
    }
    cm_df.rename(columns=cm_renaming, inplace=True)
    cm_df['date'] = pd.to_datetime(cm_df['date'], format='%d-%b-%Y')
    cm_df['Avg'] = round((cm_df['Tval']*100)/(cm_df['Tvol']), 2)
    #cm_df['date'] = cm_df['date'].dt.strftime('%Y-%m-%d')
    
    # --- PART B: F&O MARKET ---
    print(f"Fetching FnO data for {curr_mn}...")
    fno_api = f'https://www.nseindia.com/api/historicalOR/fo/tbg/daily?month={curr_mn}&year={curr_yr_long}'
    print (fno_api)
    fno_df = get_data(session, fno_api)
    
    fno_renaming = {
        'data_date':'date','data_F&O_Total_QTY':'fnoTvol','data_F&O_Total_VAL':'fnoTval',
        'data_TOTAL_TRADED_PREM_VAL':'TpremVal', 'data_Stock_Futures_VAL':'eqFuval', 
        'data_Stock_Futures_QTY':'eqFuvol', 'data_F&O_Total_PREM_VAL':'fnoPremval',
        'data_F&O_Total_PUT_CALL_RATIO':'fnoPCR', 'data_Index_Options_VAL':'idxOpval',
        'data_Index_Options_QTY':'idxOpvol', 'data_Index_Options_PREM_VAL':'idxOppremval',
        'data_Index_Options_PUT_CALL_RATIO':'idxOpPCR', 'data_Index_Futures_VAL':'IdxFuVal',
        'data_Index_Futures_QTY':'idxFuvol', 'data_Stock_Options_VAL':'eqOpval',
        'data_Stock_Options_QTY':'eqOpvol', 'data_Stock_Options_PREM_VAL':'eqOppremval',
        'data_Stock_Options_PUT_CALL_RATIO':'eqOpPCR'
    }
    fno_df.rename(columns=fno_renaming, inplace=True)
    fno_df['date'] = pd.to_datetime(fno_df['date'], format='%d-%b-%Y')
    #fno_df['date'] = fno_df['date'].dt.strftime('%Y-%m-%d')

    # --- PART C: FILTER & SAVE TO DATABASE ---
    conn = sqlite3.connect(DB_PATH)
    
    # Save CM Today
    cm_today = cm_df[cm_df['date'] == today_str]
    if not cm_today.empty:
        cm_cols = ['Date', 'Trdstocks', 'NoTrades','Tval', 'Tvol', 'Avg']
        cm_today['Date'] = cm_today['Date'].dt.strftime('%Y-%m-%d')
        cm_today[cm_cols].to_sql('cm_growth', conn, if_exists='append', index=False)
        print("✓ CM row added.")
    
    # Save FnO Today
    fno_today = fno_df[fno_df['date'] == today_str]
    if not fno_today.empty:
        fno_cols = ['date', 'idxFuvol', 'IdxFuVal', 'eqFuvol', 'eqFuval', 'idxOpvol', 
                    'idxOpval', 'idxOppremval', 'idxOpPCR', 'eqOpvol', 'eqOpval', 
                    'eqOppremval', 'eqOpPCR', 'fnoTvol', 'fnoTval', 'TpremVal', 'fnoPCR']
        fno_today['date'] = fno_today['date'].dt.strftime('%Y-%m-%d')
        fno_today[fno_cols].to_sql('fno_growth', conn, if_exists='append', index=False)
        print("✓ FnO row added.")
        
    conn.close()

except Exception as e:
    print(f"Error: {e}")
finally:
    session.close()

print(f"Task Completed: {datetime.now()}")
