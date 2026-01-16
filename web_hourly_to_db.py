from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests
import pandas as pd
import sqlite3
import time

# Getting hourly data from NSE webpage
def fetch_stock_data(stock):
    stock_encode = stock.replace('&', '%26')
    main_url = 'https://www.nseindia.com'
    api_url = f'https://www.nseindia.com/api/quote-equity?symbol={stock_encode}&section=trade_info'
    api2 = f'https://www.nseindia.com/api/quote-equity?symbol={stock_encode}'
    #headers = {
    #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    #    'Referer': main_url
    #}
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36',
    'Referer': f'https://www.nseindia.com/get-quotes/equity?symbol={stock_encode}',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
    }

    session = requests.Session()

    # Implement retry strategy
    retry = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        session.get(main_url, headers=headers)
        time.sleep(1)  # Adding a 1-second delay between requests
        response = session.get(api_url, headers=headers)
        response2 = session.get(api2, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()
        data2 = response2.json()
        ttime = datetime.now().strftime('%H:%M:%S')
        Tvol = data.get('marketDeptOrderBook', {}).get('tradeInfo', {}).get('totalTradedVolume', 0)
        Tvalue = data.get('marketDeptOrderBook', {}).get('tradeInfo', {}).get('totalTradedValue', 0)
        qtyDiff = Tvol - data.get('securityWiseDP', {}).get('quantityTraded', 0)
        finaldata = [
            stock, data.get('securityWiseDP', {}).get('secWiseDelPosDate', None), ttime, Tvalue, Tvol, qtyDiff,
            data.get('securityWiseDP', {}).get('quantityTraded', 0), data.get('securityWiseDP', {}).get('deliveryQuantity', 0),
            data2.get('priceInfo', {}).get('lastPrice', 0), data2.get('priceInfo', {}).get('open', 0),
            data2.get('priceInfo', {}).get('intraDayHighLow', {}).get('max', 0), data2.get('priceInfo', {}).get('intraDayHighLow', {}).get('min', 0),
            data2.get('priceInfo', {}).get('vwap', 0), data2.get('priceInfo', {}).get('pChange', 0), data2.get('priceInfo', {}).get('change', 0)
        ]
        return finaldata

    except requests.exceptions.RequestException as e:
        print(f"An error occurred for {stock}: {e}")
        return [stock, None, None, None, None, None, None, None, None, None, None, None, None, None, None]

if __name__ == "__main__":
    starttime = datetime.now()
    indiceslist = ['fno', 'allmarket_nonfno']
    #indiceslist = ['mystock']
    hrdb_path = "/Users/shail/Documents/Trading/market-turnover/db/nsehourly.db"
    hr_conn = sqlite3.connect(hrdb_path)  # db connection to TA db
    ot_path = "/Users/shail/Documents/Trading/market-turnover/db/onetimehourly.db"
    ot_conn = sqlite3.connect(ot_path)  # db connection to hourly web collect one time db

    for indices in indiceslist:
        inputfile = f'/Users/shail/Documents/Trading/NiftyStocks/{indices}'
        print(f'Fetching data for index {indices}')
        hourlypath = '/Users/shail/Documents/Trading/shortlist/hourly/hrlyweb_' + indices + "_" + datetime.now().strftime("%Y-%m-%d-%H-%M") + ".csv"

        with open(inputfile, "r") as f:
            stocks = [item.strip() for item in f.readlines()]

        with ThreadPoolExecutor(max_workers=9) as executor:
            results = list(tqdm(executor.map(fetch_stock_data, stocks), total=len(stocks)))

        # Create DataFrame and handle non-numeric values
        columns = ["Stock", "Date", "Runtime", "Tvalue", "Tvol", "qtyDiff", "cur_trd_qty", "cur_dly", "LTP", "Open", "High", "Low", "VWAP", "PrChgP", "PrChg"]
        hourlydf = pd.DataFrame(results, columns=columns)
        hourlydf.fillna(0, inplace=True)

        # Export data to CSV and database
        hourlydf['Stock'] = hourlydf['Stock'].replace("%26", "&", regex=True)
        hourlydf.to_csv(hourlypath, index=False)
        hourlydf.to_sql(f'hrly_{indices}', hr_conn, if_exists='append', index=False)
        print(f'Data appended to nsehourly.db successfully')
        hourlydf.to_sql(f'hrly_{indices}', ot_conn, if_exists='replace', index=False)
        print(f'Data replaced to onetimehourly.db successfully for the current hour')

    hr_conn.close()
    ot_conn.close()

    endtime = datetime.now()
    print(f"Task completed at {endtime.strftime('%H:%M:%S')} and time taken to complete the task is {str(endtime - starttime)}")
    print(f"The output file in csv format is stored at {hourlypath} and exported to db")
