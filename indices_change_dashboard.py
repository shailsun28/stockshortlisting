import pandas as pd
import streamlit as st
import sqlite3
from datetime import date
import altair as alt
import numpy as np
import os
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Refresh every 60 seconds (60000 ms)
#st_autorefresh(interval=60000, key="refresh")
# Refresh every 60 seconds (60000 ms)
#st_autorefresh = st.experimental_autorefresh(interval=60000, limit=None, key="refresh")

# Refresh every 60 seconds (60000 ms)
st_autorefresh = st_autorefresh(interval=60000, limit=None, key="refresh")

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
        # Current row - next row
        df['Valchg'] = (df['Tval'] - df['Tval'].shift(-1)).round(2)
        df['Valchg%'] = ((df['Tval'] - df['Tval'].shift(-1)) * 100 / df['Tval'].shift(-1).replace(0, np.nan)).round(2)

    if 'Tvol' in df.columns:
        df['Volchg'] = (df['Tvol'] - df['Tvol'].shift(-1)).round(2)
        df['Volchg%'] = ((df['Tvol'] - df['Tvol'].shift(-1)) * 100 / df['Tvol'].shift(-1).replace(0, np.nan)).round(2)

    if {'Valchg','Volchg'}.issubset(df.columns):
        df['Chgavg'] = (df['Valchg'] * 100 / df['Volchg']).round(2)
        df['Tavgchg%'] = ((df['Chgavg'] - df['Chgavg'].shift(-1)) * 100 / df['Chgavg'].shift(-1).replace(0, np.nan)).round(2)

    if 'noOfOrders' in df.columns:
        df['Orderchg_lac'] = ((df['noOfOrders'] - df['noOfOrders'].shift(-1)) / 100000).round(3)
        df['Orderchg%'] = ((df['noOfOrders'] - df['noOfOrders'].shift(-1)) * 100 / df['noOfOrders'].shift(-1).replace(0, np.nan)).round(2)

    if 'noOfTrades' in df.columns:
        df['Trdnochg'] = (df['noOfTrades'] - df['noOfTrades'].shift(-1)).round(2)
        df['Trdnochg%'] = ((df['noOfTrades'] - df['noOfTrades'].shift(-1)) * 100 / df['noOfTrades'].shift(-1).replace(0, np.nan)).round(2)

    if {'Valchg%','Volchg%'}.issubset(df.columns):
        df['Var%'] = (df['Valchg%'] - df['Volchg%']).round(2)

    if {'Tval','Tvol'}.issubset(df.columns):
        df['Totavg'] = (df['Tval'] * 100 / df['Tvol']).round(2)

    # Forward fill for continuity (optional)
    df = df.fillna(method="ffill")
    return df

def valuechange(df):
    df = df.copy()
    df.rename(columns={
        'declines': 'Dec',
        'advances': 'Adv',
        'unchanged': 'Unchg',
        'dayHigh': 'High',
        'dayLow': 'Low',
        'lastPrice': 'LTP',
        'pChange': 'pchg',
        'change': 'chg',
        'totalTradedVolume': 'Tvol',
        'totalTradedValue': 'Tval'
    }, inplace=True)

    # Convert numeric columns
    df = safe_numeric(df, ['Tval', 'Tvol', 'High', 'Low', 'LTP', 'chg', 'pchg', 'Adv', 'Dec', 'Unchg'])

    # Scale totals: Tval in crores (1e7), Tvol in lakhs (1e5)
    df['ffmc'] = (df.get('ffmc', 0) / 1e7).round(3)
    df['Tval'] = (df['Tval'] / 1e7).round(3)   # crores
    df['Tvol'] = (df['Tvol'] / 1e5).round(3)   # lakhs
    #df['Tval'] = (df['Tval'] / 1e).round(3)   # crores
    #df['Tvol'] = (df['Tvol'] / 1e5).round(3)   # lakhs

    # Changes (current row - next row, so last row is NaN)
    df['Valchg'] = (df['Tval'] - df['Tval'].shift(-1)).round(3)
    df['Volchg'] = (df['Tvol'] - df['Tvol'].shift(-1)).round(3)

    # Percent changes (relative to next row, so last row is NaN)
    df['Valchg%'] = ((df['Tval'] - df['Tval'].shift(-1)) * 100 / df['Tval'].shift(-1)).round(3)
    df['Volchg%'] = ((df['Tvol'] - df['Tvol'].shift(-1)) * 100 / df['Tvol'].shift(-1)).round(3)

    # Other derived metrics
    if 'Valchg' in df.columns and 'Volchg' in df.columns:
        df['Chgavg'] = (df['Valchg'] * 100 / df['Volchg']).round(3)
        df['Tavgchg%'] = ((df['Chgavg'] - df['Chgavg'].shift(-1)) * 100 / df['Chgavg'].shift(-1)).round(3)

    df['Var%'] = (df['Valchg%'] - df['Volchg%']).round(3)
    df['rto%'] = (df['Valchg%'] / df['Volchg%']).round(3)
    df['Totavg'] = (df['Tval'] / df['Tvol']).round(3)

    # Leave NaNs as-is so charts skip them (avoids misleading zeros)

    keep = [
        'symbol','Date','Time','pchg','Valchg','Volchg','Valchg%','Volchg%',
        'Var%','High','Low','LTP','chg','Adv','Dec','Unchg',
        'Tvol','Tval','Chgavg','rto%','Totavg'
    ]
    return df[[c for c in keep if c in df.columns]]
    
