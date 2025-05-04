import discord as dc
import google.generativeai as genai
import os
import threading
import logging
import time
import asyncio  # 加入 asyncio 避免 race condition
import random
import yt_dlp
from discord.ext import commands
from discord import Embed
from discord.app_commands import describe
from dotenv import load_dotenv
from flask import Flask
from datetime import datetime, timedelta, timezone
    
connect_time = 0
TARGET_CHANNEL_IDS = [
    1351423098276282478, 
    1351206275538485424, 
    1351241107190710292,
]
GEMINI_VERSION = "gemini-2.0-flash"
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")

logging.basicConfig(
    level=logging.INFO,  # 或 DEBUG 適用於更詳細的日誌
    format='%(levelname)s - %(message)s'
)

def generate_random_code(length: int):
    """
    Generate a random code with 0~9 and letters.
    """
    c = ""
    for i in range(length):
        c += random.choice("0123456789abcdefghijklmnopqrstuvwxyz")
    return c

def get_hkt_time() -> str:
    gmt8 = timezone(timedelta(hours=8))
    gmt8_time = datetime.now(gmt8)
    return gmt8_time.strftime("%Y-%m-%d %H:%M:%S") 

def send_new_info_logging(message: str) -> None:
    new_info = [
        "",
        "[]--------[System Log]--------[]",
        f"\t Msg: {message}",
        f"\tSign: {generate_random_code(7)}",
        "[]--------[System Log]--------[]"
    ]

    logging.info("\n".join(new_info))

app = Flask(__name__)
@app.route("/")
def home():
    global connect_time
    if connect_time % 5 == 0:
        send_new_info_logging(f"Flask site connection No.{connect_time}")
    connect_time += 1
    return "Furina is now awake! :D"
port = int(os.environ.get("PORT", 8080))
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

def set_bot():
    intents = dc.Intents.default()
    intents.message_content = True  
    intents.members = True 

    bot = commands.Bot(command_prefix=None, intents=intents)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_VERSION)
    return bot, model
bot, model = set_bot()

async def chat_fetch_full_history(channel: dc.TextChannel, retry_attempts: int = 0) -> list:
    """取得頻道的完整歷史訊息"""
    """回傳: [{"role": "user", "parts": "訊息內容"}]..."""
    try:
        history, messages = channel.history(limit=100), []
        async for message in history:  # 限制讀取最近 100 則
            if message.content.startswith("$re"):
                break
            
            if message.content.startswith("$skip"):
                continue
            if message.interaction_metadata is not None:
                continue
            
            role = "user" if message.author != bot.user else "model"
            messages.append({"role": role, "parts": [message.content]})

        messages.reverse()  # 讓對話順序從舊到新
        return messages
    
    except dc.HTTPException as e:
        if e.status != 429:
            logging.error(f"HTTP error fetching history: {e.status} - {e.text}")
            return []
        
        retry_after = int(e.response.headers.get("Retry-After", 1))
        logging.warning(f"The request reached the rate limit! Retrying in {retry_after} seconds.")
        
        # 增加一點緩衝時間，避免剛好在邊界又觸發
        await asyncio.sleep(retry_after + 1)
        retry_attempts += 1
        return await chat_fetch_full_history(channel, retry_attempts)
    
    except Exception as e:
        logging.error(f"Error fetching history: {e}")
        return []
    
async def chat_ask_question(question: dc.Message) -> str:
    """啟用Gemini詢問問題並回傳答案"""
    """回傳: 詢問的答案(string)"""

    user_name = question.author.name
    send_new_info_logging(f"{user_name} has sent a question at {get_hkt_time()}")
    full_history = await chat_fetch_full_history(question.channel)
    
    question_list = [
        "You are \'Furina de Fontaine\' from the game \'Genshin Impact\'.",
        " and you are the user's girlfriend (deeply in love with them).",
        "1. Format your response using Markdown. You are talking to them, not sending them message.",
        "2. Answer in the same language as the user ",
        "(if your response is in 中文,  you can ONLY USE 繁體中文-台灣(ZHTW), NOT ALLOWED TO USE the zhcn).",
        f"3. The question is asked by {user_name}.",
        "4. The new response's background depends on the previous history.",
        "5. It's better not to say too much sentence in one message, ",
        "you can wait the user provide more questions.",
        f"Question: {question.content}"
    ]

    real_question = "".join(question_list)
    chat = model.start_chat(history=full_history)
    response = chat.send_message(real_question)

    return response.text

