import numpy as np
import requests
import pandas as pd
from datetime import datetime
import sqlite3
import os
import io  # Required for in-memory processing

# Configuration
BASE_DIR_db = "/home/shail/db"
current_date = datetime.now()
print("The script started at ", current_date)
url_date = current_date.strftime('%d-%b-%Y')   # for URL
db_date = current_date.strftime('%Y-%m-%d')    # for DB storage
#formatted_date = current_date.strftime('%d-%b-%Y')
#formatted_date = '27-Jan-2026' 
url = f'https://nsearchives.nseindia.com/content/fo/fii_stats_{url_date}.xls'
print("The url is ", url)

def get_df_from_url(url):
    main_url = 'https://www.nseindia.com/all-reports'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': main_url
    }
    
    session = requests.Session()
    try:
        # Get cookies first
        session.get(main_url, headers=headers)
        response = session.get(url, headers=headers)
        
        if response.status_code == 200:
            # Use io.BytesIO to convert bytes into a file-like object
            file_stream = io.BytesIO(response.content)
            
            # Read Excel directly from the stream
            # engine='xlrd' is required for .xls files
            df = pd.read_excel(file_stream, skiprows=1, header=[0,1], engine='xlrd')
            return df
        else:
            print(f"Failed to download. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

def clean_fii_data(df):
    if df is None: return None

    # Flatten MultiIndex columns
    # We rename columns based on their position to avoid KeyError if labels shift
    new_cols = [
        'Product', 
        'Buy_Contracts', 'Buy_Amt_Cr', 
        'Sell_Contracts', 'Sell_Amt_Cr', 
        'OI_Contracts', 'OI_Amt_Cr'
    ]
    df.columns = new_cols

    # Filter out the 'Notes' or empty rows
    # Usually FII data has about 4-5 rows of products
    df = df[df['Product'].notna()]
    df = df[~df['Product'].astype(str).str.contains('Notes', case=False)]
    
    # Clean numeric columns (remove commas if any and convert to float)
    cols_to_fix = ['Buy_Contracts', 'Buy_Amt_Cr', 'Sell_Contracts', 'Sell_Amt_Cr', 'OI_Contracts', 'OI_Amt_Cr']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows where crucial data is missing
    df.dropna(subset=['Buy_Amt_Cr'], inplace=True)

    # Add Date
    df['Date'] = db_date
    
    # Reorder
    reorder_col = ['Date', 'Product', 'Buy_Contracts', 'Buy_Amt_Cr', 'Sell_Contracts', 'Sell_Amt_Cr', 'OI_Contracts', 'OI_Amt_Cr']
    return df[reorder_col]

# Execution
raw_df = get_df_from_url(url)
final_df = clean_fii_data(raw_df)

if final_df is not None:
    # Database operations
    if not os.path.exists(BASE_DIR_db):
        os.makedirs(BASE_DIR_db)
        
    db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")
    conn = sqlite3.connect(db_path)
    #df['Date'] = formatted_date
    final_df.to_sql('fii', conn, if_exists='append', index=False)
    conn.close()
    print(f"Successfully processed and saved to DB. Rows: {len(final_df)}")
else:
    print("Processing failed.")

print("The script Completed at ", datetime.now())
