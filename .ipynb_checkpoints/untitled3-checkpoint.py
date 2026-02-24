import requests
import json
import time
import pandas as pd  # Ensure Pandas is installed
import sqlite3
import os
from datetime import datetime, date
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

starttime = datetime.now()
print("\2\n"+ " ******************  Script run started  at ...   ", starttime)

db_path = os.path.join(BASE_DIR_db, 'idxfutures.db')

df.to_sql(filename, conn, if_exists='append', index=False)
current_date = starttime.strftime('%Y-%m-%d')
main_url = 'https://www.nseindia.com'
#fno_url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol={encoded_stock}'
#fno_url = "https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_fut"
nbfu_url = "https://www.nseindia.com/api/liveEquity-derivatives?index=nifty_bank_fut"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36',
    'Referer': main_url,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
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
    response2 = session.get(nbfu_url, headers=headers)
    response2.raise_for_status()
    fno = response2.json()
    df = pd.json_normalize(fno['data'])
    current_time = starttime.strftime('%H:%M')
    # These lines below were likely causing the TabError
    df['Time'] = current_time
    df['Date'] = current_date
    df['Fetcgdate'], df['Fetchtime'] = fno['timestamp'].split()
except requests.exceptions.RequestException as e:
    print(f"An error occurred for : {e}")

#df.to_sql('spur', conn, if_exists='append', index=False)
#bank = df[nfcolumns]
endtime = datetime.now()
elapsed = endtime - starttime

# total seconds as float
total_seconds = elapsed.total_seconds()
# minutes and seconds
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)
milliseconds = int((total_seconds - int(total_seconds)) * 1000)
reqcol = ['underlying', 'Date', 'Fetchtime','instrumentType', 'contract',
       'lastPrice', 'change',
       'pChange','highPrice', 'lowPrice',  'volume',
       'totalTurnover', 'value', 'premiumTurnOver', 'underlyingValue',
       'openInterest', 'noOfTrades', 'Time']
df = df[reqcol]

print(f"The time taken to complete the task is {minutes}:{seconds:02d}.{milliseconds:03d}")
df.head()