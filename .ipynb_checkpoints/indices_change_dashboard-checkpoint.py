import pandas as pd
import streamlit as st
import sqlite3
from datetime import date
import altair as alt
import numpy as np
import os

# -----------------------------
# Config
# -----------------------------
BASE_DIR_db = "/home/shail/db"
TODAY = date.today()

# -----------------------------
# Utility Functions
# -----------------------------
def safe_numeric(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def diffprocess(df):
    df = safe_numeric(df.copy(), ['Tval','Tvol','noOfTrades','noOfOrders'])
    df.fillna(0, inplace=True)

    if 'Tval' in df.columns:
        df['Valchg'] = df['Tval'].diff(-1).round(2)
        df['Valchg%'] = (df['Tval'].diff(-1)*100/df['Tval'].shift(-1).replace(0,np.nan)).round(2)
    if 'Tvol' in df.columns:
        df['Volchg'] = df['Tvol'].diff(-1).round(2)
        df['Volchg%'] = (df['Tvol'].diff(-1)*100/df['Tvol'].shift(-1).replace(0,np.nan)).round(2)
    if {'Valchg','Volchg'}.issubset(df.columns):
        df['Chgavg'] = (df['Valchg']*100/df['Volchg']).round(2)
        df['Tavgchg%'] = (df['Chgavg'].diff(-1)*100/df['Chgavg'].shift(-1).replace(0,np.nan)).round(2)

    if 'noOfOrders' in df.columns:
        df['Orderchg_lac'] = (df['noOfOrders'].diff(-1)/100000).round(3)
        df['Orderchg%'] = (df['noOfOrders'].diff(-1)*100/df['noOfOrders'].shift(-1).replace(0,np.nan)).round(2)
    if 'noOfTrades' in df.columns:
        df['Trdnochg'] = df['noOfTrades'].diff(-1).round(2)
        df['Trdnochg%'] = (df['noOfTrades'].diff(-1)*100/df['noOfTrades'].shift(-1).replace(0,np.nan)).round(2)

    if {'Valchg%','Volchg%'}.issubset(df.columns):
        df['Var%'] = (df['Valchg%']-df['Volchg%']).round(2)
    if {'Tval','Tvol'}.issubset(df.columns):
        df['Totavg'] = (df['Tval']*100/df['Tvol']).round(2)

    df.fillna(0, inplace=True)
    return df

def valuechange(df):
    df = df.copy()
    df.rename(columns={
        'declines':'Dec','advances':'Adv','unchanged':'Unchg',
        'dayHigh':'High','dayLow':'Low','lastPrice':'LTP',
        'pChange':'pchg','change':'chg',
        'totalTradedVolume':'Tvol','totalTradedValue':'Tval'
    }, inplace=True)

    df['ffmc'] = (df.get('ffmc',0)/10000000).round(3)
    df['Valchg'] = (df['Tval'].diff(-1)/10000000).round(2)
    df['Volchg'] = (df['Tvol'].diff(-1)/100000).round(2)
    df['Chgavg'] = (df['Valchg']*100/df['Volchg']).round(2)
    df['Tavgchg%'] = (df['Chgavg'].diff(-1)*100/df['Chgavg'].shift(-1).replace(0,pd.NA)).round(2)
    df['Valchg%'] = (df['Tval'].diff(-1)*100/df['Tval'].shift(-1).replace(0,pd.NA)).round(2)
    df['Volchg%'] = (df['Tvol'].diff(-1)*100/df['Tvol'].shift(-1).replace(0,pd.NA)).round(2)
    df['Var%'] = (df['Valchg%']-df['Volchg%']).round(2)
    df['rto%'] = (df['Valchg%']/df['Volchg%']).round(2)
    df['Totavg'] = (df['Tval']/df['Tvol']).round(2)
    df['Tval'] = (df['Tval']/10000000).round(3)
    df.fillna(0, inplace=True)

    keep = ['symbol','Date','Time','pchg','Valchg','Volchg','Valchg%','Volchg%',
            'Var%','High','Low','LTP','chg','Adv','Dec','Unchg',
            'Tvol','Tval','Chgavg','rto%','Totavg']
    return df[[c for c in keep if c in df.columns]]

def load_sql(db_path, table, query):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)