def load_sql(db_path, table, query):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)

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

# -----------------------------
# Chart Helpers
# -----------------------------
def plot_column_last_n_days(df, column, label, color="blue", fmt="%H:%M:%S", n=1):    
    if "Date" not in df.columns or column not in df.columns:
        return
    for d in sorted(df["Date"].unique())[-n:]:
        day_df = df[df["Date"] == d].copy()
        day_df = parse_time(day_df, fmt)

        # Convert to numeric just in case
        day_df[column] = pd.to_numeric(day_df[column], errors="coerce")

        # Ignore extreme negatives: keep only values above a threshold
        # e.g. drop anything below the 1st percentile
        q_low = day_df[column].quantile(0.01)
        day_df = day_df[day_df[column] >= q_low]

        st.markdown(f"#### {label} - {column} ({d})")
        chart = (
            alt.Chart(day_df)
            .mark_line(point=True)
            .encode(
                x="DateTime:T",
                y=alt.Y(f"{column}:Q", scale=alt.Scale()),  # let Altair autoscale
                color=alt.value(color),
                tooltip=[
                    alt.Tooltip(f"{column}:Q", title="Value"),
                    alt.Tooltip("DateTime:T", title="Time", format="%H:%M:%S")
                    #alt.Tooltip("Time:T", title="Time")   # show only time
                    ]
            )
            .properties(width=800, height=200)
        )
        st.altair_chart(chart, use_container_width=True)

def plot_adv_dec(df, label):
    if {"Adv","Dec"}.issubset(df.columns):
        base = alt.Chart(df).encode(x="DateTime:T")
        adv_line = base.mark_line(color="green").encode(y="Adv:Q")
        dec_line = base.mark_line(color="red").encode(y="Dec:Q")
        chart = alt.layer(adv_line, dec_line).properties(
            width=800, height=200, title=f"{label} - Advance vs Decline"
        )
        st.altair_chart(chart, use_container_width=True)
def plot_adv_dec_last_n_days(df, label, fmt="%H:%M:%S", n=1):
    if {"Adv","Dec"}.issubset(df.columns):
        for d in sorted(df["Date"].unique())[-n:]:
            day_df = df[df["Date"] == d].copy()
            day_df = parse_time(day_df, fmt)
            day_df["Adv"] = pd.to_numeric(day_df["Adv"], errors="coerce")
            day_df["Dec"] = pd.to_numeric(day_df["Dec"], errors="coerce")

            st.markdown(f"#### {label} - Advance vs Decline ({d})")
            plot_adv_dec(day_df, label)


# Sidebar selectors slidebar
num_days = st.sidebar.slider("Number of days to show", min_value=1, max_value=7, value=1)

