#Getting  Daily Index and sectors snapshot for multiple dates or ranges
import requests
import pandas as pd
import sqlite3
import io
from datetime import date, timedelta, datetime
import os

starttime = datetime.now()
print("\2\n"+ " ******************  Script run started  at ...   ", starttime)
BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

idx_path =  os.path.join(BASE_DIR_db, "idx_snapshot.db")
conn = sqlite3.connect(idx_path)

# List of indices
indices = [
    "NIFTY 50", "NIFTY BANK", "NIFTY AUTO", "NIFTY FINANCIAL SERVICES", "NIFTY FINANCIAL SERVICES 25/50",
    "NIFTY FMCG", "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
    "NIFTY PSU BANK", "NIFTY PRIVATE BANK", "NIFTY REALTY", "NIFTY HEALTHCARE INDEX",
    "NIFTY CONSUMER DURABLES", "NIFTY OIL & GAS", "NIFTY MIDSMALL HEALTHCARE",
    "NIFTY FINANCIAL SERVICES EX-BANK", "NIFTY MIDSMALL FINANCIAL SERVICES", "NIFTY MIDSMALL IT & TELECOM"
]

def getIndexfile(date):
    formatted_date = date.strftime('%d%m%Y')
    url = f'https://nsearchives.nseindia.com/content/indices/ind_close_all_{formatted_date}.csv'
    main_url = 'https://www.nseindia.com/all-reports'   

    # Define headers to mimic a browser request
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36',
        'Referer': main_url
    }   

    # Create a session
    session = requests.Session()
    session.get(main_url, headers=headers)  

    try:
        # Send a GET request with session cookies
        response = session.get(url, headers=headers)
        #print (response.content)
        if response.status_code == 200:
            df = pd.read_csv(io.BytesIO(response.content))
            df.rename(columns={'Index Name': 'Sector','Index Date': 'Date','Open Index Value': 'Open', 'High Index Value': 'High', 'Low Index Value': 'Low','Closing Index Value':'close', 'Points Change':'chg','Change(%)':'chg%','Volume':'Tvol','Turnover (Rs. Cr.)':'Tval'}, inplace=True)
            #print("DataFrame loaded successfully! for date ", formatted_date)
            return df
        else:
            print(f"Failed to fetch data. Status Code: {response.status_code}, Maybe weekend or Holiday", formatted_date)
            # Convert response content directly to a DataFrame

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {formatted_date}: {e}" )



current_date = datetime.now()
current_date = current_date - timedelta(1)
df = getIndexfile(current_date)
#formatted_date = current_date.strftime('%d-%m-%Y')  # Format as 'dd-mm-yyyy'
#print(formatted_date)
if df is not None:  # ✅ Check if df is valid before saving
    #df['Date'] = pd.to_datetime(df['Date'])
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')  # Example format
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    df.to_sql('idxsnapshot', conn, if_exists='append', index=False)
    print("Data loaded successfully for date:", current_date)
    #else:
    #    print(f"⚠️ Skipping {current_date.strftime('%d-%m-%Y')} due to missing data.")
    #df.to_sql('idxsnapshot', conn, if_exists='append', index=False)
    #print("DataFrame loaded successfully! for date ", current_date)
# Display the combined DataFrame
conn.close()
endtime = datetime.now()
print (f"The script completed successfully at {endtime} and time taken {endtime - starttime}", )