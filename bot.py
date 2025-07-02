import discord as dc
import os
import threading
import logging
import asyncio  # 加入 asyncio 避免 race condition
import random
from discord import Embed, app_commands
from discord.app_commands import describe
from dotenv import load_dotenv
from flask import Flask
from generalmethods import *
from geminichat import chat_process_message
# from googlesearchmethods import GoogleSearchMethods

connect_time = 0
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
        "/randomnumber": "抽一個區間內的數字 | Random a number.",
        "/randomcode": "生成一個亂碼 | Generate a random code.",
        "/rockpaperscissors": "和芙寧娜玩剪刀石頭布 | Play rock paper scissors with Furina.",
        "/serverinfo": "顯示伺服器資訊 | Show server information.",
        "/addchannel": "新增一個和芙寧娜對話的頻道 | Add a chat channel with Furina.",
        "/removechannel": "從名單中刪除一個頻道 | Remove a channel ID from the list.",
        "/createrole": "創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)",
        "/deleterole": "刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)",
        "/deletemessage": "刪除一定數量的訊息(需擁有管理訊息權限) | Delete a certain number of messages.(Requires manage messages permission)",
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
        "$ids": "查詢所有可用聊天室的ID | Check all the available chat room IDs.",
    }
    operation_embed.set_footer(text=f"Powered by HiHiYoyo606.")
    for command, description in operation_list.items():
        operation_embed.add_field(name=command, value=description, inline=False)

    await interaction.response.send_message(embeds=[commands_embed, operation_embed], ephemeral=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /help.")

"""
@bot.tree.command(name="status", description="確認芙寧娜是否在線 | Check if Furina is online.")
async def slash_status(interaction: dc.Interaction):
    # 確認芙寧娜是否在線
    # 回傳: None
    await interaction.response.send_message("# :white_check_mark::droplet:", ephemeral=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /status")
"""
    
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
    embed = Embed(
        title=f"正在刪除 {number} 則訊息 | Deleting {number} messages.",
        color=dc.Color.red()
    )
    embed.set_footer(text=f"Powered by HiHiYoyo606.")
    await interaction.followup.send(embed=embed, ephemeral=False)
    await asyncio.sleep(2)
    await interaction.channel.purge(limit=number+1)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /deletemessage with {number} messages deleted.")

@bot.tree.command(name="serverinfo", description="顯示伺服器資訊 | Show server information.")
async def slash_server_info(interaction: dc.Interaction):
    """顯示伺服器資訊"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    server_name = interaction.guild.name
    member_count = interaction.guild.member_count
    owner = interaction.guild.owner
    create_at = interaction.guild.created_at.strftime("%Y-%m-%d")
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
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /serverinfo to view server \"{server_name}\".")

@bot.tree.command(name="rockpaperscissors", description="和芙寧娜玩剪刀石頭布 | Play rock paper scissors with Furina.")
@app_commands.choices(choice=[
    app_commands.Choice(name="石頭 Rock", value="rock"),
    app_commands.Choice(name="布 Paper", value="paper"),
    app_commands.Choice(name="剪刀 Scissors", value="scissors")
])
async def slash_rock_paper_scissors(interaction: dc.Interaction, choice: str):
    """和芙寧娜玩剪刀石頭布"""
    """回傳: None"""
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    if choice == bot_choice:
        await interaction.response.send_message(f"我出...{bot_choice}...平手！ | I chose...{bot_choice}...It's a tie!", ephemeral=False)
    elif choice == "rock" and bot_choice == "scissors" or choice == "paper" and bot_choice == "rock" or choice == "scissors" and bot_choice == "paper":
        await interaction.response.send_message(f"我出...{bot_choice}...你贏了！ | I chose...{bot_choice}...You win!", ephemeral=False)
    else:
        await interaction.response.send_message(f"我出...{bot_choice}...你輸了！ | I chose...{bot_choice}...You lose!", ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /rockpaperscissors with {choice} vs {bot_choice}.")

@bot.tree.command(name="addchannel", description="新增一個和芙寧娜對話的頻道 | Add a chat channel with Furina.")
@describe(channel_id="要新增的頻道的ID | The ID of the channel to add.")
async def slash_add_channel(interaction: dc.Interaction, channel_id: str):
    """新增一個和芙寧娜對話的頻道"""
    """回傳: None"""
    channel_list = get_all_channels_from_gs()
    if int(channel_id) not in channel_list:
        add_channel_to_gs(channel_id)
        await interaction.response.send_message(f"> ✅已新增頻道 `{channel_id}`")
    else:
        await interaction.response.send_message("> ⚠️此頻道 ID 已存在", ephemeral=True)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /addchannel with {channel_id} added.")

@bot.tree.command(name="removechannel", description="從名單中刪除一個頻道 ID | Remove a channel ID from the list.")
@dc.app_commands.describe(channel_id="要刪除的頻道 ID | The ID of the channel to remove.")
async def slash_remove_channel(interaction: dc.Interaction, channel_id: str):
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

# maybe music features
"""
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
async def slash_join(interaction: dc.Interaction):
    # 離開語音頻道
    # 回傳: None

    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if not voice_client:
        await interaction.response.send_message("> 我目前不在語音頻道中 | I'm not connected to a voice channel.", ephemeral=True)
        return 

    await voice_client.disconnect()
    await interaction.response.send_message("> 我走了，再見~ | Bye~~", ephemeral=False)

@bot.tree.command(name="playsc", description="播放一首SoundCloud歌曲 | Play a song with SoundCloud.")
@describe(query="關鍵字 | Keyword.")
async def slash_play_a_soundcloud_song(interaction: dc.Interaction, query: str):
    # 播放一首SoundCloud歌曲
    # 回傳: None

    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if interaction.user.voice is None:
        await interaction.response.send_message("> 我不知道我要在哪裡放音樂... | I don't know where to put the music...")
        return
    
    # user and bot are not in the same channel
    if voice_client and voice_client.channel != interaction.user.voice.channel:
        await voice_client.disconnect()

    # connect to user's channel
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    voice_client = interaction.guild.voice_client
    await interaction.response.send_message("> 我進來了~開始播放~ | I joined the channel! Playing song now!")

    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'scsearch10'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        entries = [e for e in info.get('entries', []) if e.get('url') and 'soundcloud.com' in e.get('webpage_url', '')]

    if not entries:
        await interaction.edit_original_response(content="> 找不到可播放的SoundCloud音樂 | Cannot find playable SoundCloud song.")
        return

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        audio_url = info.get('url')
        title = info.get('title', 'ERROR: UNKNOWN SONG')
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    class SoundCloudChooser(dc.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.index = 0
            self.message = None

        async def update(self):
            entry = entries[self.index]
            title = entry['title']
            url = entry['webpage_url']
            await self.message.edit(content=f"🎵 候選曲目 {self.index + 1}/{len(entries)}：**[{title}]({url})**", view=self)

        @dc.ui.button(label="播放", style=dc.ButtonStyle.success)
        async def play(self, interaction2: dc.Interaction, button: dc.ui.Button):
            entry = entries[self.index]
            title = entry['title']
            audio_url = entry['url']

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }

            voice_client.play(
                dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    interaction.edit_original_response(content="> ✅ 播放完畢！"),
                    bot.loop
                )
            )
            await self.message.edit(content=f"> ▶️ 正在播放：**{title}**", view=None)

        @dc.ui.button(label="下一首 | Next", style=dc.ButtonStyle.primary)
        async def next(self, interaction2: dc.Interaction, button: dc.ui.Button):
            self.index = (self.index + 1) % len(entries)
            await self.update()

        @dc.ui.button(label="取消播放 | Cancel", style=dc.ButtonStyle.danger)
        async def cancel(self, interaction2: dc.Interaction, button: dc.ui.Button):
            await self.message.edit(content="> ❌ 操作已取消 | Canceled operation.", view=None)

    view = SoundCloudChooser()
    view.message = await interaction.edit_original_response(content="🔍 正在搜尋中...", view=view)
    await view.update()


    await interaction.edit_original_response(content=f"> 正在播放 {title} | Playing {title}")
    voice_client.play(
        dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"), 
        after=lambda e: asyncio.run_coroutine_threadsafe(
            interaction.edit_original_response(content="> 播完了喔 | Finished playing."),
            bot.loop
        )
    )
