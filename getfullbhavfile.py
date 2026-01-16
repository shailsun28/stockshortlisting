import pandas as pd
import sqlite3
from jugaad_data.nse import full_bhavcopy_save
from datetime import date, timedelta, datetime
import os
import warnings
import time

warnings.filterwarnings("ignore")

# Database path
db_path = "/Users/shail/Documents/Trading/market-turnover/db/fullbhavcopy.db"

# Download folder
download_folder = "/Users/shail/Documents/Trading/bhavtest"
os.makedirs(download_folder, exist_ok=True)

today = date.today()
start_date = today
#start_date = today - timedelta(days=3)
end_date = today
#end_date = today - timedelta(days=1)

# Get max date from the database
def get_max_date_in_db():
    conn = sqlite3.connect(db_path)
    try:
        query = "SELECT MAX(DATE) AS max_date FROM nsestock_t"
        result = pd.read_sql_query(query, conn)
        max_date = result.iloc[0, 0]
        return pd.to_datetime(max_date).date() if max_date else None
    except Exception as e:
        print(f"Error querying max date from database: {e}")
        return None
    finally:
        conn.close()

# Function to download, process, and save data for a specific date
def process_date(current_date):
    conn = None
    try:
        # Download the Bhavcopy
        file_path = full_bhavcopy_save(current_date, download_folder)
        # Load the CSV into a pandas DataFrame
        eqdf = pd.read_csv(file_path)
        # Clean and process the DataFrame
        eqdf.rename(columns=lambda x: x.strip(), inplace=True)
        eqdf.rename(columns={'DATE1': 'DATE'}, inplace=True)
        eqdf = eqdf[eqdf['SERIES'] == ' EQ']
        # Format the DATE column
        eqdf['DATE'] = eqdf['DATE'].str.strip()
        eqdf['DATE'] = pd.to_datetime(eqdf['DATE'], format='%d-%b-%Y').dt.date
        eqdf.sort_values(by=['DATE'], ascending=False, inplace=True)
        print(f"eqdf shape {eqdf.shape}")
        
        # Connect to the database and read the existing data
        conn = sqlite3.connect(db_path)
        existing_data = pd.read_sql_query("SELECT * FROM nsestock_t", conn)
        
        # Concatenate the new data at the top
        updated_data = pd.concat([eqdf, existing_data], ignore_index=True)
        
        # Replace the existing table with the updated data
        updated_data.to_sql('nsestock_t', conn, if_exists='replace', index=False)
        print(f"Data for {current_date} added to the top of the database successfully.")
    except Exception as e:
        print(f"Error processing data for {current_date}: {e}")
    finally:
        if conn is not None:
            conn.close()

# Main logic for iterating through the date range
max_date_in_db = get_max_date_in_db()
print(f"Max date in database: {max_date_in_db}")

current_date = start_date
while current_date <= end_date:
    if max_date_in_db and current_date <= max_date_in_db:
        print(f"Data for {current_date} is already in the database. Skipping...")
    else:
        print(f"Processing data for {current_date}...")
        process_date(current_date)
    current_date += timedelta(days=1)

print("************* Completed *****************")
print("The task completed at ", datetime.now())
