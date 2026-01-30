import httpx
import time
import pandas as pd
import sqlite3
import re
from datetime import datetime
import os

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"


#def clean_table_name(name):
    # Replaces spaces and special characters with underscores for SQL compatibility
#    return re.sub(r'\W+', '_', name).strip('_')
def clean_table_name(name):
    # 1. Replace spaces and special characters with underscores
    cleaned = re.sub(r'\W+', '_', name).strip('_')
    # 2. Remove "NIFTY" prefix (case-insensitive)
    no_nifty = re.sub(r'^NIFTY_', '', cleaned, flags=re.IGNORECASE)
    # Ensure any residual leading/trailing underscores are removed
    return no_nifty.strip('_')
print('Task start at ... ', datetime.now())
#dx_path = "/Users/shail/Documents/Trading/market-turnover/db/allindices.db"
idx_path = os.path.join(BASE_DIR_db, "allindices.db")
conn = sqlite3.connect(idx_path)

indices = [
    "NIFTY 50", "NIFTY BANK", "NIFTY AUTO", "NIFTY FINANCIAL SERVICES", 
    "NIFTY FMCG", "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
    "NIFTY PSU BANK", "NIFTY PRIVATE BANK", "NIFTY REALTY", "NIFTY HEALTHCARE INDEX",
    "NIFTY CONSUMER DURABLES", "NIFTY OIL & GAS", "NIFTY MIDSMALL HEALTHCARE","NIFTY TOTAL MARKET"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "www.nseindia.com",
    "Accept-Encoding": "gzip, deflate, br"
}

nfcolumns = ['symbol', 'Date', 'Time', 'dayHigh', 'dayLow',
            'lastPrice', 'change', 'pChange', 'ffmc',
            'totalTradedVolume', 'totalTradedValue','nearWKH', 'nearWKL','advances','declines','unchanged']

# Use a session with automatic decompression enabled
with httpx.Client(follow_redirects=True) as client:
    try:
        # Step 1: Initialize cookies
        client.get("https://www.nseindia.com", headers=headers)
        time.sleep(1)

        for index in indices:
            formatted_index = index.replace(" ", "%20").replace("&", "%26")
            #api_url = f"www.nseindia.com{formatted_index}"
            api_url = f"https://www.nseindia.com/api/equity-stockIndices?index={formatted_index}"
            
            try:
                response = client.get(api_url, headers=headers)
                response.raise_for_status()
                
                # httpx automatically decompresses if 'brotli' is installed
                data2 = response.json()

                if "data" in data2 and data2["data"]:
                    # Normalize first row of data and advance info
                    df_main = pd.json_normalize(data2["data"][0])
                    df_adv = pd.json_normalize(data2['advance'])
                    df = pd.concat([df_main, df_adv], axis=1)
                    
                    # Process timestamps
                    dt_obj = pd.to_datetime(df['lastUpdateTime'].iloc[0], format="%d-%b-%Y %H:%M:%S")
                    df['Date'] = dt_obj.date()
                    df['Time'] = dt_obj.strftime("%H:%M:%S")
                    
                    # Save to individual table
                    table_name = clean_table_name(index)
                    df[nfcolumns].to_sql(table_name, conn, if_exists='append', index=False)
                    print(f"Exported: {table_name}")

                time.sleep(1)

            except Exception as e:
                print(f"Error for {index}: {e}")

    except Exception as e:
        print(f"Connection error: {e}")

conn.close()
print('Completed Successfully', datetime.now())