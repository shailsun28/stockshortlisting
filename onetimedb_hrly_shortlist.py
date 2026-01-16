# This script to compare current delivery value for hourly collected data from web and stored to db. The compare value is also called from with sma and vol change data.
from tqdm import tqdm
import numpy as np
from datetime import date, timedelta, datetime
import pandas as pd
import sqlite3
import os


starttime = datetime.now()
print (f"Script started at {starttime.strftime('%H:%M:%S')}")
BASE_DIR = "/Users/shail/Documents/Trading"
BASE_DIR_db = "/Users/shail/Documents/Trading/market-turnover/db"
db_path = os.path.join(BASE_DIR_db, "eq_fu_buysell_qty.db")
# List of c_values
c_values = [0.66, 0.79, 0.99, 1.33, 1.66, 1.99]
# Get the current hour
current_hour = datetime.now().hour
# Mapping hours to corresponding c_values
hour_to_c_value = {
    10: 0.66,
    11: 0.79,
    12: 0.99,
    13: 1.33,
    14: 1.66,
    15: 1.99
}

# Set the comparevalue based on the current hour
#comparevalue = hour_to_c_value.get(current_hour, "Default Value")
comparevalue = hour_to_c_value.get(current_hour, 3)
#comparevalue = 2
#indiceslist = ['allmarket_nonfno']
indiceslist = ['allmarket_nonfno', 'fno']
today = date.today()
# Subtract one day to get the previous date
#today = today - timedelta(days=2)

print ("Running the script please wait till the task is complete ..... ")
#tadb_path = "/Users/shail/Documents/Trading/market-turnover/db/TA_Stock.db"
tadb_path = os.path.join(BASE_DIR_db, "deliveryavg.db")
ta_conn = sqlite3.connect(tadb_path) # db connection to TA db
#query = f"SELECT * FROM sma_vol where Date = '{today}'"
query = "SELECT * FROM sma_vol WHERE Date IN (SELECT MAX(Date) FROM sma_vol GROUP BY Stock) ORDER BY Date desc"
#query = f"SELECT * FROM sma_vol order by Date desc Limit 1"
tadf = pd.read_sql_query(query, ta_conn)   

gethour = datetime.now().strftime("%Y-%m-%d-%H")
earn_path = os.path.join(BASE_DIR, "resultdate", "niftyallmarket_earnDate.csv")
#earn_path = "/Users/shail/Documents/Trading/resultdate/niftyallmarket_earnDate.csv"
earndf = pd.read_csv(earn_path) #/Users/shail/Documents/Trading/resultdate/niftyallmarket_earnDate.csv
earndf.loc[:, 'Date'] = pd.to_datetime(earndf['Date']).dt.date
earndf.loc[earndf['Date'].isna(), 'Date'] = today
dlylist = []
periods = [5, 10, 21, 66, 125, 252]
ot_path = os.path.join(BASE_DIR_db, "onetimehourly.db")
ot_conn = sqlite3.connect(ot_path)  # db connection to TA db  
for indices in indiceslist:
    print (f"Selecting stock from index {indices} with compare value {comparevalue} based on delvery ratio")
    query = f'SELECT * FROM hrly_{indices}'
    df_from_db = pd.read_sql_query(query, ot_conn)
    date_format = '%d-%b-%Y %H:%M:%S'

    df_from_db['Date'] = pd.to_datetime(df_from_db['Date'], format=date_format, errors='coerce')
    df_from_db['capTime'] = df_from_db['Date'].dt.strftime('%H:%M')
    inputfile = os.path.join(BASE_DIR, "NiftyStocks", indices)
    hourlypath = os.path.join(BASE_DIR, "shortlist", "hourly", f"hourlyweb_{indices}-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.csv")
    hrshortlist = os.path.join(BASE_DIR, "shortlist", "hourly", f"{indices}_hrly_shortlisted_{datetime.now().strftime('%Y-%m-%d-%H')}.csv")
    dlylist = [] 
    with open(inputfile, "r") as f:
        stocks = f.readlines()  

    stocks = [item.strip() for item in stocks]
    #stocks = [line.replace('%26', '&') for line in stocks]
    for firm in stocks:
        try:    
            dfn = tadf[tadf['Stock'] == firm]
            hrn = df_from_db[df_from_db['Stock'] == firm]
            resdf = earndf[earndf['Stock']==firm]
            if dfn.shape[0] > 0:
                fromtadf = dfn.reset_index(drop=True)
                fromtadf.sort_values(by=['Date'], ascending=False, inplace=True)
                alldf = hrn.reset_index(drop=True)
                dly_avg = fromtadf.loc[0, 'DlyAvg_10']
                dlyratio = alldf.loc[0, 'cur_dly'] / dly_avg if dly_avg and dly_avg != 0 else 0
                vol_avg_10 = fromtadf.loc[0, 'VolAvg_10']
                traded_qty_rto = round((alldf.loc[0, 'Tvol'] * 100000) / vol_avg_10, 2) if vol_avg_10 and vol_avg_10 != 0 else 0
                resultdate = resdf.iloc[0,1]
                ResInDays =  resdf.iloc[0,1] - today
                if dlyratio >= comparevalue:
                    alldf['pRange'] = alldf['High'] - alldf['Low']             
                    dlylist.append((firm, round(dlyratio, 2), round(alldf.loc[0, 'PrChgP'],2) ,alldf.loc[0, 'PrChg'],traded_qty_rto, alldf.loc[0, 'High'], 
                            alldf.loc[0, 'cur_dly'], alldf.loc[0, 'cur_trd_qty'],alldf.loc[0, 'Tvalue'], alldf.loc[0, 'Tvol'],
                            alldf.loc[0, 'LTP'], alldf.loc[0, 'Low'], alldf.loc[0, 'VWAP'], alldf.loc[0, 'pRange'],fromtadf.loc[0, 'Val_CR'], fromtadf.loc[0, 'Vol'], fromtadf.loc[0, 'DlyAvg_10'], resultdate,ResInDays, alldf.loc[0, 'capTime'] ))
        except Exception as e:
            print(f"Error processing data for {firm}: {str(e)}")
            pass    

    dlydf = pd.DataFrame(dlylist, columns=["Stock", "dly_RTO" ,"prchg%", "prchg", "qty_rto", "High","cur_dly", "cur_trd_qty", "Tval", "Tvol", "LTP", "Low", "VWAP", "pRange","Val_CR", "Vol","DlyAvg_10", "RsDt","RsDays","capTime" ])    
    dlydf_out = dlydf.sort_values(by='dly_RTO', ascending=False)
    print(dlydf_out.head(10))
    print("\2\n")
ot_conn.close()
ta_conn.close() 
print("\2\n"+" ******************  Task Completed! ********************* ")
endtime = datetime.now()
print (f' Task completed at {endtime.strftime('%H:%M:%S')}')
print (f"Total shortlisted stock for Index {indices} are {dlydf_out.shape[0]} for compare value {comparevalue} . Displaying top 10 order by dly_RTO")






