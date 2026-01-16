
# This script to compare current delivery value for hourly collected data from web and stored to db. The compare value is also called from with sma and vol change data.
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import numpy as np
#from datetime import date, datetime
from datetime import date, timedelta, datetime
import requests
import pandas as pd
import sqlite3
import re
starttime = datetime.now()
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
today = today - timedelta(days=2)

print ("Running the script please wait till the task is complete ..... ")
tadb_path = "/Users/shail/Documents/Trading/market-turnover/db/TA_Stock.db"
#conn = sqlite3.connect(db_path) #db connection to bhav copy
ta_conn = sqlite3.connect(tadb_path) # db connection to TA db
#query = f"SELECT * FROM sma_vol where Date = '{today}'"
query = "SELECT * FROM sma_vol WHERE Date IN (SELECT MAX(Date) FROM sma_vol GROUP BY Stock) ORDER BY Date desc"
#query = f"SELECT * FROM sma_vol order by Date desc Limit 1"
tadf = pd.read_sql_query(query, ta_conn)   

gethour = datetime.now().strftime("%Y-%m-%d-%H")
earndf = pd.read_csv('/Users/shail/Documents/Trading/resultdate/niftyallmarket_earnDate.csv') #/Users/shail/Documents/Trading/resultdate/niftyallmarket_earnDate.csv
earndf.loc[:, 'Date'] = pd.to_datetime(earndf['Date']).dt.date
earndf.loc[earndf['Date'].isna(), 'Date'] = today
#dlylist = []
periods = [5, 10, 21, 66, 125, 252]
ot_path = "/Users/shail/Documents/Trading/market-turnover/db/onetimehourly.db"
ot_conn = sqlite3.connect(ot_path)  # db connection to TA db  
for indices in indiceslist:
    print (f"Selecting stock from index {indices} with compare value {comparevalue} based on delvery ratio")
    query = f'SELECT * FROM hrly_{indices}'
    #print (query)
    df_from_db = pd.read_sql_query(query, ot_conn)
    #df_from_db['Date'] = '18-Dec-2025 15:00'
    # Formating Date column to get only time
    date_format = '%d-%b-%Y %H:%M:%S'
    #date_format = '%d-%b-%Y %H:%M'
    df_from_db['Date'] = pd.to_datetime(df_from_db['Date'], format=date_format, errors='coerce')
    # Extract only the time part and create a new column 'Time'
    #df_from_db['capTime'] = df_from_db['Date'].dt.strftime('%H:%M:%S')
    df_from_db['capTime'] = df_from_db['Date'].dt.strftime('%H:%M')

    inputfile = '/Users/shail/Documents/Trading/NiftyStocks/' + indices
    #calout = '/Users/shail/Documents/Trading/dlycalculated/' + indices + '-cal-out-' + gethour + ".csv"
    hourlypath = '/Users/shail/Documents/Trading/shortlist/hourly/hourlyweb_' + indices + "-" + datetime.now().strftime("%Y-%m-%d-%H-%M") + ".csv"
    #hrshortlist = '/Users/shail/Documents/Trading/hourly/hourly_' + indices + '-shortlisted-' + gethour + ".csv"  
    hrshortlist = f'/Users/shail/Documents/Trading/shortlist/hourly/{indices}_hrly_shortlisted_{datetime.now().strftime("%Y-%m-%d-%H")}.csv'  
    #hrshortlist = f'/Users/shail/Documents/Trading/shortlist/hourly/{indices}_hrly_shortlisted_{current_hour}.csv' 
    #hrshortlist = '/Users/shail/Documents/Trading/hourly/hourly_fno_shortlist.csv'
    dlylist = [] 
    with open(inputfile, "r") as f:
        stocks = f.readlines()  

    stocks = [item.strip() for item in stocks]
    #stocks = [line.replace('%26', '&') for line in stocks]
    for firm in stocks:
        try:    
            #ta_query = f'SELECT * FROM sma_vol where Stock = "{firm}" order by DATE desc limit 1'
            dfn = tadf[tadf['Stock'] == firm]
            #dfn = pd.read_sql_query(ta_query, ta_conn) 
            hrn = df_from_db[df_from_db['Stock'] == firm]
            resdf = earndf[earndf['Stock']==firm]
            #resdf['Date'] = pd.to_datetime(resdf['Date']).dt.date
            #resdf.loc[:, 'Date'] = pd.to_datetime(resdf['Date']).dt.date
        # Replace NaTType values with a default date (e.g., current date)
            #resdf['Date'] = resdf['Date'].fillna(today)
            #resdf.loc[resdf['Date'].isna(), 'Date'] = today
            #if dfn.shape[0] > 10:
            if dfn.shape[0] > 0:
                fromtadf = dfn.reset_index(drop=True)
                fromtadf.sort_values(by=['Date'], ascending=False, inplace=True)
                alldf = hrn.reset_index(drop=True)
                #dlyratio = alldf.loc[0, 'cur_dly'] / fromtadf.loc[0, 'DlyAvg_10']
                dly_avg = fromtadf.loc[0, 'DlyAvg_10']
                dlyratio = alldf.loc[0, 'cur_dly'] / dly_avg if dly_avg and dly_avg != 0 else 0

                #traded_qty_rto = round(alldf.loc[0, 'Tvol']*100000 / fromtadf.loc[0, 'VolAvg_10'], 2)
                vol_avg_10 = fromtadf.loc[0, 'VolAvg_10']
                traded_qty_rto = round((alldf.loc[0, 'Tvol'] * 100000) / vol_avg_10, 2) if vol_avg_10 and vol_avg_10 != 0 else 0
                #volChgP = round((alldf.loc[0, 'Tvol']*100000 - fromtadf.loc[0, 'Vol_lac'])*100/fromtadf.loc[0, 'Vol_lac'],2)
                
                volChgP = round((alldf.loc[0, 'Tvol'] - fromtadf.loc[0, 'Vol_lac'])*100/fromtadf.loc[0, 'Vol_lac'],2)

                valueChgP = round((alldf.loc[0, 'Tvalue'] - fromtadf.loc[0, 'Val_CR'])*100/fromtadf.loc[0, 'Val_CR'],2)
                resultdate = resdf.iloc[0,1]
                ResInDays =  resdf.iloc[0,1] - today
                
                #TvolDiff = alldf.loc[0, 'Tvol']*100000 - fromtadf.loc[0, 'Vol']
                #TvalueDiff = alldf.loc[0, 'Tvalue'] - fromtadf.loc[0, 'Val_CR']
                #ffshares_per = round(alldf.loc[0, 'DELIV_QTY']*100 / ffstock.loc[0,'ff_shares'], 3)
                if dlyratio >= comparevalue:
                    #print (f'Stock is {firm} with delivery ration {dlyratio}')
                    #print (f'Stock is {firm} with delivery ration {dlyratio}')
                    alldf['pRange'] = alldf['High'] - alldf['Low']
                                    
                    for period in periods:
                        alldf[f'Diff_SMA_{period}'] = np.abs(alldf.loc[0, 'LTP'] - fromtadf.loc[0, f'SMA_{period}'])                              

                    # Find the minimum difference and the corresponding SMA period
                    alldf['SMA_Diff'] = alldf[[f'Diff_SMA_{period}' for period in periods]].min(axis=1)
                    alldf['Near_SMA'] = alldf.apply(lambda row: min([(row[f'Diff_SMA_{period}'], period) for period in periods], key=lambda x: x[0])[1], axis=1)                                  

                    # Calculate the percentage difference relative to LaPr
                    alldf['Near_SMA_%'] = ((alldf['SMA_Diff'] / alldf['LTP']) * 100).round(2)
                    alldf[f'SMA_{alldf.loc[0,'Near_SMA']}'] = fromtadf.loc[0,f'SMA_{alldf.loc[0,'Near_SMA']}']
                    # Remove the temporary difference columns
                    alldf.drop(columns=[f'Diff_SMA_{period}' for period in periods], inplace=True)
                    HI52WNearP = round((fromtadf.loc[0,'52WH'] - alldf.loc[0,'LTP'])*100 / fromtadf.loc[0,'52WH'],2)
                    LO52WNearP = round((alldf.loc[0,'LTP'] - fromtadf.loc[0,'52WL'])*100 / fromtadf.loc[0,'52WL'],2)
                    volChg_21P = round((alldf.loc[0, 'Tvol']*100000 - fromtadf.loc[0, 'VolAvg_21'])*100/fromtadf.loc[0, 'VolAvg_21'],2)
                    valueChg_21P = round((alldf.loc[0, 'Tvalue'] - fromtadf.loc[0, 'ValAvg_21'])*100/fromtadf.loc[0, 'ValAvg_21'],2)
                    #LTP_Avg_D = round(alldf.loc[0,'LTP'] - alldf.loc[0, 'VWAP'], 2)
                    volChg_10P = round((alldf.loc[0, 'Tvol']*100000 - fromtadf.loc[0, 'VolAvg_10'])*100/fromtadf.loc[0, 'VolAvg_10'],2)
                    valueChg_10P = round((alldf.loc[0, 'Tvalue'] - fromtadf.loc[0, 'ValAvg_10'])*100/fromtadf.loc[0, 'ValAvg_10'],2)
                    dlylist.append((firm, round(dlyratio, 2), round(alldf.loc[0, 'PrChgP'],2) ,alldf.loc[0, 'PrChg'],traded_qty_rto, valueChgP,volChgP,valueChg_21P,volChg_21P, alldf.loc[0, 'High'], 
                            fromtadf.loc[0, 'DlyAvg_10'], alldf.loc[0, 'cur_dly'], alldf.loc[0, 'cur_trd_qty'], alldf.loc[0, 'Tvol'], fromtadf.loc[0, 'Vol_lac'],alldf.loc[0, 'Tvalue'],
                            alldf.loc[0,'Near_SMA'],alldf.loc[0,f'SMA_{alldf.loc[0,'Near_SMA']}'],alldf.loc[0,'SMA_Diff'],alldf.loc[0,'Near_SMA_%'],fromtadf.loc[0, '52WH'],
                            alldf.loc[0, 'LTP'], alldf.loc[0, 'Low'], alldf.loc[0, 'VWAP'],fromtadf.loc[0, '52WL'],alldf.loc[0, 'pRange'],fromtadf.loc[0, 'Val_CR'],resultdate,ResInDays,HI52WNearP,LO52WNearP, alldf.loc[0, 'capTime'], alldf.loc[0, 'Runtime'],valueChg_10P,volChg_10P ))
                    #dlylist.append((firm, round(dlyratio, 2), round(alldf.loc[0, 'PrChgP'],2) ,alldf.loc[0, 'PrChg'],traded_qty_rto,volChgP, valueChgP, alldf.loc[0, 'High'], fromtadf.loc[0, 'DlyAvg_10'], alldf.loc[0, 'cur_dly'], alldf.loc[0, 'cur_trd_qty'], alldf.loc[0, 'Tvol']*100000, fromtadf.loc[0, 'Vol'],alldf.loc[0, 'Tvalue'], alldf.loc[0, 'LTP'], alldf.loc[0, 'Low'], alldf.loc[0, 'VWAP'], alldf.loc[0, 'pRange'],fromtadf.loc[0, 'Val_CR'],resultdate,ResInDays))
        except Exception as e:
            print(f"Error processing data for {firm}: {str(e)}")
            pass    
    dlydf_columns = ["Stock" ,"dly_RTO" ,"prchg%", "prchg" , "qty_rto","Tvalchg%","Tvolchg%",'ValChg_21d%','VolChg_21d%' , "HiPr", "10_avg_dly", "cur_dly", "cur_trade_qty", "cur_vol(lac)", "pre_vol","cur_val(cr)","Nr_SMA" ,"SMA_Val", "SMA_Diff", "Nr_SMA%","52WH" ,"LTP", "LoPr", "AvgPr","52WL" ,"pRange","pre_val_cr", "RsDt","RsDays","Hi52WNr%","Lo52WNr%","capTime",'Runtime','valChg_10d%','volChg_10d%']

    #dlydf_columns = ["Stock" ,"dly_RTO" ,"prchg%", "prchg" , "qty_rto","Tvalchg%","Tvolchg%",'ValChg_21d%','VolChg_21d%' , "HiPr", "10_avg_dly", "cur_dly", "cur_trade_qty", "cur_vol(lac)", "pre_vol","cur_val(cr)","pre_val_cr","Nr_SMA" ,"SMA_Val", "SMA_Diff", "Nr_SMA%","52WH" ,"LTP", "LoPr", "AvgPr","52WL" , "RsDt","RsDays","Hi52WNr%","Lo52WNr%","capTime",LTP_Avg_D]
    #dlydf_columns = ["Stock", "dly_RTO" ,"prchg%", "prchg" , "qty_rto","Tvolchg%","Tvalchg%" , "High", "10_avg_dly", "cur_dly", "cur_trade_qty", "cur_vol", "pre_vol","cur_val","Nr_SMA" ,"SMA_Val", "SMA_Diff", "Nr_SMA%","52WH" ,"LTP", "Low", "VWAP","52WL" ,"pRange","pre_val_cr", "RsDt","RsDays","Hi52WNr%","Lo52WNr%"]
    dlydf = pd.DataFrame(dlylist, columns=dlydf_columns)
    #dlydf = pd.DataFrame(dlylist, columns=["Stock", "dly_RTO" ,"prchg%", "prchg" , "qty_rto","Tvolchg%","Tvalchg%" , "High", "10_avg_dly", "cur_dly", "cur_trade_qty", "cur_vol", "pre_vol","cur_val" ,"LTP", "Low", "VWAP", "pRange","pre_val_cr", "ResDate","ResInDays"])
    #newcolumn = ["Stock", "dly_RTO" ,"prchg %chg" , "qty_rto","Tvalchg%" ,"Tvolchg%", "High","LTP","VWAP", "Low","cur_dly","cur_val","pre_val_cr","cur_vol", "pre_vol"]
    #newcolumn = ["Stock", "dly_RTO" ,"prchg%" , "prchg" , "qty_rto","Tvalchg%" ,"Tvolchg%", "High","LTP","VWAP","cur_dly","cur_val","cur_vol", "ResDate","ResInDays" ]
    # Convert and format the 'RsDt' column to show only month and day
    dlydf['RsDt'] = pd.to_datetime(dlydf['RsDt']).dt.strftime('%d-%b')
    # Sort the DataFrame by 'dly_RTO' in descending order
    outcolumns = ['Stock','dly_RTO', 'prchg%', 'qty_rto','Tvalchg%', 'Tvolchg%','valChg_10d%','volChg_10d%','ValChg_21d%','VolChg_21d%',"cur_val(cr)", "cur_vol(lac)",'capTime','HiPr', 'LTP', 'AvgPr','LoPr' , 'Nr_SMA', 'Nr_SMA%',"Hi52WNr%","Lo52WNr%", 'SMA_Val' ,'RsDt','RsDays']
    #outcolumns = ['Stock','dly_RTO', 'prchg%', 'qty_rto','Tvalchg%', 'Tvolchg%','ValChg_21d%','VolChg_21d%',"cur_val(cr)", "cur_vol(lac)",'capTime','HiPr', 'LTP', 'AvgPr','LoPr' , 'Nr_SMA', 'Nr_SMA%',"Hi52WNr%","Lo52WNr%", 'SMA_Val','52WH','52WL' ,'RsDt','RsDays','valChg_10d%','volChg_10d%']
    dlydf_out = dlydf[outcolumns]
    dlydf_out = dlydf_out.sort_values(by='dly_RTO', ascending=False)
    #dlydf_out.drop(index=True)
    #dlydf.to_csv(hrshortlist, index=False, mode = 'a', header = False)       
    dlydf_out.to_csv(hrshortlist, index=False, mode = 'w')            
    #print(f"** The hourly shortlist stockfile for {indices} is stored at > {shortlisted} **")
    print (f"Total shortlisted stock for Index {indices} are {dlydf_out.shape[0]} for compare value {comparevalue} . Displaying top 10 order by dly_RTO")
    print(dlydf_out.head(10))
    #print(dlydf.shape)
    print("\2\n")
ot_conn.close()
ta_conn.close() 
print("\2\n"+" ******************  Task Completed! ********************* ")
endtime = datetime.now()
time_taken = endtime - starttime
print (f' Time taken to complete the task is {str(time_taken)} and Task completed at {endtime.strftime('%H:%M:%S')}')
