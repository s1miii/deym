import asyncio
import requests
from flask import Flask
from threading import Thread
from telegram import Bot
from telegram.error import TelegramError
import os
import time

# --- CONFIG ---
bot_token = '7915679077:AAGtiiiwdD8_hCkHHjkZc8881ow1MjGAlTw'
channel_chat_id = '-1002546564669'
covalent_api_key = 'cqt_rQTWFJ7gRk7hb8JFwX4BQrWx43tV'

# --- Flask keep_alive server ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Telegram bot setup ---
bot = Bot(token=bot_token)

# Load notified group IDs from file if exists
if os.path.exists("notified.txt"):
    with open("notified.txt", "r") as f:
        notified_group_ids = set(f.read().splitlines())
else:
    notified_group_ids = set()

# Creator token count cache
creator_token_count_cache = {}
cache_expiry_seconds = 300  # 5 minutes

def get_creator_token_count(creator_address):
    current_time = time.time()
    if creator_address in creator_token_count_cache:
        cached_entry = creator_token_count_cache[creator_address]
        if current_time - cached_entry["timestamp"] < cache_expiry_seconds:
            return cached_entry["count"]

    try:
        url = 'https://api.arena.trade/groups_plus'
        params = { 'creator_address': f"eq.{creator_address}" }
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; TokenBot/1.0)',
            'Accept': 'application/json'
        }
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            groups = res.json()
            count = len(groups)
            creator_token_count_cache[creator_address] = {
                "count": count,
                "timestamp": current_time
            }
            return count
        else:
            return 0
    except:
        return 0

def get_creator_purchase_info(creator_address, token_contract_address, token_price_usd, covalent_api_key):
    try:
        url = f"https://api.covalenthq.com/v1/43114/address/{creator_address}/transfers_v2/"
        params = {
            "contract-address": token_contract_address,
            "key": covalent_api_key,
            "page-size": 100
        }
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            items = data.get("data", {}).get("items", [])

            total_bought = 0
            decimals = 18

            for item in items:
                for transfer in item.get("transfers", []):
                    if transfer.get("contract_address", "").lower() == token_contract_address.lower():
                        decimals = int(transfer.get("contract_decimals", 18))
                        if transfer.get("to_address", "").lower() == creator_address.lower():
                            delta = int(transfer.get("delta", "0"))
                            total_bought += delta

            if total_bought > 0:
                token_amount = total_bought / (10 ** decimals)
                usd_value = token_amount * token_price_usd
                return token_amount, usd_value

            return 0, 0
        else:
            return 0, 0
    except:
        return 0, 0

# Main bot loop
async def main():
    print("Bot started! Press Ctrl+C to stop.")
    while True:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TokenBot/1.0)',
                'Accept': 'application/json'
            }
            url = 'https://api.arena.trade/groups_plus'
            params = {'limit': 1, 'order': 'create_time.desc'}
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                groups = response.json()
                for group in groups:
                    group_id = str(group.get('row_id'))
                    if group_id in notified_group_ids:
                        continue
                        
                    # Skip if creator has multiple tokens
                    creator_address = group.get('creator_address', '')
                    creator_token_count = get_creator_token_count(creator_address)
                    if creator_token_count > 1:
                        print(f"Skipping token - creator has {creator_token_count} tokens")
                        continue

                    token_name = group.get('token_name', 'N/A')
                    token_symbol = group.get('token_symbol', 'N/A')
                    contract_address = group.get('token_contract_address', 'N/A')
                    creator_address = group.get('creator_address', 'N/A')
                    create_time = group.get('create_time', 'N/A')
                    latest_price_usd = group.get('latest_price_usd', 0.0)

                    arena_creator_link = f"https://arena.trade/user/{creator_address}"
                    starsarena_link = f"https://starsarena.com/community/{contract_address}/trade"
                    arenabook_link = f"https://arenabook.xyz/token/{contract_address}"
                    arena_trade_link = f"https://arena.trade/token/{contract_address}"

                    twitter_handle = group.get('creator_twitter_handle', 'N/A')
                    twitter_followers = group.get('creator_twitter_followers', 0)
                    twitter_info = f"[@{twitter_handle}](https://twitter.com/{twitter_handle}) ({twitter_followers} followers)" if twitter_handle else "Not Available"

                    photo_url = group.get('photo_url')
                    image_token_line = "🖼 *Image Token*\n" if photo_url else ""

                    amount_bought, usd_bought = get_creator_purchase_info(
                        creator_address, contract_address, latest_price_usd, covalent_api_key
                    )

                    creator_token_count = get_creator_token_count(creator_address)
                    farmer_tag = " *[🌾FARMER🌾]*" if creator_token_count > 1 else ""
                    token_count_display = f" [*{creator_token_count}* token{'s' if creator_token_count != 1 else ''}]"

                    message = (
                        f"🚀 *New Token Alert!*\n\n"
                        f"*Token:* {token_name} ({token_symbol})\n"
                        f"{image_token_line}"
                        f"*Trade Links:*\n"
                        f"[ArenaBook]({arenabook_link}) | [Arena Trade]({arena_trade_link}) | [StarsArena]({starsarena_link})\n\n"
                        f"*Contract Address:* `{contract_address}`\n\n"
                        f"*Creator:* [View Profile]({arena_creator_link}){farmer_tag}{token_count_display}\n"
                        f"*Twitter:* {twitter_info}\n"
                        f"*Launch Time:* {create_time}\n"
                        f"*Price:* ${latest_price_usd:.10f}\n"
                    )

                    if amount_bought > 0:
                        message += f"\n🔍 *Creator buy :* {amount_bought:.4f} {token_symbol} (~${usd_bought:.2f})"

                    try:
                        if photo_url:
                            bot.send_photo(chat_id=channel_chat_id, photo=photo_url, caption=message, parse_mode='Markdown')
                        else:
                            bot.send_message(chat_id=channel_chat_id, text=message, parse_mode='Markdown')

                        print(f"Sent notification for {token_name}")
                        notified_group_ids.add(group_id)
                        with open("notified.txt", "a") as f:
                            f.write(f"{group_id}\n")

                    except TelegramError as e:
                        print(f"Telegram error: {e}")
                        if "retry after" in str(e).lower():
                            retry_time = int(str(e).split()[-2]) + 1
                            print(f"Waiting {retry_time} seconds before retry...")
                            await asyncio.sleep(retry_time)
                        continue

            else:
                print(f"Failed to fetch data from Arena API: {response.status_code}")

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(5)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
