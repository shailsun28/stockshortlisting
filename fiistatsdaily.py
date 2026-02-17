import numpy as np
import requests
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os
import io  # Required for in-memory processing

# Configuration
BASE_DIR_db = "/home/shail/db"
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

def get_df_from_url(url):
    main_url = 'https://www.nseindia.com/all-reports'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': main_url
    }
    session = requests.Session()
    try:
        session.get(main_url, headers=headers)
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_stream = io.BytesIO(response.content)
            df = pd.read_excel(file_stream, skiprows=1, header=[0,1], engine='xlrd')
            return df
        else:
            print(f"File not available for {url} (status {response.status_code})")
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def clean_fii_data(df, date_str):
    if df is None: 
        return None
    new_cols = [
        'Product', 
        'Buy_Contracts', 'Buy_Amt_Cr', 
        'Sell_Contracts', 'Sell_Amt_Cr', 
        'OI_Contracts', 'OI_Amt_Cr'
    ]
    df.columns = new_cols
    df = df[df['Product'].notna()]
    df = df[~df['Product'].astype(str).str.contains('Notes', case=False)]
    cols_to_fix = ['Buy_Contracts', 'Buy_Amt_Cr', 'Sell_Contracts', 'Sell_Amt_Cr', 'OI_Contracts', 'OI_Amt_Cr']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=['Buy_Amt_Cr'], inplace=True)
    df['Date'] = date_str
    reorder_col = ['Date', 'Product', 'Buy_Contracts', 'Buy_Amt_Cr', 'Sell_Contracts', 'Sell_Amt_Cr', 'OI_Contracts', 'OI_Amt_Cr']
    return df[reorder_col]

# --- Single date execution ---

target_date = datetime.now()
print ("The script started at ", target_date)
target_date = target_date - timedelta(1)

url_date = target_date.strftime('%d-%b-%Y')   # for URL
db_date = target_date.strftime('%Y-%m-%d')    # for DB storage

url = f'https://nsearchives.nseindia.com/content/fo/fii_stats_{url_date}.xls'
print (f"getting fii data for {url_date} and the fetching url is {url}")

print("The script started at ", datetime.now())
conn = sqlite3.connect(db_path)

try:
    raw_df = get_df_from_url(url)
    final_df = clean_fii_data(raw_df, db_date)
    if final_df is not None and not final_df.empty:
        final_df['NetAmt_cr'] = final_df['Buy_Amt_Cr'] - final_df['Sell_Amt_Cr']
        final_df['Netcon'] = final_df['Buy_Contracts'] - final_df['Sell_Contracts']
        final_df.to_sql('fii', conn, if_exists='append', index=False)
        print(f"Saved FII data for {db_date}, rows: {len(final_df)}")
    else:
        print(f"No data for {db_date}")
except Exception as e:
    print(f"Skipped {db_date} due to error: {e}")

conn.close()
print("The script Completed at ", datetime.now())
