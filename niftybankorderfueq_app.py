import os
import sqlite3
import pandas as pd
import streamlit as st
import altair as alt
import numpy as np
import time
import requests
from datetime import date
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_DIR_db = "/home/shail/db"
BASE_DIR = "/home/shail/stockshortlisting"

# --- Page config ---
st.set_page_config(layout="wide")

@st.cache_data
def buysell_fno_func(stock: str):
    """
    Process buy/sell FNO data for a single stock from niftybank.db/niftybank table.
    """
    db_path = os.path.join(BASE_DIR_db, "niftybank.db")
    todays_date = date.today()
    with sqlite3.connect(db_path) as tg_conn:
        tg_query = f"""
            SELECT * FROM niftybank
            WHERE Date = "{todays_date}" AND Stock = "{stock}"
            ORDER BY Time DESC
        """
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

    newcol = ['Stock', 'Date', 'Time', '%Prchg_eq','bsd%_eq', '%Prchg_fu', 'bsd%_fu',
              'tot%_eq', 'tot%_fu', 'Tbuy_eq', 'Tsell_eq', 
              'High_eq', 'PrChg_eq', 'Ltp_eq', 'Vwap_eq', 'Ltp_fu','PrChg_fu',
              'Tsell_fu', 'Tbuy_fu','fuOI',
              'ValChg%_eq', 'Valchg_eq', 'VolChg%_eq', 'Volchg_eq', 'var%_eq',
              'ValChg%_fu', 'Valchg_fu', 'VolChg%_fu', 'Volchg_fu','var%_fu',
              'avg_eq', 'oichg_fu']
    alldf = alldf[newcol]
    return alldf

