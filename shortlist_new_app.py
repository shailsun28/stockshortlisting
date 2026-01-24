import pandas as pd
import streamlit as st
import sqlite3
from datetime import datetime, date
import time
import altair as alt
import requests
import json
import numpy as np
import importlib.util
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

def buysell_fno_func(stock: str):
    """
    Process buy/sell FNO data for a single stock.
    """
    db_path = os.path.join(BASE_DIR_db, "eq_fu_buysell_qty.db")
    todays_date = date.today()
    with sqlite3.connect(db_path) as tg_conn:
        tg_query = f'SELECT * FROM fno WHERE Date = "{todays_date}" ORDER BY Time DESC'
        tgdf = pd.read_sql_query(tg_query, tg_conn)

    alldf = tgdf[tgdf['Stock'] == stock].sort_values(by=['Time'], ascending=False).reset_index(drop=True)
    if alldf.empty:
        return pd.DataFrame()

    numeric_cols = [
        'Tbuy_eq', 'Tsell_eq', 'Tvalue_eq', 'Tvol_eq',
        'High_eq', 'PrChg_eq', '%Prchg_eq', 'Ltp_eq', 'Vwap_eq', 'Ltp_fu',
        'PrChg_fu', '%Prchg_fu', 'Tsell_fu', 'Tbuy_fu', 'Tvol_fu',
        'Tvalue_fu', 'fuOI'
    ]
    alldf[numeric_cols] = alldf[numeric_cols].apply(pd.to_numeric, errors='coerce')
    alldf.fillna(0, inplace=True)

    # Transformations (same as before)
    alldf['Tvalue_eq'] = alldf['Tvalue_eq'] / 10000000
    alldf['ValChg%_eq'] = round((alldf['Tvalue_eq'] - alldf['Tvalue_eq'].shift(-1)) * 100 / alldf['Tvalue_eq'].shift(-1), 2)
    alldf['Valchg_eq'] = alldf['Tvalue_eq'] - alldf['Tvalue_eq'].shift(-1)
    # ... keep rest of transformations unchanged ...
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

    return alldf

