import discord as dc
import google.generativeai as genai
import os
import gspread
from dotenv import load_dotenv
from discord.ext import commands
from google.oauth2.service_account import Credentials

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")
LOGGING_CHANNEL_ID = int(os.getenv("LOGGING_CHANNEL_ID")) # Log sending channel
SHEET_ID = os.getenv("SHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME")
GEMINI_VERSION = os.getenv("GEMINI_VERSION")
GOOGLE_FURINA_CHANNEL_SHEET_CSV_URL = os.getenv("GOOGLE_FURINA_CHANNEL_SHEET_CSV_URL")
GOOGLE_FURINA_ERROR_SHEET_CSV_URL = os.getenv("GOOGLE_FURINA_ERROR_SHEET_CSV_URL")
FURINA_CHANNEL_WORKSHEET_NAME=os.getenv("FURINA_CHANNEL_WORKSHEET_NAME")
FURINA_ERROR_WORKSHEET_NAME=os.getenv("FURINA_ERROR_WORKSHEET_NAME")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
with open("version.txt", "r") as f:
    VERSION = f.read().strip()

developers_id = [
    802714733219414047,
    985858138542600212,
]

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

bot, model = set_bot(), set_model()
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gs=gspread.authorize(creds)
spreadsheet=gs.open_by_key(SHEET_ID)
furina_channel_ws=spreadsheet.worksheet(FURINA_CHANNEL_WORKSHEET_NAME)
furina_error_ws=spreadsheet.worksheet(FURINA_ERROR_WORKSHEET_NAME)

if __name__ == "__main__":
    pass