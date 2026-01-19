import pandas as pd
import streamlit as st
import sqlite3
from datetime import date, timedelta, datetime
import time
import altair as alt
import httpx
import json
import numpy as np
import importlib.util
import os 


#BASE_DIR = "/Users/shail/Documents/Trading"
#BASE_DIR_db = "/Users/shail/Documents/Trading/market-turnover/db"
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

# -----------------------------
# Functions
# -----------------------------

def buysell_fno_func(stocklist):
    #db_path = "/Users/shail/Documents/Trading/market-turnover/db/eq_fu_buysell_qty.db"
    db_path = os.path.join(BASE_DIR_db,"eq_fu_buysell_qty.db")
    todays_date = date.today()
    todays_date = todays_date - timedelta(days=2)
    with sqlite3.connect(db_path) as tg_conn:
        #tg_query = f'select * from fno where Date = "{todays_date}" order by Time desc'
        #tg_query = "SELECT * FROM fno WHERE Date IN (SELECT MAX(Date) FROM fno GROUP BY Stock) ORDER BY Date DESC, Time DESC"
        tg_query = "SELECT * FROM fno WHERE Date = (SELECT MAX(Date) FROM fno) ORDER BY Time DESC";
        #tg_query = "SELECT * FROM fno WHERE Date IN (SELECT MAX(Date) FROM fno GROUP BY Stock) ORDER BY Date DESC, Time DESC"
        tgdf = pd.read_sql_query(tg_query, tg_conn)

    df_list = []
    numeric_cols = [
        'Tbuy_eq', 'Tsell_eq', 'Tvalue_eq', 'Tvol_eq',
        'High_eq', 'PrChg_eq', '%Prchg_eq', 'Ltp_eq', 'Vwap_eq', 'Ltp_fu',
        'PrChg_fu', '%Prchg_fu', 'Tsell_fu', 'Tbuy_fu', 'Tvol_fu',
        'Tvalue_fu', 'fuOI'
    ]

    for stock in stocklist:
        alldf = tgdf[tgdf['Stock'] == stock].sort_values(by=['Time'], ascending=False).reset_index(drop=True)
        if alldf.empty:
            continue
        alldf[numeric_cols] = alldf[numeric_cols].apply(pd.to_numeric, errors='coerce')
        alldf.fillna(0, inplace=True)

        # Transformations
        alldf['Tvalue_eq'] = alldf['Tvalue_eq'] / 10000000
        alldf['ValChg%_eq'] = round((alldf['Tvalue_eq'] - alldf['Tvalue_eq'].shift(-1)) * 100 / alldf['Tvalue_eq'].shift(-1), 2)
        alldf['Valchg_eq'] = alldf['Tvalue_eq'] - alldf['Tvalue_eq'].shift(-1)
        alldf['VolChg%_eq'] = round((alldf['Tvol_eq'] - alldf['Tvol_eq'].shift(-1)) * 100 / alldf['Tvol_eq'].shift(-1), 2)
        alldf['Volchg_eq'] = round((alldf['Tvol_eq'] - alldf['Tvol_eq'].shift(-1)), 2)
        alldf['var%_eq'] = alldf['ValChg%_eq'] - alldf['VolChg%_eq']
        alldf['bsd%_eq'] = round(((alldf['Tbuy_eq'] - alldf['Tsell_eq']) * 100) / alldf['Tbuy_eq'], 2)

        alldf['ValChg%_fu'] = round((alldf['Tvalue_fu'] - alldf['Tvalue_fu'].shift(-1)) * 100 / alldf['Tvalue_fu'].shift(-1), 2)
        alldf['Valchg_fu'] = round((alldf['Tvalue_fu'] - alldf['Tvalue_fu'].shift(-1)), 3)
        alldf['VolChg%_fu'] = round((alldf['Tvol_fu'] - alldf['Tvol_fu'].shift(-1)) * 100 / alldf['Tvol_fu'].shift(-1), 2)
        alldf['Volchg_fu'] = round((alldf['Tvol_fu'] - alldf['Tvol_fu'].shift(-1)), 2)
        alldf['var%_fu'] = alldf['ValChg%_fu'] - alldf['VolChg%_fu']
        alldf['bsd%_fu'] = round(((alldf['Tbuy_fu'] - alldf['Tsell_fu']) * 100) / alldf['Tbuy_fu'], 2)

        alldf['tot%_eq'] = round(((alldf['Tbuy_eq'] - alldf['Tsell_eq']) * 100) / (alldf['Tbuy_eq'] + alldf['Tsell_eq']), 2)
        alldf['tot%_fu'] = round(((alldf['Tbuy_fu'] - alldf['Tsell_fu']) * 100) / (alldf['Tbuy_fu'] + alldf['Tsell_fu']), 2)
        alldf['avg_eq'] = round(alldf['Valchg_eq'] / (alldf['Volchg_eq']), 2)
        alldf['oichg_fu'] = round(alldf['fuOI'] - (alldf['fuOI'].shift(-1)), 2)
        alldf['avg_fu'] = round(alldf['Valchg_fu'] / (alldf['Volchg_fu']), 2)
        alldf['avgOI_fu'] = round(alldf['Valchg_fu'] / (alldf['oichg_fu']), 2)
        alldf['Valchg_fu'] = round(alldf['Valchg_fu'] / 10000000, 3)

        df_list.append(alldf)

    if not df_list:
        return pd.DataFrame()

    cal_columns = [
        'Stock', 'Date', 'Time', '%Prchg_eq', 'Valchg_eq', 'Volchg_eq',
        'ValChg%_eq', 'VolChg%_eq', 'ValChg%_fu', 'VolChg%_fu', 'Valchg_fu',
        'Volchg_fu', 'bsd%_eq', 'avg_eq', '%Prchg_fu', 'bsd%_fu', 'var%_fu',
        'Ltp_fu', 'avg_fu', 'tot%_eq', 'tot%_fu'
    ]
    #eqfu[cal_columns]
    eqfu = pd.concat(df_list)
    return eqfu

