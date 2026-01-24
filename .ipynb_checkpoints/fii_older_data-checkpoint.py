import numpy as np
import requests
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os
import io  # Required for in-memory processing

# Configuration
BASE_DIR_db = "/home/shail/db"
current_date = datetime.now()
print("The script started at ", current_date)

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

# --- Loop over last 9 months ---
start_date = current_date - timedelta(days=270)  # ~9 months
conn = sqlite3.connect(db_path)

for day_offset in range((current_date - start_date).days + 1):
    download_date = start_date + timedelta(days=day_offset)
    formatted_date = download_date.strftime('%d-%b-%Y')  # e.g. 16-Jan-2026
    url = f'https://nsearchives.nseindia.com/content/fo/fii_stats_{formatted_date}.xls'

    try:
        raw_df = get_df_from_url(url)
        final_df = clean_fii_data(raw_df, formatted_date)
        if final_df is not None and not final_df.empty:
            final_df.to_sql('fii', conn, if_exists='append', index=False)
            print(f"Saved FII data for {formatted_date}, rows: {len(final_df)}")
        else:
            print(f"No data for {formatted_date}")
    except Exception as e:
        print(f"Skipped {formatted_date} due to error: {e}")

conn.close()
print("The script Completed at ", datetime.now())
