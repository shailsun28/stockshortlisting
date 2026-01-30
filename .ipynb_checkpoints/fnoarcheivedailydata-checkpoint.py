import requests
import pandas as pd
import io, zipfile
from datetime import datetime, timedelta
import sqlite3
import os 
import re

print("The Task start at ", datetime.now())
BASE_DIR_db = "/home/shail/db"
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

# --- Column cleaning ---
def clean_columns(df, date_str):
    replacements = {
        "contract": "con",
        "traded": "Trd",
        "quantity": "Qty",
        "openinterest": "OI",
        "future": "fu",
        "option": "op",
        "index": "idx",
        "total": "tot",
        "value": "val"
    }
    new_cols = []
    for col in df.columns:
        c = col.strip().lower()
        c = re.sub(r"[ ,_.()]", "", c)
        for k, v in replacements.items():
            c = c.replace(k, v)
        new_cols.append(c)
    df.columns = new_cols
    df.insert(0, "Date", date_str)  # Date as first column
    return df

def csv_from_url(url):
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
            df = pd.read_csv(file_stream, skiprows=1, on_bad_lines="skip")
            return df
        else:
            return None
    except Exception as e:
        print(f'Error downloading {url}: {e}')
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
        return None
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    dfs = {}
    for fname in zip_file.namelist():
        if fname.endswith(".csv"):
            with zip_file.open(fname) as f:
                df = pd.read_csv(f, skiprows=1, on_bad_lines="skip")
                df = df.dropna(how="all")
                keyname = fname.replace(".csv", "")
                dfs[keyname] = df
    return dfs

# --- Loop over last 9 months ---
conn = sqlite3.connect(db_path)
current_date = datetime.now()
start_date = current_date - timedelta(days=270)

for day_offset in range((current_date - start_date).days + 1):
    download_date = start_date + timedelta(days=day_offset)
    url_date = download_date.strftime('%d%m%Y')   # for URL
    db_date = download_date.strftime('%Y-%m-%d')  # for DB storage

    print(f"Processing {db_date}...")

    oi_url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{url_date}.csv"
    vol_url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{url_date}.csv"
    zip_url = f"https://nsearchives.nseindia.com/archives/fo/mkt/fo{url_date}.zip"

    try:
        oi_df = csv_from_url(oi_url)
        if oi_df is not None:
            oi_df = clean_columns(oi_df, db_date)
            oi_df.to_sql("participant_oi", conn, if_exists="append", index=False)

        vol_df = csv_from_url(vol_url)
        if vol_df is not None:
            vol_df = clean_columns(vol_df, db_date)
            vol_df.to_sql("participant_vol", conn, if_exists="append", index=False)

        dfs_dict = df_from_zip(zip_url)
        if dfs_dict:
            fo_key = f"fo_{url_date}"
            futidx_key = f"futidx{url_date}"
            futstk_key = f"futstk{url_date}"

            if fo_key in dfs_dict:
                fo_df = clean_columns(dfs_dict[fo_key], db_date)
                # Drop Vol Futures rows
                if 'product' in fo_df.columns:
                    fo_df = fo_df[~fo_df['product'].str.strip().str.lower().eq('vol futures')]
                fo_df.to_sql("fnototal", conn, if_exists="append", index=False)

            if futidx_key in dfs_dict:
                futidx_df = clean_columns(dfs_dict[futidx_key], db_date)
                futidx_df.to_sql("fuidx", conn, if_exists="append", index=False)

            if futstk_key in dfs_dict:
                futstk_df = clean_columns(dfs_dict[futstk_key], db_date)
                futstk_df = futstk_df.drop(columns=['sno'])
                futstk_df.to_sql("fustk", conn, if_exists="append", index=False)

        print(f"Finished {db_date}")
    except Exception as e:
        print(f"Skipped {db_date} due to error: {e}")

conn.close()
print(f"The Task Completed at {datetime.now()} and file saved to {db_path}")
