import asyncio
import json
import os
import time
from pairs import run_pairs
import aiofiles
import aiohttp
from Buy2 import solana_client, execute_buy_operation, load_pools_data
from dexscreener import read_base_mint, getSymbol, monitor_price
from Sell import sell


# Load configuration
def load_config():
    with open('config.json', 'r') as file:
        return json.load(file)
    
    
async def check_for_new_pool(file_path='pools.json', interval=1):
    if not os.path.exists(file_path):
        return False  # File does not exist, can't detect changes
    
    async with aiofiles.open(file_path, mode='r') as file:
        content = await file.read()
        initial_data = json.loads(content if content else '{}')
    
    while True:
        await asyncio.sleep(interval)
        async with aiofiles.open(file_path, mode='r') as file:
            content = await file.read()
            current_data = json.loads(content if content else '{}')
            
            if current_data != initial_data:
                return True  # File changed


async def check_wallet_for_base_mint(base_mint):
    #logging.debug("Entering check wallet function.")
    headers = {
        "x-api-key": "__WBAOR-Ss_B2avG"
    }

    url = f"https://api.shyft.to/sol/v1/wallet/token_balance?network=mainnet-beta&wallet=3XBdssBmvx8YYnqU9ioSD5wA4GRc1nKeta2CxUwfXXCb&token={base_mint}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                result = await response.json()  # Use .json() to parse the response body as JSON
                if result['success'] and float(result['result']['balance']) > 0:
                    return True  # Token found with balance greater than 0
                else:
                    return False  # Token not found or balance is 0
        except aiohttp.ClientError as e:
            print(f"Error: {e}")
            return False  # Return False in case of request failure

async def clear_pools_json():
    async with aiofiles.open('pools.json', 'w') as file:
        await file.write(json.dumps([]))
        
    print("Cleared contents of pools.json.")

async def start_token_monitoring(base_mint):
    config = load_config()  
    payer_pubkey_str = config['payer_pubkey_str']  #
    
    # Use the getSymbol function to retrieve token and quote symbols
    token_symbol, quote_symbol = getSymbol(base_mint)
    if token_symbol and quote_symbol:
        print(f"Token symbol: {token_symbol}, Quote symbol: {quote_symbol}")
        #  percentage increases to monitor
        increase_list = [100, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 10000]
        monitor_price(base_mint, increase_list)
        token_to_sell = base_mint
        await sell(solana_client, token_to_sell, payer_pubkey_str)  
    else:
        print("Unable to retrieve token symbol or quote symbol.")

api_key = "__WBAOR-Ss_B2avG"
async def continuously_run():
    while True:  #  loop to allow the process to restart
        config = load_config()  # Load configurations 
        print("Starting the pairs detection...")
        task_pairs = asyncio.create_task(run_pairs())
        task_check_pool = asyncio.create_task(check_for_new_pool())

        done, pending = await asyncio.wait(
            {task_pairs, task_check_pool},
            return_when=asyncio.FIRST_COMPLETED
        )

        if any(task == task_check_pool for task in done):
            print("New pool detected in pools.json. Stopping pairs detection.")
            task_pairs.cancel()

            pools_data = load_pools_data('pools.json')  
            print("Starting the buy operation...")
            start_time = time.time()  

            try:
                execute_buy_operation(solana_client, pools_data, config['payer_pubkey_str'], config['amount'], api_key)
                end_time = time.time()  
                print(f"Buy operation completed successfully in {end_time - start_time:.2f} seconds.")

                base_mint = pools_data[-1].get('base_mint') if pools_data else None
                
                if not base_mint:
                    print("No base_mint found for the transaction.")
                else:
                    if await check_wallet_for_base_mint(base_mint):
                        print(f"Transaction confirmed via wallet balance check in {end_time - start_time:.2f} seconds.")
                        await start_token_monitoring(base_mint)
                    else:
                        print(f"Transaction might have failed, unable to confirm via wallet balance in {end_time - start_time:.2f} seconds.")
                        await clear_pools_json()
            except Exception as e:
                end_time = time.time()  
                print(f"Buy operation failed in {end_time - start_time:.2f} seconds: {e}")
                await clear_pools_json()
        else:
            print("Pairs detection completed or stopped unexpectedly.")

        for task in pending:
            task.cancel()

        # Brief delay before restarting to prevent rapid, uncontrollable loops in case of immediate failure
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(continuously_run())