async def chat_sent_message_to_channel(original_message: dc.Message, message_to_send: str) -> None:
    """確保不超過 Discord 2000 字限制下發送訊息"""
    """回傳: None"""
    
    max_length = 2000
    for i in range(0, len(message_to_send), max_length):
        chunk = message_to_send[i:i + max_length]
        await original_message.channel.send(chunk)
        await asyncio.sleep(3)
    
    send_new_info_logging(f"Bot successfully sent message at {get_hkt_time()}")

async def chat_process_message(message: dc.Message) -> None:
    """處理收到的訊息並產生回應"""
    """回傳: None"""

    if message.author == bot.user:
        return  # 忽略自己發送的訊息
    if not (message.channel.id in TARGET_CHANNEL_IDS or isinstance(message.channel, dc.DMChannel)):
        return  # 忽略非目標頻道訊息
    if message.content.startswith("$skip") or message.content.startswith("$re"):
        return  # 忽略 $skip 指令
    
    try:
        response = await chat_ask_question(message)
        response_strip = response.strip()
        if not response_strip:
            await message.channel.send("Oops! I didn't get a response.")
            raise Exception("Empty response")
        
        await chat_sent_message_to_channel(message, response_strip)
    except Exception as e:
        logging.error(f"Error processing message: {e}")

@bot.tree.command(name="help", description="顯示說明訊息 | Show the informations.")
async def slash_help(interaction: dc.Interaction):
    """顯示說明訊息"""
    """回傳: None"""
    commands_embed = Embed(
        title="指令說明 | Help",
        color=dc.Color.blue(),
    )
    commands_list = {
        "/help": "顯示說明訊息 | Show the informations.",
        "/status": "確認芙寧娜是否在線 | Check if Furina is online.",
        "/randomnumber": "抽一個區間內的數字 | Random a number.",
        "/randomcode": "生成一個亂碼 | Generate a random code.",
        "/createrole": "創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)",
        "/deleterole": "刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)",
        "/deletemessage": "刪除一定數量的訊息 | Delete a certain number of messages.",
        "/serverinfo": "顯示伺服器資訊 | Show server information.",
        "/musicplay": "播放音樂 | Play music."
    }
    commands_embed.set_footer(text=f"Powered by HiHiYoyo606.")
    for command, description in commands_list.items():
        commands_embed.add_field(name=command, value=description, inline=False)
    
    operation_embed = Embed(
        title="操作說明 | Help",
        color=dc.Color.blue(),
    )
    operation_list = {
        "$re": "輸出`$re`以重置對話 | Send `$re` to reset the conversation.",
        "$skip": "在訊息加上前綴`$skip`以跳過該訊息 | Add the prefix `$skip` to skip the message.",
    }
    operation_embed.set_footer(text=f"Powered by HiHiYoyo606.")
    for command, description in operation_list.items():
        operation_embed.add_field(name=command, value=description, inline=False)

    await interaction.response.send_message(embeds=[commands_embed, operation_embed], ephemeral=True)
    send_new_info_logging(f"Someone has asked for Furina's help at {get_hkt_time()}")

@bot.tree.command(name="status", description="確認芙寧娜是否在線 | Check if Furina is online.")
async def slash_status(interaction: dc.Interaction):
    """確認芙寧娜是否在線"""
    """回傳: None"""
    await interaction.response.send_message("# :white_check_mark::droplet:", ephemeral=True)
    send_new_info_logging(f"Someone has checked Furina's status at {get_hkt_time()}")

@bot.tree.command(name="randomnumber", description="抽一個區間內的數字 | Get a random number in a range.")
@describe(min_value="隨機數字的最小值 (預設 1) | The minimum value for the random number (default 1).")
@describe(max_value="隨機數字的最大值 (預設 100) | The maximum value for the random number (default 100).")
async def slash_random_number(interaction: dc.Interaction, min_value: int = 1, max_value: int = 100):
    """抽一個數字"""
    """回傳: None"""
    arr = [random.randint(min_value, max_value) for _ in range(11+45+14)] # lol
    real_r = random.choice(arr)
    await interaction.response.send_message(f"# {real_r}", ephemeral=False)
    send_new_info_logging(f"Someone has asked for a random number at {get_hkt_time()}")

@bot.tree.command(name="randomcode", description="生成一個亂碼 | Get a random code.")
@describe(length="亂碼的長度 (預設 8) | The length of the random code (default 8).")
async def slash_random_code(interaction: dc.Interaction, length: int = 8):
    """生成一個亂碼"""
    """回傳: None"""
    await interaction.response.send_message(f"# {generate_random_code(length)}", ephemeral=False)
    send_new_info_logging(f"Someone has asked for a random code at {get_hkt_time()}")

