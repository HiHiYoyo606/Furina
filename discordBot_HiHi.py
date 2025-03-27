import discord as dc
import google.generativeai as genai
import os
import threading
import logging
import time
import asyncio  # 加入 asyncio 避免 race condition
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

logging.basicConfig(
    level=logging.INFO,  # 或 DEBUG 適用於更詳細的日誌
    format='%(asctime)s - %(levelname)s - %(message)s'
)
time.timezone = "Asia/Taipei"

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

bot = commands.Bot(command_prefix='!', intents=intents)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

TARGET_CHANNEL_IDS = [
    1351423098276282478, 
    1351206275538485424, 
    1351241107190710292,
]

async def fetch_full_history(channel: dc.TextChannel) -> list:
    """取得頻道的完整歷史訊息"""
    """回傳: [{"role": "user", "parts": "訊息內容"}]..."""
    try:
        messages = []
        async for message in channel.history(limit=100):  # 限制讀取最近 100 則
            if message.content.startswith("$re"):
                break
            
            if message.content.startswith("$skip"):
                continue
            if message.interaction is not None:
                continue
            
            role = "user" if message.author != bot.user else "model"
            messages.append({"role": role, "parts": [message.content]})

        messages.reverse()  # 讓對話順序從舊到新
        return messages
    
    except Exception as e:
        logging.error(f"Error fetching history: {e}")
        return []
    
async def ask_question(question: dc.Message) -> str:
    """啟用Gemini詢問問題並回傳答案"""
    """回傳: 詢問的答案(string)"""

    user_name = question.author.name
    logging.info(f"{user_name} has sent a question at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    full_history = await fetch_full_history(question.channel)
    
    real_question = f"""You are 'Furina de Fontaine' from the game 'Genshin Impact' and you are the user's girlfriend (deeply in love with them).
                    1. Format your response using Markdown, Imagine you are in the life in Genshin Impact, so you are \"talking\" to the user, not sending message.
                    2. Answer in the same language as the user (if your response is in 中文,  you can ONLY USE 繁體中文-台灣(ZHTW), NOT ALLOWED TO USE the zhcn).
                    3. The question is asked by {user_name}.
                    4. The new response's background depends on the previous history.
                    Question: {question.content}"""
    
    chat = model.start_chat(history=full_history)
    response = chat.send_message(real_question)

    return response.text

async def sent_message_to_channel(original_message: dc.Message, message_to_send: str) -> None:
    """確保不超過 Discord 2000 字限制下發送訊息"""
    """回傳: None"""
    
    max_length = 2000
    for i in range(0, len(message_to_send), max_length):
        chunk = message_to_send[i:i + max_length]
        await original_message.channel.send(chunk)
        await asyncio.sleep(3)
    
    logging.info(f"Bot successfully sent message at {time.strftime('%Y-%m-%d %H:%M:%S')}")

async def process_message(message: dc.Message) -> None:
    """處理收到的訊息並產生回應"""
    """回傳: None"""

    if bot.user in message.mentions:
        await message.channel.send(":D? Ask HiHiYoyo606 to let me speak with you:D")
        return

    if message.author == bot.user:
        return  # 忽略自己發送的訊息
    if not (message.channel.id in TARGET_CHANNEL_IDS or isinstance(message.channel, dc.DMChannel)):
        return  # 忽略非目標頻道訊息
    
    try:
        response = await ask_question(message)
        response_strip = response.strip()
        if not response_strip:
            await message.channel.send("Oops! I didn't get a response.")
            raise Exception("Empty response")
        
        await sent_message_to_channel(message, response_strip)
    except Exception as e:
        logging.error(f"Error processing message: {e}")

@bot.tree.command(name="help", description="顯示說明訊息 | Show the informations.")
async def help(interaction: dc.Interaction):
    """顯示說明訊息"""
    """回傳: None"""
    help_message = """
    以下是可用的指令 | The following commands are available:
    - `/help`
    ```顯示此說明訊息 | Show this help message.```

    以下是一些操作 | The following operations are available:
    - 如果你想重置對話，請輸出`$re` | Send `$re` to reset the conversation.
    - 如果你想要忽略特定訊息，請在訊息前面加上`$skip` | Add `$skip' before the message you want to skip.
    """
    await interaction.response.send_message(help_message, ephemeral=True)

@bot.event
async def on_ready():
    logging.info(f"You are logged in as {bot.user}")
    await asyncio.sleep(3)  # 確保 WebSocket 初始化完成

@bot.event
async def on_message(message: dc.Message):
    await process_message(message)  # 確保只執行一次

async def main():
    try:
        await bot.start(DISCORD_BOT_API_KEY)
    except dc.errors.RateLimited as e:
        logging.warning(f"Rate limit triggered. Retry after: {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await main()
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
