import discord as dc
import asyncio  # 加入 asyncio 避免 race condition
import logging
import threading
import os
from flask import Flask
from objects import *
from generalmethods import *
from generalcommands import *
from geminichat import chat_process_message

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

app = Flask(__name__)
@app.route("/")
def home():
    return "Furina is now awake! :D"
port = int(os.environ.get("PORT", 8080))
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

@bot.event
async def on_ready():
    await send_new_info_logging(bot=bot, message=f"Logged in as {bot.user}, system is ready.")

    try:
        synced = await bot.tree.sync()
        await send_new_info_logging(bot=bot, message=f"Synced {len(synced)} commands.")
    except Exception as e:
        await send_new_error_logging(f"Error syncing commands: {e}")

    await asyncio.sleep(3)  # 確保 WebSocket 初始化完成

@bot.event
async def on_message(message: dc.Message):
    await chat_process_message(bot, model, message)  # 確保只執行一次

async def main():
    await bot.start(DISCORD_BOT_API_KEY)
    await send_new_info_logging(bot=bot, message=f"Bot successfully started at {get_hkt_time()}.", to_discord=False) 

if __name__ == "__main__":
    asyncio.run(main())