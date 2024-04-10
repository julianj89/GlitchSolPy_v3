from functools import lru_cache
from create_close_account import  sell_get_token_account, get_token_account


# Adjust based on expected number of different token accounts used
@lru_cache(maxsize=32)
def cached_sell_get_token_account(client, owner_pubkey, mint):
    return sell_get_token_account(client, owner_pubkey, mint)

@lru_cache(maxsize=32)
def cached_get_token_account(client, owner_pubkey, mint):
    return get_token_account(client, owner_pubkey, mint)
