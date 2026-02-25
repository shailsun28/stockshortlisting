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
              'tot%_eq', 'tot%_fu', 'Tbuy_eq', 'Tsell_eq', 'Tvalue_eq', 'Tvol_eq',
              'High_eq', 'PrChg_eq', 'Ltp_eq', 'Vwap_eq', 'Ltp_fu','PrChg_fu',
              'Tsell_fu', 'Tbuy_fu', 'Tvol_fu', 'Tvalue_fu','fuOI',
              'ValChg%_eq', 'Valchg_eq', 'VolChg%_eq', 'Volchg_eq', 'var%_eq',
              'ValChg%_fu', 'Valchg_fu', 'VolChg%_fu', 'Volchg_fu','var%_fu',
              'avg_eq', 'oichg_fu','avg_fu', 'avgOI_fu']
    alldf = alldf[newcol]
    return alldf

# --- Sidebar selectors ---
st.sidebar.header("Filter Options")

# Load available stocks from niftybank table
with sqlite3.connect(os.path.join(BASE_DIR_db, "niftybank.db")) as conn:
    fno_df = pd.read_sql_query("SELECT * FROM niftybank ORDER BY Date DESC", conn)

fno_stocks = fno_df['Stock'].unique() if not fno_df.empty else []
selected_fno_stock = st.sidebar.selectbox("Select an FNO Stock:", fno_stocks, key="fno_selector")
manual_stock = st.sidebar.text_input("Enter any Stock Symbol:", "").strip()

tab1, tab2 = st.tabs(["FNO DlyRatio", "Fu & Eq BuySellData"])

if selected_fno_stock or manual_stock:
    stock_to_analyze = manual_stock if manual_stock else selected_fno_stock
    buysell_df_single = buysell_fno_func(stock_to_analyze)

    # --- Tab 1 ---
    with tab1:
        st.subheader(f"Fu & Eq BuySell Order Graphs for {stock_to_analyze}")
        if not buysell_df_single.empty:
            filtered_df = buysell_df_single.copy()
            #filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format="%H:%M:%S", errors="coerce")
            filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format="%H:%M", errors="coerce")
            filtered_df['Volchg_eq'] = round(filtered_df['Volchg_eq'] / 1000, 2)
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

    # ---
    with tab2:
        #st.subheader(f"Buy Sell Trade data for {selected_fno_stock}")
        st.subheader(f"Buy Sell Trade data for {stock_to_analyze}")
        st.dataframe(buysell_df_single)