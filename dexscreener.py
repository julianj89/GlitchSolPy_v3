import requests
import json
import os
import sys
import time


def read_base_mint(file_path='pools.json'):
    with open(file_path, 'r') as file:
        data = json.load(file)
        # Assuming you want the first item's baseMint
        return data[0]['base_mint']
    

# Define get_price function
def get_price(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    exclude = ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB']
    response = requests.get(url).json()

    if token_address not in exclude:
        for pair in response['pairs']:
            if pair['quoteToken']['address'] == 'So11111111111111111111111111111111111111112':
                return float(pair['priceUsd'])
    else:
        return response['pairs'][0]['priceUsd']
    return None

# Monitor price increases
def monitor_price(token_address, increase_list):
    initial_price = get_price(token_address)
    if initial_price is None:
        print("Unable to retrieve price for the given token address.")
        return

    print(f"Monitoring price for token address {token_address}. Initial price: {initial_price}")
    # Track which increase targets have been met
    increase_flags = {increase: False for increase in increase_list}
    while True:  # Continuous monitoring
        current_price = get_price(token_address)
        if current_price is not None:
            print(f"Current price: {current_price}")
            for increase in increase_list:
                target_price = initial_price * ((100 + increase) / 100)
                if not increase_flags[increase] and current_price >= target_price:
                    print(f"Price has increased by {increase}%, reaching {current_price}")
                    increase_flags[increase] = True  # Mark this increase as met
        else:
            print("Current price is None, check if token address is correct or API limit reached.")
        time.sleep(15)  # Check every 15 seconds


def getSymbol(token):
    # Correct the addresses for USDC and USDT
    exclude = {
        'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',
        'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 'USDT'
    }

    # Check if the token is in the exclude list and return its symbol along with 'SOL'
    if token in exclude:
        return exclude[token], 'SOL'

    # Continue with the API request if the token is not in the exclude list
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"

    try:
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            resp = response.json()
            # Iterate through the pairs to find a pair with 'SOL' as quoteToken
            for pair in resp['pairs']:
                if pair['quoteToken']['symbol'] == 'SOL':
                    # Return the symbol of the base token and 'SOL'
                    return pair['baseToken']['symbol'], 'SOL'
            # If no pair with 'SOL' was found, return empty strings
            return "", ""
        else:
            # Log the failure status code
            print(f"[getSymbol] Request failed with status code {response.status_code}")
            return "", ""  # Return empty strings if request failed

    except requests.exceptions.RequestException as e:
        # Log the exception
        print(f"[getSymbol] error occurred: {e}")
        return "", ""  # Return empty strings if an exception occurred

        
#
# Main execution
if __name__ == "__main__":
    # Read the token address from the trades.json file
    token_address = read_base_mint()

    # Get the symbol of the token
    token_symbol, quote_symbol = getSymbol(token_address)
    if token_symbol and quote_symbol:  # Ensure symbols were successfully retrieved
        print(f"Token symbol: {token_symbol}, Quote symbol: {quote_symbol}")

        # Define the list of percentage increases to monitor
        increase_list = [100, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 10000]
        
        # Start monitoring the price for the given token address
        monitor_price(token_address, increase_list)
    else:
        print("Unable to retrieve token symbol or quote symbol.")

