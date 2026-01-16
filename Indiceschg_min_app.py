import streamlit as st
import pandas as pd
import sqlite3
import numpy as np

# -----------------------------
# Utility Functions
# -----------------------------

def orderfunc(df):
    subset = df.copy()
    numeric_cols = ['noOfTrades', 'noOfOrders']
    subset[numeric_cols] = subset[numeric_cols].apply(pd.to_numeric, errors='coerce')
    subset.fillna(0, inplace=True)
    subset['Orderchg'] = round(subset['noOfOrders'].diff(-1)/100000,3)
    subset['Trdnochg'] = round(subset['noOfTrades'].diff(-1), 2)
    subset['Orderchg%'] = round(subset['noOfOrders'].diff(-1) * 100 / subset['noOfOrders'].shift(-1).replace(0, np.nan), 2)
    subset['Trdnochg%'] = round(subset['noOfTrades'].diff(-1) * 100 / subset['noOfTrades'].shift(-1).replace(0, np.nan), 2)
    return subset

def diffprocess(df):
    subset = df.copy()
    numeric_cols = ['Tval', 'Tvol','noOfTrades', 'noOfOrders']
    subset[numeric_cols] = subset[numeric_cols].apply(pd.to_numeric, errors='coerce')
    subset.fillna(0, inplace=True)

    # Differences and percentages
    subset['Valchg'] = round(subset['Tval'].diff(-1), 2)
    subset['Volchg'] = round(subset['Tvol'].diff(-1), 2)
    subset['Chgavg'] = round(subset['Valchg'] * 100 / subset['Volchg'], 2)
    subset['Tavgchg%'] = round(subset['Chgavg'].diff(-1) * 100 / subset['Chgavg'].shift(-1).replace(0, np.nan), 2)
    subset['Valchg%'] = round(subset['Tval'].diff(-1) * 100 / subset['Tval'].shift(-1).replace(0, np.nan), 2)
    subset['Volchg%'] = round(subset['Tvol'].diff(-1) * 100 / subset['Tvol'].shift(-1).replace(0, np.nan), 2)

    subset.fillna(0, inplace=True)
    subset['Orderchg_lac'] = round(subset['noOfOrders'].diff(-1)/100000,3)
    subset['Trdnochg'] = round(subset['noOfTrades'].diff(-1), 2)
    subset['Orderchg%'] = round(subset['noOfOrders'].diff(-1) * 100 / subset['noOfOrders'].shift(-1).replace(0, np.nan), 2)
    subset['Trdnochg%'] = round(subset['noOfTrades'].diff(-1) * 100 / subset['noOfTrades'].shift(-1).replace(0, np.nan), 2)

    subset['Var%'] = round(subset['Valchg%'] - subset['Volchg%'], 2)
    subset['Totavg'] = round(subset['Tval'] * 100 / subset['Tvol'], 2)
    return subset

# --- your valuechange function stays the same ---
def valuechange(df):
    subset = df.copy()
    subset.rename(columns={
        'declines': 'Dec', 'advances': 'Adv',
        'unchanged': 'Unchg', 'dayHigh': 'High', 'dayLow': 'Low',
        'lastPrice': 'LTP', 'pChange': 'chg%', 'change': 'chg',
        'totalTradedVolume': 'Tvol', 'totalTradedValue': 'Tval'
    }, inplace=True)

    newcol = ['symbol', 'Date', 'Time','chg%', 'Valchg', 'Volchg', 'Valchg%', 'Volchg%',
              'Var%', 'High', 'Low', 'LTP', 'chg', 'Adv', 'Dec', 'Unchg',
              'Tvol', 'Tval','Tavg', 'rto%']

    subset['ffmc'] = round(subset['ffmc']/10000000, 3)
    subset.fillna(0, inplace=True)
    subset['Valchg'] = round(subset['Tval'].diff(-1)/10000000, 2)
    subset['Volchg'] = round(subset['Tvol'].diff(-1)/100000, 2)
    subset['Tavg'] = round(subset['Valchg'] * 100 / subset['Volchg'], 2)
    subset['Tavgchg%'] = round(subset['Tavg'].diff(-1) * 100 / subset['Tavg'].shift(-1).replace(0, pd.NA), 2)
    subset['Valchg%'] = round(subset['Tval'].diff(-1) * 100 / subset['Tval'].shift(-1).replace(0, pd.NA), 2)
    subset['Volchg%'] = round(subset['Tvol'].diff(-1) * 100 / subset['Tvol'].shift(-1).replace(0, pd.NA), 2)
    subset.fillna(0, inplace=True)
    subset['Var%'] = round(subset['Valchg%'] - subset['Volchg%'], 2)
    subset['rto%'] = round(subset['Valchg%']/subset['Volchg%'],2)
    subset['Totavg'] = round(subset['Tval']/subset['Tvol'],2)
    subset['Tval'] = round(subset['Tval']/10000000, 3)
    subset = subset[newcol]
    return subset
