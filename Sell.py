from functools import lru_cache
from spl.token.instructions import close_account, CloseAccountParams
from solana.rpc.types import TokenAccountOpts
from solana.rpc.api import RPCException
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from solana.rpc.api import Client, Keypair
import base58
from create_close_account import  make_swap_instruction, read_and_validate_pool_data
from dexscreener import getSymbol, read_base_mint
import time
from cache_utils import  cached_sell_get_token_account, cached_get_token_account
import json
LAMPORTS_PER_SOL = 1000000000

api_key = "__WBAOR-Ss_B2avG"

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


def load_and_validate_bought_pool_data(token_to_sell, file_path='pools.json'):
    with open(file_path, 'r') as file:
        pools_data = json.load(file)
    
    for pool in pools_data:
        if 'base_mint' in pool and pool['base_mint'] == token_to_sell:
            return pool  # Found the matching pool
        
        

def sell(solana_client, TOKEN_TO_SWAP_SELL, payer):
    token_symbol, SOL_Symbol = getSymbol(TOKEN_TO_SWAP_SELL)
    mint = Pubkey.from_string(TOKEN_TO_SWAP_SELL)
    sol = Pubkey.from_string("So11111111111111111111111111111111111111112")

    print("1. Get TOKEN_PROGRAM_ID...")
    TOKEN_PROGRAM_ID = solana_client.get_account_info_json_parsed(mint).value.owner

    print("2. Get Pool Keys from bought pools...")
    pool_data = load_and_validate_bought_pool_data(TOKEN_TO_SWAP_SELL)

    if not pool_data:
        print(f"a|Sell Pool ERROR {token_symbol}", "[Raydium]: Pool Data Not Found or Invalid")
        return "failed"

    if pool_data['base_mint'] != TOKEN_TO_SWAP_SELL:
        print(f"a|Sell Pool ERROR {token_symbol} [Raydium]: Base Mint not matching. Expected: {pool_data.get('base_mint')}, Found: {TOKEN_TO_SWAP_SELL}")
        return "failed"

    print("3. Get Token Balance from wallet...")
    balanceBool = True
    amount_in = 0  # Initialize amount_in to zero
    while balanceBool:
        tokenPk = mint
        accountProgramId = solana_client.get_account_info_json_parsed(tokenPk)
        programid_of_token = accountProgramId.value.owner
        accounts = solana_client.get_token_accounts_by_owner_json_parsed(payer.pubkey(), TokenAccountOpts(program_id=programid_of_token)).value

        for account in accounts:
            mint_in_acc = account.account.data.parsed['info']['mint']
            if mint_in_acc == str(mint):
                amount_in = int(account.account.data.parsed['info']['tokenAmount']['amount'])
                print("3.1 Token Balance [Lamports]: ", amount_in)
                amount_in = int(amount_in * 1)  # This line sells 10% of the supply each time
                break

        if amount_in > 0:
            balanceBool = False
        else:
            print("No Token Found")  # Changed message for clarity
            return "no_balance"  # Exit the function if no balance

    print("4. Get token accounts for swap...")
    swap_token_account = cached_sell_get_token_account(solana_client, payer.pubkey(), mint)
    WSOL_token_account, WSOL_token_account_Instructions = cached_get_token_account(solana_client, payer.pubkey(), sol)

    if swap_token_account == None:
        print("swap_token_account not found...")
        return "failed"
    else:
        print("5. Create Swap Instructions...")
        instructions_swap = make_swap_instruction(amount_in,
                                                  swap_token_account,
                                                  WSOL_token_account,
                                                  mint,
                                                  solana_client,
                                                  payer.pubkey())

        print("6. Create Instructions to Close WSOL account...")
        params = CloseAccountParams(account=WSOL_token_account, dest=payer.pubkey(), owner=payer.pubkey(),
                                    program_id=TOKEN_PROGRAM_ID)
        closeAcc = close_account(params)

        print("7. Create transaction and add instructions to Close WSOL account...")
        swap_tx = Transaction()
        signers = [payer]
        if WSOL_token_account_Instructions != None:
            swap_tx.add(WSOL_token_account_Instructions)
            swap_tx.add(instructions_swap)
            swap_tx.add(closeAcc)

    # Here you serialize, encode, and send the transaction to Shyft before executing it on the blockchain
    encoded_txn = base58.b58encode(swap_tx.serialize()).decode('utf-8')
    send_transaction_to_shyft(encoded_txn, "__WBAOR-Ss_B2avG")

    try:
        print("8. Execute Transaction...")
        start_time = time.time()
        txn = solana_client.send_transaction(swap_tx, *signers)
        txid_string_sig = txn.value
        print("9. Transaction Successful")
        print("Transaction Signature: ", txid_string_sig)
    except RPCException as e:
        print(f"Error: [{e.args[0].message}]...\nRetrying...")
    except Exception as e:
        print(f"Error: [{e}]...\nEnd...")
        return "failed"



def main():
    solana_client = Client("https://rpc.shyft.to?api_key=__WBAOR-Ss_B2avG")
    token_toSell = read_base_mint()
    private_key_string = "3G1ZJjjQAYvDCHhm4Tw7a7TPUfLBdsVhgd1AMmS4cQ1JKvhEc2AwePCk3cr1et5zbXBrz1tVtuY5pupVvYsH8LRu"
    private_key_bytes = base58.b58decode(private_key_string)
    payer = Keypair.from_bytes(private_key_bytes)
    print(f"Your Wallet Address : {payer.pubkey()}")
    sell(solana_client, token_toSell, payer)

if __name__ == "__main__":
    main()
