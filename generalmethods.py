import string
import random
import discord as dc
import logging
import csv
import requests
from objects import all_server_queue, ws, LOGGING_CHANNEL_ID, VERSION, GOOGLE_SHEET_CSV_URL
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord import Embed

logging.basicConfig(
    level=logging.INFO,  # 或 DEBUG 適用於更詳細的日誌
    format='%(levelname)s - %(message)s'
)

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
    embed = get_general_embed(message="\n".join(embed_parts), 
                              color=[dc.Color.blue() if level == "info" else dc.Color.red()][0],
                              title=f"System Log - {level.upper()}")
    
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

def add_channel_to_gs(channel_id: str):
    ws.append_row([channel_id])

def remove_channel_from_gs(channel_id: str):
    rows = ws.get_all_values()
    header = rows[0]
    data = rows[1:]

    new_data = [
        row for row in data if row[0] != channel_id
    ]

    ws.clear()
    ws.append_row(header)
    ws.append_rows(new_data)

def get_all_channels_from_gs() -> list[int]:
    file = requests.get(GOOGLE_SHEET_CSV_URL)
    csv_content = file.content.decode("utf-8").splitlines()
    
    all_channels = []

    reader = csv.DictReader(csv_content)
    for row in reader:
        try:
            channel_id = int(row.get("channel_id", "").strip())
            all_channels.append(channel_id)
        except (ValueError, TypeError):
            continue  # 忽略轉換失敗或空值

    return all_channels


def get_general_embed(message: str | dict, 
                      color: dc.Color = dc.Color.blue(), 
                      title: str = None, 
                      icon : str = None, 
                      banner: str = None) -> Embed:
    
    embed = Embed(
        title=title,
        description=message if isinstance(message, str) else None,
        color=color,
    )
    
    if isinstance(message, dict):
        for key, value in message.items():
            embed.add_field(name=key, value=value, inline=False)
    
    if icon:
        embed.set_thumbnail(url=icon)
    if banner:
        embed.set_image(url=banner)
    
    embed.set_footer(text=f"Powered by HiHiYoyo606 | Version: {VERSION}")
    return embed

if __name__ == "__main__":
    pass