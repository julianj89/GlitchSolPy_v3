from spl.token.instructions import create_associated_token_account, get_associated_token_address

from solders.pubkey import Pubkey
from solders.instruction import Instruction

from solana.rpc.types import TokenAccountOpts
from solana.transaction import AccountMeta

from layouts import SWAP_LAYOUT
import logging
import json, requests

LAMPORTS_PER_SOL = 1000000000
AMM_PROGRAM_ID = Pubkey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')
SERUM_PROGRAM_ID = Pubkey.from_string('srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX')  #9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin  origingal: srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX

public_key_string = "3XBdssBmvx8YYnqU9ioSD5wA4GRc1nKeta2CxUwfXXCb"
public_key_object = Pubkey.from_string(public_key_string)




# Function to read and validate pool data, revised for clarity and error handling
def read_and_validate_pool_data(filepath='C:\\Users\\Julian\\Desktop\\Glitch\Glitch v2\\trading bot tests\\GlitchSolPy\\pools.json'):
    try:
        with open(filepath, 'r') as file:
            pools_data = json.load(file)  # This might be a list
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading pools.json: {e}")
        return None

    # Check if pools_data is a list and take the first element
    if isinstance(pools_data, list):
        pool_data = pools_data[0]  # Assuming we only care about the first pool
    else:
        pool_data = pools_data  # It's already a dictionary

    # Check if pool_data contains all required keys
    required_keys = [
        'amm_id', 'authority', 'open_orders', 'target_orders', 'base_vault',
        'quote_vault', 'market_id', 'bids', 'asks', 'event_queue',
        'market_base_vault', 'market_quote_vault', 'market_authority'
    ]

    missing_keys = [key for key in required_keys if key not in pool_data]
    if missing_keys:
        logging.error(f"Missing required keys in pool data: {missing_keys}")
        return None

    return pool_data


def make_swap_instruction(amount_in: int, token_account_in: Pubkey, token_account_out: Pubkey, mint: Pubkey, ctx, owner: Pubkey) -> Instruction:
    logging.debug("Starting make_swap_instruction")
    pools_data = read_and_validate_pool_data()
    if pools_data is None:
        logging.error("Pools data is not properly initialized.")
        raise ValueError("Pools data is not properly initialized.")

    # Convert necessary string values in pools_data to Pubkey objects
    accounts = {key: Pubkey.from_string(value) if isinstance(value, str) else value for key, value in pools_data.items()}

    tokenPk = mint
    try:
        TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        logging.debug(f"Retrieved TOKEN_PROGRAM_ID: {TOKEN_PROGRAM_ID}")
    except Exception as e:
        logging.error(f"Error retrieving TOKEN_PROGRAM_ID: {e}")
        raise
    try:
        keys = [
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=accounts["amm_id"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["authority"], is_signer=False, is_writable=False),
        AccountMeta(pubkey=accounts["open_orders"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["target_orders"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["base_vault"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["quote_vault"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=SERUM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=accounts["market_id"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["bids"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["asks"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["event_queue"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["market_base_vault"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["market_quote_vault"], is_signer=False, is_writable=True),
        AccountMeta(pubkey=accounts["market_authority"], is_signer=False, is_writable=False),
        AccountMeta(pubkey=token_account_in, is_signer=False, is_writable=True),  # UserSourceTokenAccount
        AccountMeta(pubkey=token_account_out, is_signer=False, is_writable=True),  # UserDestTokenAccount
        AccountMeta(pubkey=owner, is_signer=True, is_writable=False)  # UserOwner

    ]
        logging.debug("AccountMeta keys prepared.")
    except Exception as e:
        logging.error(f"Error preparing AccountMeta keys: {e}")
        raise

    try:
        data = SWAP_LAYOUT.build({
            "instruction": 9,
            "amount_in": int(amount_in),
            "min_amount_out": 0
        })
        logging.debug("Data for SWAP_LAYOUT built successfully.")
    except Exception as e:
     #   logging.error(f"Error building data for SWAP_LAYOUT: {e}")
        raise

    try:
        instruction = Instruction(AMM_PROGRAM_ID, data, keys)
        logging.debug("Swap instruction created successfully.")
        return instruction
    except Exception as e:
        logging.error(f"Error creating swap instruction: {e}")
        raise


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


def sell_get_token_account(ctx,
                           owner: Pubkey.from_string,
                           mint: Pubkey.from_string):
    try:
        account_data = ctx.get_token_accounts_by_owner(owner, TokenAccountOpts(mint))
        return account_data.value[0].pubkey
    except:
        print("Mint Token Not found")
        return None


def extract_pool_info(pools_list: list, mint: str) -> dict:
    for pool in pools_list:

        if pool['baseMint'] == mint and pool['quoteMint'] == 'So11111111111111111111111111111111111111112':
            return pool
        elif pool['quoteMint'] == mint and pool['baseMint'] == 'So11111111111111111111111111111111111111112':
            return pool
    raise Exception(f'{mint} pool not found!')