# -----------------------------
# Load Index Tables
# -----------------------------
idx_tables = ["50","BANK","IT","PHARMA","METAL","OIL_GAS","TOTAL_MARKET"]
idx_path = os.path.join(BASE_DIR_db, 'allindices.db')

dfs = {
    tab: parse_time(
        load_sql(
            idx_path,
            tab,
            f"""
            SELECT *
            FROM '{tab}'
            WHERE Date IN (
                SELECT DISTINCT Date FROM '{tab}' ORDER BY Date DESC LIMIT {num_days}
            )
            ORDER BY Date DESC
            """),
        "%H:%M:%S"
    )
    for tab in idx_tables
}

index_dataframes = {
    name: valuechange(dfs[tab])
    for name, tab in zip(["NIFTY 50","BANK","IT","PHARMA","METAL","OIL & GAS","TOTAL MARKET"], idx_tables)
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

db_path = os.path.join(BASE_DIR_db, "allturnover.db")

results = {
    t: diffprocess(
        parse_time(
            load_sql(
                db_path,
                t,
                f"""
                SELECT *
                FROM '{t}'
                WHERE Date IN (
                    SELECT DISTINCT Date FROM '{t}' ORDER BY Date DESC LIMIT {num_days}
                )
                ORDER BY Date DESC
                """),
            "%H:%M"
        )
    )[cols]
    for t, cols in tables.items()
}

turnover_dataframes = {"CM": results['cm_total'], "FNO": results['fno_total'], "GT": results['grand_total']}

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Indices & Turnover Dashboard", layout="wide")
st.title("📊 Indices & Turnover Change Dashboard")
if st.button("🔄 Refresh now"):
    st.rerun()
    #st.experimental_rerun()
    #st.experimental_set_query_params(updated=str(time.time()))

# Sidebar selectors
#selected_index = st.sidebar.selectbox("Select an Index:", list(index_dataframes.keys()))
selected_index = st.sidebar.selectbox( "Select an Index:", list(index_dataframes.keys()), index=list(index_dataframes.keys()).index("BANK") )
selected_turnover = st.sidebar.selectbox("Select Turnover Table:", list(turnover_dataframes.keys()))

# Shared chart specs for both index and turnover
COMMON_CHART_SPECS = [
    ("Valchg", "blue", "Valchg (cr)"),
    ("Volchg", "green", "Volchg (lac)"),
    ("pchg", "orange", "% Change"),   # will be skipped if not present
    ("Chgavg", "purple", "Change Avg"),
    ("Var%", "yellow", "Varation Val-Vol %"),
#    ("Dec", "red", "Decline"),
]

# -----------------------------
# Index Section
# -----------------------------
st.subheader(f"{selected_index} Val(cr) & Vol(lac) change data for {num_days} days (every min) ")
for col, color, title in COMMON_CHART_SPECS:
    #st.markdown(f"### {selected_index} - {title}")
    plot_column_last_n_days(
        index_dataframes[selected_index].copy(),
        column=col,
        label=selected_index,
        color=color,
        fmt="%H:%M:%S",
        n=num_days
    )
# Adv/Dec combined
plot_adv_dec_last_n_days(index_dataframes[selected_index].copy(), selected_index, fmt="%H:%M:%S", n=num_days)
# Ensure default is Bank


# -----------------------------
# Turnover Section
# -----------------------------
st.subheader(f"{selected_turnover} Val(cr) & Vol(lac) change data for {num_days} days (every 2 min) ")
for col, color, title in COMMON_CHART_SPECS:
    #st.markdown(f"### {selected_turnover} - {title}")
    plot_column_last_n_days(
        turnover_dataframes[selected_turnover].copy(),
        column=col,
        label=selected_turnover,
        color=color,
        fmt="%H:%M",
        n=num_days
    )
plot_adv_dec_last_n_days(turnover_dataframes[selected_turnover].copy(), selected_turnover, fmt="%H:%M", n=num_days)

# -----------------------------
# Data Tables
# -----------------------------
st.subheader(f"{selected_index} Data Table")
st.dataframe(index_dataframes[selected_index])

st.subheader(f"{selected_turnover} Turnover Data Table")
st.dataframe(turnover_dataframes[selected_turnover])