def parse_time(df, fmt):
    if 'Time' in df.columns:
        df['Time'] = pd.to_datetime(df['Time'], format=fmt, errors="coerce")
        df.sort_values(by='Time', inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df

def plot_charts(df, label, chart_specs):
    for col, color, title in chart_specs:
        if col in df.columns:
            chart = (
                alt.Chart(df)
                .mark_line(point=True)
                .encode(x="Time:T", y=f"{col}:Q", color=alt.value(color))
                .properties(width=500, height=200, title=f"{label} - {title}")
            )
            st.altair_chart(chart, width="stretch")

# -----------------------------
# Load Index Tables
# -----------------------------
idx_tables = ["50","BANK","IT","PHARMA","METAL","OIL_GAS","TOTAL_MARKET"]
idx_path = os.path.join(BASE_DIR_db, 'allindices.db')

dfs = {tab: load_sql(idx_path, tab, f"SELECT * FROM '{tab}' WHERE Date='{TODAY}' ORDER BY Time DESC") for tab in idx_tables}
index_dataframes = {name: valuechange(dfs[tab]) for name, tab in zip(
    ["NIFTY 50","BANK","IT","PHARMA","METAL","OIL & GAS","TOTAL MARKET"], idx_tables)}

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
db_path = os.path.join(BASE_DIR_db, "allturnover.db")

results = {t: diffprocess(load_sql(db_path, t, f"SELECT * FROM '{t}' WHERE Date='{TODAY}' ORDER BY Time DESC"))[cols]
           for t, cols in tables.items()}
turnover_dataframes = {"CM": results['cm_total'], "FNO": results['fno_total'], "GT": results['grand_total']}

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Indices & Turnover Dashboard", layout="wide")
st.title("📊 Indices & Turnover Change Dashboard")

# Sidebar selectors
selected_index = st.sidebar.selectbox("Select an Indices:", list(index_dataframes.keys()))
selected_turnover = st.sidebar.selectbox("Select Turnover Table:", list(turnover_dataframes.keys()))

# Shared chart specs for both index and turnover
COMMON_CHART_SPECS = [
    ("Valchg", "blue", "Valchg (cr)"),
    ("Volchg", "green", "Volchg (lac)"),
    ("pchg", "orange", "% Change"),   # will be skipped if not present
    ("Chgavg", "purple", "Change Avg"),
#    ("Totavg", "orange", "Total Avg"),
    ("Adv", "green", "Advance"),
    ("Dec", "red", "Decline"),
]

# -----------------------------
# Index Section
# -----------------------------
st.subheader(f"{selected_index} Data every 2 min")
#st.dataframe(index_dataframes[selected_index].head(50))

# Parse time with hh:mm:ss for index tables
plot_df = parse_time(index_dataframes[selected_index].copy(), "%H:%M:%S")

# Plot charts for index
plot_charts(plot_df, selected_index, COMMON_CHART_SPECS)

# -----------------------------
# Turnover Section
# -----------------------------
st.subheader(f"{selected_turnover} Turnover Data every 2 min")
#st.dataframe(turnover_dataframes[selected_turnover].head(50))

# Parse time with hh:mm for turnover tables
plot_turnover_df = parse_time(turnover_dataframes[selected_turnover].copy(), "%H:%M")

# Plot charts for turnover
plot_charts(plot_turnover_df, selected_turnover, COMMON_CHART_SPECS)
st.subheader(f"{selected_index} Data Table")
st.dataframe(index_dataframes[selected_index])
st.subheader(f"{selected_turnover} Turnover Data Table")
st.dataframe(turnover_dataframes[selected_turnover])

