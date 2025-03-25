import discord as dc
import google.generativeai as genai
import os
import threading
import logging
import asyncio  # 加入 asyncio 避免 race condition
from dotenv import load_dotenv
from flask import Flask

logging.basicConfig(
    level=logging.INFO,  # 或 DEBUG 適用於更詳細的日誌
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
@app.route("/")
def home():
    logging.info("The flask site is connected by someone. Please ensure that Discord won't deny the connection.")
    return "Furina is now awake! :D"
port = int(os.environ.get("PORT", 8080))
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

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

async def fetch_full_history(channel: dc.TextChannel) -> list:
    """取得頻道的完整歷史訊息，並回傳陣列 (格式: [{"role": "user", "parts": "訊息內容"}])"""
    try:
        messages = []
        async for message in channel.history(limit=100):  # 限制讀取最近 100 則
            role = "user" if message.author != client.user else "model"
            messages.append({"role": role, "parts": [message.content]})

        messages.reverse()  # 讓對話順序從舊到新
        return messages
    
    except Exception as e:
        logging.error(f"Error fetching history: {e}")
        return []
    
async def ask_question(question: dc.Message) -> str:
    user_name = question.author.name
    logging.info(f"New message sent by {user_name}: {question.content}")
    
    # 取得頻道完整歷史訊息
    full_history = await fetch_full_history(question.channel)
    
    real_question = f"""You are 'Furina de Fontaine' from the game 'Genshin Impact' and you are the user's girlfriend (deeply in love with them).
                    1. Format your response using Markdown, Imagine you are in the life in Genshin Impact, so you are \"talking\" to the user, not sending message.
                    2. Answer in the same language as the user (if in Chinese(any region), ONLY use Traditional Chinese(ZHTW), NOT the zhcn).
                    3. The question is asked by {user_name}.
                    4. The new response's background depends on the previous history.
                    Question: {question.content}"""
    
    chat = model.start_chat(history=full_history)
    response = chat.send_message(real_question)
    if not response.text:
        await question.channel.send("Oops! I didn't get a response.")
        return

    return response.text

async def sent_message_to_channel(original_message: dc.Message, message_to_send: str):
    # 確保不超過 Discord 2000 字限制
    max_length = 2000
    for i in range(0, len(message_to_send), max_length):
        chunk = message_to_send[i:i + max_length]
        await original_message.channel.send(chunk)
        await asyncio.sleep(3)
    
    r_log_arr = message_to_send.split("\n\n")
    res_oneln = "\n".join(r_log_arr) + "\n"
    logging.info(f"New message sent by bot: {res_oneln}")

async def process_message(message: dc.Message):
    """處理收到的訊息並產生回應"""
    if client.user in message.mentions:
        await message.channel.send(":D? Ask HiHiYoyo606 to let me speak with you:D")
        return

    if message.author == client.user:
        return  # 忽略自己發送的訊息
    if not (message.channel.id in TARGET_CHANNEL_IDS or isinstance(message.channel, dc.DMChannel)):
        return  # 忽略非目標頻道訊息
    
    try:
        response = await ask_question(message)
        response_strip = response.strip()
        await sent_message_to_channel(message, response_strip)
    except Exception as e:
        logging.error(f"Error processing message: {e}")

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
    except dc.errors.RateLimited as e:
        logging.warning(f"Rate limit triggered. Retry after: {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await main()
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
