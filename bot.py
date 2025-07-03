import discord as dc
import os
import threading
import logging
import asyncio  # 加入 asyncio 避免 race condition
import random
from collections import defaultdict
from yt_dlp import YoutubeDL as ytdlp
from discord.app_commands import describe
from dotenv import load_dotenv
from flask import Flask
from generalmethods import *
from geminichat import chat_process_message
# from googlesearchmethods import GoogleSearchMethods

connect_time = 0
all_server_queue = defaultdict(asyncio.Queue)
load_dotenv()
DISCORD_BOT_API_KEY = os.getenv("DISCORD_BOT_API_KEY")

logging.basicConfig(
    level=logging.INFO,  # 或 DEBUG 適用於更詳細的日誌
    format='%(levelname)s - %(message)s'
)

app = Flask(__name__)
@app.route("/")
def home():
    global connect_time
    if connect_time % 5 == 0:
        asyncio.run(send_new_info_logging(bot=bot, message=f"Flask site connection No.{connect_time}", to_discord=False))
    connect_time += 1
    return "Furina is now awake! :D"
port = int(os.environ.get("PORT", 8080))
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

bot, model = set_bot()

class HelpView(dc.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

        self.pages = self.generate_embeds()
        self.current = 0

        # 預設顯示第一頁
        self.message = None

    def generate_embeds(self):
        embeds = [ 
            # 📘 Page 一般指令
            get_general_embed(message={
                "/help": "顯示說明訊息 | Show the informations.",
                "/randomnumber": "抽一個區間內的數字 | Random a number.",
                "/randomcode": "生成一個亂碼 | Generate a random code.",
                "/rockpaperscissors": "和芙寧娜玩剪刀石頭布 | Play rock paper scissors with Furina.",
                "/whois": "顯示特定成員在伺服器內的資訊 | Show a member's infomation in server.",
                "/serverinfo": "顯示伺服器資訊 | Show server information.",
                "/addchannel": "新增一個和芙寧娜對話的頻道 | Add a chat channel with Furina.",
                "/removechannel": "從名單中刪除一個頻道 | Remove a channel ID from the list.",
            }, color=dc.Color.blue(), title="一般指令 | Normal Commands"),

            # Page 語音指令
            get_general_embed(message={
                "/join": "加入語音頻道 | Join a voice channel.",
                "/leave": "離開語音頻道 | Leave a voice channel.",
                "/playyt": "播放一首Youtube歌曲 | Play a song with Youtube.",
                "/skip": "跳過當前正在播放的歌曲 | Skip the current playing song.",
                "/queue": "查詢目前序列 | Check the current queue.",
                "/clear": "清空播放序列 | Clear the play queue.",
            }, color=dc.Color.blue(), title="語音指令 | Voice Commands"),

            # Page 管理指令
            get_general_embed(message={
                "/createrole": "創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)",
                "/deleterole": "刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)",
                "/deletemessage": "刪除一定數量的訊息(需擁有管理訊息權限) | Delete a certain number of messages.(Requires manage messages permission)",
            }, color=dc.Color.blue(), title="管理指令 | Manage Commands"),

            # 🛠️ Page 操作說明
            get_general_embed(message={
                "$re": "輸出`$re`以重置對話 | Send `$re` to reset the conversation.",
                "$skip": "在訊息加上前綴`$skip`以跳過該訊息 | Add the prefix `$skip` to skip the message.",
                "$ids": "查詢所有可用聊天室的ID | Check all the available chat room IDs.",
            }, color=dc.Color.blue(), title="操作說明 | Operations")
        ]
        return embeds

    @dc.ui.button(label="上一頁 Previous page", style=dc.ButtonStyle.gray)
    async def previous(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @dc.ui.button(label="下一頁 Next page", style=dc.ButtonStyle.gray)
    async def next(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

class MemberInfoView(dc.ui.View):
    def __init__(self, user: dc.Member):
        super().__init__(timeout=120)

        self.current = 0
        self.pages = None

        # 預設顯示第一頁
        self.message = None
        return None

    async def generate_embeds(self, user: dc.Member):
        embeds = []

        infomations_page1 = {
            "用戶名稱 | User Name": user.name,
            "用戶ID | User ID": user.id,
            "加入日期 | Joined At": user.joined_at.strftime("%Y-%m-%d"),
            "創建日期 | Created At": user.created_at.strftime("%Y-%m-%d"),
            "最高身分組 | Highest Role": user.top_role.mention if user.top_role != user.guild.default_role else None,
        }
        roles = [role.mention for role in user.roles if role != user.guild.default_role]
        roles.reverse()
        roles = roles if len(roles) > 0 else None
        infomations_page2 = {
            "身分組 | Roles": "\n".join(roles) if roles else None,
        }
        user = await bot.fetch_user(user.id)
        banner = user.banner.url if user.banner else None
        icon = user.avatar.url if user.avatar else None
        embed1 = get_general_embed(infomations_page1, dc.Color.blue(), "用戶資訊 | User Information", icon=icon, banner=banner)
        embed2 = get_general_embed(infomations_page2, dc.Color.blue(), "用戶資訊 | User Information", icon=icon, banner=banner)
        embeds.append(embed1)
        embeds.append(embed2)
        self.pages = embeds

        return embeds

    @dc.ui.button(label="上一頁 Previous page", style=dc.ButtonStyle.gray)
    async def previous(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @dc.ui.button(label="下一頁 Next page", style=dc.ButtonStyle.gray)
    async def next(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)    

@bot.tree.command(name="help", description="顯示說明訊息 | Show the informations.")
async def slash_help(interaction: dc.Interaction):
    """顯示說明訊息"""
    """回傳: None"""

    view = HelpView()
    await interaction.response.send_message(
        embed=view.pages[0], view=view, ephemeral=True
    )

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /help.")
    
@bot.tree.command(name="randomnumber", description="抽一個區間內的數字 | Get a random number in a range.")
@describe(min_value="隨機數字的最小值 (預設 1) | The minimum value for the random number (default 1).")
@describe(max_value="隨機數字的最大值 (預設 100) | The maximum value for the random number (default 100).")
async def slash_random_number(interaction: dc.Interaction, min_value: int = 1, max_value: int = 100):
    """抽一個數字"""
    """回傳: None"""
    if min_value > max_value:
        await interaction.response.send_message(f"> {min_value}比{max_value}還大嗎？ | {min_value} is bigger than {max_value}?", ephemeral=False)
        return

    arr = [random.randint(min_value, max_value) for _ in range(11+45+14)] # lol
    real_r = random.choice(arr)
    await interaction.response.send_message(f"# {real_r}", ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /randomnumber with {real_r}.")

@bot.tree.command(name="randomcode", description="生成一個亂碼 | Get a random code.")
@describe(length="亂碼的長度 (預設 8) | The length of the random code (default 8).")
async def slash_random_code(interaction: dc.Interaction, length: int = 8):
    """生成一個亂碼"""
    """回傳: None"""
    await interaction.response.send_message(f"# {generate_random_code(length)}", ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /randomcode")

@bot.tree.command(name="createrole", description="創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)")
@describe(role_name="身分組的名稱 | The name of the role.")
@describe(r="rgb紅色碼(0~255 預設0) | r value (0~255, default 0).")
@describe(g="rgb綠色碼(0~255 預設0) | g value (0~255, default 0).")
@describe(b="rgb藍色碼(0~255 預設0) | b value (0~255, default 0).")
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
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.manage_roles is False:
        await interaction.response.send_message("> 你沒有管理身分組的權限 | You don't have the permission to manage roles.", ephemeral=True)
        return

    role_color = dc.Color.from_rgb(r, g, b)
    role = await interaction.guild.create_role(name=role_name, colour=role_color, hoist=hoist, mentionable=mentionable)
    await interaction.response.send_message(f"# {role.mention}", ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /createrole.")

@bot.tree.command(name="deleterole", description="刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)")
@describe(role="要刪除的身分組 | The role to be deleted.")
async def slash_delete_role(interaction: dc.Interaction, role: dc.Role):
    """刪除一個身分組"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.manage_roles is False:
        await interaction.response.send_message("> 你沒有管理身分組的權限 | You don't have the permission to manage roles.", ephemeral=True)
        return

    role_name = role.name
    await role.delete()
    await interaction.response.send_message(f"# 已刪除 {role_name}", ephemeral=False)

@bot.tree.command(name="deletemessage", description="刪除一定數量的訊息(需擁有管理訊息權限) | Delete a certain number of messages.(Requires manage messages permission)")
@describe(number="要刪除的訊息數量 | The number of messages to delete.")
async def slash_delete_message(interaction: dc.Interaction, number: int):
    """刪除一定數量的訊息"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.manage_messages is False:
        await interaction.response.send_message("> 你沒有管理訊息的權限 | You don't have the permission to manage messages.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)  # 延遲回應以保持 interaction 有效
    embed = get_general_embed(f"正在刪除 {number} 則訊息 | Deleting {number} messages.", dc.Color.red())

    await interaction.followup.send(embed=embed, ephemeral=False)
    await asyncio.sleep(2)
    await interaction.channel.purge(limit=number+1)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /deletemessage with {number} messages deleted.")

@bot.tree.command(name="whois", description="顯示特定成員在伺服器內的資訊 | Show a member's infomation in server.")
@describe(user="要查詢的用戶 | The user to be queried.")
async def slash_whois(interaction: dc.Interaction, user: dc.Member):
    """顯示特定成員在伺服器內的資訊"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    view = MemberInfoView(user)

    await interaction.response.send_message(view=view, embed=(await view.generate_embeds(user))[0], ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /whois to view {user.name}'s infomation.")

@bot.tree.command(name="serverinfo", description="顯示伺服器資訊 | Show server information.")
async def slash_server_info(interaction: dc.Interaction):
    """顯示伺服器資訊"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    infomations = {
        "伺服器名稱 | Server Name": interaction.guild.name,
        "成員數量 | Member Count": str(interaction.guild.member_count),
        "擁有者 | Owner": interaction.guild.owner.mention,
        "創建日期 | Created At": interaction.guild.created_at.strftime("%Y-%m-%d"),
        "描述 | Description": interaction.guild.description if interaction.guild.description else None,
        "身分組數量 | Role Count": str(len(interaction.guild.roles)),
        "頻道數量 | Channel Count": str(len(interaction.guild.channels)),
        "語音頻道數量 | Voice Channel Count": str(len(interaction.guild.voice_channels)),
        "文字頻道數量 | Text Channel Count": str(len(interaction.guild.text_channels)),
        "表情符號數量 | Emoji Count": str(len(interaction.guild.emojis)),
    }
    icon = interaction.guild.icon.url if interaction.guild.icon else None
    banner = interaction.guild.banner.url if interaction.guild.banner else None

    embed = get_general_embed(infomations, dc.Color.blue(), "伺服器資訊 | Server Information", icon=icon, banner=banner)

    await interaction.response.send_message(embed=embed, ephemeral=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /serverinfo to view server \"{interaction.guild.name}\".")

@bot.tree.command(name="rockpaperscissors", description="和芙寧娜玩剪刀石頭布 | Play rock paper scissors with Furina.")
@dc.app_commands.choices(choice=[
    dc.app_commands.Choice(name="石頭 Rock", value="石頭 Rock"),
    dc.app_commands.Choice(name="布 Paper", value="布 Paper"),
    dc.app_commands.Choice(name="剪刀 Scissors", value="剪刀 Scissors")
])
async def slash_rock_paper_scissors(interaction: dc.Interaction, choice: str):
    """和芙寧娜玩剪刀石頭布"""
    """回傳: None"""
    choices = ["石頭 Rock", "布 Raper", "剪刀 Scissors"]
    bot_choice = random.choice(choices)
    if choice == bot_choice:
        await interaction.response.send_message(f"> 我出...{bot_choice}...平手！ | I chose...{bot_choice}...It's a tie!", ephemeral=False)
    elif choice == "石頭 Rock" and bot_choice == "剪刀 Scissors" or choice == "布 Paper" and bot_choice == "石頭 Rock" or choice == "剪刀 Scissors" and bot_choice == "布 Saper":
        await interaction.response.send_message(f"> 我出...{bot_choice}...你贏了！ | I chose...{bot_choice}...You win!", ephemeral=False)
    else:
        await interaction.response.send_message(f"> 我出...{bot_choice}...你輸了！ | I chose...{bot_choice}...You lose!", ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /rockpaperscissors with {choice} vs {bot_choice}.")

@bot.tree.command(name="addchannel", description="新增一個和芙寧娜對話的頻道 | Add a chat channel with Furina.")
@describe(channel_id="要新增的頻道的ID(空則為當前頻道) | The ID of the channel to add(leave empty for current channel).")
async def slash_add_channel(interaction: dc.Interaction, channel_id: str = None):
    """新增一個和芙寧娜對話的頻道"""
    """回傳: None"""
    if channel_id is None:
        channel_id = str(interaction.channel.id)

    if not channel_id.isdigit():
        await interaction.response.send_message("> 別想騙我，這甚至不是數字:< | This is not a number.")
        return

    channel_list = get_all_channels_from_gs()
    if int(channel_id) not in channel_list:
        add_channel_to_gs(channel_id)
        await interaction.response.send_message(f"> ✅已新增頻道 `{channel_id}`")
    else:
        await interaction.response.send_message("> ⚠️此頻道ID 已存在", ephemeral=True)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /addchannel with {channel_id} added.")

@bot.tree.command(name="removechannel", description="從名單中刪除一個頻道ID | Remove a channel ID from the list.")
@dc.app_commands.describe(channel_id="要刪除的頻道ID(空則為當前頻道) | The ID of the channel to remove(leave empty for current channel).")
async def slash_remove_channel(interaction: dc.Interaction, channel_id: str = None):
    """從名單中刪除一個頻道ID"""
    """回傳: None"""
    if channel_id is None:
        channel_id = str(interaction.channel.id)

    if not channel_id.isdigit():
        await interaction.response.send_message("> 別想騙我，這甚至不是數字:< | This is not a number.")
        return
    try:
        all_channels = get_all_channels_from_gs()
        if int(channel_id) in all_channels:
            remove_channel_from_gs(channel_id)
            await interaction.response.send_message(f"> 🗑️已移除頻道 `{channel_id}`")
        else:
            await interaction.response.send_message("> ❌找不到此頻道 ID", ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("> ⚠️尚未建立頻道資料，無法刪除", ephemeral=True)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /removechannel with {channel_id} removed.")

@bot.tree.command(name="join", description="加入語音頻道 | Join a voice channel.")
async def slash_join(interaction: dc.Interaction):
    # 加入語音頻道
    # 回傳: None

    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return

    if interaction.user.voice is None:
        await interaction.response.send_message("> 你得先進房間我才知道去哪裡！ | You need to be in a voice channel to use this command.", ephemeral=True)
        return

    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.channel != interaction.user.voice.channel:
        await voice_client.disconnect()

    await interaction.user.voice.channel.connect()
    await interaction.response.send_message("> 我進來了~ | I joined the channel!")

@bot.tree.command(name="leave", description="離開語音頻道 | Leave a voice channel.")
async def slash_leave(interaction: dc.Interaction):
    # 離開語音頻道
    # 回傳: None

    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if not voice_client:
        await interaction.response.send_message("> 我目前不在語音頻道中 | I'm not connected to a voice channel.", ephemeral=True)
        return 

    if voice_client.is_playing():
        await interaction.channel.purge(limit=1)

    await voice_client.disconnect()
    await interaction.response.send_message("> 我走了，再見~ | Bye~~", ephemeral=False)

async def play_next(guild: dc.Guild, command_channel: dc.TextChannel = None):
    if all_server_queue[guild.id].empty():
        await command_channel.send("> 播完了，還要再加歌嗎 | Ended Playing, gonna add more?")
        return
    voice_client = guild.voice_client
    if not voice_client:
        return

    audio_url, title, thumbnail, duration = await all_server_queue[guild.id].get()
    await send_new_info_logging(bot=bot, message=f"Someone is listening music: {title}")

    embed = get_general_embed(
        message=f"**{title}**",
        color=0x1DB954,
        title="🎶正在播放 | Now Playing",
    )
    embed.set_thumbnail(url=thumbnail)
    embed.add_field(name="⏳進度 Progress", value="🔘──────────", inline=False)
    message = await command_channel.send(embed=embed)

    def update_progress_bar(progress):
        total_blocks = 10
        filled = int(progress / duration * total_blocks)
        bar = "■" * filled + "🔘" + "□" * (total_blocks - filled - 1)
        return f"{bar}  `{int(progress) // 60}m{int(progress) % 60}s / {duration // 60}m{duration % 60}s`"

    async def update_embed():
        if not voice_client.is_playing():
            await message.delete()
            return

        for i in range(0, duration, 5):
            embed.set_field_at(0, name="⏳進度 Progress", value=update_progress_bar(i), inline=False)
            await message.edit(embed=embed)
            await asyncio.sleep(5)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    voice_client.play(
        dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild, command_channel), bot.loop)
    )

    # 執行進度條更新（不會擋住主線程）
    bot.loop.create_task(update_embed())

@bot.tree.command(name="playyt", description="播放一首Youtube歌曲(新歌較高概率會被擋)")
@describe(query="關鍵字 | Keyword.")
@describe(skip="是否插播 (預設 False) | Whether to interrupt current song (default False).")
async def slash_play_a_yt_song(interaction: dc.Interaction, query: str, skip: bool = False):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return

    if interaction.user.voice is None:
        await interaction.response.send_message("> 我不知道我要在哪裡放音樂... | I don't know where to put the music...")
        return

    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.channel != interaction.user.voice.channel:
        await voice_client.disconnect()

    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    voice_client = interaction.guild.voice_client
    await interaction.response.send_message("> 我進來了~讓我找一下歌... | I joined the channel! Give me a second...")

    ydl_opts = {
        'format': 'ba/b',
        'default_search': 'ytsearch5',
        'cookiefile': './cookies.txt',
        'noplaylist': True,  # 只取單首，避免誤抓整個播放清單
        'quiet': True,
        'no_warnings': True,
        'source_address': '0.0.0.0',  # 嘗試強制本機 IP
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    def extract():
        with ytdlp(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0]
        return info
    
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, extract)
    
    audio_url = info.get('url')
    title = info.get('title', 'UNKNOWN SONG')
    thumbnail = info.get("thumbnail")
    duration = info.get("duration", 0)  # seconds

    if skip and voice_client.is_playing():
        voice_client.stop()  # trigger after callback to auto-play the inserted song

    await all_server_queue[interaction.guild.id].put((audio_url, title, thumbnail, duration))
    await interaction.edit_original_response(content=f"> 已將 **{title}** 加入佇列！| Added **{title}** to queue!")
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /playyt with {title} added to his queue.")

    if not voice_client.is_playing():
        await play_next(interaction.guild, interaction.channel)

@bot.tree.command(name="pause", description="暫停播放序列 | Pause the play queue.")
async def slash_pause(interaction: dc.Interaction):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("> 已暫停播放序列。| Paused the play queue.")

@bot.tree.command(name="skip", description="跳過當前正在播放的歌曲 | Skip the current playing song.")
async def slash_skip(interaction: dc.Interaction):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        await interaction.response.send_message("> 目前沒有歌曲正在播放。| No song is currently playing.")
        return

    voice_client.stop()
    await interaction.response.send_message("> 已跳過當前歌曲。| Skipped the current song.")
    
@bot.tree.command(name="queue", description="查詢目前序列 | Check the current queue.")
async def slash_queue(interaction: dc.Interaction):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return

    queue = all_server_queue[interaction.guild.id]
    if queue.empty():
        await interaction.response.send_message("> 播放序列是空的喔！| The queue is currently empty.")
        return

    items = list(queue)
    titles = [f"{i+1}. {title}" for i, (_, title) in enumerate(items)]
    message = "\n".join(titles)
    await interaction.response.send_message(f"🎶 當前播放序列 | Current play queue:\n{message}")
    
@bot.tree.command(name="clear", description="清空播放序列 | Clear the play queue.")
async def slash_clear(interaction: dc.Interaction):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client.is_playing():
        await interaction.channel.purge(limit=1)

    queue = all_server_queue[interaction.guild.id]
    cleared = 0
    while not queue.empty():
        queue.get_nowait()
        cleared += 1

    await interaction.response.send_message(f"> 已清空播放序列，共移除 {cleared} 首歌曲。| Cleared queue ({cleared} songs removed).")

@bot.event
async def on_ready():
    await send_new_info_logging(bot=bot, message=f"Logged in as {bot.user}, system is ready.")

    try:
        synced = await bot.tree.sync()
        await send_new_info_logging(bot=bot, message=f"Synced {len(synced)} commands.")
    except Exception as e:
        await send_new_error_logging(f"Error syncing commands: {e}")

    await asyncio.sleep(3)  # 確保 WebSocket 初始化完成

@bot.event
async def on_message(message: dc.Message):
    await chat_process_message(bot, model, message)  # 確保只執行一次

async def main():
    await bot.start(DISCORD_BOT_API_KEY)
    await send_new_info_logging(bot=bot, message=f"Bot successfully started at {get_hkt_time()}.", to_discord=False) 

if __name__ == "__main__":
    asyncio.run(main())
