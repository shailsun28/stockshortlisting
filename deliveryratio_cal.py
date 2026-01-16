import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

# --- Configuration and Setup ---
starttime = datetime.now()
print(f"The Task start at {starttime} Please wait .......")
today = date.today()
today = today - timedelta(2)
# Define database paths
DB_PATH = "/Users/shail/Documents/Trading/market-turnover/db/fullbhavcopy.db"
TA_DB_PATH = "/Users/shail/Documents/Trading/market-turnover/db/deliveryavg.db"

# Define the file containing stock symbols
INPUT_FILE = '/Users/shail/Documents/Trading/NiftyStocks/niftyallmarket_symbol'
print(f'Select file to update db: {INPUT_FILE}')

# Define calculation parameters
ROLLING_WINDOW = 10
LOOKBACK_LIMIT = 253 # Sufficient to cover the rolling window + 1 day for calculations

# --- Data Loading ---

# 1. Load all stock symbols from the input file
with open(INPUT_FILE, "r") as f:
    stocks = [line.strip() for line in f.readlines() if line.strip()]

# 2. Connect to the main database and load data for all relevant stocks
# This single query is much faster than looping through symbols with individual queries
conn = sqlite3.connect(DB_PATH)
# Use a SQL IN clause to fetch data for all symbols in one go
query = f"SELECT * FROM nsestock_t WHERE SYMBOL IN ({','.join(['?']*len(stocks))}) ORDER BY Date DESC"
full_df = pd.read_sql_query(query, conn, params=stocks)
conn.close()



# --- Data Processing and Optimization ---

# Standardize column names using a single rename operation
rename_map = {
    'TURNOVER_LACS': 'Val_CR',
    'TTL_TRD_QNTY': 'Vol',
    'HIGH_PRICE': 'HiPr',
    'LAST_PRICE': 'LTP',
    'AVG_PRICE': 'AvgPr',
    'DELIV_QTY': 'DELIV_QTY',
    'CLOSE_PRICE': 'ClPr',
    'PREV_CLOSE': 'PvPr',
    'LOW_PRICE': 'LoPr',
    'SYMBOL': 'Stock',
    'DATE': 'Date'
}
full_df.rename(columns=rename_map, inplace=True)

# Pre-process data types once for the entire DataFrame
full_df['DELIV_QTY'] = full_df['DELIV_QTY'].astype(float)
full_df['Val_CR'] = round(full_df['Val_CR'] / 100, 3)
# Ensure Date column is a proper datetime object (useful if not already)
#full_df['Date'] = pd.to_datetime(full_df['Date'])
# Use highly efficient pandas groupby and rolling operations for calculations
# These operations are vectorized and applied per stock group
def calculate_technicals(group):
    # Ensure the group is sorted by date for correct rolling/shifting
    group = group.sort_values(by='Date', ascending=False)
    
    # Apply rolling mean and shift
    # shift(N) moves the window forward N days, so today's row gets the average of the *next* N days
    group[f'DlyAvg_{ROLLING_WINDOW}'] = round(
        group['DELIV_QTY'].rolling(window=ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean().shift(-(ROLLING_WINDOW)), 1
    )
    group[f'VolAvg_{ROLLING_WINDOW}'] = round(
        group['Vol'].rolling(window=ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean().shift(-(ROLLING_WINDOW)), 1
    )
    # Calculate ratio, using .div() for clarity and speed
    group[f'DlyRto_{ROLLING_WINDOW}'] = round(group['DELIV_QTY'].div(group[f'DlyAvg_{ROLLING_WINDOW}']), 1)
    
    # Calculate price change %
    group['Pr_chg_%'] = round((group['ClPr'] - group['PvPr']) * 100 / group['PvPr'], 2)
    
    # Only keep the last N rows needed if we fetched more initially
    return group.head(LOOKBACK_LIMIT)

# Apply the function to each stock group
#processed_df = full_df.groupby('Stock').apply(calculate_technicals).reset_index(drop=True)
processed_df = full_df.groupby('Stock').apply(calculate_technicals, include_groups=False).reset_index()

# 1. Drop unnecessary columns (including the index level if created by apply)
processed_df = processed_df.drop(columns=['SERIES', 'level_1'], errors='ignore')
reorder_col = ['Stock','Date', 'DlyRto_10', 'Pr_chg_%', 'HiPr', 'LTP', 'AvgPr', 'Vol', 'Val_CR', 'PvPr', 'OPEN_PRICE', 'LoPr',
       'ClPr', 'NO_OF_TRADES', 'DELIV_QTY',
       'DELIV_PER', 'VolAvg_10' ,'DlyAvg_10']
processed_df = processed_df[reorder_col]
# --- Data Export ---

ta_conn = sqlite3.connect(TA_DB_PATH, timeout=10.0)
# 'if_exists="replace"' drops the existing table and creates a new one
todaydate_df = processed_df[processed_df['Date'] == str(today)]
todaydate_df.to_sql('sma_vol', ta_conn, if_exists='append', index=False)
#Below is to get save whole df after calculation delivery ration and volavg.
#processed_df.to_sql('sma_vol', ta_conn, if_exists='replace', index=False)
ta_conn.close()

# --- Summary ---
endtime = datetime.now()
print(f"The total time taken is {endtime - starttime} and completed at {endtime}")
print(f"The output is stored at {TA_DB_PATH} and total rows are {processed_df.shape[0]}")