@st.cache_data
def shortlist_func(stock: str):
    """
    Process bhavcopy + 52-week data for a single stock.
    """
    db_path = os.path.join(BASE_DIR_db, "fullbhavcopy.db")
    conn = sqlite3.connect(db_path)

    # Load 52-week high/low data
    hl_52w_path = os.path.join(BASE_DIR, "52weekhl", "52_wk_High_low.csv")
    df1 = pd.read_csv(hl_52w_path)

    # Define all column renames in one dictionary
    rename_map = {
        'Adjusted_52_Week_High': '52WH',
        'Adjusted_52_Week_Low': '52WL',
        'TURNOVER_LACS': 'Val_CR',
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

    df1.rename(columns=rename_map, inplace=True)

    query = f"SELECT * FROM nsestock_t WHERE SYMBOL = '{stock}' ORDER BY Date DESC LIMIT 360"
    hl_df = pd.read_sql_query(query, conn)

    hl_df['DELIV_QTY'] = hl_df['DELIV_QTY'].astype(float)
    hl_df.rename(columns=rename_map, inplace=True)

    hl_df['Val_CR'] = round(hl_df['Val_CR'] / 100, 3)
    hl_df = pd.merge(hl_df, df1[['Stock', '52WH', '52WL']], on='Stock', how='left')

    # Derived metrics
    hl_df['DlyAvg_10'] = round(hl_df['DELIV_QTY'].rolling(window=10, min_periods=10).mean().shift(-10), 1)
    hl_df['DlyRto_10'] = round(hl_df['DELIV_QTY'] / hl_df['DlyAvg_10'], 1)
    hl_df['Pr_chg'] = round(hl_df['ClPr'] - hl_df['PvPr'], 2)
    hl_df['Pr_chg_%'] = round((hl_df['ClPr'] - hl_df['PvPr']) * 100 / hl_df['PvPr'], 2)
    hl_df['LO52WNr%'] = round((hl_df['ClPr'] - hl_df['52WL']) * 100 / hl_df['52WL'], 2)
    hl_df['HI52WNr%'] = round((hl_df['52WH'] - hl_df['ClPr']) * 100 / hl_df['52WH'], 2)
    hl_df['DayHiNr%'] = round((hl_df['HiPr'] - hl_df['ClPr']) * 100 / hl_df['HiPr'], 2)
    hl_df['DayLoNr%'] = round((hl_df['ClPr'] - hl_df['LoPr']) * 100 / hl_df['LoPr'], 2)

    # Rolling averages
    periods = [1, 5, 10, 21, 50, 66, 96, 125, 190, 252]
    for period in periods:
        hl_df[f'SMA_{period}'] = round(hl_df['ClPr'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df[f'VolAvg_{period}'] = round(hl_df['Vol'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df[f'ValAvg_{period}'] = round(hl_df['Val_CR'].rolling(window=period, min_periods=period).mean().shift(-period), 1)
        hl_df.loc[:, f'ValChg%_Avg_{period}'] = round((hl_df['Val_CR'] - hl_df[f'ValAvg_{period}']) * 100 / hl_df[f'ValAvg_{period}'], 2)
        hl_df.loc[:, f'VolChg%_Avg_{period}'] = round((hl_df['Vol'] - hl_df[f'VolAvg_{period}']) * 100 / hl_df[f'VolAvg_{period}'], 2)

    hl_df['VolRto_10'] = round(hl_df['Vol'] / hl_df['VolAvg_10'], 1)
    hl_df.fillna(0, inplace=True)

    hl_df['Vol_lac'] = round(hl_df['Vol'] / 100000, 3)
    specific_map = { 'Pr_chg_%': 'prchg%', 'DlyRto_10': 'dly_RTO', 'VolRto_10': 'qty_rto' }
    
    # Reorder columns
     # --- Pattern-based rename: remove "Avg_" everywhere --- 
    hl_df.rename(columns=lambda c: c.replace("Avg_", ""), inplace=True)
    hl_df.rename(columns=specific_map, inplace=True)
    newcol = [
    'Stock', 'Date', 'dly_RTO', 'prchg%', 'qty_rto','LTP', 'HiPr', 
    'ValChg%_10', 'VolChg%_10', 'ValChg%_21', 'VolChg%_21',
    'ValChg%_50', 'VolChg%_50',
    'AvgPr', 'Val_CR','Vol_lac', 'LoPr', 'ClPr',
    'NO_OF_TRADES', 'DELIV_QTY', 'DELIV_PER',
    '52WH', '52WL', 'Dly10', 'Pr_chg', 'LO52WNr%', 'HI52WNr%',
    'DayHiNr%', 'DayLoNr%',
    'SMA_1', 'Vol1', 'Val1', 'ValChg%_1', 'VolChg%_1',
    'SMA_5', 'Vol5', 'Val5', 'ValChg%_5', 'VolChg%_5',
    'SMA_10', 'Vol10', 'Val10',
    'SMA_21', 'Vol21', 'Val21',
    'SMA_50', 'Vol50', 'Val50',
    'SMA_66', 'Vol66', 'Val66', 'ValChg%_66', 'VolChg%_66',
    'SMA_96', 'Vol96', 'Val96', 'ValChg%_96', 'VolChg%_96',
    'SMA_125', 'Vol125', 'Val125', 'ValChg%_125', 'VolChg%_125',
    'SMA_190', 'Vol190', 'Val190', 'ValChg%_190', 'VolChg%_190',
    'SMA_252', 'Vol252', 'Val252', 'ValChg%_252', 'VolChg%_252',
    'Vol'
    ]

    hl_df = hl_df[newcol]
 
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

def parse_time(df, fmt):
    if 'Time' in df.columns and 'Date' in df.columns:
        df['DateTime'] = pd.to_datetime(
            df['Date'].astype(str) + ' ' + df['Time'].astype(str),
            format=f"%Y-%m-%d {fmt}", errors="coerce"
        )
        #df.sort_values(by='DateTime', inplace=True)
        df.sort_values(by='DateTime', ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df

# --- Sidebar selectors ---
st.sidebar.header("Filter Options")

with sqlite3.connect(os.path.join(BASE_DIR_db, "niftybank.db")) as conn:
    fno_df = pd.read_sql_query("SELECT * FROM niftybank ORDER BY Date DESC", conn)

fno_stocks = fno_df['Stock'].unique() if not fno_df.empty else []
selected_fno_stock = st.sidebar.selectbox("Select an FNO Stock:", fno_stocks, key="fno_selector")
manual_stock = st.sidebar.text_input("Enter any Stock Symbol:", "").strip()

# NEW: column selector for Tab 3
available_cols = fno_df.columns.tolist()
#selected_column = st.sidebar.selectbox("Select column for All Stocks Graph:", available_cols)

tab1, tab2, tab3 = st.tabs(["FNO DlyRatio", "Fu & Eq BuySellData", "All Stocks Graph"])


if selected_fno_stock or manual_stock:
    stock_to_analyze = manual_stock if manual_stock else selected_fno_stock
    buysell_df_single = buysell_fno_func(stock_to_analyze)
    shortlisted_df_single = shortlist_func(stock_to_analyze)
    qtyjson, chgjson = fetch_nse_data(stock_to_analyze)

    # --- Tab 1 ---
    with tab1:

        #st.subheader(f"Fu & Eq BuySell Order Graphs for {stock_to_analyze}")    
        st.subheader(f"Fu & Eq BuySell Order Graphs for {stock_to_analyze}")
        if not buysell_df_single.empty:
            filtered_df = buysell_df_single.copy()
            #filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format="%H:%M:%S", errors="coerce")
            filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format="%H:%M", errors="coerce")
            filtered_df['Volchg_eq'] = round(filtered_df['Volchg_eq'] / 1000, 2)
            plot_df = filtered_df.reset_index(drop=True)

            chart_specs = [
                ("%Prchg_eq", "blue", "%Prchg_eq"),
                ("Valchg_eq", "blue", "Valchg_eq(cr)"),
                ("Volchg_eq", "green", "Volchg_eq(K)"),
                ("PrChg_eq", "orange", "PriceChg_eq"),
                ("%Prchg_fu", "orange", "%Prchg_fu"),
                ("Valchg_fu", "blue", "Valchg_fu(cr)"),
                ("Volchg_fu", "green", "Volchg_fu(K)"),
                ("bsd%_eq", "blue", "BuySellDiff_eq"),
                ("bsd%_fu", "orange", "BuySellDiff_fu"),
                ("tot%_eq", "blue", "TotBuySell_eq"),
                ("tot%_fu", "orange", "TotBuySell_fu"),
            ]
            for col, color, title in chart_specs:
                if col in plot_df.columns:
                    chart = (
                        alt.Chart(plot_df)
                        .mark_line(point=True)
                        .encode(x="Time:T", y=f"{col}:Q", color=alt.value(color))
                        .properties(width=1000, height=200, title=f"{title} for {stock_to_analyze}")
                    )
                    st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f"No BuySell data found for {stock_to_analyze}")
        st.subheader(f"Price Info for {stock_to_analyze}")    
        # Fetch NSE API JSON for the selected FNO stock
        qtyjson, chgjson = fetch_nse_data(stock_to_analyze)    

        # Derived metrics
        DayLoNrP, DayHiNrP = None, None
        if qtyjson:
            meta = qtyjson['equityResponse'][0]['metaData']
            ltp = qtyjson['equityResponse'][0]['tradeInfo']['lastPrice']
            day_low = meta['dayLow']
            day_high = meta['dayHigh']
            DayLoNrP = np.round((ltp - day_low) * 100 / ltp, 2)
            DayHiNrP = np.round((day_high - ltp) * 100 / ltp, 2)    

        # Display metrics in rows of 5
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
                cols = st.columns([0.9] * 5)
                for j, (label, value) in enumerate(metrics[i:i+5]):
                    cols[j].metric(label, value, border=True)    

        st.subheader(f"Delivery Ratio History for {stock_to_analyze}")
        shortlisted_df_single
    # ---
    with tab2:
        #st.subheader(f"Buy Sell Trade data for {selected_fno_stock}")
        st.subheader(f"Buy Sell Trade data for {stock_to_analyze}")
        st.dataframe(buysell_df_single)
    # --- Tab 3 ---

with tab3:
    st.subheader("All Stocks Graphs (Grouped Metrics)")

    chart_groups = [
        (["%Prchg_eq", "%Prchg_fu"], ["blue", "orange"], "% Price Change"),
        (["Valchg_eq", "Valchg_fu"], ["blue", "orange"], "Value Change (cr)"),
        (["Volchg_eq", "Volchg_fu"], ["green", "orange"], "Volume Change"),
        (["bsd%_eq", "bsd%_fu"], ["blue", "orange"], "Buy-Sell Diff"),
        (["tot%_eq", "tot%_fu"], ["blue", "orange"], "Total Buy-Sell %"),
        (["PrChg_eq", "PrChg_fu"], ["orange", "blue"], "Price Change"),
    ]

    group_options = [g[2] for g in chart_groups]
    selected_groups = st.multiselect(
        "Select metric groups to plot:",
        group_options,
        default=[group_options[0]]
    )

    for stock in fno_stocks:
        st.markdown(f"### {stock}")
        df_all = buysell_fno_func(stock)
        if not df_all.empty:
            # Combine Date + Time into full DateTime
            df_all['DateTime'] = pd.to_datetime(
                df_all['Date'].astype(str) + " " + df_all['Time'].astype(str),
                errors="coerce"
            )
            # Extract just the time string for tooltip
            df_all['TimeOnly'] = pd.to_datetime(df_all['Time'], errors="coerce").dt.strftime("%H:%M")

            if "Volchg_eq" in df_all.columns:
                df_all['Volchg_eq'] = round(df_all['Volchg_eq'] / 1000, 2)

            plot_df = df_all.reset_index(drop=True)

            for cols, colors, title in chart_groups:
                if title in selected_groups:
                    layers = []
                    for col, color in zip(cols, colors):
                        if col in plot_df.columns:
                            layers.append(
                                alt.Chart(plot_df)
                                .mark_line(point=True)
                                .encode(
                                    x=alt.X("DateTime:T", title="DateTime"),
                                    y=f"{col}:Q",
                                    color=alt.value(color),
                                    tooltip=["Stock", "Time", col]  # show only time + value
                                )
                            )
                    if layers:
                        chart = alt.layer(*layers).properties(
                            width=1000, height=200, title=f"{title} for {stock}"
                        )
                        st.altair_chart(chart, use_container_width=True)
        else:
            st.warning(f"No BuySell data found for {stock}")
