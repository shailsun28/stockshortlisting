import pandas as pd
import sqlite3
from datetime import date, timedelta, datetime
import time
import numpy as np
import os
from dateutil.parser import parse
import warnings
warnings.filterwarnings("ignore")

#Shortlisted stock daily at the end of the day after 8 p.m)

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

starttime = datetime.now()
print ("Please wait script started at ", starttime)
today = date.today()
# Subtract one day to get the previous date
today = today - timedelta(1)

#indiceslist = ['allmarket_nonfno', 'fno']
indiceslist = ['fno']
comparevalue = 2
#indiceslist = ['niftybank']
getdate = today.strftime("%Y-%b-%d")
#tadb_path = "/Users/shail/Documents/Trading/market-turnover/db/TA_Stock.db"
tadb_path = os.path.join(BASE_DIR_db,"deliveryavg.db")
#conn = sqlite3.connect(db_path) #db connection to bhav copy
ta_conn = sqlite3.connect(tadb_path) # db connection to TA db
#query = f'SELECT * FROM sma_vol WHERE SYMBOL = "{line}" ORDER BY "DATE" DESC LIMIT 1'
#query = 'SELECT * FROM sma_vol where DATE = "2025-02-01"'
#query = f'SELECT * FROM sma_vol where DATE = "{today}"'
#query = f'SELECT * FROM sma_vol WHERE Date = "{today}"'
query = f'SELECT * from sma_vol where Date = "{today}"'
print (query)
tadf = pd.read_sql_query(query, ta_conn)
#print (tadf.shape)

earn_path = os.path.join(BASE_DIR,"resultdate","niftyallmarket_earnDate.csv")
earndf = pd.read_csv(earn_path) #/Users/shail/Documents/Trading/resultdate/niftyallmarket_earnDate.csv
earndf.loc[:, 'Date'] = pd.to_datetime(earndf['Date']).dt.date
earndf.loc[earndf['Date'].isna(), 'Date'] = today
#ffdf=pd.read_csv('/Users/shail/Documents/Trading/NiftyStocks/allmarket_freefloat_shares.csv')
#ffdf=pd.read_csv('/Users/shail/Documents/Trading/NiftyStocks/niftyallmarket_mcap.csv')
#####

#comparevalue = 2
periods = [5, 10, 21, 50 ,66, 96, 125, 190, 252]
#indiceslist = ['niftybank']
for indices in indiceslist:
    print (f"fetching data for index {indices}  ......")
    #inputfile = '/Users/shail/Documents/Trading/NiftyStocks/' + indices
    inputfile = os.path.join(BASE_DIR, "NiftyStocks", indices)
    #alout = '/Users/shail/Documents/Trading/dlycalculated/' + indices + '-cal-out-' + getdate + ".csv"
    #shortlisted = '/Users/shail/Documents/Trading/shortlist/daily/' + indices + '_daily_short_' + getdate + ".csv"
    calout = os.path.join(BASE_DIR, "dlycalculated", f"{indices}-cal-out-{getdate}.csv")
    shortlisted = os.path.join(BASE_DIR, "shortlist", "daily", f"{indices}_daily_short_{getdate}.csv")
    with open(inputfile, "r") as f:
        stocks = f.readlines()  
    stocks = [line.strip() for line in stocks]
    #stocks = [line.replace('%26', '&') for line in stocks]
    shortlist = []
    calcluate = []
    trylist = []    
######

# Merge DataFrames on 'SYMBOL' column to add 52 week high and low as on date 24 Jan 25
#eqdf1 = pd.merge(eqdf1, df1[['SYMBOL', '52WH', '52WL']], on='SYMBOL', how='left')
##################
    for line in stocks:
        line=line.strip()
        resdf = earndf[earndf['Stock']==line]
        #hl_df = pd.read_sql_query(query, ta_conn)
        hl_df = tadf[tadf['Stock']==line].reset_index(drop=True)
        #print (f"{line} dimension is {hl_df.shape}")
        if hl_df.empty:
            print(f"No data for Stock {line}")
            continue
        newdf1 = hl_df.copy()
        if newdf1.loc[0,'DlyRto_10'] > comparevalue and newdf1.shape[0] >0:
            #print (line)
            newdf1['RsDt'] = resdf.iloc[0, 1] if not resdf.empty else None
            newdf1['RsDays'] = (resdf.iloc[0, 1] - today).days if not resdf.empty else None
            #newdf1['resultdate'] = resdf.iloc[0,1]
            newdf1['LTP'] = newdf1['LTP'].astype(float)
            trylist.append(newdf1.iloc[:,:])
            shortlist.append(newdf1.iloc[:1,:])
    short_df = pd.concat(shortlist) 
    rename_columns = {'HiPr':'HIGH', 'AvgPr':'VWAP', 'Val_CR':'Tval', 'LoPr':'Low', 'DlyRto_10':'dly_RTO', 'Pr_chg_%':'prchg%'}
    short_df.rename(columns = rename_columns)
        #if newdf1.loc[0,'DlyRto_10'] > comparevalue :
            #print(f'{line} dly ratio is {newdf1.loc[0,'DlyRto_10']}')
    print(short_df.head(10))        
print("\2\n"+" ******************  Task Completed! ********************* ")
endtime = datetime.now()
print (f'Task completed at {endtime}')