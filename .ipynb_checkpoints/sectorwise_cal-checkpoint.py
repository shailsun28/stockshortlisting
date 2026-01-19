import pandas as pd
import numpy as np # Needed for np.nan in valuechange function
import json
from datetime import datetime
import sqlite3
import os # To ensure the path exists

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

def valuechange(df):
    """
    Processes the input DataFrame to calculate various metrics.
    """
    subset = df.copy()
    
    subset.rename(columns={
        'declines': 'Dec', 'advances': 'Adv',
        'unchanged': 'Unchg', 'dayHigh': 'High', 'dayLow': 'Low', 'lastPrice': 'LTP', 'pChange': 'chg%',
        'change': 'chg', 'totalTradedVolume': 'Tvol',
        'totalTradedValue': 'Tval'}, inplace = True)
    
    # Ensure numeric columns are correctly converted before math operations
    # Assuming 'Tval' and 'Tvol' are the primary columns that need this based on original code comments
    numeric_cols_to_convert = ['Tval', 'Tvol', 'ffmc'] 
    for col in numeric_cols_to_convert:
        if col in subset.columns:
            subset[col] = pd.to_numeric(subset[col], errors='coerce').fillna(0)

    # Apply initial scaling and handle NaNs
    if 'ffmc' in subset.columns:
        subset['ffmc'] = round(subset['ffmc'] / 10000000, 3)
    
    subset.fillna(0, inplace=True)
    
    # Calculate differences and percentages
    # Use np.nan instead of 0 in replace() to correctly handle division by zero behavior
    subset['Valchg'] = round(subset['Tval'].diff(-1) / 10000000, 2)
    subset['Volchg'] = round(subset['Tvol'].diff(-1) / 100000, 2)
    subset['Tavg'] = round(subset['Valchg'] * 100 / subset['Volchg'].replace(0, np.nan), 2)
    subset['Tavgchg%'] = round(subset['Tavg'].diff(-1) * 100 / subset['Tavg'].shift(-1).replace(0, np.nan), 2)
    
    # Handle potential division by zero
    subset['Valchg%'] = round(subset['Tval'].diff(-1) * 100 / subset['Tval'].shift(-1).replace(0, np.nan), 2)
    subset['Volchg%'] = round(subset['Tvol'].diff(-1) * 100 / subset['Tvol'].shift(-1).replace(0, np.nan), 2)

    subset.fillna(0, inplace=True) # Fill NaNs created by diff/division
    
    # Calculate variance percentage
    subset['Var%'] = round(subset['Valchg%'] - subset['Volchg%'], 2)
    subset['rto%'] = round(subset['Valchg%']/subset['Volchg%'].replace(0, np.nan),2)
    subset['Totavg'] = round(subset['Tval']/subset['Tvol'].replace(0, np.nan),2)
    
    subset['Tval'] = round(subset['Tval'], 3) # Already scaled earlier

    # Define final columns required
    newcol = ['symbol', 'Date', 'Time', 'High', 'Low', 'LTP', 'chg', 'chg%', 
       'Adv', 'Dec', 'Unchg','Tvol', 'Tval', 'Valchg',
       'Volchg', 'Tavg', 'Valchg%', 'Volchg%', 'Var%', 'rto%','ffmc',
       'Totavg']
    
    # Filter to only required columns, handling potential missing columns safely
    subset = subset[[col for col in newcol if col in subset.columns]]

    return subset.fillna(0) # Final fill of any remaining NaNs

# --- Main Script ---

tables = [
    "50", "BANK", "AUTO", "FINANCIAL_SERVICES", 
    "FMCG", "IT", "MEDIA", "METAL", "PHARMA",
    "PSU_BANK", "PRIVATE_BANK", "REALTY", "HEALTHCARE_INDEX",
    "CONSUMER_DURABLES", "OIL_GAS", "MIDSMALL_HEALTHCARE", "TOTAL_MARKET"
]

idx_path = os.path.join(BASE_DIR_db, "allindices.db")
cal_path = os.path.join(BASE_DIR_db, "sector_calulated.db")

# 1. Read raw data into dictionary of DataFrames
dfs = {}
with sqlite3.connect(idx_path) as gconn:
    for tab in tables:
        # Use try-except in case a table doesn't exist
        try:
            query = f"SELECT * FROM '{tab}' ORDER BY Date DESC, Time DESC"
            dfs[tab] = pd.read_sql_query(query, gconn)
            print(f"Loaded raw data for table: {tab}")
        except pd.io.sql.DatabaseError as e:
            print(f"Error loading table {tab}: {e}")

# 2. Process data using the valuechange function
# We can automate this processing using a dictionary comprehension for all tables
calculated_dfs = {}
for tab_name, df in dfs.items():
    if not df.empty:
        # The valuechange function expects 'symbol' column which the index data frames might not have
        # Adding a placeholder symbol if missing based on the table name
        if 'symbol' not in df.columns:
             df['symbol'] = tab_name 
        calculated_dfs[tab_name] = valuechange(df)
        print(f"Processed data for {tab_name}")

# 3. Save the calculated DataFrames to the new database file
# Ensure the directory for cal_path exists if necessary
os.makedirs(os.path.dirname(cal_path), exist_ok=True)

with sqlite3.connect(cal_path) as cconn:
    for table_name, df_to_save in calculated_dfs.items():
        df_to_save.to_sql(table_name, cconn, if_exists='replace', index=False)
        print(f"Saved calculated data to new DB in table: {table_name}")

print(f"\nAll calculated data saved successfully to {cal_path}")