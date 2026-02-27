import pandas as pd
import os
import requests
import sqlite3
from pandas import json_normalize
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"
DB_PATH = "/home/shail/db/growth_nse_db.db"

MAIN_URL = 'https://www.nseindia.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': MAIN_URL
}

def get_data_from_url(url):
    """
    Optimized session handler: Initializes session, fetches JSON, 
    and returns a normalized DataFrame.
    """
    with requests.Session() as s:
        # NSE requires visiting the home page first to set cookies
        s.get(MAIN_URL, headers=HEADERS, timeout=10)
        resp = s.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = json_normalize(data['data'], sep='_')
        # Return cleaned DF (drop all-zero columns)
        return df.loc[:, (df != 0).any(axis=0)]

def fetch_cm_data(year, month):
    """Handles CM Market API logic"""
    short_yr = str(year)[-2:]
    mn = month
    #mn = month.upper()
    api = f'https://www.nseindia.com/api/historicalOR/cm/tbg/daily?month={mn}&year={short_yr}'
    
    df = get_data_from_url(api)
    renaming = {
        'data_F_TIMESTAMP':'Date', 'data_CDT_NOS_OF_SECURITY_TRADES': 'Trdstocks',
        'data_CDT_NOS_OF_TRADES': 'NoTrades', 'data_CDT_TRADES_QTY': 'Tvol',
        'data_CDT_TRADES_VALUES' : 'Tval'
    }
    df = df.rename(columns=renaming)
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')
    #df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df['Avg'] = round((df['Tval'] * 100) / (df['Tvol']), 2)
    cm_cols = ['Date', 'Trdstocks', 'NoTrades','Tval', 'Tvol', 'Avg']
    df = df[cm_cols].copy()
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    #df['Date'] = df['Date'].strftime('%Y-%m-%d')
    return df

def fetch_fno_data(year, month):
    """Handles F&O Market API logic"""
    long_yr = str(year)
    #mn = month.upper()
    mn = month
    api = f'https://www.nseindia.com/api/historicalOR/fo/tbg/daily?month={mn}&year={long_yr}'
    
    df = get_data_from_url(api)
    renaming = {
        'data_date':'Date','data_F&O_Total_QTY':'fnoTvol','data_F&O_Total_VAL':'fnoTval',
        'data_TOTAL_TRADED_PREM_VAL':'TpremVal', 'data_Stock_Futures_VAL':'eqFuval', 
        'data_Stock_Futures_QTY':'eqFuvol', 'data_F&O_Total_PREM_VAL':'fnoPremval',
        'data_F&O_Total_PUT_CALL_RATIO':'fnoPCR', 'data_Index_Options_VAL':'idxOpval',
        'data_Index_Options_QTY':'idxOpvol', 'data_Index_Options_PREM_VAL':'idxOppremval',
        'data_Index_Options_PUT_CALL_RATIO':'idxOpPCR', 'data_Index_Futures_VAL':'IdxFuVal',
        'data_Index_Futures_QTY':'idxFuvol', 'data_Stock_Options_VAL':'eqOpval',
        'data_Stock_Options_QTY':'eqOpvol', 'data_Stock_Options_PREM_VAL':'eqOppremval',
        'data_Stock_Options_PUT_CALL_RATIO':'eqOpPCR'
    }
    df = df.rename(columns=renaming)
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')
    fno_cols = ['Date', 'idxFuvol', 'IdxFuVal', 'eqFuvol', 'eqFuval', 'idxOpvol', 
                'idxOpval', 'idxOppremval', 'idxOpPCR', 'eqOpvol', 'eqOpval', 
                'eqOppremval', 'eqOpPCR', 'fnoTvol', 'fnoTval', 'TpremVal', 'fnoPCR']
    df = df[fno_cols].copy()
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    #df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')
    #df['Date'] = df['Date'].strftime('%Y-%m-%d')
    return df

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    now = datetime.now()
    curr_mn = now.strftime('%b')  # e.g., 'Jan'
    curr_yr_short = now.strftime('%y')  # e.g., '26'
    curr_yr_long = now.strftime('%Y')   # e.g., '2026'
    today_str = now.strftime('%Y-%m-%d') # e.g., '2026-Jan-08'

              
    DB_PATH = os.path.join(BASE_DIR_db, "growth_nse_db.db")
    conn = sqlite3.connect(DB_PATH)
    try:
        print(f"\n--- Processing {curr_mn} {curr_yr_long} ---")
        
        # 1. Fetch CM Data
        cmdata = fetch_cm_data(curr_yr_long, curr_mn)
        cm_today = cmdata[cmdata['Date'] == today_str]
        if not cm_today.empty:
            print(f"✓ Fetched {len(cm_today)} CM records.")
            # Save to DB logic here:
            cm_today.to_sql('cm_growth', conn, if_exists='append', index=False)
            #cmdata.to_sql('cm_growth', conn, if_exists='append', index=False)
        else:
            print(f"! No CM data for {curr_mn}.")

        # 2. Fetch FnO Data
        fnodata = fetch_fno_data(curr_yr_long, curr_mn)
        #target_date = target_date - timedelta(1)
        #yday = now - timedelta(1)
        #today_str = yday.strftime('%Y-%m-%d')
        fno_today = fnodata[fnodata['Date'] == today_str]
        if not fnodata.empty:
            print(f"✓ Fetched {len(fno_today)} F&O records.")
            # Save to DB logic here:
            #fnodata.to_sql('fno_growth', conn, if_exists='append', index=False)
            fno_today.to_sql('fno_growth', conn, if_exists='append', index=False)
        else:
            print(f"! No F&O data for {curr_mn}.")

    except Exception as e:
        print(f"Error processing {curr_mn}: {e}")
        #continue # Skip to next month if one fails
    conn.close()
    print ("*** Successfully complete the Task ***")
