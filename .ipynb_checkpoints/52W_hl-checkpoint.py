import requests
import pandas as pd
from datetime import date, timedelta, datetime
import os
current_date = datetime.now()
#current_date = current_date - timedelta(1)
 # Format the date as 'ddmmyyyy'

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

formatted_date = current_date.strftime('%d%m%Y')
url = f'https://nsearchives.nseindia.com/content/CM_52_wk_High_low_{formatted_date}.csv'

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
        file_path = os.path.join(BASE_DIR, "52weekhl", f"CM_52_wk_High_low_{datetime.now().strftime('%d%m%Y')}.csv")
        #file_path = f'/Users/shail/Documents/Trading/52weekhl/CM_52_wk_High_low_{datetime.now().strftime("%d%m%Y")}.csv'
        # Write the content to a file
        with open(file_path, 'wb') as file:
            file.write(response.content)
            print(f"File downloaded successfully: {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}' "stockname:", stock)
        return None

# Generate the URL with the current date
#url = generate_date_url()
# Download the file
file_path = download_file(url)

# Import the downloaded file to DataFrame
if file_path:
    df = pd.read_csv(file_path, skiprows=2, on_bad_lines='skip', delimiter=',')
    # Display the first few rows of the DataFrame
    #print(df.head())
df.rename(columns={'Adjusted 52_Week_High': '52WH', '52_Week_High_Date': '52WH_Date', 'Adjusted 52_Week_Low': '52WL','52_Week_Low_DT':'52WL_Date'}, inplace=True)
# Check and delete rows containing '-'
df= df[~(df.isin(['-']).any(axis=1))]
df = df[df['SERIES']=='EQ']
file_path = os.path.join(BASE_DIR, "52weekhl", f"CM_52_wk_High_low_{datetime.now().strftime('%d%m%Y')}.csv")
#outfile = '/Users/shail/Documents/Trading/NiftyStocks/52_wk_High_low.csv'
outfile = os.path.join(BASE_DIR, "52weekhl", "52_wk_High_low.csv")
df.to_csv(outfile,index=False)
print("\2\n"+" ******************  Task Completed! ********************* ")
endtime = datetime.now()
print(f"The task completed at {endtime} and file is saved at {outfile}")

