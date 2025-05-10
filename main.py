import asyncio
import requests
import time
from telegram import Bot
from telegram.error import TelegramError

# Initialize Telegram bot
bot_token = '7915679077:AAGtiiiwdD8_hCkHHjkZc8881ow1MjGAlTw'
channel_chat_id = '-1002546564669'
bot = Bot(token=bot_token)

# Store IDs of already notified groups
notified_group_ids = set()

async def main():
    print("Bot started! Press Ctrl+C to stop.")
    while True:
        try:
            print("Fetching latest token launches...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TokenBot/1.0)',
                'Accept': 'application/json'
            }
            url = 'https://api.arena.trade/groups_plus'
            params = {
                'limit': 1,
                'order': 'create_time.desc'
            }
            response = requests.get(url, headers=headers, params=params)
            
            print(f"API Response: {response.text}")  # Debug line
            
            if response.status_code == 200:
                groups = response.json()
                
                for group in groups:
                    group_id = group.get('row_id')
                    if group_id not in notified_group_ids:
                        token_name = group.get('token_name', 'N/A')
                        token_symbol = group.get('token_symbol', 'N/A')
                        contract_address = group.get('token_contract_address', 'N/A')
                        creator_address = group.get('creator_address', 'N/A')
                        create_time = group.get('create_time', 'N/A')
                        latest_price_usd = group.get('latest_price_usd', 0.0)

                        snowtrace_link = f"https://snowtrace.io/address/{creator_address}"
                        arena_creator_link = f"https://arena.trade/user/{creator_address}"
                        arena_token_link = f"https://starsarena.com/community/{contract_address}/trade"

                        twitter_handle = group.get('creator_twitter_handle', 'N/A')
                        twitter_followers = group.get('creator_twitter_followers', 0)
                        twitter_info = f"[@{twitter_handle}](https://twitter.com/{twitter_handle}) ({twitter_followers} followers)" if twitter_handle else "Not Available"
                        
                        message = (
                            f"🚀 *New Token Alert!*\n\n"
                            f"*Token:* {token_name} ({token_symbol})\n"
                            f"*View on Arena:* [Click Here]({arena_token_link})\n"
                            f"*Creator:* [View Profile]({arena_creator_link})\n"
                            f"*Twitter:* {twitter_info}\n"
                            f"*Launch Time:* {create_time}\n"
                            f"*Price:* ${latest_price_usd:.10f}"
                        )

                        try:
                            await bot.send_message(chat_id=channel_chat_id, text=message, parse_mode='Markdown')
                            notified_group_ids.add(group_id)
                            print(f"Sent notification for {token_name}")
                        except TelegramError as e:
                            print(f"Telegram error: {e}")
                            if "retry after" in str(e).lower():
                                retry_time = int(str(e).split()[-2]) + 1
                                print(f"Waiting {retry_time} seconds before retry...")
                                await asyncio.sleep(retry_time)
                            continue

            else:
                print(f"Failed to fetch data: {response.status_code}")

        except Exception as e:
            print(f"Error: {e}")

        # Wait longer between checks to avoid rate limits
        await asyncio.sleep(1)  # Check every 10 seconds

if __name__ == "__main__":
    asyncio.run(main())
