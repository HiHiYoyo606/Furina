import asyncio
import discord as dc
import google.generativeai as genai
import os
import gspread
import threading
from flask import Flask
from dotenv import load_dotenv
from discord.ext import commands
from collections import defaultdict
from google.oauth2.service_account import Credentials
from enum import Enum

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")
LOGGING_CHANNEL_ID = int(os.getenv("LOGGING_CHANNEL_ID")) # Log sending channel
SHEET_ID = os.getenv("SHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")
GEMINI_VERSION = os.getenv("GEMINI_VERSION")
GOOGLE_SHEET_CSV_URL = os.getenv("GOOGLE_SHEET_CSV_URL")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TOTAL_BLOCKS = 20
with open("version.txt", "r") as f:
    VERSION = f.read().strip()

class HoyoGames(Enum):
    GI= "Genshin Impact"
    HSR= "Honkai Star Rail"
    ZZZ= "Zenless Zone Zero"
song_file_dict = {
    "Genshin Impact": "gisongs.txt",
    "Honkai Star Rail": "hsrsongs.txt",
    "Zenless Zone Zero": "zzzsongs.txt"
}

def set_bot():
    intents = dc.Intents.default()
    intents.message_content = True  
    intents.members = True 
    bot = commands.Bot(command_prefix=None, intents=intents)
    return bot

def set_model():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_VERSION)
    return model

app = Flask(__name__)
@app.route("/")
def home():
    return "Furina is now awake! :D"
port = int(os.environ.get("PORT", 8080))
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

bot, model = set_bot(), set_model()
server_playing_hoyomix = {} # 存每個server目前是否播放Hoyo的歌
all_server_queue = defaultdict(asyncio.Queue) # MusicInfoView
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gs=gspread.authorize(creds)
spreadsheet=gs.open_by_key(SHEET_ID)
ws=spreadsheet.worksheet("Furina")

if __name__ == "__main__":
    pass