def shortlist_func(stock: str):
    """
    Process bhavcopy + 52-week data for a single stock.
    """
    db_path = os.path.join(BASE_DIR_db, "fullbhavcopy.db")
    conn = sqlite3.connect(db_path)

    hl_52w_path = os.path.join(BASE_DIR, "52weekhl", "52_wk_High_low.csv")
    df1 = pd.read_csv(hl_52w_path)
    df1.rename(columns={'Adjusted_52_Week_High': '52WH', 'Adjusted_52_Week_Low': '52WL'}, inplace=True)

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

    # Rolling averages and derived metrics (same as before)
    periods = [1, 5, 10, 21, 50, 66, 96, 125, 190, 252]
    for period in periods:
        hl_df[f'SMA_{period}'] = round(hl_df['CLOSE_PRICE'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df[f'VolAvg_{period}'] = round(hl_df['Vol'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df[f'ValAvg_{period}'] = round(hl_df['Val_CR'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df.loc[:, f'ValChg%_Avg_{period}'] = round((hl_df['Val_CR'] - hl_df[f'ValAvg_{period}']) * 100 / hl_df[f'ValAvg_{period}'], 2)
        hl_df.loc[:, f'VolChg%_Avg_{period}'] = round((hl_df['Vol'] - hl_df[f'VolAvg_{period}']) * 100 / hl_df[f'VolAvg_{period}'], 2)

    hl_df['VolRto_10'] = round(hl_df['Vol'] / hl_df['VolAvg_10'], 1)
    hl_df.fillna(0, inplace=True)

    hl_df['Vol_lac'] = round(hl_df['Vol'] / 100000, 3)
    hl_df.rename(columns={'SYMBOL': 'Stock', 'DATE': 'Date', 'LOW_PRICE': 'LoPr', 'PREV_CLOSE': 'PvPr', 'CLOSE_PRICE': 'ClPr'}, inplace=True)
    reorder_col = [
        'Stock', 'Date', 'DlyRto_10', 'Pr_chg_%', 'VolRto_10', 'LTP', 'AvgPr', 'HiPr','ValChg%_Avg_10', 
        'VolChg%_Avg_10','ValChg%_Avg_21',   'VolChg%_Avg_21','ValChg%_Avg_50', 'VolChg%_Avg_50','DayHiNr%','DayLoNr%', 
        'HI52WNr%', 'LO52WNr%', '52WH', '52WL', 'Vol_lac', 'Val_CR', 'ClPr', 'PvPr',
        'LoPr', 'SMA_5', 'SMA_10', 'SMA_21', 'SMA_50', 'SMA_66', 'SMA_96', 'SMA_125', 'SMA_190', 'SMA_252',
        'NO_OF_TRADES', 'DELIV_QTY', 'DELIV_PER', 'DlyAvg_10',
        'Pr_chg', 'OPEN_PRICE', 'ValChg%_Avg_1', 'VolChg%_Avg_1',
        'ValChg%_Avg_5', 'VolChg%_Avg_5','ValChg%_Avg_66', 'VolChg%_Avg_66',
        'ValChg%_Avg_96', 'VolChg%_Avg_96','ValChg%_Avg_125', 'VolChg%_Avg_125','ValChg%_Avg_190', 'VolChg%_Avg_190',
        'ValChg%_Avg_252', 'VolChg%_Avg_252', 'VolAvg_252', 'ValAvg_252', 'VolAvg_190', 'ValAvg_190', 'VolAvg_125', 
        'ValAvg_125', 'VolAvg_96', 'ValAvg_96', 'VolAvg_66', 'ValAvg_66',
        'VolAvg_50', 'ValAvg_50', 'VolAvg_21', 'ValAvg_21', 'VolAvg_10', 'ValAvg_10', 'VolAvg_5', 'ValAvg_5'
        ]
    #hl_df = hl_df[reorder_col]
    conn.close()
    return hl_df

def fetch_nse_data(stock: str):
    """
    Fetch NSE JSON data (quote + change history) for a single stock.
    Returns (qtyjson, chgjson) or (None, None) if request fails.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': f'https://www.nseindia.com/get-quotes/equity?symbol={stock}',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    encoded_stock = stock.replace("&", "%26")
    main_url = "https://www.nseindia.com"
    qty_url = (
        f"https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?"
        f"functionName=getSymbolData&marketType=N&series=EQ&symbol={encoded_stock}"
    )
    chg_url = (
        f"https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?"
        f"functionName=getYearwiseData&symbol={encoded_stock}EQN"
    )

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
        # Warm up session
        session.get(main_url, headers=headers)
        time.sleep(1)  # polite delay
        qty_resp = session.get(qty_url, headers=headers)
        qty_resp.raise_for_status()
        chg_resp = session.get(chg_url, headers=headers)
        chg_resp.raise_for_status()
        return qty_resp.json(), chg_resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching NSE data for {stock}: {e}")
        return None, None


#shortlist_script_path = "/Users/shail/Documents/Trading/My-Code/onetimedb_hrly_shortlist.py"
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


dfs = [shortlist_func(s) for s in stock_list]
shortlisted_df = pd.concat(dfs)

st.sidebar.header("Filter Options")

# Dropdown for shortlisted stocks
unique_stocks = shortlisted_df['Stock'].unique() if not shortlisted_df.empty else []
selected_stock = st.sidebar.selectbox("Select a Stock:", unique_stocks, key="stock_selector")

# Free text input for any stock
manual_stock = st.sidebar.text_input("Enter any Stock Symbol:", "").strip()

# Collect whichever stocks are chosen
stocks_to_process = []
if selected_stock:
    stocks_to_process.append(selected_stock)
if manual_stock:
    stocks_to_process.append(manual_stock)
    
dlyhistory_df = shortlist_func(selected_stock)
buysell_df = buysell_fno_func(selected_stock)

for stock in stocks_to_process:
    # Run your single-stock functions
    shortlisted_df_single = shortlist_func(stock)
    buysell_df_single = buysell_fno_func(stock)

    # Fetch NSE API JSON
    qtyjson, chgjson = fetch_nse_data(stock)   # helper function we outlined earlier

    # Derived metrics
    DayLoNrP, DayHiNrP = None, None
    if qtyjson:
        meta = qtyjson['equityResponse'][0]['metaData']
        ltp = qtyjson['equityResponse'][0]['tradeInfo']['lastPrice']
        day_low = meta['dayLow']
        day_high = meta['dayHigh']
        DayLoNrP = np.round((ltp - day_low) * 100 / ltp, 2)
        DayHiNrP = np.round((day_high - ltp) * 100 / ltp, 2)

    # Tabs per stock
    st.title(f"Stock Analysis Dashboard for {stock}")
    tab1, tab2, tab3 = st.tabs([f"{stock} DlyRatio", f"Hourly_Shortlisted Stock", f"{stock} BuySellData"])

    # Tab 1
    with tab1:
        st.subheader(f"Price Info for {stock}")
        if qtyjson and chgjson:
            metrics = [
                ("Change%", qtyjson['equityResponse'][0]['metaData']['pChange']),
                ("DayHiNr%", DayHiNrP),
                ("DayHigh", qtyjson['equityResponse'][0]['metaData']['dayHigh']),
                ("WeekChg%", chgjson[0]['one_week_chng_per']),
                ("MonthChg%", chgjson[0]['one_month_chng_per']),
                ("Ltp", qtyjson['equityResponse'][0]['tradeInfo']['lastPrice']),
                ("DayLoNrP%", DayLoNrP),
                ("DayLow", qtyjson['equityResponse'][0]['metaData']['dayLow']),
                ("PrChg", qtyjson['equityResponse'][0]['metaData']['change']),
                ("3MonChg%", chgjson[0]['three_month_chng_per']),
            ]
            for i in range(0, len(metrics), 5):
                cols = st.columns([0.9]*5)
                for j, (label, value) in enumerate(metrics[i:i+5]):
                    cols[j].metric(label, value, border=True)

        st.subheader(f"Delivery Ratio History for {stock}")
        st.dataframe(shortlisted_df_single)

        # Charts from buysell_df_single
        filtered_df = buysell_df_single.copy()
        if not filtered_df.empty:
            filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format="%H:%M:%S", errors="coerce")
            filtered_df['Volchg_eq'] = round(filtered_df['Volchg_eq']/1000,2)
            plot_df = filtered_df.reset_index(drop=True)

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
                    ).properties(width=500, height=200, title=f"{title} for {stock}")
                    st.altair_chart(chart, width="stretch")
                    #st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f"No BuySell data found for {stock}")

    # Tab 2
    with tab2:
        st.subheader("Hourly Shortlisted (global dlydf_out)")
        st.dataframe(dlydf_out)

    # Tab 3
    with tab3:
        st.subheader(f"Buy Sell Trade data for {stock}")
        st.dataframe(buysell_df_single)


