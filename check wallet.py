from functools import lru_cache
from spl.token.instructions import close_account, CloseAccountParams
from solana.rpc.types import TokenAccountOpts
from solana.rpc.api import RPCException
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from solana.rpc.api import Client, Keypair
import base58

import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts

# Helper function to safely convert base58 string to Pubkey
def safe_pubkey_from_base58(base58_str):
    decoded_bytes = base58.b58decode(base58_str)
    if len(decoded_bytes) == 32:
        return Pubkey.from_bytes(decoded_bytes)  # Use from_bytes for solders Pubkey
    else:
        raise ValueError("Invalid public key length after base58 decoding")

class WalletChecker:
    def __init__(self, client_endpoint):
        self.client = AsyncClient(client_endpoint)

    async def check_wallet_for_base_mint(self, wallet_address, base_mint):
        print(f"Checking wallet for base mint address: {base_mint}")

        try:
            # Use the safe conversion from base58 to Pubkey
            wallet_pubkey = safe_pubkey_from_base58(wallet_address)
            base_mint_pubkey = safe_pubkey_from_base58(base_mint)
            response = await self.client.get_token_accounts_by_owner(
                wallet_pubkey,
                opts=TokenAccountOpts(mint=base_mint_pubkey)
            )
            # Directly handle the response without assuming a 'result' attribute
            accounts = response.value  # Assuming 'value' is the correct attribute based on your previous message

            if accounts:
                print("Token found in wallet.")
                return True
            else:
                print("Token not found in wallet.")
                return False
        except Exception as e:
            print(f"Error checking wallet: {e}")
            return False

async def main():
    # Replace these with your wallet address and the mint address you want to check
    wallet_address = '3XBdssBmvx8YYnqU9ioSD5wA4GRc1nKeta2CxUwfXXCb'
    base_mint = 'BwKpcFD92VWE8E6dMxCzroADW7byZ3VuPvbuRwEYEJk3'

    checker = WalletChecker("https://api.mainnet-beta.solana.com")  # or another RPC endpoint as needed
    result = await checker.check_wallet_for_base_mint(wallet_address, base_mint)
    print(f"Check result: {result}")

    await checker.client.close()

if __name__ == "__main__":
    asyncio.run(main())
