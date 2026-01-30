import httpx
import brotli
import json
import time
import pandas as pd  # Ensure Pandas is installed
import sqlite3
import os
from datetime import datetime, date
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

starttime = datetime.now()
print("\2\n"+ " ******************  Script run started  at ...   ", starttime)

dbpath = os.path.join(BASE_DIR_db, "fuopspur.db")
conn = sqlite3.connect(dbpath)
current_date = starttime.strftime('%Y-%m-%d')
#api_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY 50"
api_url = "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings"

# Headers to mimic a real browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/market-data/oi-spurts",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br"
	}

# Main NSE site to retrieve cookies
main_url = "https://www.nseindia.com/market-data/oi-spurts"

# Start session with httpx
with httpx.Client() as client:
    try:
	    response = client.get(main_url, headers=headers)
	    response.raise_for_status()
	    cookies = dict(client.cookies)  # Extract cookies
	    time.sleep(3)  # Wait briefly before the next request	
	    response2 = client.get(api_url, headers=headers, cookies=cookies)
	    response2.raise_for_status()
	    data = json.loads(response2.text)
	    df = pd.json_normalize(data['data'])
	    current_time = starttime.strftime('%H:%M')
	    df['Time'] = current_time
	    df['Date'] = current_date
	    #print(df.shape)
    except httpx.HTTPStatusError as e:
        print(f"Error fetching data: {e}")
df.to_sql('spur', conn, if_exists='append', index=False)
conn.close()
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
print(f"The time taken to complete the task is {minutes}:{seconds:02d}.{milliseconds:03d}")