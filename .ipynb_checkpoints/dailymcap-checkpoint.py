import requests
import sqlite3
import pandas as pd
from datetime import datetime
import os

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

print ("The task Started at  ", datetime.now())
db_path =  os.path.join(BASE_DIR_db,"mcap.db")
conn = sqlite3.connect(db_path)
main_url = 'https://www.nseindia.com'
api_url = f'https://www.nseindia.com/api/marketStatus'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36',
    'Referer': main_url
}

session = requests.Session()

try:
    session.get(main_url, headers=headers)
    response = session.get(api_url, headers=headers)
    #response2 = session.get(api2_url, headers=headers)

    response.raise_for_status()
    #response2.raise_for_status()

    data = response.json()

    #result = [[data['marketcap']['timeStamp'],data['indicativenifty50']['finalClosingValue'], data['indicativenifty50']['perChange'], data['marketcap']['marketCapinTRDollars'], data['marketcap']['marketCapinLACCRRupeesFormatted'], data['marketcap']['marketCapinLACCRRupees'],data['marketState'][4]['last'],  data['marketState'][4]['expiryDate']]]
        

except requests.exceptions.RequestException as e:
    print(f"Error fetching data for {stock}: {e}")

finally:
    session.close()
alllist = [data['marketcap']['timeStamp'],data['indicativenifty50']['finalClosingValue'], data['indicativenifty50']['perChange'], data['marketcap']['marketCapinTRDollars'], data['marketcap']['marketCapinLACCRRupeesFormatted'], data['marketcap']['marketCapinLACCRRupees'],data['marketState'][4]['last'],  data['marketState'][4]['expiryDate']]
dfl = pd.DataFrame([alllist],columns=["Date","nifty","Pchg", "TrDollar", "lacCRinr_adj","lacCRinr", "USDINR","FuExDate"])
date_format = '%d-%b-%Y' 
dfl['Date'] = pd.to_datetime(dfl['Date']).dt.strftime('%Y-%m-%d')
#outfile = "/Users/shail/Documents/Trading/market-turnover/mcap.csv"
# Add a timestamp to ensure you can sort by 'newest'
dfl.to_sql('mcap', conn, if_exists='append', index=False)
#dfl.to_csv(outfile, mode = 'a', header = None,index=False)
#df.to_csv(outfile, mode = 'a')
conn.close()
print (f"The Daily Market Cap and USD INR value downloaded and saved to mcap.db ", datetime.now())

