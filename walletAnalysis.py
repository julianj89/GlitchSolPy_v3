import asyncio
from datetime import datetime,  timedelta

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

"""
Set the variables
"""
RPC_HTTPS_URL = "https://solana-mainnet.g.alchemy.com/v2/0kHZ9dSMN1WJtVkWBh3bcoTQCAaFwT3S"
""" If you want to set the hours to weekly, its simple just use 24 x 7 """
total_hours = 100000#hours like 1 hour before or 2 hour or 1000 hours
wallet_public_key = "GDG7sd2ET6woQzm9ux4wvuTxCyRMqDi2wDw28Xrm2xkA"






"""----------------------------------------------------------------------------"""
ctx = AsyncClient(RPC_HTTPS_URL)

total_sold = 0
total_bought = 0
all_trades = {}


async def add_buy_sell(txn,number):
    for inner_instructions in txn.meta.inner_instructions:
        inner_instructions = inner_instructions.instructions
        try:
            if len(inner_instructions) == 2:
                for ins in inner_instructions:
                        
                        try:
                            if ins.parsed['type'] == 'transfer' and (ins.parsed['info']['authority'] == '5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1' or ins.parsed['info']['authority'] == wallet_public_key):
                                account = ins.parsed['info']['destination']
                                try:
                                    while True:
                                        try:
                                            mint_info = (await ctx.get_account_info_json_parsed(Pubkey.from_string(account)))
                                            break
                                        except:
                                            pass
                                    mint_address = mint_info.value.data.parsed['info']['mint']
                                except:
                                    try:
                                        # will use this part if token account is closed. we can also get mint by getting it from source, ever seen bonklot.sol?
                                        account = ins.parsed['info']['source']
                                        while True:
                                            try:
                                                mint_info = (await ctx.get_account_info_json_parsed(Pubkey.from_string(account)))
                                                break
                                            except:
                                                pass
                                        mint_address = mint_info.value.data.parsed['info']['mint']
                                    except:
                                        mint_address = account 

                                if all_trades[number]['from_mint'] == None:
                                    amount = ins.parsed['info']['amount']
                                    all_trades[number]['from_mint'] = mint_address
                                    all_trades[number]['from_amount'] = amount

                                elif all_trades[number]['from_mint'] != None and (all_trades[number]['from_mint'] == 'So11111111111111111111111111111111111111112' or mint_address == 'So11111111111111111111111111111111111111112'):
                                    amount = ins.parsed['info']['amount']
                                    all_trades[number]['to_mint'] = mint_address
                                    all_trades[number]['to_amount'] = amount
                                    break
                        except:
                            pass

        except:
             pass


async def main():
    global total_bought
    global total_sold

    print()
    print()

    """Get current time and calculate older time"""
    now = datetime.now()
    day_ago = now - timedelta(hours=total_hours) # Subtract one day
    timestamp_max = day_ago.timestamp()  # Get the timestamp
    local_time  = datetime.fromtimestamp(timestamp_max)  # Convert the timestamp back to UTC datetime
    print(f"[Local-Timezone] Time before {total_hours} Hours: {local_time.strftime("%Y-%m-%d %H:%M:%S")}")

    print()
    print()

    number = 1

    # get last 1000 signatures from wallet. Solana rpc only supports 1000 transactions.
    signaturess = await ctx.get_signatures_for_address(Pubkey.from_string(wallet_public_key),limit=1000,commitment='confirmed')
    m = 0
    for sig in signaturess.value:
        m = m + 1
        all_trades[number] = {
                                    'from_mint': None,
                                    'from_amount': None,
                                    'to_mint': None,
                                    'to_amount': None,
                                    'time': None
                            }

        try:
            while True:
                try:
                    txn = (await ctx.get_transaction(sig.signature,encoding="jsonParsed",max_supported_transaction_version=0))
                    blocktime = (await ctx.get_block_time(txn.value.slot)).value
                    break
                except:
                    pass

            if blocktime < timestamp_max:
                break
            if txn.value.transaction.meta.err == None:
                txn = txn.value.transaction

                all_trades[number]['time'] = blocktime

                await add_buy_sell(txn,number)
                aaa = all_trades[number]['from_mint']
                bbb = all_trades[number]['to_mint']
                if  aaa == None or bbb == None:
                        del all_trades[number]
                else:
                    date_time = datetime.fromtimestamp(blocktime)
                    print(f"Number: {number} - {all_trades[number]} - Time: {date_time}")
                    number = number + 1
            
            # time.sleep(0.1) #Uncomment this if your rpc is shit
                
        except:
            # time.sleep(2) #Uncomment this if your rpc is shit
            pass
    print()
    print("-------------- Got All trades -----\n Calculating PNL: \n")             
    for trade in all_trades:
        from_mint = all_trades[trade]['from_mint']
        to_mint = all_trades[trade]['to_mint']
        if from_mint == "So11111111111111111111111111111111111111112":
             total_bought = total_bought + int(all_trades[trade]['from_amount'])
        elif to_mint == "So11111111111111111111111111111111111111112":
             total_sold = total_sold + int(all_trades[trade]['to_amount'])
    total_bought = total_bought
    total_sold = total_sold



    PNL = (total_sold - total_bought)/ 10**9
    print(f"Total Buys: {total_bought / 10 ** 9} SOL\nTotal Sells: {total_sold / 10 ** 9} SOL\nTotal PNL: {PNL} SOL")


asyncio.run(main())
