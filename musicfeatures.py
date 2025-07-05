import logging
import asyncio
import discord as dc
from objects import *
from generalmethods import *
from views import *
from discord.app_commands import describe
from yt_dlp import YoutubeDL as ytdlp

async def update_music_embed(guild: dc.Guild, voice_client: dc.VoiceClient, message: dc.Message, duration: int):
    def make_bar(progress):
        total_blocks = 15
        filled = min(int(progress / duration * total_blocks), total_blocks - 1)
        bar = "■" * filled + "🔘" + "□" * (total_blocks - filled - 1)
        return f"{bar}  `{int(progress) // 60}m{int(progress) % 60}s / {duration // 60}m{duration % 60}s`"

    for i in range(0, duration, 5):
        if not voice_client.is_connected() or not voice_client.is_playing():
            playback_status[guild.id] = "paused"
            break
        if playback_status.get(guild.id) == "paused":
            await asyncio.sleep(5)
            continue

        try:
            embed = message.embeds[0]
            embed.set_field_at(1, name="⏳進度 | Progress", value=make_bar(i), inline=False)
            await message.edit(embed=embed)
        except dc.NotFound:
            logging.warning(f"[{guild.name}] 播放訊息已消失，無法更新進度。")
            break
        except Exception as e:
            logging.error(f"[{guild.name}] 更新 embed 失敗：{e}")
            break
        await asyncio.sleep(5)

async def play_next(guild: dc.Guild, command_channel: dc.TextChannel = None):
    queue = get_server_queue(guild)
    voice_client = guild.voice_client

    # 檢查 queue 和語音連線是否存在
    if queue.empty() or not voice_client or not voice_client.is_connected():
        if command_channel:
            await command_channel.send("> 播放結束啦，要不要再加首歌 | Ended Playing, wanna queue more?")
        return

    # 取得下一首歌曲資訊
    view: MusicInfoView = await queue.get()
    audio_url = view.url
    duration = view.duration
    message = view.message
    await send_new_info_logging(bot=bot, message=f"Someone is listening music: {view.title}")

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
            
    def safe_callback_factory(view: MusicInfoView):
        def inner_callback(error):
            if view and view.message:
                def make_end_bar(duration):
                    total_blocks = 15
                    filled = min(total_blocks, total_blocks - 1)
                    bar = "■" * filled + "🔘" + "□" * (total_blocks - filled - 1)
                    return f"{bar}  `{duration // 60}m{duration % 60}s / {duration // 60}m{duration % 60}s`"
                
                try:
                    embed = view.message.embeds[0]
                    embed.set_field_at(
                        1,
                        name="⏳進度 | Progress",
                        value=make_end_bar(view.duration),
                        inline=False
                    )
                    asyncio.run_coroutine_threadsafe(
                        view.message.edit(embed=embed),
                        bot.loop
                    )
                except Exception as e:
                    logging.warning(f"[{guild.name}] 強制更新進度條失敗：{e}")

                asyncio.run_coroutine_threadsafe(
                    play_next(guild, command_channel),
                    bot.loop
                )
        return inner_callback

    def play_music():
        try:
            voice_client.play(
                dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
                after=safe_callback_factory(view)
            )
        except Exception as e:
            logging.error(f"[{guild.name}] ffmpeg 播放錯誤：{e}")

    # 播放 ffmpeg（非同步執行）
    await asyncio.get_event_loop().run_in_executor(None, play_music)

    # 開始進度更新（非阻塞
    bot.loop.create_task(update_music_embed(guild, voice_client, message, duration))

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
    if isinstance(interaction.user.voice.channel, dc.StageChannel):
        # be speaker
        await interaction.user.voice.channel.guild.me.edit(suppress=False)
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

@bot.tree.command(name="playyt", description="播放一首Youtube歌曲")
@describe(query="關鍵字 | Keyword.")
@describe(skip="是否插播(預設否) | Whether to interrupt current song (default False).")
async def slash_playyt(interaction: dc.Interaction, query: str, skip: bool = False):
    # 🧸 優先保護 interaction 不失效
    try:
        await interaction.response.defer(thinking=True)
    except dc.NotFound:
        logging.warning(f"[{interaction.guild.name}] interaction 失效，無法 defer。")
        return

    # 🚪 環境檢查
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.followup.send("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.voice is None:
        await interaction.followup.send("> 我不知道我要在哪裡放音樂... | I don't know where to put the music...")
        return

    # 🔊 語音連線管理
    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.channel != interaction.user.voice.channel:
        await voice_client.disconnect()
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()
        if isinstance(interaction.user.voice.channel, dc.StageChannel):
            await interaction.user.voice.channel.guild.me.edit(suppress=False)

    voice_client = interaction.guild.voice_client
    await interaction.followup.send("> 我進來了~讓我找一下歌... | I joined the channel! Give me a second...")

    # 🎵 非阻塞 yt-dlp 搜尋
    ydl_opts = {
        'format': 'ba/b',
        'default_search': 'ytsearch',
        'cookiefile': './cookies.txt',
    }

    def yt_search():
        with ytdlp(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                return info['entries'][0]
            return info

    try:
        info = await asyncio.get_event_loop().run_in_executor(None, yt_search)
    except Exception as e:
        await interaction.channel.send("> 無法取得歌曲資訊，請稍後再試 | Failed to retrieve song info.", ephemeral=True)
        logging.error(f"[{interaction.guild.name}] yt-dlp error: {e}")
        return

    # 🎼 處理歌曲資訊
    audio_url = info.get('url')
    title = info.get('title', 'UNKNOWN SONG')
    thumbnail = info.get("thumbnail")
    duration = info.get("duration", 0)
    uploader = info.get("uploader", "UNKNOWN ARTIST")

    try:
        guild_id = interaction.guild.id
        view = MusicInfoView(guild_id=guild_id, 
                             title=title, 
                             thumbnail=thumbnail, 
                             uploader=uploader, 
                             duration=duration, 
                             url=audio_url)
        message = await interaction.channel.send(embed=view.embed, view=view)
        view.message = message
        await all_server_queue[guild_id].put(view)
        playback_status[guild_id] = "playing"
    except Exception as e:
        logging.warning(f"[{interaction.guild.name}] 無法送出播放 embed...{e}")
        return

    if skip and voice_client.is_playing():
        voice_client.stop()

    # 📥 加入播放序列
    
    await interaction.channel.send(content=f"> 已將 **{title}** 加入序列 | Added **{title}** to queue!")
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /playyt with {title} added to his queue.")

    if not voice_client.is_playing():
        await play_next(interaction.guild, interaction.channel)