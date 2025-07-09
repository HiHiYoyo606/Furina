import string
import random
import discord as dc
import logging
import csv
import requests
import aiohttp
from objects import furina_channel_ws, furina_error_ws, developers_id, server_playing_hoyomix
from objects import LOGGING_CHANNEL_ID, VERSION, GOOGLE_FURINA_CHANNEL_SHEET_CSV_URL, GOOGLE_FURINA_ERROR_SHEET_CSV_URL
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

async def _send_log_to_discord(bot: commands.Bot, level: str, message: str, ping_admin: bool = False) -> None:
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
            pings = []
            for userid in developers_id:
                user = await bot.fetch_user(userid)
                mention = user.mention
                pings.append(mention)            
            await log_channel.send(content=" ".join(pings) if ping_admin else "", embed=embed)
        else:
            logging.warning(f"Logging channel with ID {LOGGING_CHANNEL_ID} not found.")
    except Exception as e:
        logging.exception(f"Failed to send log to Discord channel {LOGGING_CHANNEL_ID}: {e}")

async def send_new_info_logging(bot: commands.Bot, message: str, to_discord: bool = True) -> None:
    _send_log_to_main_logging("info", message)
    if to_discord:
        await _send_log_to_discord(bot, "info", message)

async def send_new_error_logging(bot: commands.Bot, message: str, to_discord: bool = True, ping_admin: bool = False) -> None:
    _send_log_to_main_logging("error", message)
    if to_discord:
        await _send_log_to_discord(bot, "error", message, ping_admin)

class GoogleSheet:
    def __init__(self):
        self.error_worksheet = furina_error_ws
        self.channel_worksheet = furina_channel_ws

    @staticmethod
    async def get_all_channels_from_gs() -> list[int]:
        async with aiohttp.ClientSession() as session:
            async with session.get(GOOGLE_FURINA_CHANNEL_SHEET_CSV_URL) as response:
                text = await response.text()
                    
        csv_content = text.splitlines()
        
        all_channels = []

        reader = csv.DictReader(csv_content)
        for row in reader:
            try:
                channel_id = int(row.get("dc_channel_id", "").strip())
                all_channels.append(channel_id)
            except (ValueError, TypeError):
                continue  # 忽略轉換失敗或空值

        return all_channels
    
    @staticmethod
    def is_hash_code_in_error_sheet(code: str) -> bool:
        file = requests.get(GOOGLE_FURINA_ERROR_SHEET_CSV_URL)
        csv_content = file.content.decode("utf-8").splitlines()
        
        all_hash_codes = []
        reader = csv.DictReader(csv_content)
        for row in reader:
            try:
                hash_code = row.get("hashcode", "").strip()
                all_hash_codes.append(hash_code)
            except (ValueError, TypeError):
                continue  # 忽略轉換失敗或空值

        return code in all_hash_codes
    
    @staticmethod
    def add_error_to_gs(content: list):
        furina_error_ws.append_row(content)

    @staticmethod
    def add_channel_to_gs(channel_id: int):
        furina_channel_ws.append_row([channel_id.__str__()])

    @staticmethod
    def remove_channel_from_gs(channel_id: int):
        rows = furina_channel_ws.get_all_values()
        header = rows[0]
        data = rows[1:]

        new_data = [
            row for row in data if row[0] != channel_id.__str__()
        ]

        furina_channel_ws.clear()
        furina_channel_ws.append_row(header)
        furina_channel_ws.append_rows(new_data)

    @staticmethod
    def remove_error_from_gs(hashcode: str):
        """
        remove error from google sheet.

        return:
            user_id: str
            channel_id: str
            guild_id: str
            error_content: str
        """
        rows = furina_error_ws.get_all_values()
        header = rows[0]
        data = rows[1:]
        hash_index = header.index("hashcode")

        user_id_index = header.index("userid")
        channel_id_index = header.index("channelid")
        content_index = header.index("content")

        user_id, channel_id, content = None, None, None
        new_data = []
        for row in data:
            if row[hash_index] == hashcode:
                user_id: str = row[user_id_index]
                channel_id: str = row[channel_id_index]
                content: str = row[content_index]
            else:
                new_data.append(row)

        furina_error_ws.clear()
        furina_error_ws.append_row(header)
        furina_error_ws.append_rows(new_data)
        return user_id, channel_id, content

async def add_error(bot: commands.Bot, interaction: dc.Interaction, content: str):
    await interaction.response.defer(thinking=True)
    hash_code = generate_random_code(8)
    while GoogleSheet.is_hash_code_in_error_sheet(hash_code):
        hash_code = generate_random_code(8)

    is_dm = isinstance(interaction.channel, dc.DMChannel)
    if is_dm:
        dm_channel = interaction.user.dm_channel or await interaction.user.create_dm()
        dm_channel_id = str(dm_channel.id)
    row = [
        content,
        interaction.user.name,
        str(interaction.user.id),
        interaction.guild.name if not is_dm else None,
        str(interaction.guild.id) if not is_dm else None,
        str(interaction.channel.id) if not is_dm else str(dm_channel_id),
        get_hkt_time(),
        hash_code
    ]
    GoogleSheet.add_error_to_gs(row)

    await interaction.followup.send("> 您的錯誤回報成功被記錄 | Your error report has been recorded successfully.")
    await send_new_error_logging(bot=bot, message=f"{interaction.user.name} has reported an error: {content}\nHashcode: {hash_code}", ping_admin=True)

async def fix_error(bot: commands.Bot, interaction: dc.Interaction, hashcode: str, hint: str = None):
    await interaction.response.defer(thinking=True)
    if interaction.user.id not in developers_id:
        await interaction.followup.send("> 此指令僅限Furina的開發者使用 | This command is only for Furina's developers.", ephemeral=True)
        return
    
    user_id, channel_id, content = GoogleSheet.remove_error_from_gs(hashcode)
    if content is None:
        await interaction.followup.send("> 錯誤不存在 | Error does not exist.")
        return

    try:
        user = await bot.fetch_user(user_id)
        channel: dc.TextChannel = await bot.fetch_channel(int(channel_id))
        fix_message = f"{user.mention}\n> 您的錯誤已修復 | Your error has been fixed.\n> 錯誤內容 | Content: {content}"
        if hint:
            fix_message += f"\n> 提示 | Hint: {hint}"
        await channel.send(fix_message)
        await interaction.followup.send("> 向使用者回報成功 | Report to user successfully.")
    except Exception as e:
        await interaction.followup.send("> 向使用者回報失敗 | Failed to report to user.")
        await send_new_error_logging(bot=bot, message=f"Failed to report to user: {e}", to_discord=False)
        return

def remove_hoyomix_status(guild: dc.Guild):
    if server_playing_hoyomix.get(guild.id):
        server_playing_hoyomix.pop(guild.id)

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