# -----------------------------
# Load Index Tables
# -----------------------------

idx_tables = ["50", "BANK", "IT", "PHARMA", "METAL", "OIL_GAS", "TOTAL_MARKET"]
idx_path = "/Users/shail/Documents/Trading/market-turnover/db/allindices.db"

dfs = {}
with sqlite3.connect(idx_path) as gconn:
    for tab in idx_tables:
        query = f"SELECT * FROM '{tab}' ORDER BY Date DESC, Time DESC"
        dfs[tab] = pd.read_sql_query(query, gconn)

bank = valuechange(dfs['BANK'])
nifty = valuechange(dfs['50'])
it = valuechange(dfs['IT'])
pharma = valuechange(dfs['PHARMA'])
metal = valuechange(dfs['METAL'])
oil = valuechange(dfs['OIL_GAS'])
tm = valuechange(dfs['TOTAL_MARKET'])

index_dataframes = {
    "NIFTY 50": nifty,
    "BANK": bank,
    "IT": it,
    "PHARMA": pharma,
    "METAL": metal,
    "OIL & GAS": oil,
    "TOTAL MARKET": tm
}

# -----------------------------
# Load Turnover Tables
# -----------------------------

tables = {
    'cm_total': ['Date','Time','pchg','Valchg','Volchg','Chgavg','Var%','Adv','Dec','Tavgchg%',
                 'Trdnochg','Orderchg_lac','averageTrade','Valchg%','Volchg%','Orderchg%','Trdnochg%','Totavg'],
    'fno_total': ['Date','Time','Valchg','Volchg','Chgavg','Var%','Adv','Dec','Tavgchg%',
                  'oival_lac','Trdnochg','Orderchg_lac','averageTrade','Ttrd','Unchg',
                  'Valchg%','Volchg%','Orderchg%','Trdnochg%','Totavg'],
    'grand_total': ['Date','Time','Valchg','Volchg','Chgavg','Var%','Adv','Dec','Tavgchg%',
                    'oival_lac','Trdnochg','averageTrade','noOfOrders','Ttrd','Unchg',
                    'Valchg%','Volchg%','Orderchg_lac','Orderchg%','Trdnochg%','Totavg']
}

results = {}
db_path = "/Users/shail/Documents/Trading/market-turnover/db/allturnover.db"

def process_table(dataframe, reorder_columns):
    dataframe = diffprocess(dataframe)
    dataframe = dataframe[reorder_columns]
    return dataframe

with sqlite3.connect(db_path) as gconn:
    for table_name, reorder_columns in tables.items():
        query = f"SELECT * FROM {table_name} ORDER BY Date DESC, Time DESC"
        dataframe = pd.read_sql_query(query, gconn)
        results[table_name] = process_table(dataframe, reorder_columns)

cm = results['cm_total']
fn = results['fno_total']
gt = results['grand_total']

turnover_dataframes = {
    "CM": cm,
    "FNO": fn,
    "GT": gt
}

# -----------------------------
# Streamlit UI
# -----------------------------

st.title("Index & Turnover Dashboard")

# Auto-refresh every 2 minutes
#st.experimental_autorefresh(interval=120000, limit=None, key="refresh")

# First selector: Index
selected_index = st.sidebar.selectbox("Select an Index:", list(index_dataframes.keys()))

# Second selector: Turnover
selected_turnover = st.sidebar.selectbox("Select Turnover Table:", list(turnover_dataframes.keys()))

# Show both tables one above the other
st.subheader(f"{selected_index} DataFrame")
st.dataframe(index_dataframes[selected_index].head(50))   # limit rows if needed

st.subheader(f"{selected_turnover} Turnover DataFrame")
st.dataframe(turnover_dataframes[selected_turnover].head(50))
