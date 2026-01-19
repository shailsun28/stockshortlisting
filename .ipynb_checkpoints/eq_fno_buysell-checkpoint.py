import httpx
import json
import time
import pandas as pd
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import os

BASE_DIR = "/home/shail/stockshortlisting"
BASE_DIR_db = "/home/shail/db"

print ('Started the script at ', datetime.now())
def fetch_stock_data(stock):
    """
    Fetch stock data for a given stock symbol using NSE API.
    """
    #headers = {
    #    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    #    "Accept": "application/json, text/plain, */*",
    #    "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={stock}"
    #}
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36',
    'Referer': f'https://www.nseindia.com/get-quotes/equity?symbol={stock}',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
    }
    encoded_stock = stock.replace('&','%26')
    main_url = f"https://www.nseindia.com"
    qty_url = f"https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol={encoded_stock}"
    fno_url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolDerivativesData&symbol={encoded_stock}'
    with httpx.Client(timeout=10) as client:
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_time = now.strftime('%H:%M:%S')
        current_date = now.strftime('%Y-%m-%d')
        
        try:
            # Fetch session cookies
            response = client.get(main_url, headers=headers)
            response.raise_for_status()
            cookies = dict(client.cookies)
            time.sleep(1)  # Prevent NSE blocking
            qty_resp = client.get(qty_url, headers=headers, cookies=cookies)
            # price_resp = client.get(price_url, headers=headers, cookies=cookies) # price_url is same as qty_url, can reuse response
            fno_resp = client.get(fno_url, headers=headers, cookies=cookies)
            qty_resp.raise_for_status()
            fno_resp.raise_for_status()

            # Convert to JSON
            qtyjson = json.loads(qty_resp.text)
            fnojson = json.loads(fno_resp.text)

            # Filter for FUTSTK data only
            # The 'data' key might be missing, so use .get() safely
            all_futstk_data = [item for item in fnojson.get('data', []) if item.get('instrumentType') == 'FUTSTK']

            # Iterate through *only* the FUTSTK items to find the current month match
            for item in all_futstk_data:
                expiry_date_str = item.get('expiryDate')
                
                # Use a try block for date parsing, in case of bad data
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%d-%b-%Y')
                    
                    if expiry_date.year == current_year and expiry_date.month == current_month:
                        # We found the match! Get the identifier from THIS item, not an empty list index
                        current_month_identifier = item['identifier']
                        fustk_enconded = current_month_identifier.replace('&','%26')
                        # --- Proceed with fetching the specific futures trade info ---
                        fubuysell_url = f'https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getTradeInfoDerivative&symbol={encoded_stock}&identifier={fustk_enconded}'
                        fustk_resp = client.get(fubuysell_url, headers=headers, cookies=cookies)
                        fustk_resp.raise_for_status()
                        fustk_data_text = fustk_resp.text
                        fustkjson = json.loads(fustk_data_text)

                        # Return all the data points here, as we have successfully found all info
                        return [
                            stock, current_date, current_time,
                            qtyjson.get('equityResponse', [{}])[0].get('orderBook', {}).get('totalBuyQuantity', None),
                            qtyjson.get('equityResponse', [{}])[0].get('orderBook', {}).get('totalSellQuantity', None),
                            qtyjson.get('equityResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedValue', None),
                            qtyjson.get('equityResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedVolume', None),
                            qtyjson.get('equityResponse', [{}])[0].get('metaData', {}).get('dayHigh', None),
                            qtyjson.get('equityResponse', [{}])[0].get('metaData', {}).get('change', None),
                            qtyjson.get('equityResponse', [{}])[0].get('metaData', {}).get('pChange', None),
                            qtyjson.get('equityResponse', [{}])[0].get('metaData', {}).get('previousClose', None),
                            qtyjson.get('equityResponse', [{}])[0].get('metaData', {}).get('averagePrice', None),
                            # Access safely using .get() where possible
                            fustkjson.get('derivateResponse', [{}])[0].get('metaData', {}).get('last', None),
                            fustkjson.get('derivateResponse', [{}])[0].get('metaData', {}).get('change', None),
                            fustkjson.get('derivateResponse', [{}])[0].get('metaData', {}).get('perchange', None),
                            fustkjson.get('derivateResponse', [{}])[0].get('orderBook', {}).get('totalSellQuantity', None),
                            fustkjson.get('derivateResponse', [{}])[0].get('orderBook', {}).get('totalBuyQuantity', None),
                            fustkjson.get('derivateResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedVolume', None), 
                            fustkjson.get('derivateResponse', [{}])[0].get('tradeInfo', {}).get('totalTradedValue', None),
                            fustkjson.get('derivateResponse', [{}])[0].get('tradeInfo', {}).get('openinterest', None)
                        ]

                except ValueError:
                    # Handle date parsing errors for a specific item gracefully
                    print(f"Could not parse expiry date for an item in {stock}")
                    continue # Skip this item and continue the loop

        except (httpx.HTTPStatusError, httpx.ReadTimeout) as e:
            print(f"Error fetching data for {stock}: {e}")
            return [stock] + [None] * 19 # Adjust the length of Nones to match the number of columns
        except KeyError as e:
            print(f"Missing data key in JSON for {stock}: {e}")
            return [stock] + [None] * 19
        
        # If the loop finishes without finding a current month FUTSTK contract
        print(f"No current month FUTSTK contract found for {stock}.")
        return [stock] + [None] * 19 # Return Nones for this stock


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
        "Stock", "Date", "Time", "Tbuy_eq", "Tsell_eq",
        "Tvalue_eq", "Tvol_eq", "High_eq", "PrChg_eq", "%Prchg_eq", "Ltp_eq", "Vwap_eq", "Ltp_fu",
        'PrChg_fu', '%Prchg_fu', 'Tsell_fu', 'Tbuy_fu', 'Tvol_fu', 'Tvalue_fu', 'fuOI'                
    ])
    #df['%Prchg_fu'] = round(df['%Prchg_fu'])
    #df['%Prchg_eq'] = pd.to_numeric(df['%Prchg_eq']).round(2)
    #df['%Prchg_fu'] = pd.to_numeric(df['%Prchg_fu'], errors='coerce').astype(float).round(2)
    # Write to SQLite
    df['Stock'] = df['Stock'].replace('%26', '&', regex=True)
    df.to_sql(filename, conn, if_exists='append', index=False)
    conn.close()
    return df

if __name__ == "__main__":
    #base_dir = "/Users/shail/Documents/Trading/NiftyStocks/"
    #db_path = "/Users/shail/Documents/Trading/market-turnover/db/eq_fu_buysell_qty.db"
    db_path = os.path.join(BASE_DIR_db, "eq_fu_buysell_qty.db")
    files_to_process = ["fno"]

    for filename in files_to_process:
        filepath = os.path.join(BASE_DIR,"NiftyStocks",filename)
        if os.path.exists(filepath):
            process_file(filepath, filename, db_path)
        else:
            print(f"File not found: {filepath}")
    print(f"***** Script completed successfully at {datetime.now()} *****")