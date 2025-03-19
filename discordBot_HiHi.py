import discord as dc
import google.generativeai as genai
import os
from dotenv import load_dotenv
from enum import Enum
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Successfully let Furina wake up."

port = int(os.environ.get("PORT", 8080))
import threading
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")

intents = dc.Intents.default()
intents.message_content = True  
intents.members = True 

client = dc.Client(intents=intents)
genai.configure(api_key=GEMINI_API_KEY)

TARGET_CHANNEL_IDS = [
    1351423098276282478,
    1351206275538485424,
]

class UserType(Enum):
    USER = "user"
    MODEL = "model"

async def fetch_and_process_history(channel: dc.TextChannel):
    """取得頻道的最近歷史訊息並進行總結"""
    try:
        print(f"Fetching history from channel: {channel.name}")
        messages = []
        async for message in channel.history(limit=50):  # 限制讀取最近 50 則
            messages.append(message.content)
        
        if not messages:
            return "No recent messages available."

        history_summary = f"""Summarize the following chat history in a concise way:
        {messages}
        """
        model = genai.GenerativeModel("gemini-2.0-flash")
        chat = model.start_chat(history=[])
        summary = chat.send_message(history_summary)
        return summary.text.strip()
    
    except Exception as e:
        print(f"Error fetching history: {e}")
        return "Failed to fetch history."

async def process_message(message: dc.Message):
    """處理收到的訊息並產生回應"""
    in_DM = isinstance(message.channel, dc.DMChannel)
    if message.channel.id in TARGET_CHANNEL_IDS or in_DM:
        if client.user in message.mentions:
            await message.channel.send(":D? Ask HiHiYoyo606 to let me speak with you:D")
            return
            
        if message.author == client.user:
            return

        user_name = message.author.nick if message.author.nick else message.author.name
        
        # 取得頻道最近的聊天摘要
        history_summary = await fetch_and_process_history(message.channel)

        real_question = f"""Please answer this question, assume you are the character \"Furina de Fontaine\" in the game "Genshin Impact" and you are the user's gf(the stage that you love he/she so hard), to answer this question. 
                        1. Please remember that you are in discord, so if any pattern is needed, use MarkDown pattern. 
                        2. Answer the question in the language used by user (if is zh, use zhtw instead of zhcn), if user didn't ask you to use others. 
                        3. The question is asked by {user_name}. Users might tell you who they are or their other name.
                        4. Consider the recent discussion in the channel: {history_summary}
                        Qusetion: {message.content}"""
        
        # 確保新的 chat session，避免舊歷史影響輸出
        model = genai.GenerativeModel("gemini-2.0-flash")
        chat = model.start_chat(history=[])  # 每次對話都初始化
        
        response = chat.send_message(real_question)
        max_length = 2000
        response_text = response.text

        for i in range(0, len(response_text), max_length):
            chunk = response_text[i:i + max_length]
            await message.channel.send(chunk)

@client.event
async def on_ready():
    print(f"You are logged in as {client.user}")

@client.event
async def on_message(message: dc.Message):
    await process_message(message)

client.run(DISCORD_BOT_API_KEY)
