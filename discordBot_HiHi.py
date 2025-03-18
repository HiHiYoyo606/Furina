import discord as dc
import google.generativeai as genai
import os
from dotenv import load_dotenv
from enum import Enum
from flask import Flask

#ignroe thus part
app = Flask(__name__)
@app.route("/")
def home():
    return "This port is just a placeholder for Render."
port = int(os.environ.get("PORT", 8080))
import threading
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")

intents = dc.Intents.default()
intents.message_content = True  # Enable message content intent
intents.members = True 

client = dc.Client(intents=intents)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat(history=[])

TARGET_CHANNEL_IDS = [
    1351068939173498943,
    1351206275538485424,
]

class UserType(Enum):
    USER = "user"
    MODEL = "model"

def add_content_record(message: str, user_type: UserType):
    chat.history.append({
        "role": user_type.value,
        "parts": [message]
    })    

async def fetch_and_process_history(channel: dc.TextChannel):
    try:
        print(f"Fetching history from channel: {channel.name}")
        async for message in channel.history(limit=300):
            add_content_record(message.content, UserType.USER)
            # You can also process messages here, e.g., summarize them
        print(f"Finished fetching history from {channel.name}.")
    except Exception as e:
        print(f"Error fetching history: {e}")

@client.event
async def on_ready():
    print(f"You are logged in as {client.user}")

@client.event
async def on_message(message: dc.Message):
    in_DM = isinstance(message.channel, dc.DMChannel)
    if message.channel.id in TARGET_CHANNEL_IDS or in_DM:
        if client.user in message.mentions:
            await message.channel.send(":D? Ask HiHiYoyo606 to let me speak with you:D")
            return
            
        if message.author == client.user or message.author.bot:
            return

        user_name = ""
        if not in_DM:
            user_name = message.author.nick if message.author.nick else message.author.name
        else:
            user_name = message.author.name

        chat.history = []
        await fetch_and_process_history(message.channel)
        add_content_record(message.content, UserType.USER)
        real_question = f"""Please answer this question, assume you are the character \"Furina de Fontaine\" in the game "Genshin Impact" and you are the user's gf, to answer this question. 
                        1. Please remember that you are in discord, so if any pattern is needed, use MarkDown pattern. Also, if you need to express the feelings, use emoji, emotes and emoji-text instead of describing it.
                        2. Answer the question in the language used by user (if is zh, use zhtw instead of zhcn), if user didn't ask you to use others. 
                        3. The question is asked by {user_name}. 
                        Qusetion: {message.content}"""
        response = chat.send_message(real_question)
            
        max_length = 2000
        response_text = response.text
        for i in range(0, len(response_text), max_length):
            chunk = response_text[i:i + max_length]
            await message.channel.send(chunk)
        
        add_content_record(response.text, UserType.MODEL)

client.run(DISCORD_BOT_API_KEY)