"""

"""
@bot.tree.command(name="furinaphoto", description="顯示隨機一張芙寧娜的照片(每日搜尋額度有限請見諒) | Show a random photo of Furina.(Daily search limit exists)")
async def slash_furina_photo(interaction: dc.Interaction):
    # 顯示隨機一張芙寧娜的照片
    # 回傳: None
    # Defer the interaction publicly. We will edit this message later.
    await interaction.response.defer(thinking=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /furina_photo.")
    try:
        search_query = "芙寧娜" # Define the search term
        # Generate a random start index from the possible pages (1, 11, 21, ..., 91)
        possible_start_indices = [1 + i * 10 for i in range(10)] # Generates [1, 11, 21, ..., 91]
        random_start_index = random.choice(possible_start_indices)
        # Perform a single search with the random start index
        image_urls = await GoogleSearchMethods.google_search(search_query, num_results=10, start_index=random_start_index)

        if not image_urls:
            logging.warning(f"Google Image Search for '{search_query}' (start={random_start_index}) returned no results or failed.")
            # Edit the original deferred message to show the error
            await interaction.edit_original_response(content="抱歉，我找不到任何芙寧娜的照片！(網路搜尋失敗或沒有結果)")
            return
        # No need to shuffle if we only fetched one page's worth
        random_image_url = random.choice(image_urls)
        await send_new_info_logging(bot=bot, message="slash_furina_photo called, url returned: " + random_image_url)
        await interaction.edit_original_response(content=f"# 我可愛嗎:D | Am I cute?:D\n{random_image_url}")

    except Exception as e:
        # Log the error
        await send_new_error_logging(f"Error in slash_furina_photo: {e}")
        try:
            # Try to edit the original deferred message to show a generic error
            await interaction.edit_original_response(content="執行此指令時發生了內部錯誤，請稍後再試。")
        except dc.NotFound:
            # If editing fails, the interaction likely expired or was deleted
            await send_new_error_logging(f"Interaction expired or was deleted before sending error message for slash_furina_photo for {interaction.user}.")
        except dc.HTTPException as http_e:
             # Handle potential other HTTP errors during edit
             await send_new_error_logging(f"HTTP error editing interaction for slash_furina_photo error message: {http_e}")
"""

"""
@bot.tree.command(name="timeout", description="使一個用戶被停權(需擁有對成員停權權限) | Timeout a user in a text channel(Requires timeout members permission).")
@describe(user="要停權的用戶 | The user to be timed out.")
@describe(s="停權秒數 | The number of seconds to timeout.")
@describe(reason="停權原因 | The reason for timeout.")
async def text_mute(interaction: dc.Interaction, user: dc.Member, s: int, reason: str):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.guild_permissions.moderate_members is False:
        await interaction.response.send_message("你沒有管理成員的權限 | You don't have the permission to manage members.", ephemeral=True)
        return
    
    await user.timeout(datetime.now() + timedelta(seconds=s), reason=reason)
    await interaction.response.send_message(f"# 水神的懲罰!! {user} 被停權 {s} 秒!! 原因: {reason}")
    send_new_info_logging(f"Someone is timed out.")
"""
    
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
