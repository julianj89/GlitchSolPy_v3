from spl.token.instructions import create_associated_token_account, get_associated_token_address
from spl.token.instructions import close_account, CloseAccountParams
from spl.token.client import Token
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solana.rpc.types import TokenAccountOpts
from solana.transaction import AccountMeta
from construct import Bytes, Int8ul, Int64ul, BytesInteger
from construct import Struct as cStruct
from spl.token.core import _TokenCore

from solana.rpc.commitment import Commitment
from solana.rpc.api import RPCException
from solana.rpc.api import Client, Keypair
import base58

from solders.signature import Signature
from layouts import SWAP_LAYOUT
import json
import logging
from create_close_account import get_token_account,  make_swap_instruction, read_and_validate_pool_data, LAMPORTS_PER_SOL
import requests
import time

def send_transaction_to_shyft(encoded_txn, api_key, network='mainnet-beta'):
    url = "https://api.shyft.to/sol/v1/transaction/send_txn"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "network": network,
        "encoded_transaction": encoded_txn
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

solana_client = Client("https://rpc.shyft.to?api_key=__WBAOR-Ss_B2avG") #https://api.mainnet-beta.solana.com  https://rpc.shyft.to?api_key=__WBAOR-Ss_B2avG   https://mainnet.helius-rpc.com/?api-key=d11eeb0d-6d4d-4efb-a57b-2c113f383648

# Configure logging to write to a file, including the time, level, and message
# logging.basicConfig(filename='debug.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_token_account(ctx,
                      owner: Pubkey.from_string,
                      mint: Pubkey.from_string):
    try:
        account_data = ctx.get_token_accounts_by_owner(owner, TokenAccountOpts(mint))
        return account_data.value[0].pubkey, None
    except:
        swap_associated_token_address = get_associated_token_address(owner, mint)
        swap_token_account_Instructions = create_associated_token_account(owner, owner, mint)
        return swap_associated_token_address, swap_token_account_Instructions

# Function to load pools data from a JSON file
def load_pools_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        # Ensure data is a list for consistency
        if isinstance(data, dict):
            # logging.debug("Loaded data is a dictionary. Converting to a list for consistency.")
            data = [data]  # Convert to a list of one dictionary
        elif not isinstance(data, list):
            # logging.error(f"Unexpected type for loaded data: {type(data)}. Expected dict or list.")
            return []
        return data


def process_pool(pool):
    accounts_dict = {
        "amm_id": pool.get("id", None),
        "authority": pool.get("authority", None),
        "open_orders": pool.get("open_orders", None),
        "target_orders": pool.get("target_orders", None),
        "base_vault": pool.get("base_vault", None),
        "quote_vault": pool.get("quote_vault", None),
        "market_id": pool.get("market_id", None),
        "bids": pool.get("bids", None),
        "asks": pool.get("asks", None),
        "event_queue": pool.get("event_queue", None),
        "market_base_vault": pool.get("market_base_vault", None),
        "market_quote_vault": pool.get("market_quote_vault", None),
        "market_authority": pool.get("market_authority", None)
    }
    return accounts_dict

def execute_buy_operation(solana_client, pools_data, payer_pubkey_str, amount, api_key):
    """Execute buy operation for each pool in the pools data."""
    payer = Keypair.from_base58_string(payer_pubkey_str)
    print(f"Payer Public Key: {payer.pubkey()}")

    for pool in pools_data:
        processed_pool = process_pool(pool)
        logging.debug(f"Processed Pool: {processed_pool}")
        # Now, only call process_pool once and use `processed_pool` directly afterwards.

        
        mint = Pubkey.from_string(pool['base_mint'])
        amount_in = int(amount * LAMPORTS_PER_SOL)
        
        # Initialize the transaction attempt counter
        attempt_count = 0
        max_attempts = 1 

        while attempt_count < max_attempts:
            try:
                # Transaction related logic
                print("1. Get TOKEN_PROGRAM_ID...")
                accountProgramId = solana_client.get_account_info_json_parsed(mint)
                TOKEN_PROGRAM_ID = accountProgramId.value.owner

                print("2. Get Mint Token accounts addresses...")
                swap_associated_token_address, swap_token_account_Instructions = get_token_account(
                    solana_client, payer.pubkey(), mint)

                print("3. Create Wrap Sol Instructions...")
                balance_needed = Token.get_min_balance_rent_for_exempt_for_account(solana_client)
                WSOL_token_account, swap_tx, payer, Wsol_account_keyPair, opts = _TokenCore._create_wrapped_native_account_args(
                    TOKEN_PROGRAM_ID, payer.pubkey(), payer, amount_in,
                    False, balance_needed, Commitment("confirmed"))

                print("4. Create Swap Instructions...")
                #logging.debug(f"processed_pool: {processed_pool}")
                instructions_swap = make_swap_instruction(
                    amount_in,
                    WSOL_token_account,
                    swap_associated_token_address,
                    mint,
                    solana_client,
                    payer.pubkey()
                )

                print("5. Create Close Account Instructions...")
                params = CloseAccountParams(account=WSOL_token_account, dest=payer.pubkey(), owner=payer.pubkey(),
                                            program_id=TOKEN_PROGRAM_ID)
                closeAcc = close_account(params)

                print("6. Add instructions to transaction...")
                if swap_token_account_Instructions is not None:
                    swap_tx.add(swap_token_account_Instructions)
                swap_tx.add(instructions_swap)
                swap_tx.add(closeAcc)

                print("7. Execute Transaction...")
                serialized_txn = swap_tx.serialize().decode('base64')  # Assuming swap_tx is your Transaction object
                shyft_response = send_transaction_to_shyft(serialized_txn, api_key, 'mainnet-beta')
                print(f"Shyft submission response: {shyft_response}")

                print(f"8. Transaction Confirmed. Base mint of processed pool: {mint}")   #print("8. Transaction Confirmed")
                
                # Transaction was successful, exit the while loop
                break

            except Exception as e:
                logging.error(f"Transaction failed on attempt {attempt_count + 1}: {e}")
                attempt_count += 1  # Make sure this line is inside the except block
                
                if attempt_count == max_attempts:
                    logging.error(f"Transaction failed after {max_attempts} attempts.")
                    break  # Exit the while loop after the final attempt
                else:
                    logging.info(f"Retrying transaction (Attempt {attempt_count + 1} of {max_attempts}).")




        for pool in pools_data:
         process_pool(pool)

def main():
    """Main function to trigger the buy operation."""
    file_path = r'C:\Users\Julian\Desktop\Glitch\Glitch v2\trading bot tests\GlitchSolPy\pools.json'
    payer_pubkey_str = "3G1ZJjjQAYvDCHhm4Tw7a7TPUfLBdsVhgd1AMmS4cQ1JKvhEc2AwePCk3cr1et5zbXBrz1tVtuY5pupVvYsH8LRu"
    amount = 0.0004960  # Example amount

    pools_data = load_pools_data(file_path)
    if pools_data:
        execute_buy_operation(solana_client, pools_data, payer_pubkey_str, amount)
    else:
        logging.error("No pool data available to execute buy operation.")

if __name__ == '__main__':
    # Configure logging at the start of your script
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    main()

    