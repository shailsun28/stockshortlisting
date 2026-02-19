# This script to compare current delivery value for hourly collected data from web and stored to db. The compare value is also called from with sma and vol change data.
from tqdm import tqdm
import numpy as np
from datetime import date, timedelta, datetime
import pandas as pd
import sqlite3
import os
starttime = datetime.now()
print (f"Script started at {starttime.strftime('%H:%M:%S')}")
#BASE_DIR = "/Users/shail/Documents/Trading"
#BASE_DIR_db = "/Users/shail/Documents/Trading/market-turnover/db"
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

def dlyrto_cal_func(stock: str):
    """
    Process bhavcopy + 52-week data for a single stock.
    """
    db_path = os.path.join(BASE_DIR_db, "fullbhavcopy.db")
    conn = sqlite3.connect(db_path)

    # Define all column renames in one dictionary
    rename_map = {
        'TURNOVER_LACS': 'Val_CR',
        'DELIV_QTY' : 'DlyQty',
        'DELIV_PER': 'DlyPct',
        'TTL_TRD_QNTY': 'Vol',
        'HIGH_PRICE': 'HiPr',
        'LAST_PRICE': 'LTP',
        'AVG_PRICE': 'AvgPr',
        'SYMBOL': 'Stock',
        'DATE': 'Date',
        'LOW_PRICE': 'LoPr',
        'PREV_CLOSE': 'PvPr',
        'CLOSE_PRICE': 'ClPr'
    }


    query = f"SELECT * FROM nsestock_t WHERE SYMBOL = '{stock}' ORDER BY Date DESC LIMIT 360"
    hl_df = pd.read_sql_query(query, conn)
    hl_df.rename(columns=rename_map, inplace=True)
    hl_df['DlyQty'] = hl_df['DlyQty'].astype(int)
    

    hl_df['Val_CR'] = round(hl_df['Val_CR'] / 100, 3)

    # Derived metrics
    hl_df['DlyAvg_10'] = round(hl_df['DlyQty'].rolling(window=10, min_periods=10).mean().shift(-10), 1)
    #hl_df['DlyRto_10'] = round(hl_df['DlyQty'] / hl_df['DlyAvg_10'], 1)

    # Rolling averages
    periods = [1, 5, 10, 21]
    for period in periods:
        hl_df[f'VolAvg_{period}'] = round(hl_df['Vol'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df[f'ValAvg_{period}'] = round(hl_df['Val_CR'].rolling(window=period, min_periods=period).mean().shift(-period), 1)

    hl_df['Vol_lac'] = round(hl_df['Vol'] / 100000, 3)
    #specific_map = { 'Pr_chg_%': 'prchg%', 'DlyRto_10': 'dly_RTO', 'VolRto_10': 'qty_rto' }
    specific_map = { 'Pr_chg_%': 'prchg%'}
    
    # Reorder columns
     # --- Pattern-based rename: remove "Avg_" everywhere --- 
    hl_df.rename(columns=lambda c: c.replace("Avg_", ""), inplace=True)
    hl_df.rename(columns=specific_map, inplace=True)
    selcol = ['Stock',  'Date', 'HiPr', 'LoPr', 'LTP',
       'AvgPr', 'Val_CR', 'Vol', 'DlyQty', 'Vol1', 'Val1','Vol5', 'Val5','Dly10',
       'DlyPct', 'Vol10', 'Val10', 'Vol21', 'Val21', 
       'Vol_lac']
       
    hl_df = hl_df[selcol]
    conn.close()
    #return hl_df
    return hl_df.head(1)

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
comparevalue = hour_to_c_value.get(current_hour, 2)
#comparevalue = 2
#indiceslist = ['allmarket_nonfno']
indiceslist = ['allmarket_nonfno', 'fno']
today = date.today()
# Subtract one day to get the previous date
#today = today - timedelta(days=2)

print ("Running the script please wait till the task is complete ..... ")

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
results = {}  # dictionary to hold DataFrames per index

for indices in indiceslist:
    print(f"Selecting stock from index {indices} with compare value {comparevalue} based on delivery ratio")
    query = f'SELECT * FROM hrly_{indices}'
    df_from_db = pd.read_sql_query(query, ot_conn)
    date_format = '%d-%b-%Y %H:%M:%S'

    df_from_db['Date'] = pd.to_datetime(df_from_db['Date'], format=date_format, errors='coerce')
    df_from_db['capTime'] = df_from_db['Date'].dt.strftime('%H:%M')
    inputfile = os.path.join(BASE_DIR, "NiftyStocks", indices)
    dlylist = []

    with open(inputfile, "r") as f:
        stocks = [line.strip() for line in f]

    for firm in stocks:
        try:
            #dfn = tadf[tadf['Stock'] == firm]
            dfn = dlyrto_cal_func(firm).copy()
            hrn = df_from_db[df_from_db['Stock'] == firm].copy()
            hrn.reset_index(drop=True, inplace=True)
            #converting volume to actual quantity instead in lac unit.
            hrn['Tvolqty'] = hrn['Tvol']* 100000
            resdf = earndf[earndf['Stock'] == firm]
            if dfn.shape[0] > 0:
                #fromtadf = dfn.reset_index(drop=True).sort_values(by=['Date'], ascending=False)
                alldf = hrn.copy()
                dly10_val = dfn['Dly10'].iloc[0] 
                vol10_val = dfn['Vol10'].iloc[0] 

                dlyratio = alldf.loc[0, 'cur_dly'] / dly10_val if dly10_val else 0
                traded_qty_rto = round((alldf.loc[0, 'Tvolqty']) / vol10_val, 2) if vol10_val else 0
                Valchg1p = round((hrn.loc[0,'Tvalue'] - dfn.loc[0, 'Val1'])*100 / dfn.loc[0, 'Val1'], 2)
                Valchg5p = round((hrn.loc[0,'Tvalue'] - dfn.loc[0, 'Val5'])*100 / dfn.loc[0, 'Val5'], 2)
                Valchg10p = round((hrn.loc[0,'Tvalue'] - dfn.loc[0, 'Val10'])*100 / dfn.loc[0, 'Val10'], 2)
                Valchg21p = round((hrn.loc[0,'Tvalue'] - dfn.loc[0, 'Val21'])*100 / dfn.loc[0, 'Val21'], 2)
                Volchg1p = round((hrn.loc[0,'Tvolqty'] - dfn.loc[0, 'Vol1'])*100 / dfn.loc[0, 'Vol1'], 2)
                Volchg5p = round((hrn.loc[0,'Tvolqty'] - dfn.loc[0, 'Vol5'])*100 / dfn.loc[0, 'Vol5'], 2)
                Volchg10p = round((hrn.loc[0,'Tvolqty'] - dfn.loc[0, 'Vol10'])*100 / dfn.loc[0, 'Vol10'], 2)
                Volchg21p = round((hrn.loc[0,'Tvolqty'] - dfn.loc[0, 'Vol21'])*100 / dfn.loc[0, 'Vol21'], 2)
                
                #hl_df['ValChg%_10'] = round((hl_df['Val_CR'] - hl_df[f'ValAvg_{period}']) * 100 / hl_df[f'ValAvg_{period}'], 2)
                
                resultdate = resdf.iloc[0, 1]
                ResInDays = resdf.iloc[0, 1] - today
                if dlyratio >= comparevalue:
                    alldf['pRange'] = alldf['High'] - alldf['Low']
                    dlylist.append((
                        firm, round(dlyratio, 2), round(alldf.loc[0, 'PrChgP'], 2), traded_qty_rto,
                        alldf.loc[0, 'High'], alldf.loc[0, 'cur_dly'],
                        alldf.loc[0, 'Tvalue'], alldf.loc[0, 'Tvol'], alldf.loc[0, 'LTP'],
                        alldf.loc[0, 'Low'], alldf.loc[0, 'VWAP'], alldf.loc[0, 'PrChg'],
                        dfn['Val_CR'].iloc[0],dfn['Vol'].iloc[0],dfn['Dly10'].iloc[0]
                        , resultdate, ResInDays, alldf.loc[0, 'capTime'] , Valchg1p, Volchg1p, Valchg5p, Volchg5p,Valchg10p ,Volchg10p, Valchg21p, Volchg21p
                    ))
        except Exception as e:
            print(f"Error processing data for {firm}: {str(e)}")
            pass

    dlydf = pd.DataFrame(dlylist, columns=[
        "Stock", "dly_RTO", "prchg%", "qty_rto", "High", "cur_dly",
        "Tval", "Tvol", "LTP", "Low", "VWAP", "prchg", "Val1d", "Vol1d",
        "DlyAvg_10", "RsDt", "RsDays", "capTime", "Valchg1p", "Volchg1p", "Valchg5p", "Volchg5p", "Valchg10p", "Volchg10p", "Valchg21p", "Volchg21p"
    ])
    dlydf_out = dlydf.sort_values(by='dly_RTO', ascending=False)

    # Store in dictionary with index name as key
    results[indices] = dlydf_out

    #print(dlydf_out.head(10))
    print("\n")
fno_df = results.get("fno", pd.DataFrame()) 
fno_df.reset_index(drop=True, inplace=True)
nonfno_df = results.get("allmarket_nonfno", pd.DataFrame())
nonfno_df.reset_index(drop=True, inplace=True)
# After loop you can access each DataFrame by its index name
print("****************** Task Completed! *********************")
for idx, df in results.items():
    print(f"Total shortlisted stock for Index {idx}: {df.shape[0]} for compare value {comparevalue}")
    #print (df.head(10))
ot_conn.close()

print("\2\n"+" ******************  Task Completed! ********************* ")
endtime = datetime.now()
print (f'Task completed at {endtime}')

