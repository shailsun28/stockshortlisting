import requests
import pandas as pd
import io, zipfile
from datetime import datetime, timedelta
import sqlite3
import os, re

print("The Task start at ", datetime.now())
BASE_DIR_db = "/home/shail/db"
current_date = datetime.now()
db_path = os.path.join(BASE_DIR_db, "fnodailydata.db")

# --- Column cleaning ---
def clean_columns(df):
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
    return df

# --- CSV download ---
def csv_from_url(url, date_str):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/all-reports"}
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com/all-reports", headers=headers)
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_stream = io.BytesIO(response.content)
            df = pd.read_csv(file_stream, skiprows=1, on_bad_lines="skip")
            df["Date"] = date_str
            return clean_columns(df)
        else:
            print(f"File not available for {date_str} (status {response.status_code})")
            return None
    except Exception as e:
        print(f"Error downloading {url} for {date_str}: {e}")
        return None

# --- ZIP download ---
def df_from_zip(url, date_str):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/all-reports"}
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com/all-reports", headers=headers)
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            print(f"ZIP not available for {date_str} (status {response.status_code})")
            return None
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        dfs = {}
        for fname in zip_file.namelist():
            if fname.endswith(".csv"):
                with zip_file.open(fname) as f:
                    df = pd.read_csv(f, skiprows=1, on_bad_lines="skip")
                    df = df.dropna(how="all")
                    df["Date"] = date_str
                    df = clean_columns(df)
                    dfs[fname.replace(".csv", "")] = df
        return dfs
    except Exception as e:
        print(f"Error processing ZIP for {date_str}: {e}")
        return None

# --- Loop over last 9 months ---
conn = sqlite3.connect(db_path)
start_date = current_date - timedelta(days=270)  # ~9 months

for day_offset in range((current_date - start_date).days + 1):
    download_date = start_date + timedelta(days=day_offset)
    date_str = download_date.strftime("%Y-%m-%d")
    dmy_str = download_date.strftime("%d%m%Y")

    oi_url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{dmy_str}.csv"
    vol_url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{dmy_str}.csv"
    zip_url = f"https://nsearchives.nseindia.com/archives/fo/mkt/fo{dmy_str}.zip"

    try:
        oi_df = csv_from_url(oi_url, date_str)
        if oi_df is not None:
            oi_df.to_sql("participant_oi", conn, if_exists="append", index=False)

        vol_df = csv_from_url(vol_url, date_str)
        if vol_df is not None:
            vol_df.to_sql("participant_vol", conn, if_exists="append", index=False)

        dfs_dict = df_from_zip(zip_url, date_str)
        if dfs_dict:
            for name, df in dfs_dict.items():
                df.to_sql(name, conn, if_exists="append", index=False)

        print(f"Processed {date_str}")
    except Exception as e:
        print(f"Skipped {date_str} due to error: {e}")

conn.close()
print(f"The Task Completed at {datetime.now()} and file saved to {db_path}")
