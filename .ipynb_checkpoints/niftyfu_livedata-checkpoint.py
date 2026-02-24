import requests
import time
import pandas as pd
import sqlite3
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_DIR_db = "/home/shail/db"

starttime = datetime.now()
print("\n****************** Script run started at ...", starttime)

db_path = os.path.join(BASE_DIR_db, 'fnolivedata.db')
conn = sqlite3.connect(db_path)

current_date = starttime.strftime('%Y-%m-%d')
main_url = 'https://www.nseindia.com'
#nbfu_url = "https://www.nseindia.com/api/liveEquity-derivatives?index=nifty_bank_fut"
niftyfu_url = "https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_fut"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': main_url,
    'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

session = requests.Session()
retry = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

try:
    session.get(main_url, headers=headers)
    time.sleep(1)
    response = session.get(niftyfu_url, headers=headers)
    response.raise_for_status()
    fno = response.json()

    df = pd.json_normalize(fno['data'])
    current_time = starttime.strftime('%H:%M')

    df['Time'] = current_time
    df['Date'] = current_date
    fetch_date, fetch_time = fno['timestamp'].split()
    df['Fetchdate'] = fetch_date
    df['Fetchtime'] = fetch_time

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    df = pd.DataFrame()  # empty fallback

# Select required columns safely
reqcol = ['underlying', 'Date', 'Fetchtime','instrumentType', 'contract',
          'lastPrice', 'change','pChange','highPrice', 'lowPrice', 'volume',
          'totalTurnover', 'value', 'premiumTurnOver', 'underlyingValue',
          'openInterest', 'noOfTrades', 'Time']

df = df[[c for c in reqcol if c in df.columns]]

# Save to SQL table
table_name = "niftyfu_live"
df.to_sql(table_name, conn, if_exists='append', index=False)

endtime = datetime.now()
elapsed = endtime - starttime
total_seconds = elapsed.total_seconds()
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)
milliseconds = int((total_seconds - int(total_seconds)) * 1000)

print(f"The time taken to complete the task is {minutes}:{seconds:02d}.{milliseconds:03d}")
print(df.head())

conn.close()
