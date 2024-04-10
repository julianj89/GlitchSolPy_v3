# Import necessary libraries and modules
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
import time
import asyncio
from Data_layouts import AMM_INFO_LAYOUT_V4_1, MARKET_LAYOUT
from constants import RAY_AUTHORITY_V4, RAY_V4
import json

# Define the asynchronous function to get pool details in the form of strings
async def gen_pool_strings(amm_id, ctx, retry_count=2):  # Set retry count to 2
    try:
        amm_id = Pubkey.from_string(amm_id)
        for attempt in range(retry_count):  # Retry loop for AMM data
            try:
                start = time.time()
                while time.time() - start < 3:  # Loop with timeout check
                    try:
                        amm_data = (await ctx.get_account_info_json_parsed(amm_id)).value.data
                        break  # Break if data fetched successfully
                    except:
                        await asyncio.sleep(0.5)  # Wait before retrying
                else:
                    if attempt < retry_count - 1:  # Check if should retry
                        continue  # Retry the outer loop
                    else:
                        return {"error": "server timeout - took too long to find the pool info"}

                # If we reach here, AMM data was fetched successfully
                amm_data_decoded = AMM_INFO_LAYOUT_V4_1.parse(amm_data)
                OPEN_BOOK_PROGRAM = Pubkey.from_bytes(amm_data_decoded.serumProgramId)
                marketId = Pubkey.from_bytes(amm_data_decoded.serumMarket)

                # Now attempt to fetch the market information
                for market_attempt in range(retry_count):  # Retry loop for market info
                    try:
                        start = time.time()
                        while time.time() - start < 3:  # Timeout check for market info
                            try:
                                marketInfo = (await ctx.get_account_info_json_parsed(marketId)).value.data
                                break  # Break if data fetched successfully
                            except:
                                await asyncio.sleep(0.5)  # Wait before retrying
                        else:
                            if market_attempt < retry_count - 1:
                                continue  # Retry the outer loop for market info
                            else:
                                return {"error": "server timeout - took too long to find the pool info"}

                        # If here, market info was successfully fetched
                        market_decoded = MARKET_LAYOUT.parse(marketInfo)
                        # Construct and return the pool keys
                        pool_keys = {
                            "amm_id": str(amm_id),
                            "base_mint": str(Pubkey.from_bytes(market_decoded.base_mint)),
                            "quote_mint": str(Pubkey.from_bytes(market_decoded.quote_mint)),
                            "lp_mint": str(Pubkey.from_bytes(amm_data_decoded.lpMintAddress)),
                            "version": 4,
                            "base_decimals": amm_data_decoded.coinDecimals,
                            "quote_decimals": amm_data_decoded.pcDecimals,
                            "lpDecimals": amm_data_decoded.coinDecimals,
                            "programId": str(RAY_V4),
                            "authority": str(RAY_AUTHORITY_V4),
                            "open_orders": str(Pubkey.from_bytes(amm_data_decoded.ammOpenOrders)),
                            "target_orders": str(Pubkey.from_bytes(amm_data_decoded.ammTargetOrders)),
                            "base_vault": str(Pubkey.from_bytes(amm_data_decoded.poolCoinTokenAccount)),
                            "quote_vault": str(Pubkey.from_bytes(amm_data_decoded.poolPcTokenAccount)),
                            "withdrawQueue": str(Pubkey.from_bytes(amm_data_decoded.poolWithdrawQueue)),
                            "lpVault": str(Pubkey.from_bytes(amm_data_decoded.poolTempLpTokenAccount)),
                            "marketProgramId": str(OPEN_BOOK_PROGRAM),
                            "market_id": str(marketId),
                            "market_authority": str(Pubkey.create_program_address(
                                [bytes(marketId)]
                                + [bytes([market_decoded.vault_signer_nonce])]
                                + [bytes(7)],
                                OPEN_BOOK_PROGRAM,
                            )),
                            "market_base_vault": str(Pubkey.from_bytes(market_decoded.base_vault)),
                            "market_quote_vault": str(Pubkey.from_bytes(market_decoded.quote_vault)),
                            "bids": str(Pubkey.from_bytes(market_decoded.bids)),
                            "asks": str(Pubkey.from_bytes(market_decoded.asks)),
                            "event_queue": str(Pubkey.from_bytes(market_decoded.event_queue)),
                            "pool_open_time": amm_data_decoded.poolOpenTime
                        }
                        return pool_keys  # Return the successfully built pool keys
                    except Exception as e:
                        if market_attempt < retry_count - 1:
                            continue
                        else:
                            return {"error": str(e)}  # Return exception if all retries fail

            except Exception as e:
                if attempt < retry_count - 1:
                    continue
                else:
                    return {"error": "unexpected error occurred - " + str(e)}  # More detailed error message

    except Exception as e:
        return {"error": "incorrect pair address - " + str(e)}  # Include exception details