@bot.tree.command(name="createrole", description="創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)")
@describe(role_name="身分組的名稱 | The name of the role.")
@describe(r="rgb紅色碼(0~255 預設255) | r value (0~255, default 0).")
@describe(g="rgb綠色碼(0~255 預設255) | g value (0~255, default 0).")
@describe(b="rgb藍色碼(0~255 預設255) | b value (0~255, default 0).")
@describe(hoist="是否分隔顯示(預設不分隔) | Whether to hoist the role (default False).")
@describe(mentionable="是否可提及(預設是) | Whether the role can be mentioned (default True).")
async def slash_create_role(interaction: dc.Interaction, 
                   role_name: str, 
                   r: int = 0,
                   g: int = 0,
                   b: int = 0,
                   hoist: bool = False, 
                   mentionable: bool = True):
    """創建一個身分組"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.manage_roles is False:
        await interaction.response.send_message("你沒有管理身分組的權限 | You don't have the permission to manage roles.", ephemeral=True)
        return

    role_color = dc.Colour.from_rgb(r, g, b)
    role = await interaction.guild.create_role(name=role_name, colour=dc.Colour(role_color), hoist=hoist, mentionable=mentionable)
    await interaction.response.send_message(f"# {role.mention}", ephemeral=False)
    send_new_info_logging(f"Someone has created a role at {get_hkt_time()} in his/her server.")

@bot.tree.command(name="deleterole", description="刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)")
@describe(role="要刪除的身分組 | The role to be deleted.")
async def slash_delete_role(interaction: dc.Interaction, role: dc.Role):
    """刪除一個身分組"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.manage_roles is False:
        await interaction.response.send_message("你沒有管理身分組的權限 | You don't have the permission to manage roles.", ephemeral=True)
        return

    role_name = role.name
    await role.delete()
    await interaction.response.send_message(f"# 已刪除 {role_name}", ephemeral=False)

@bot.tree.command(name="deletemessage", description="刪除一定數量的訊息 | Delete a certain number of messages.")
@describe(number="要刪除的訊息數量 | The number of messages to delete.")
async def slash_delete_message(interaction: dc.Interaction, number: int):
    """刪除一定數量的訊息"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return

    await interaction.channel.purge(limit=number)

    embed = Embed(
        title=f"已刪除 {number} 則訊息. | Deleted {number} messages.",
        color=dc.Color.red()
    )
    embed.set_footer(text=f"Powered by HiHiYoyo606.")
    await interaction.response.send_message(embed=embed, ephemeral=False)
    send_new_info_logging(f"Someone deleted {number} messages in a channel at {get_hkt_time()}.", ephemeral=False)

@bot.tree.command(name="serverinfo", description="顯示伺服器資訊 | Show server information.")
async def slash_server_info(interaction: dc.Interaction):
    """顯示伺服器資訊"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    server_name = interaction.guild.name
    member_count = interaction.guild.member_count
    owner = interaction.guild.owner
    create_at = interaction.guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
    description = interaction.guild.description
    icon = interaction.guild.icon.url if interaction.guild.icon else None
    banner = interaction.guild.banner.url if interaction.guild.banner else None

    embed = dc.Embed(
        title="伺服器資訊 | Server Information",
        color=dc.Color.blue()
    )
    embed.set_thumbnail(url=icon)
    embed.add_field(name="伺服器名稱 | Server Name", value=server_name, inline=False)
    embed.add_field(name="成員數量 | Member Count", value=str(member_count), inline=False)
    embed.add_field(name="擁有者 | Owner", value=owner.mention, inline=False)
    embed.add_field(name="創建日期 | Created At", value=create_at, inline=False)
    embed.add_field(name="描述 | Description", value=description, inline=False)
    if banner:
        embed.set_image(url=banner)
    embed.set_footer(text=f"Powered by HiHiYoyo606.")

    await interaction.response.send_message(embed=embed, ephemeral=False)
    send_new_info_logging(f"Someone has asked for server information at {get_hkt_time()}")

queues = {}
# yt-dlp options: best audio, don't download playlist if URL is a playlist link, suppress output, auto-search
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'auto'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
SONG_INFO_KEYS = ['url', 'title', 'requester'] # Define keys for song info dict

