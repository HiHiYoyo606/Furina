import string
import random
import discord as dc
import google.generativeai as genai
import os
import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord import Embed
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")
LOGGING_CHANNEL_ID = int(os.getenv("LOGGING_CHANNEL_ID")) # Log sending channel
GEMINI_VERSION = "gemini-2.0-flash"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gs=gspread.authorize(creds)
spreadsheet=gs.open_by_key("1BufQ57OeV8Alc4IE5pm0G_20iwm4F_q5fKGik2Sl74I")
ws=spreadsheet.worksheet("Furina")

def generate_random_code(length: int):
    """
    Generate a random code with 0~9 and letters.
    """
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choices(characters, k=length))

def get_hkt_time() -> str:
    gmt8 = timezone(timedelta(hours=8))
    gmt8_time = datetime.now(gmt8)
    return gmt8_time.strftime("%Y-%m-%d %H:%M:%S") 

def _send_log_to_main_logging(level: str, message: str) -> None:
    now_time = get_hkt_time()
    main_part = [
        f"[System Log - {level.upper()}]",
        f"\t Msg: {message}",
        f"\tTime: {now_time}",
        "[System Log End]" 
    ]
    
    full_log_message = "\n".join(main_part)

    if level == "info":
        logging.info(full_log_message)
    elif level == "error":
        logging.error(full_log_message)

async def _send_log_to_discord(bot: commands.Bot, level: str, message: str) -> None:
    """Helper function to format and send log messages to Discord and console."""
    now_time = get_hkt_time()
    embed_parts = [
        message,
        f"{now_time}",
    ]
    embed = Embed(
        colour=[dc.Color.blue() if level == "info" else dc.Color.red()][0],
        title=f"System Log - {level.upper()}",
        description="\n".join(embed_parts),
    )
    
    try:
        log_channel = bot.get_channel(LOGGING_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        else:
            logging.warning(f"Logging channel with ID {LOGGING_CHANNEL_ID} not found.")
    except Exception as e:
        logging.exception(f"Failed to send log to Discord channel {LOGGING_CHANNEL_ID}: {e}")

async def send_new_info_logging(bot: commands.Bot, message: str, to_discord: bool = True) -> None:
    _send_log_to_main_logging("info", message)
    if to_discord:
        await _send_log_to_discord(bot, "info", message)

async def send_new_error_logging(bot: commands.Bot, message: str, to_discord: bool = True) -> None:
    _send_log_to_main_logging("error", message)
    if to_discord:
        await _send_log_to_discord(bot, "error", message)

def set_bot():
    intents = dc.Intents.default()
    intents.message_content = True  
    intents.members = True 

    bot = commands.Bot(command_prefix=None, intents=intents)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_VERSION)
    return bot, model

def add_channel_to_gs(channel_id: str):
    ws.append_row([channel_id, "1"])

def remove_channel_from_gs(channel_id: str):
    records = ws.get_all_records()
    new_records = []
    for r in records:
        if r["channel_id"] == channel_id:
            r["active"] = "0"
        new_records.append(r)
    ws.clear()
    ws.extend(new_records)

def get_all_channels_from_gs():
    records = ws.get_all_records()
    return [
        int(r["channel_id"]) for r in records
        if str(r.get("active", "1")) == "1"
    ]
