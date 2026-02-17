import requests
import pandas as pd
import io, zipfile
from datetime import datetime, timedelta
import sqlite3
import os 
import re
#https://www.nseindia.com/api/daily-reports?key=FO
print ("The Task start at  ", datetime.now())
BASE_DIR_db = "/home/shail/db"
current_date = datetime.now()
download_date = current_date
#download_date = current_date - timedelta(1)

print (f' Getting daily reports for date {download_date}')
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

url_date = download_date.strftime('%d%m%Y')   # for URL
db_date = download_date.strftime('%Y-%m-%d')    # for DB storage

oi_url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{url_date}.csv"
vol_url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{url_date}.csv"
zip_url = f"https://nsearchives.nseindia.com/archives/fo/mkt/fo{url_date}.zip"


#def clean_columns(df):
def clean_columns(df, date_str):
    # Define replacements
    replacements = {
        "contract": "con",
        "traded": "Trd",
        "quantity": "Qty",
        "openinterest": "OI",
        "future": "fu",
        "option": "op",
        "index": "idx",
        "index": "idx",
        "total": "tot",
        "value": "val"
    }

    new_cols = []
    for col in df.columns:
        # Lowercase and strip spaces
        #df['Date'] = date_str
        #df = df.set_index('Date') 
        c = col.strip().lower()
        # Remove special characters
        c = re.sub(r"[ ,_.()]", "", c)
        # Apply replacements
        for k, v in replacements.items():
            c = c.replace(k, v)
        new_cols.append(c)

    df.columns = new_cols
    #df['Date'] = date_str
    #df = df.set_index('Date') 
    # Add Date column as the first column in the table.
    df.insert(0, "Date", date_str) # ensures Date is the first column
    return df

def csv_from_url(url):
    main_url = 'https://www.nseindia.com/all-reports'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.124 Safari/537.36',
        'Referer': main_url
    }
    
    session = requests.Session()
    try:
        # Warm up session to get cookies
        session.get(main_url, headers=headers)
        response = session.get(url, headers=headers)
        
        if response.status_code == 200:
            # Read CSV directly from response content
            file_stream = io.BytesIO(response.content)
            df = pd.read_csv(file_stream,skiprows=1)
            #df['Date'] = download_date.strftime('%Y-%m-%d')
            return df
        else:
            print(f"Failed to download. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f'An error occurred: {e}')
        return None



def df_from_zip(url):
    main_url = 'https://www.nseindia.com/all-reports'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': main_url
    }

    session = requests.Session()
    session.get(main_url, headers=headers)
    response = session.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to download. Status code: {response.status_code}")
        return None

    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    dfs = {}

    for fname in zip_file.namelist():
        if fname.endswith(".csv"):   # only process CSV files
            with zip_file.open(fname) as f:
                # Skip first line if it's metadata, drop empty rows
                df = pd.read_csv(f, skiprows=1, on_bad_lines="skip")
                df = df.dropna(how="all")
                #df['Date'] = download_date
                #df['Date'] = download_date.strftime('%Y-%m-%d')
                #df = df.set_index('Date') 

                # Remove .csv extension for dictionary key
                keyname = fname.replace(".csv", "")
                dfs[keyname] = df

    return dfs

# Usage
oi_df = csv_from_url(oi_url)
vol_df = csv_from_url(vol_url)
dfs_dict = df_from_zip(zip_url)

if dfs_dict:
    fo_df = dfs_dict[f"fo_{url_date}"]
    futidx_df = dfs_dict[f"futidx{url_date}"]
    futstk_df = dfs_dict[f"futstk{url_date}"]

oi_df = clean_columns(oi_df, db_date)
vol_df = clean_columns(vol_df, db_date)
fo_df = clean_columns(fo_df, db_date)
fuidx = clean_columns(futidx_df, db_date)
futstk_df = clean_columns(futstk_df, db_date)


#### Calculationg Avg and Value of OI eod for fuidx.
# --- Build TOTAL rows for fuidx ---
totals = fuidx.groupby("Date", as_index=False)[
    ["noofconsTrd","TrdQty","totTrdvalrsincrs","OIqtyasatendoftradinghrs"]
].sum()
totals["symbol"] = "TOTAL"

fuidx_with_total = pd.concat([fuidx, totals], ignore_index=True)
fuidx_with_total.sort_values(["Date","symbol"], ascending=False, inplace=True)
fuidx_with_total.reset_index(drop=True, inplace=True)
fuidx_with_total.head(6)
#df_with_totals = df_with_totals.sort_values(['Date','symbol']).reset_index(drop=True)
fuidx_val = fuidx_with_total.copy()
fuidx_val['ValPerQty'] = round(fuidx_val['totTrdvalrsincrs']*10000000 / fuidx_val['TrdQty'],3)
fuidx_val['OI_eod_val_cr'] = round(fuidx_val['OIqtyasatendoftradinghrs']*fuidx_val['ValPerQty']/ 1e7, 3)
reorder = ['Date', 'symbol', 'ValPerQty', 'noofconsTrd', 'TrdQty','OIqtyasatendoftradinghrs', 'totTrdvalrsincrs', 'OI_eod_val_cr']
fuidx_val = fuidx_val[reorder]
####
# Connect to SQLite
conn = sqlite3.connect(db_path)

# Save the two single CSV DataFrames
if oi_df is not None:
    oi_df.to_sql("participant_oi", conn, if_exists="append", index=False)
    print("Saved oi_df -> participant_oi")

if vol_df is not None:
    vol_df.to_sql("participant_vol", conn, if_exists="append", index=False)
    print("Saved vol_df -> participant_vol")

# Remove rows where product == 'Vol Futures'
#fo_df = fo_df[fo_df['product'] != 'Vol Futures']
# Drop rows where product contains 'Vol Futures' (case-insensitive, strip spaces) 
fo_df = fo_df[~fo_df['product'].str.strip().str.lower().eq('vol futures')]

# Save each extracted CSV from the ZIP into its own table
fo_df.to_sql("fnototal", conn, if_exists="append", index=False)
#futidx_df.to_sql("fuidx", conn, if_exists="append", index=False)
fuidx_val.to_sql("fuidx", conn, if_exists="append", index=False)
futstk_df = futstk_df.drop(columns=['sno'])
futstk_df.to_sql("fustk", conn, if_exists="append", index=False)

# Close connection
conn.close()
print (f"The Task Completed at  {datetime.now()} and file save to {db_path} ")
