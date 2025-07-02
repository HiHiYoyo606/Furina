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
from discord.ui import View, Button
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

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=120)

        self.pages = self.generate_embeds()
        self.current = 0

        # 預設顯示第一頁
        self.message = None

    def generate_embeds(self):
        embeds = []

        # 📘 Page 1: 指令總覽
        embed1 = dc.Embed(title="指令總覽 | Commands List", color=dc.Color.blue())
        embed1.set_footer(text="Powered by HiHiYoyo606")
        for cmd, desc in {
            "/help": "顯示說明訊息 | Show the informations.",
            "/randomnumber": "抽一個區間內的數字 | Random a number.",
            "/randomcode": "生成一個亂碼 | Generate a random code.",
            "/rockpaperscissors": "和芙寧娜玩剪刀石頭布 | Play rock paper scissors with Furina.",
            "/serverinfo": "顯示伺服器資訊 | Show server information.",
            "/addchannel": "新增一個和芙寧娜對話的頻道 | Add a chat channel with Furina.",
            "/removechannel": "從名單中刪除一個頻道 | Remove a channel ID from the list.",
            "/createrole": "創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)",
            "/deleterole": "刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)",
            "/deletemessage": "刪除一定數量的訊息(需擁有管理訊息權限) | Delete a certain number of messages.(Requires manage messages permission)",
        }.items():
            embed1.add_field(name=cmd, value=desc, inline=False)
        embeds.append(embed1)

        # 🛠️ Page 2: 操作說明
        embed2 = dc.Embed(title="操作說明 | Operations", color=dc.Color.blue())
        embed2.set_footer(text="Powered by HiHiYoyo606")
        for cmd, desc in {
            "$re": "輸出`$re`以重置對話 | Send `$re` to reset the conversation.",
            "$skip": "在訊息加上前綴`$skip`以跳過該訊息 | Add the prefix `$skip` to skip the message.",
            "$ids": "查詢所有可用聊天室的ID | Check all the available chat room IDs.",
        }.items():
            embed2.add_field(name=cmd, value=desc, inline=False)
        embeds.append(embed2)

        return embeds

    @dc.ui.button(label="上一頁 Previous page", style=dc.ButtonStyle.gray)
    async def previous(self, interaction: dc.Interaction, button: Button):
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @dc.ui.button(label="下一頁 Next page", style=dc.ButtonStyle.gray)
    async def next(self, interaction: dc.Interaction, button: Button):
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

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