# Define the asynchronous function to get pool details in the form of public keys
async def gen_pool_public_keys(amm_id, ctx):
    try:
        amm_id = Pubkey.from_string(amm_id)
        start = time.time()
        while True:
            try:
                amm_data = (await ctx.get_account_info_json_parsed(amm_id)).value.data
                break
            except:
                if (time.time() - start) > 3:
                    return {"error": "server timeout - took too long to find the pool info"}
                pass

        amm_data_decoded = AMM_INFO_LAYOUT_V4_1.parse(amm_data)
        OPEN_BOOK_PROGRAM = Pubkey.from_bytes(amm_data_decoded.serumProgramId)
        marketId = Pubkey.from_bytes(amm_data_decoded.serumMarket)
        try:
            while True:
                try:
                    marketInfo = (await ctx.get_account_info_json_parsed(marketId)).value.data
                    break
                except:
                    if (time.time() - start) > 3:
                        return {"error": "server timeout - took too long to find the pool info"}
                    pass

            market_decoded = MARKET_LAYOUT.parse(marketInfo)

            pool_keys = {
                "amm_id": str(amm_id),
                "base_mint": str(Pubkey.from_bytes(market_decoded.base_mint)),
                "quote_mint": str(Pubkey.from_bytes(market_decoded.quote_mint)),
                "lp_mint": str(Pubkey.from_bytes(amm_data_decoded.lpMintAddress)),
                "version": 4,
                "base_decimals": amm_data_decoded.coinDecimals,
                "quote_decimals": amm_data_decoded.pcDecimals,
                "lpDecimals": amm_data_decoded.coinDecimals,
                "programId": str(RAY_V4),
                "authority": str(RAY_AUTHORITY_V4),
                "open_orders": str(Pubkey.from_bytes(amm_data_decoded.ammOpenOrders)),
                "target_orders": str(Pubkey.from_bytes(amm_data_decoded.ammTargetOrders)),
                "base_vault": str(Pubkey.from_bytes(amm_data_decoded.poolCoinTokenAccount)),
                "quote_vault": str(Pubkey.from_bytes(amm_data_decoded.poolPcTokenAccount)),
                "withdrawQueue": str(Pubkey.from_bytes(amm_data_decoded.poolWithdrawQueue)),
                "lpVault": str(Pubkey.from_bytes(amm_data_decoded.poolTempLpTokenAccount)),
                "marketProgramId": str(OPEN_BOOK_PROGRAM),
                "market_id": str(marketId),
                "market_authority": str(Pubkey.create_program_address(
                    [bytes(marketId)]
                    + [bytes([market_decoded.vault_signer_nonce])]
                    + [bytes(7)],
                    OPEN_BOOK_PROGRAM,
                )),
                "market_base_vault": str(Pubkey.from_bytes(market_decoded.base_vault)),
                "market_quote_vault": str(Pubkey.from_bytes(market_decoded.quote_vault)),
                "bids": str(Pubkey.from_bytes(market_decoded.bids)),
                "asks": str(Pubkey.from_bytes(market_decoded.asks)),
                "event_queue": str(Pubkey.from_bytes(market_decoded.event_queue)),
                "pool_open_time": amm_data_decoded.poolOpenTime
            }
            
            # Handling JSON file update
            try:
                with open('pools.json', 'r') as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []  # If there's an error or file doesn't exist, start with an empty list

            data.append(pool_keys)  # Append the new data

            with open('pools.json', 'w') as file:
                json.dump(data, file, indent=4)  # Write back the updated list to the file
            
            return pool_keys
        except:
            return {"error": "unexpected error occurred"}
    except:
        return {"error": "incorrect pair address"}


# Main  function that uses the above utility functions
# Modify the signature of the get_data function to accept amm_id
async def get_data(amm_id):
    # amm_id is now passed as an argument
    RPC_HTTPS_URL = "https://mainnet.helius-rpc.com/?api-key=b61ee6e2-d514-4da1-9837-2c4c26e784be"
    ctx = AsyncClient(RPC_HTTPS_URL, commitment=Confirmed)

    # Fetch and print keys in the form of strings
    keys_in_the_form_strings = await gen_pool_strings(amm_id, ctx)
    # print(keys_in_the_form_strings)
    # print("*" * 500)  # Separator

    # Fetch and print keys in the form of public keys
    keys_in_the_form_of_public_keys = await gen_pool_public_keys(amm_id, ctx)
    # print(keys_in_the_form_of_public_keys)

