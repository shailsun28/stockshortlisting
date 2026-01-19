from datetime import datetime
import requests
import pandas as pd
import sqlite3
import os
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

starttime = datetime.now()
print("\2\n"+ " ******************  Script run started  at ...   ", starttime)
#### Adding new columns to existing databse.
#cursor = conn.cursor()
# Add the column 'pchg' (assuming it's a FLOAT type)
#cursor.execute("ALTER TABLE cm_total ADD COLUMN pchg FLOAT")
# Commit and close
#conn.commit()
######
# Setup database connection
db_path = os.path.join(BASE_DIR_db, "allturnover.db")
conn = sqlite3.connect(db_path)

#filepath = "/Users/shail/Documents/Trading/market-turnover"
#json_url = "https://www.nseindia.com/api/market-turnover-popup"
n50advdec = "https://www.nseindia.com/api/NextApi/apiClient/indexTrackerApi?functionName=getAdvanceDecline&&index=NIFTY%2050"

nbadvdec ="https://www.nseindia.com/api/NextApi/apiClient/indexTrackerApi?functionName=getAdvanceDecline&&index=NIFTY%20BANK"
json_url = "https://www.nseindia.com/api/NextApi/apiClient?functionName=getMarketTurnoverSummary"
api2 = "https://www.nseindia.com/api/NextApi/apiClient?functionName=getMarketStatistics"
api_url = 'https://www.nseindia.com/api/NextApi/apiClient?functionName=getIndexData'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/", 
}
now = datetime.now()
current_date = now.strftime('%Y-%m-%d')
current_time = now.strftime('%H:%M')
try:
    # Fetch the JSON data
    response = requests.get(json_url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    response2 = requests.get(api2, headers=headers, timeout=10)
    response2.raise_for_status()
    data2 = response2.json()
    response3 = requests.get(api_url, headers=headers, timeout=10)
    response3.raise_for_status()
    data3 = response3.json()
    eq = pd.json_normalize(data['data']['equities'][3])  # cash market total value
    eq['pchg'] = data3['data'][0]['percChange']
    fn = pd.json_normalize(data['data']['equityDerivatives'][4]) # fno market Total value
    gt = pd.json_normalize(data['data']['grandTotal'])
    df2 = pd.json_normalize(data2['data'])
#GRand Total Data.
    gtcol = ['Date', 'Time', 
       'Tvol', 'Tval', 'oival_lac','noOfTrades', 
       'averageTrade', 'noOfOrders']
    gt_rename = {
       'volume':'Tvol','value':'Tval','oivalue': 'oival_lac'
    }
    rename_df2 = {'snapshotCapitalMarket.total':'Ttrd','snapshotCapitalMarket.advances':'Adv',
       'snapshotCapitalMarket.declines':'Dec',
       'snapshotCapitalMarket.unchange':'Unchg'}
    adcol = ['snapshotCapitalMarket.total','snapshotCapitalMarket.advances',
       'snapshotCapitalMarket.declines',
       'snapshotCapitalMarket.unchange']
# for Adv Decline dataframe.
    df2 = df2[adcol]
    df2.rename(columns=rename_df2, inplace=True)
# for Cashmarket
    eq.rename(columns=gt_rename, inplace=True)
    eqcol = ['Date', 'Time', 'pchg',
       'Tvol', 'Tval','noOfTrades', 
       'averageTrade', 'noOfOrders'] 
    eq['Tval'] = round (eq['Tval']/10000000, 3)
    eq['Tvol'] = round (eq['Tvol']/100000, 3)
    eq['Date'] = current_date
    eq['Time'] = current_time
    eq = eq[eqcol]
    cm = pd.concat([eq.reset_index(drop=True), df2.reset_index(drop=True)], axis=1)
#For FNO total market turnover
    fn.rename(columns=gt_rename, inplace=True)
    fn['Tval'] = round (fn['Tval']/10000000, 3)
    fn['Tvol'] = round (fn['Tvol']/100000, 3)
    fn['oival_lac'] = round (fn['oival_lac']/100000, 3)
    fn['Date'] = current_date
    fn['Time'] = current_time
    fn = fn[gtcol]
    fno = pd.concat([fn.reset_index(drop=True), df2.reset_index(drop=True)], axis=1)

# For Grand Total
    gt.rename(columns=gt_rename, inplace=True)
    gt['Tval'] = round (gt['Tval']/10000000, 3)
    gt['Tvol'] = round (gt['Tvol']/100000, 3)
    gt['oival_lac'] = round (gt['oival_lac']/100000, 3)
    gt['Date'] = current_date
    gt['Time'] = current_time
    gt = gt[gtcol]
    df = pd.concat([gt.reset_index(drop=True), df2.reset_index(drop=True)], axis=1)
    #totdf.to_csv(os.path.join(filepath, "grand-total.csv"), index=False, mode='a', header=False)
    df.to_sql('grand_total', conn, if_exists='append', index=False)
    cm.to_sql('cm_total', conn, if_exists='append', index=False)
    fno.to_sql('fno_total', conn, if_exists='append', index=False)



except requests.exceptions.RequestException as e:
    print (f"Error fetching data: {e}")
    #logging.error(f"Error fetching data: {e}", exc_info=True)
except Exception as e:
    print (f"Error fetching data: {e}")
    #logging.error(f"An unexpected error occurred: {e}", exc_info=True)
conn.close()
endtime = datetime.now()
print ("The script completed successfully at ", endtime)
