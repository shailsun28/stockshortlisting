##https://nsearchives.nseindia.com/content/fo/fii_stats_08-Jan-2026.xls
import numpy as np
import requests
import pandas as pd
from datetime import date, timedelta, datetime
import sqlite3
import os

#This code is to download fii stats xls file and save it to fiistats db.
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

current_date = datetime.now()
print ("The script started at ", current_date)
#current_date = current_date - timedelta(2)
 # Format the date as 'ddmmyyyy'
#formatted_date = current_date.strftime('%d%m%Y')
formatted_date = current_date.strftime('%d-%b-%Y')
formatted_date = '16012026'
#url = f'https://nsearchives.nseindia.com/content/CM_52_wk_High_low_{formatted_date}.csv'
url = f'https://nsearchives.nseindia.com/content/fo/fii_stats_{formatted_date}.xls'
print ("The url is ", url)
# Function to download the file
def download_file(url):
    #main_url = 'https://www.nseindia.com'
    main_url = 'https://www.nseindia.com/all-reports'
        # Define header to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.124 Safari/537.36',
        'Referer': main_url
    }
    # Create a session
    session = requests.Session()
    try:
        # Send a GET request to the main NSE India website to get the cookies
        session.get(main_url, headers=headers)

        # Send a GET request to the API endpoint with the session cookies and header
        response = session.get(url, headers=headers)
        #response = requests.get(url)
      # Check if the request was successful
        #if response.status_code == 200:
        # Define the file path
        #file_path = f'/Users/shail/Documents/Trading/52weekhl/CM_52_wk_High_low_{datetime.now().strftime("%d%m%Y")}.csv'
        file_path = os.path.join(BASE_DIR, f"fii_stats_{formatted_date}.xls")
        print (file_path)
        # Write the content to a file
        with open(file_path, 'wb') as file:
            file.write(response.content)
            print(f"File downloaded successfully: {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}' "stockname:", url)
        return None

# Generate the URL with the current date
#url = generate_date_url()
# Download the file#
file_path = download_file(url)


#now = datetime.now()

# Ensure you run this in your terminal if you haven't already: pip install xlrd openpyxl

def read_fii_excel_clean_table_final(file_path):
    """
    Reads the specific FII statistics Excel file, skips the first row, 
    cleans headers, filters notes section, and adds a date column.
    """
    
    # --- Step 1: Reading Excel file with corrected header syntax ---
    # skiprows=1 ignores the very first row of the Excel sheet. 
    # header= reads the next two rows (rows 2 and 3) as our MultiIndex headers.
    df = pd.read_excel(
        file_path, 
        skiprows=1,      
        header=[0,1],    
        engine='xlrd'  
    )
    
    # --- Step 2: Force rename the first column label immediately ---
    # This is the key fix for the KeyError. We guarantee the first column is named 'Product' 
    # while it is still a MultiIndex structure.
    current_cols = df.columns.tolist()
    # The first element in current_cols is the tuple for the first column. We replace it.
    current_cols[0] = 'Product' 
    df.columns = pd.Index(current_cols) # Reassign as a standard Index now

    # --- Step 3: Filtering out Notes section and empty rows ---
    
    # Now we can reliably use 'Product' for filtering
    #print (df.head(3).T)


    # Filter out rows containing the string 'Notes:' in the 'Product' column
    #df = df[~df['Product'].astype(str).str.contains('Notes:', na=False)]
    
    # --- Step 4: Flattening the remaining headers ---
    # The remaining columns still have the multi-index tuples. We flatten them manually now.
    
    new_column_names_mapping = {
        ('Unnamed: 0_level_0', 'Unnamed: 0_level_1'): 'FuIndex',
        ('BUY', 'No. of contracts'): 'Buy_Contracts',
        ('BUY', 'Amt in Crores'): 'Buy_Amt_Cr',
        ('SELL', 'No. of contracts'): 'Sell_Contracts',
        ('SELL', 'Amt in Crores'): 'Sell_Amt_Cr',
        ('OPEN INTEREST AT THE END OF THE DAY', 'No. of contracts'): 'OI_Contracts',
        ('OPEN INTEREST AT THE END OF THE DAY', 'Amt in Crores'): 'OI_Amt_Cr'
    }
    
    # Rename only the remaining multi-index columns
    df.rename(columns=new_column_names_mapping, inplace=True)
     # Drop rows where the 'Product' column is entirely empty (NaN)
    df.dropna(subset=['Buy_Amt_Cr'], how='all', inplace=True)
    # --- Step 5: Add 'Date' Column and Set Index ---
    
    # Using the current date of execution (January 8, 2026)
    #df['Date'] = date(2026, 1, 8) 
    df['Date'] = formatted_date 
    
    # Set 'Product' as the index for a clean table view
    #df.set_index('Product', inplace=True)
    
    return df

# Example Usage:
file_location = file_path 

# This line should now run successfully without the KeyError
df_final_table = read_fii_excel_clean_table_final(file_location) 
reorder_col = ['Date','Product', 'Buy_Contracts', 'Buy_Amt_Cr', 'Sell_Contracts',
       'Sell_Amt_Cr', 'OI_Contracts', 'OI_Amt_Cr']
downdf = df_final_table[reorder_col]

# Saving to Database.
#db_path = "/Users/shail/Documents/Trading/market-turnover/db/fiistats.db"
db_path = os.path.join(BASE_DIR_db, "fiistats.db")
conn = sqlite3.connect(db_path)
        #final_df.to_sql('fno_growth', conn, if_exists='replace', index=False)
downdf.to_sql('fii', conn, if_exists='append', index=False)
conn.close()
print ("The script Completed successfully at ", datetime.now())
#