#Function to calculate SMA , ValAvg , VolAvg and their % change
def calsmavalavg_func(stocks):
    """
    Processes stock data for a given list of stocks and returns the final DataFrame.

    Parameters:
        stocks (list): List of stock symbols.

    Returns:
        pd.DataFrame: Final processed DataFrame.
    """
    # Define the database path and establish the connection
    #db_path = "/Users/shail/Documents/Trading/market-turnover/db/fullbhavcopy.db"
    db_path = os.path.join(BASE_DIR_db, "fullbhavcopy.db")
    conn = sqlite3.connect(db_path)  # DB connection to bhav copy

    # Load 52-week high/low data
    highlow_path = os.path.join(BASE_DIR,"NiftyStocks" ,"52_wk_High_low.csv")
    df1 = pd.read_csv(highlow_path)
    rename_hl = {'Adjusted_52_Week_High': '52WH', 'Adjusted_52_Week_Low': '52WL'}
    df1.rename(columns=rename_hl, inplace=True)

    # Define periods and initialize talist
    periods = [1, 5, 10, 21, 50, 66, 96, 125, 190, 252]
    talist = []

    for stock in stocks:
        stock = stock.strip()  # Remove any leading/trailing whitespace/newlines
        query = f"SELECT * FROM nsestock_t WHERE SYMBOL = '{stock}' ORDER BY Date DESC LIMIT 360"
        hl_df = pd.read_sql_query(query, conn)

        hl_df['DELIV_QTY'] = hl_df['DELIV_QTY'].astype(float)
        hl_df.rename(columns={
            'TURNOVER_LACS': 'Val_CR',
            'TTL_TRD_QNTY': 'Vol',
            'HIGH_PRICE': 'HiPr',
            'LAST_PRICE': 'LTP',
            'AVG_PRICE': 'AvgPr'
        }, inplace=True)
        hl_df['Val_CR'] = round(hl_df['Val_CR'] / 100, 3)
        hl_df = pd.merge(hl_df, df1[['SYMBOL', '52WH', '52WL']], on='SYMBOL', how='left')

        hl_df['DlyAvg_10'] = round(hl_df['DELIV_QTY'].rolling(window=10, min_periods=10).mean().shift(-10), 1)
        hl_df['DlyRto_10'] = round(hl_df['DELIV_QTY'] / hl_df['DlyAvg_10'], 1)
        hl_df['Pr_chg'] = round(hl_df['CLOSE_PRICE'] - hl_df['PREV_CLOSE'], 2)
        hl_df['Pr_chg_%'] = round((hl_df['CLOSE_PRICE'] - hl_df['PREV_CLOSE']) * 100 / hl_df['PREV_CLOSE'], 2)
        hl_df['LO52WNr%'] = round((hl_df['CLOSE_PRICE'] - hl_df['52WL']) * 100 / hl_df['52WL'], 2)
        hl_df['HI52WNr%'] = round((hl_df['52WH'] - hl_df['CLOSE_PRICE']) * 100 / hl_df['52WH'], 2)
        hl_df['DayHiNr%'] = round((hl_df['HiPr'] - hl_df['CLOSE_PRICE']) * 100 / hl_df['HiPr'], 2)
        hl_df['DayLoNr%'] = round((hl_df['CLOSE_PRICE'] - hl_df['LOW_PRICE']) * 100 / hl_df['LOW_PRICE'], 2)
        for period in periods:
            hl_df[f'SMA_{period}'] = round(hl_df['CLOSE_PRICE'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
            hl_df[f'VolAvg_{period}'] = round(hl_df['Vol'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
            hl_df[f'ValAvg_{period}'] = round(hl_df['Val_CR'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
            hl_df.loc[:, f'ValChg%_Avg_{period}'] = round((hl_df['Val_CR'] - hl_df[f'ValAvg_{period}']) * 100 / hl_df[f'ValAvg_{period}'], 2)
            hl_df.loc[:, f'VolChg%_Avg_{period}'] = round((hl_df['Vol'] - hl_df[f'VolAvg_{period}']) * 100 / hl_df[f'VolAvg_{period}'], 2)

        hl_df['VolRto_10'] = round(hl_df['Vol'] / hl_df['VolAvg_10'], 1)
        hl_df.fillna(0, inplace=True)
        talist.append(hl_df)

    df = pd.concat(talist)
    df['Vol_lac'] = round(df['Vol'] / 100000, 3)

    rename_col = {
        'SYMBOL': 'Stock',
        'DATE': 'Date',
        'LOW_PRICE': 'LoPr',
        'PREV_CLOSE': 'PvPr',
        'CLOSE_PRICE': 'ClPr'
    }
    df.rename(columns=rename_col, inplace=True)

    reorder_col = [
        'Stock', 'Date', 'DlyRto_10', 'Pr_chg_%', 'VolRto_10', 'LTP', 'AvgPr', 'HiPr','DayHiNr%','DayLoNr%', 'HI52WNr%', 'LO52WNr%', '52WH', '52WL', 'Vol_lac', 'Val_CR', 'ClPr', 'PvPr',
        'LoPr', 'SMA_5', 'SMA_10', 'SMA_21', 'SMA_50', 'SMA_66', 'SMA_96', 'SMA_125', 'SMA_190', 'SMA_252',
        'NO_OF_TRADES', 'DELIV_QTY', 'DELIV_PER', 'DlyAvg_10',
        'Pr_chg', 'OPEN_PRICE', 'ValChg%_Avg_1', 'VolChg%_Avg_1',
        'ValChg%_Avg_5', 'VolChg%_Avg_5',
        'ValChg%_Avg_10', 'VolChg%_Avg_10',
        'ValChg%_Avg_21', 'VolChg%_Avg_21',
        'ValChg%_Avg_50', 'VolChg%_Avg_50',
        'ValChg%_Avg_66', 'VolChg%_Avg_66',
        'ValChg%_Avg_96', 'VolChg%_Avg_96',
        'ValChg%_Avg_125', 'VolChg%_Avg_125',
        'ValChg%_Avg_190', 'VolChg%_Avg_190',
        'ValChg%_Avg_252', 'VolChg%_Avg_252', 'VolAvg_252', 'ValAvg_252', 'VolAvg_190', 'ValAvg_190', 'VolAvg_125', 'ValAvg_125', 'VolAvg_96', 'ValAvg_96', 'VolAvg_66', 'ValAvg_66',
        'VolAvg_50', 'ValAvg_50', 'VolAvg_21', 'ValAvg_21', 'VolAvg_10', 'ValAvg_10', 'VolAvg_5', 'ValAvg_5'
    ]
    df = df[reorder_col]

    # Close the database connection
    conn.close()

    return df

# -----------------------------
# Import shortlist script
# -----------------------------
#shortlist_script_path = "/Users/shail/Documents/Trading/My-Code/onetimedb_hrly_shortlist.py"
#shortlist_script_path = "/Users/shail/StockShortlist//onetimedb_hrly_shortlist.py"
shortlist_script_path = os.path.join(BASE_DIR, "onetimedb_hrly_shortlist.py")
spec = importlib.util.spec_from_file_location("onetimedb_hrly_shortlist", shortlist_script_path)
shortlist_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shortlist_module)

if hasattr(shortlist_module, "dlydf_out"):
    dlydf_out = shortlist_module.dlydf_out
    stock_list = dlydf_out["Stock"].tolist() if "Stock" in dlydf_out.columns else []
else:
    dlydf_out = pd.DataFrame()
    stock_list = []

#shortlist_script_path = os.path.join(BASE_DIR, "daily_shortlist.py")
#spec = importlib.util.spec_from_file_location("daily_shortlist.py", shortlist_script_path)
#shortlist_module = importlib.util.module_from_spec(spec)
#spec.loader.exec_module(shortlist_module)
#if hasattr(shortlist_module, "short_df"):
#    dlydf_out = shortlist_module.short_df
#    stock_list = dlydf_out["Stock"].tolist() if "Stock" in dlydf_out.columns else []
#else:
#    dlydf_out = pd.DataFrame()
#    stock_list = []

# -----------------------------
# Prepare DataFrames
# -----------------------------
shortlisted_df = calsmavalavg_func(stock_list)
buysell_df = buysell_fno_func(stock_list)

#### Getting all the require columns for shortlisted columns.
periods = [5, 10, 21, 66, 125, 252]
updatelist = []
for stock in stock_list:
    shtupdate_df = dlydf_out[dlydf_out['Stock']==stock].copy()   # ✅ use .copy()
    sma_vals = shortlisted_df[shortlisted_df['Stock']==stock]

    shtupdate_df['valChgd%'] = round((shtupdate_df['Tval'] - sma_vals['Val_CR'])*100/ sma_vals['Val_CR'],2)
    shtupdate_df['volChgd%'] = round((shtupdate_df['Tvol'] - sma_vals['Vol_lac'])*100/ sma_vals['Vol_lac'],2)
    shtupdate_df['valChg10d%'] = round((shtupdate_df['Tval'] - sma_vals['ValAvg_10'])*100/ sma_vals['ValAvg_10'],2)
    shtupdate_df['volChg10d%'] = round((shtupdate_df['Tvol'] - sma_vals['VolAvg_10'])*100/ sma_vals['VolAvg_10'],2)
    shtupdate_df['valChg21d%'] = round((shtupdate_df['Tval'] - sma_vals['ValAvg_21'])*100/ sma_vals['ValAvg_21'],2)
    shtupdate_df['volChg21d%'] = round((shtupdate_df['Tvol'] - sma_vals['VolAvg_21'])*100/ sma_vals['VolAvg_21'],2)
    shtupdate_df['LO52WNr%'] = round((shtupdate_df['LTP'] - sma_vals['52WL']) * 100 / shtupdate_df['LTP'], 2)
    shtupdate_df['HI52WNr%']= round((sma_vals['52WH'] - shtupdate_df['LTP']) * 100 / shtupdate_df['LTP'], 2)

    for period in periods:
        shtupdate_df[f'Diff_SMA_{period}'] = np.abs(shtupdate_df['LTP'] - sma_vals[f'SMA_{period}'])  

    shtupdate_df['SMA_Diff'] = shtupdate_df[[f'Diff_SMA_{period}' for period in periods]].min(axis=1)
    shtupdate_df['Nr_SMA'] = shtupdate_df.apply(
        lambda row: min([(row[f'Diff_SMA_{period}'], period) for period in periods], key=lambda x: x[0])[1],
        axis=1
    )

    shtupdate_df['Nr_SMA_%'] = ((shtupdate_df['SMA_Diff'] / shtupdate_df['LTP']) * 100).round(2)
    shtupdate_df['SMA_Val'] = shtupdate_df.apply(
        lambda row: sma_vals[f"SMA_{row['Nr_SMA']}"].values[0],
        axis=1
    )

    shtupdate_df.drop(columns=[f'Diff_SMA_{period}' for period in periods], inplace=True)  # ✅ safe now
    updatelist.append(shtupdate_df)
newshortlist = pd.concat(updatelist, ignore_index=True) if updatelist else pd.DataFrame()
newcol = ['Stock', 'dly_RTO', 'prchg%', 'qty_rto', 'valChgd%', 'volChgd%',
       'valChg10d%', 'volChg10d%', 'valChg21d%', 'volChg21d%',
       'Tval', 'Tvol', 'capTime', 'High', 'LTP', 'VWAP',
       'Low', 'Nr_SMA', 'Nr_SMA_%', 'HI52WNr%', 'LO52WNr%', 'SMA_Val', 'RsDt',
       'RsDays']
newshortlist = newshortlist[newcol]
####
# -----------------------------
# Streamlit UI
# -----------------------------


# -----------------------------
# Sidebar: single stock selector
# -----------------------------
st.sidebar.header("Filter Options")
unique_stocks = newshortlist['Stock'].unique() if not newshortlist.empty else []
selected_stock = st.sidebar.selectbox("Select a Stock:", unique_stocks, key="stock_selector")

# -----------------------------
# NSE API fetch for selected stock



st.title(f"Stock Analysis Dashboard for {selected_stock}")
# Tabs
tab1, tab2, tab3 = st.tabs(["DlyRatio", "Hourly_Shortlisted", "BuySellData"])

# Tab 1
with tab1:
    st.subheader(f"Price Info for {selected_stock}")

    st.subheader(f"Delivery Ratio History for {selected_stock}")
    #stock_data = newshortlist[newshortlist['Stock'] == selected_stock]
    stock_data = shortlisted_df[shortlisted_df['Stock'] == selected_stock]
    #stock_data['Volchg_eq'] = round(stock_data['Volchg_eq']/1000,2)
    st.dataframe(stock_data)

    # Filter BuySell data
    filtered_df = buysell_df[buysell_df['Stock'] == selected_stock].copy()
    if not filtered_df.empty:
        filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format="%H:%M:%S", errors="coerce")
        filtered_df['Volchg_eq'] = round(filtered_df['Volchg_eq']/1000,2)
        plot_df = filtered_df.reset_index(drop=True)



        # Charts loop
        chart_specs = [
            ("Valchg_eq", "blue", "Valchg_eq(cr)"),
            ("Volchg_eq", "green", "Volchg_eq(K)"),
            ("%Prchg_fu", "orange", "%Prchg_fu"),
            ("%Prchg_eq", "blue", "%Prchg_eq"),
            ("PrChg_eq", "orange", "PriceChg_eq"),
            ("bsd%_eq", "blue", "BuySellDiff_eq"),
            ("bsd%_fu", "orange", "BuySellDiff_fu"),
            ("tot%_eq", "blue", "TotBuySell_eq"),
            ("tot%_fu", "orange", "TotBuySell_fu"),
            ("var%_eq", "blue", "VarValVol%_eq"),
        ]
        for col, color, title in chart_specs:
            if col in plot_df.columns:
                chart = alt.Chart(plot_df).mark_line(point=True).encode(
                    x="Time:T", y=f"{col}:Q", color=alt.value(color)
                ).properties(width=500, height=200, title=f"{title} for {selected_stock}")
                st.altair_chart(chart, width="stretch")
    else:
        st.warning(f"No BuySell data found for {selected_stock}")
# Tab 2: Display dlydf_out
# Tab 2
with tab2:
    st.subheader("Hourly Shortlisted")
    if not newshortlist.empty:
        st.dataframe(newshortlist)
    else:
        st.warning("No shortlisted data available")

# Tab 3
with tab3:
    st.subheader("Buy Sell Trade data for Future and Stock")
    if not buysell_df.empty:
        buysell_stock_data = buysell_df[buysell_df['Stock'] == selected_stock]
        st.dataframe(buysell_stock_data)
    else:
        st.warning("No BuySell data available")


