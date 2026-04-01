import os
import time
import json
import requests
import pandas as pd
import sqlite3
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

def fetch_stock_data(stock: str):
    """
    Fetch equity + derivative data for a given NSE stock symbol.
    Returns a list of values or Nones if request fails.
    """

    now = datetime.now()
    current_year = now.year
    #current_month = now.month
    current_month = 4
    current_time = now.strftime('%H:%M:%S')
    current_time = now.strftime('%H:%M')
    current_date = now.strftime('%Y-%m-%d')

    encoded_stock = stock.replace('&', '%26')
    main_url = 'https://www.nseindia.com'
    qty_url = f"https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol={encoded_stock}"
    fno_url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol={encoded_stock}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.124 Safari/537.36',
        'Referer': f'https://www.nseindia.com/get-quotes/equity?symbol={encoded_stock}',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    session = requests.Session()
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
        time.sleep(1)

        response = session.get(qty_url, headers=headers)
        response2 = session.get(fno_url, headers=headers)
        response.raise_for_status()
        eqjson = response.json()
        fno = response2.json()

        all_futstk_data = [item for item in fno.get('data', []) if item.get('instrumentType') == 'FUTSTK']

        for item in all_futstk_data:
            expiry_date_str = item.get('expiryDate')
            expiry_date = datetime.strptime(expiry_date_str, '%d-%b-%Y')

            if expiry_date.year == current_year and expiry_date.month == current_month:
                current_month_identifier = item['identifier']
                fustk_encoded = current_month_identifier.replace('&', '%26')

                fubuysell_url = (
                    f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?'
                    f'functionName=getTradeInfoDerivative&symbol={encoded_stock}&identifier={fustk_encoded}'
                )

                fuorder_resp = session.get(fubuysell_url, headers=headers)
                fuorder_resp.raise_for_status()
                fustkjson = fuorder_resp.json()
                dt_str = fustkjson['derivateResponse'][0]['lastUpdateTime'] 
                date_part, fetch_time = dt_str.split()
                listnew = [
                    stock, current_date, current_time, fetch_time,
                    eqjson.get('equityResponse', [{}])[0].get('orderBook', {}).get('totalBuyQuantity', None),
                    eqjson.get('equityResponse', [{}])[0].get('orderBook', {}).get('totalSellQuantity', None),
                    eqjson.get('equityResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedValue', None),
                    eqjson.get('equityResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedVolume', None),
                    eqjson.get('equityResponse', [{}])[0].get('metaData', {}).get('dayHigh', None),
                    eqjson.get('equityResponse', [{}])[0].get('metaData', {}).get('change', None),
                    eqjson.get('equityResponse', [{}])[0].get('metaData', {}).get('pChange', None),
                    eqjson.get('equityResponse', [{}])[0].get('metaData', {}).get('previousClose', None),
                    eqjson.get('equityResponse', [{}])[0].get('metaData', {}).get('averagePrice', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('metaData', {}).get('last', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('metaData', {}).get('change', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('metaData', {}).get('perchange', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('orderBook', {}).get('totalSellQuantity', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('orderBook', {}).get('totalBuyQuantity', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedVolume', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedValue', None),
                    fustkjson.get('derivateResponse', [{}])[0].get('tradeInfo', {}).get('openinterest', None)
                ]
                return listnew

        # If no matching expiry found
        return [stock] + [None] * 19

    except requests.exceptions.RequestException as e:
        print(f"An error occurred for {stock}: {e}")
        return [stock] + [None] * 19

def process_file(filepath, filename, db_path):
    """
    Process stock data file and store results in SQLite.
    """
    conn = sqlite3.connect(db_path)

    # Read stock symbols
    with open(filepath, 'r') as file:
        #stocks = [line.strip().replace('&','%26') for line in file.readlines()]
        stocks = [line.strip() for line in file.readlines()]

    # Fetch data using multi-threading
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(tqdm(executor.map(fetch_stock_data, stocks), total=len(stocks)))

    # Filter out failed requests (None)
    results = [res for res in results if res]

    # Create DataFrame
    df = pd.DataFrame(results, columns=[
        "Stock", "Date", "Time", "fetch_time","Tbuy_eq", "Tsell_eq",
        "Tvalue_eq", "Tvol_eq", "High_eq", "PrChg_eq", "%Prchg_eq", "Ltp_eq", "Vwap_eq", "Ltp_fu",
        'PrChg_fu', '%Prchg_fu', 'Tsell_fu', 'Tbuy_fu', 'Tvol_fu', 'Tvalue_fu', 'fuOI'                
    ])
    #df['%Prchg_fu'] = round(df['%Prchg_fu'])
    #df['%Prchg_eq'] = pd.to_numeric(df['%Prchg_eq']).round(2)
    df['%Prchg_fu'] = pd.to_numeric(df['%Prchg_fu'], errors='coerce').astype(float).round(2)
    # Write to SQLite
    df['Stock'] = df['Stock'].replace('%26', '&', regex=True)
    df = df.drop_duplicates(subset=['Stock', 'Date', 'Time'])
    df.to_sql(filename, conn, if_exists='append', index=False)
    conn.close()
    return df

if __name__ == "__main__":
    starttime = datetime.now()
    print(f"* Task started at {starttime} *****")
    #base_dir = "/Users/shail/Documents/Trading/NiftyStocks/"
    #db_path = "/Users/shail/Documents/Trading/market-turnover/db/eq_fu_buysell_qty.db"
    db_path = os.path.join(BASE_DIR_db, "niftybank.db")
    files_to_process = ["niftybank"]

    for filename in files_to_process:
        filepath = os.path.join(BASE_DIR,"NiftyStocks",filename)
        if os.path.exists(filepath):
            process_file(filepath, filename, db_path)
        else:
            print(f"File not found: {filepath}")
    print(f"***** Script completed successfully *****")
    endtime = datetime.now()
    elapsed = endtime - starttime

# total seconds as float
    total_seconds = elapsed.total_seconds()
# minutes and seconds
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds - int(total_seconds)) * 1000)
    print(f"The time taken to complete the task is {minutes}:{seconds:02d}.{milliseconds:03d}")
