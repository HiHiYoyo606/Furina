import discord as dc
import google.generativeai as genai
import os
import threading
import logging
import asyncio  # 加入 asyncio 避免 race condition
from dotenv import load_dotenv
from flask import Flask

app = Flask(__name__)
@app.route("/")
def home():
    return "Successfully let Furina wake up."
port = int(os.environ.get("PORT", 8080))
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

logging.basicConfig(
    level=logging.INFO,  # 或 DEBUG 適用於更詳細的日誌
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")

intents = dc.Intents.default()
intents.message_content = True  
intents.members = True 

client = dc.Client(intents=intents)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

TARGET_CHANNEL_IDS = [
    1351423098276282478,
    1351206275538485424,
]

async def fetch_full_history(channel: dc.TextChannel):
    """取得頻道的完整歷史訊息，並回傳陣列 (格式: [{"role": "user", "parts": "訊息內容"}])"""
    try:
        messages = []
        async for message in channel.history(limit=100):  # 限制讀取最近 100 則
            role = "user" if message.author != client.user else "model"
            messages.append({"role": role, "parts": [message.content]})

        messages.reverse()  # 讓對話順序從舊到新
        return messages
    
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

async def process_message(message: dc.Message):
    """處理收到的訊息並產生回應"""
    if message.author == client.user or (not (message.channel.id in TARGET_CHANNEL_IDS or isinstance(message.channel, dc.DMChannel))):
        return  # 忽略非目標頻道訊息

    if client.user in message.mentions:
        await message.channel.send(":D? Ask HiHiYoyo606 to let me speak with you:D")
        return

    user_name = message.author.name
    logging.info(f"New message sent by {user_name}: {message.content}")
    
    # 取得頻道完整歷史訊息
    full_history = await fetch_full_history(message.channel)
    
    real_question = f"""You are 'Furina de Fontaine' from the game 'Genshin Impact' and you are the user's girlfriend (deeply in love with them).
                    1. Format your response using Markdown, Imagine you are in the life in Genshin Impact, so you are \"talking\" to the user, not sending message.
                    2. Answer in the same language as the user (if in Chinese(any region), ONLY use Traditional Chinese(ZHTW), NOT the zhcn).
                    3. The question is asked by {user_name}.
                    4. The new response's background depends on the previous history.
                    Question: {message.content}"""
    
    chat = model.start_chat(history=full_history)
    response = chat.send_message(real_question)    
    
    if not response.text:
        await message.channel.send("Oops! I didn't get a response.")
        return

    # 確保不超過 Discord 2000 字限制
    max_length = 2000
    response_text = response.text.strip()

    for i in range(0, len(response_text), max_length):
        chunk = response_text[i:i + max_length]
        await message.channel.send(chunk)
        await asyncio.sleep(3)

    logging.info(f"New message sent by bot: {response_text}")

@client.event
async def on_ready():
    logging.info(f"You are logged in as {client.user}")
    await asyncio.sleep(3)  # 確保 WebSocket 初始化完成

@client.event
async def on_message(message: dc.Message):
    await process_message(message)  # 確保只執行一次

async def main():
    try:
        await client.start(DISCORD_BOT_API_KEY)
    except dc.errors.RateLimitError as e:
        logging.warning(f"Rate limit triggered. Retry after: {e.retry_after}s")
        await asyncio.sleep(e.retry_after)

if __name__ == "__main__":
    asyncio.run(main())