async def play_next_song(guild_id: int):
    """Plays the next song in the queue for the given guild."""
    if guild_id not in queues or not queues[guild_id]:
        logging.info(f"佇列為空，停止播放。")
        return
    
    guild = bot.get_guild(guild_id)
    if not guild:
        logging.warning(f"Guild {guild_id} not found, 清理佇列。")
        queues.pop(guild_id, None)
        return

    voice_client = guild.voice_client
    if not voice_client:
        logging.warning(f"語音客戶端未連接，清理佇列。")
        queues.pop(guild_id, None)
        return

    song_info = queues[guild_id].pop(0) if queues[guild_id] else None
    if not song_info:
        logging.info(f"無歌曲可播放。")
        return

    url = song_info.get('url', None)
    title = song_info.get('title', '未知歌曲')

    try:
        source = dc.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        def next_song_callback(error):
            asyncio.ensure_future(play_next_song_callback(guild_id, error))
        voice_client.play(source, after=next_song_callback)
        logging.info(f"🎶 正在播放: {title}")
    except Exception as e:
        logging.error(f"播放時發生錯誤: {e}")
        await play_next_song(guild_id)

async def play_next_song_callback(guild_id: int, error=None):
    """Callback function for play_next_song."""
    if error:
        logging.error(f'播放錯誤: {error}')
    await play_next_song(guild_id)

@bot.tree.command(name="musicplay", description="播放音樂 | Play music.")
async def slash_music_play(interaction: dc.Interaction, url_or_keyword: str):
    """播放音樂指令"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("指令只能在伺服器中使用", ephemeral=True)
        return

    if interaction.user.voice is None:
        await interaction.response.send_message("請先加入語音頻道", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client
    guild_id = interaction.guild.id

    if voice_client is None:
        try:
            voice_client = await voice_channel.connect()
        except dc.errors.ClientException:
            logging.error("機器人已在語音頻道，無法重新連線。")
            return
        except Exception as e:
            await interaction.followup.send(f"無法加入語音頻道: {e}")
            logging.error(f"Failed to connect: {e}")
            return
    elif voice_client.channel != voice_channel:
        try:
            await voice_client.disconnect()
            await voice_channel.connect()
        except Exception as e:
            await interaction.followup.send(f"無法移動到語音頻道: {e}")
            logging.error(f"Failed to move: {e}")
            return

    await interaction.response.defer()

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url_or_keyword, download=False)
            if '_type' in info and info['_type'] == 'playlist' and info.get('entries'):
                info = info['entries'][0]
            elif not info.get('entries'):
                await interaction.followup.send(f"找不到 '{url_or_keyword}' 的歌曲。")
                return

            song_info = {'url': info['url'], 'title': info.get('title', '未知歌曲')}
        
        if voice_client.is_playing() or voice_client.is_paused():
            queues.setdefault(guild_id, []).append(song_info)
            await interaction.followup.send(f"✅ 已將 **{song_info['title']}** 加入佇列。")
        else:
            queues[guild_id] = [song_info]
            await play_next_song(guild_id)
            await interaction.followup.send(f"🎶 正在播放: **{song_info['title']}**")
    except yt_dlp.utils.DownloadError as e:
        await interaction.followup.send(f"無法取得歌曲資訊，請稍後再試。\n錯誤: {e}")
    except Exception as e:
        await interaction.followup.send(f"發生未預期的錯誤: {e}")


"""
@bot.tree.command(name="timeout", description="使一個用戶被停權(需擁有對成員停權權限) | Timeout a user in a text channel(Requires timeout members permission).")
@describe(user="要停權的用戶 | The user to be timed out.")
@describe(s="停權秒數 | The number of seconds to timeout.")
@describe(reason="停權原因 | The reason for timeout.")
async def text_mute(interaction: dc.Interaction, user: dc.Member, s: int, reason: str):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.moderate_members is False:
        await interaction.response.send_message("你沒有管理成員的權限 | You don't have the permission to manage members.", ephemeral=True)
        return
    
    await user.timeout(datetime.now() + timedelta(seconds=s), reason=reason)
    await interaction.response.send_message(f"# 水神的懲罰!! {user} 被停權 {s} 秒!! 原因: {reason}")
    send_new_info_logging(f"Someone is timed out at {get_hkt_time()}.")
"""
    
@bot.event
async def on_ready():
    logging.info(f"You are logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        send_new_info_logging(f"Synced {len(synced)} commands")
    except Exception as e:
        logging.error(f"Error syncing commands: {e}")

    await asyncio.sleep(3)  # 確保 WebSocket 初始化完成

@bot.event
async def on_message(message: dc.Message):
    await chat_process_message(message)  # 確保只執行一次

async def main():
    try:
        await bot.start(DISCORD_BOT_API_KEY)
        send_new_info_logging(f"Bot successfully started at {get_hkt_time()}") 
    except dc.HTTPException as e:
        if e.status == 429:
            retry_after = e.response.headers.get("Retry-After")
            logging.warning(f"Rate limited! Retry after {retry_after} seconds.")
            # what? \
            await asyncio.sleep(delay=int(retry_after))
            return await main()

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
