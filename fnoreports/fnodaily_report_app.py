import os
import sqlite3
import pandas as pd
import streamlit as st
import altair as alt
import numpy as np
from datetime import date, timedelta

# -----------------------------
# Config
# -----------------------------
BASE_DIR_db = "/home/shail/db"
spurdb = os.path.join(BASE_DIR_db, "fuopspur.db")
TODAY = date.today()

banknifty = [
    "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
    "FEDERALBNK", "CANBK", "BANKBARODA", "UNIONBANK", "PNB",
    "IDFCFIRSTB", "AUBANK", "INDUSINDBK", "YESBANK"
]

reqcol = [
    "symbol","Date","Time","latestOI","volume",
    "futValue","optValue","total","premValue","underlyingValue"
]

changecol = [
    "latestOI","volume","futValue","optValue",
    "total","premValue","underlyingValue"
]

# -----------------------------
# Utility Functions
# -----------------------------
def safe_numeric(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def add_changes(df, cols):
    df = safe_numeric(df.copy(), cols)
    for col in cols:
        df[f"{col}_chg"] = df[col].diff(-1).round(2)
        df[f"{col}_chg%"] = (df[col].diff(-1) * 100 / df[col].shift(-1).replace(0, np.nan)).round(2)
    df.fillna(0, inplace=True)
    return df

def parse_datetime(df):
    df = df.copy()
    # Parse Date and Time separately
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    df["Time"] = pd.to_datetime(df["Time"], format="%H:%M", errors="coerce").dt.time

    # Combine into one datetime column
    df["DateTime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str),
                                    errors="coerce")

    # Sort by DateTime descending
    df.sort_values(by="DateTime", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def plot_charts_old(df, label, cols):
    for col in cols:
        if col in df.columns:
            chart = (
                alt.Chart(df)
                .mark_line(point=True)
                .encode(x="DateTime:T", y=f"{col}:Q", color=alt.value("blue"))
                .properties(width=500, height=200, title=f"{label} - {col}")
            )
            st.altair_chart(chart, use_container_width=True)

def plot_charts(df, label, cols):
    if "DateTime" not in df.columns or df["DateTime"].isna().all():
        return

    for col in cols:
        if col in df.columns:
            chart = (
                alt.Chart(df)
                .mark_line(point=True)
                .encode(
                    x="DateTime:T",
                    y=f"{col}:Q",
                    color=alt.value("blue")
                )
                .properties(width=500, height=200, title=f"{label} - {col}")
                #.facet(row="Date")   # separate panel for each Date
                .facet(column="Date")

            )
            st.altair_chart(chart, use_container_width=True)


# -----------------------------
# Load Data
# -----------------------------
placeholders = ",".join(["?"] * len(banknifty))
query_spur = f"""
    SELECT {",".join(reqcol)}
    FROM spur
    WHERE symbol IN ({placeholders})
    ORDER BY Date DESC, Time DESC
"""

with sqlite3.connect(spurdb) as conn:
    spurdf = pd.read_sql_query(query_spur, conn, params=banknifty)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="BankNifty Dashboard", layout="wide")
st.title("📊 BankNifty Change Dashboard")

# Sidebar selectors
selected_symbol = st.sidebar.selectbox("Select BankNifty Symbol:", banknifty)
days_back = st.sidebar.slider("Number of days to display:", min_value=1, max_value=60, value=7)

# Filter for selected symbol
sym_df = spurdf[spurdf["symbol"] == selected_symbol].copy()
sym_df = add_changes(sym_df, changecol)
sym_df = parse_datetime(sym_df)

# Apply date filter
start_date = TODAY - timedelta(days=days_back)
sym_df = sym_df[sym_df["Date"] >= pd.to_datetime(start_date)]

st.subheader(f"{selected_symbol} DataFrame (Last {days_back} days)")
st.dataframe(sym_df)

# Plot charts for each numeric column and its change
for col in changecol:
    plot_charts(sym_df, selected_symbol, [col, f"{col}_chg", f"{col}_chg%"])
