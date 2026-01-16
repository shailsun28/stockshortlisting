import requests
from datetime import datetime


# Getting Result
def fetch_stock_data(stock):
    #main_url = 'https://www.nseindia.com'
    main_url = f"https://www.nseindia.com/get-quotes/equity?symbol={stock}"
    api = f'https://www.nseindia.com/api/corp-info?symbol={stock}&corpType=eventcalender&market=equities'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.124 Safari/537.36',
        #'Referer': f'https://www.nseindia.com/get-quotes/equity?symbol={stock}'
        'Referer': main_url
    }
    session = requests.Session()

    finaldata = None  # Initialize finaldata to None

    try:
        session.get(main_url, headers=headers)
        response = session.get(api, headers=headers)
        response.raise_for_status()

        data = response.json()
        if len(data) > 2:
            indexneed = len(data) - 1
            finaldata = [stock, data[indexneed]['bm_date'], data[indexneed]['bm_dt'], data[indexneed]['bm_purpose'],data[indexneed]['bm_timestamp']]
        else:
            print(f'Event calendar has no data for {stock}')
            finaldata = [stock, None, None, None, None]  # Handle cases with no data

    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e} stockname: {stock}')
        finaldata = [stock, None, None, None, None]  # Handle request errors
        pass

    return finaldata

if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    import pandas as pd
    from tqdm import tqdm
    import os

    starttime = datetime.now()
    print(" ######## Task Started  at ...   ", starttime)
    
    #indiceslist = ['smallcap50', 'FNO']
    indiceslist = ['niftyallmarket']
    gethour = datetime.now().strftime("%Y-%m-%d-%H")
    
    for indices in indiceslist:
        inputfile = '/Users/shail/Documents/Trading/NiftyStocks/' + indices
        calout = '/Users/shail/Documents/Trading/resultdate/' + indices + "_earnDate.csv"
        results = []
        
        with open(inputfile, "r") as f:
            stocks = f.readlines()
        
        #stocks = [item.strip() for item in stocks]
        stocks = [line.strip() for line in stocks]
        with ThreadPoolExecutor() as executor:
            results = list(tqdm(executor.map(fetch_stock_data, stocks), total=len(stocks)))
        
        hourlydf = pd.DataFrame(results, columns=["Stock", "Date", "Time", "Purpose","AnnounceDate"])
        # Replace '%26' with '&' in the 'Stock' column
        hourlydf['Stock'] = hourlydf['Stock'].replace('%26', '&', regex=True)
        hourlydf.to_csv(calout, index=False, mode='w', header=True)
        print(hourlydf.head(10))
    
    print(" ******************  Task Completed! ********************* at ", datetime.now().strftime("%Y-%m-%d-%H-%M"))
    endtime = datetime.now()
    print(f"The file is stored at {calout} and total time taken is {endtime - starttime}")
