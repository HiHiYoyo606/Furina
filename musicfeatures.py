import logging
import asyncio
import discord as dc
from objects import *
from generalmethods import *
from views import *
from discord.app_commands import describe
from yt_dlp import YoutubeDL as ytdlp

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
    voice_client = interaction.guild.voice_client
    if not voice_client:
        await interaction.response.send_message("> 我目前不在語音頻道中喔 | I'm not connected to any voice channel.", ephemeral=True)
        return
    
    if voice_client.is_playing():
        queue = all_server_queue[interaction.guild.id]
        snapshot = list(queue._queue)
        for view in snapshot:
            if hasattr(view, "message") and view.message and not view.is_deleted:
                await view.message.delete()
        all_server_queue.pop(interaction.guild.id)
        remove_hoyomix_status(guild=interaction.guild)
        interaction.guild.voice_client.stop()

    await voice_client.disconnect()
    await interaction.channel.send("> 我走了，再見~ | Bye~~")

@bot.tree.command(name="queue", description="查看播放序列 | Check the play queue.")
async def slash_queue(interaction: dc.Interaction):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return

    queue = all_server_queue[interaction.guild.id]
    if queue.empty():
        await interaction.response.send_message("> 播放序列是空的喔！| The queue is currently empty.", ephemeral=True)
        return

    items = list(queue._queue)
    message = "\n".join(f"> {i+1}. {view.title}" for i, view in enumerate(items))
    await interaction.response.send_message(f"> 當前播放序列 | Current play queue:\n{message}", ephemeral=False)

@bot.tree.command(name="hoyomixlist", description="查看Furina收錄的Hoyomix歌單 | Check Furina's Hoyomix list.")
@dc.app_commands.choices(choice=[
    dc.app_commands.Choice(name="原神 Genshin Impact", value="GI"),
    dc.app_commands.Choice(name="崩鐵 Honkai Star Rail", value="HSR"),
])
@describe(songsperpage="每頁顯示的歌曲數量(預設至少10, 至多50) | The number of songs to display per page. (default at least 10, at most 50)")
async def slash_hoyomixlist(interaction: dc.Interaction, choice: str, songsperpage: int = 0):
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.followup.send("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    game = HoyoGames[choice]
    songsperpage = min(50, max(10, songsperpage))
    view = HoyomixSongsListView(game=game, songs_per_page=songsperpage)
    await interaction.response.send_message(embed=view.pages[0], view=view)

async def play_connection_check(interaction: dc.Interaction):
    await interaction.response.defer(thinking=True)

    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.followup.send("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return -1
    if interaction.user.voice is None:
        await interaction.followup.send("> 我不知道我要在哪裡放音樂... | I don't know where to put the music...")
        return -1
    
    voice_client = dc.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.channel != interaction.user.voice.channel:
        await voice_client.disconnect()
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()
        if isinstance(interaction.user.voice.channel, dc.StageChannel):
            await interaction.user.voice.channel.guild.me.edit(suppress=False)

    await interaction.followup.send("> 我進來了~讓我找一下歌... | I joined the channel! Give me a second...")

async def update_music_embed(guild: dc.Guild, voice_client: dc.VoiceClient, message: dc.Message, duration: int):
    def make_bar(progress):
        filled = min(int(progress / duration * TOTAL_BLOCKS), TOTAL_BLOCKS - 1)
        bar = "■" * filled + "🔘" + "□" * (TOTAL_BLOCKS - filled - 1)
        return f"{bar}  `{int(progress) // 60}m{int(progress) % 60}s / {duration // 60}m{duration % 60}s`"
    
    start_time = asyncio.get_event_loop().time()
    played_seconds = 0
    while played_seconds < duration:
        if not voice_client or not voice_client.is_connected() or not voice_client.is_playing():
            break

        if voice_client.is_paused():
            start_time = int(asyncio.get_event_loop().time())
            continue

        played_seconds = int(asyncio.get_event_loop().time() - start_time)

        try:
            if not message:
                break
            embed = message.embeds[0]
            embed.set_field_at(1, name="⏳進度 | Progress", value=make_bar(played_seconds), inline=False)
            await message.edit(embed=embed)
        except dc.NotFound:
            logging.warning(f"[{guild.name}] 播放訊息已消失，無法更新進度。")
            break
        except Exception as e:
            logging.error(f"[{guild.name}] 更新 embed 失敗：{e}")
            break

        await asyncio.sleep(1)

async def add_infoview(interaction: dc.Interaction, view: MusicInfoView, interrupt: bool = False):
    voice_client = interaction.guild.voice_client
    queue = all_server_queue[interaction.guild.id]
    if interrupt:
        queue._queue.appendleft(view)
        if voice_client.is_playing():
            voice_client.stop()
    else:
        await queue.put(view)

async def get_ytdlp_infoview(interaction: dc.Interaction, 
                             query: str, 
                             current_number: int = None, 
                             total_number: int = None,
                             command: str = "playyt", 
                             quiet: bool = True):
    """
    Get ytdlp informations, push it to the queue.
    Parameters:
        interaction (dc.Interaction): Interaction object.
        query (str): query to search.
        current_number (int, optional): current number in the queue. Defaults to None.
        total_number (int, optional): total number in the queue. Defaults to None.
        command (str, optional): command name. Defaults to "playyt".
    
    Returns:
        MusicInfoView: the MusicInfoView object representing the song.
    """
    ydl_opts = {
        'format': 'ba/b',
        'default_search': 'ytsearch',
        'cookiefile': './cookies.txt',
        'skip_download': True,
        'nocheckcertificate': True,
    }

    with ytdlp(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            if len(info['entries']) > 0:
                info = info['entries'][0]
            else:
                info = ydl.extract_info(query.replace(" HOYO-MiX", " Yu-peng Music"), download=False)

    audio_url = info.get('url')
    title = info.get('title', 'UNKNOWN SONG')
    thumbnail = info.get("thumbnail")
    duration = info.get("duration", 0)
    uploader = info.get("uploader", "UNKNOWN ARTIST")
    voice_client = interaction.guild.voice_client
    view = MusicInfoView(guild_id=interaction.guild.id, 
                         title=title, 
                         thumbnail=thumbnail, 
                         uploader=uploader, 
                         duration=duration, 
                         url=audio_url)
    current_process = f"> # ({current_number}/{total_number})" if current_number is not None and total_number is not None else ""
    message = (await interaction.channel.send(content=current_process, embed=view.embed, view=view)) if not voice_client.is_playing() else None
    view.message = message

    if not quiet:
        current_process = "" if current_number is None or total_number is None else f"\n> 當前序號 | Current number: {current_number}/{total_number}"
        await interaction.edit_original_response(content=f"> 已將 **{title}** 加入序列 | Added **{title}** to queue!" + current_process)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used {command} with {title} added to his queue.")

    return view

async def play_next_from_queue(interaction: dc.Interaction, full_played: bool = False):
    guild_id = interaction.guild.id
    queue = all_server_queue[guild_id]
    voice_client = interaction.guild.voice_client

    if queue.empty() and full_played and voice_client is not None and not voice_client.is_playing():
        await interaction.channel.send("> 播放結束啦，要不要再加首歌 | Ended Playing, wanna queue more?\n" +
                                       "> 不加我就要走了喔 | I will go if you don't add anything.")

    if isinstance(interaction.user.voice.channel, dc.StageChannel):
        await interaction.user.voice.channel.guild.me.edit(suppress=False)
    # 拿出下一首 view
    view: MusicInfoView = await queue.get()
    audio_url = view.url
    duration = view.duration
    if not view.message:
        view.message = await interaction.channel.send(embed=view.embed, view=view)
    voice_client = interaction.guild.voice_client

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    full_played = False
    def safe_callback_factory(view: MusicInfoView):
        def inner_callback(error):
            nonlocal full_played
            full_played = True
            
            if view and view.message:
                bot.loop.create_task(view.message.delete())
                view.is_deleted = True

            # 播完接下一首（遞迴）
            bot.loop.create_task(play_next_from_queue(interaction, full_played))
        return inner_callback

    def play_music():
        voice_client.play(
            dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
            after=safe_callback_factory(view)
        )

    await asyncio.get_event_loop().run_in_executor(None, play_music)
    bot.loop.create_task(update_music_embed(interaction.guild, voice_client, view.message, duration))

async def play_single_song(interaction: dc.Interaction, 
                           query: str,
                           command: str = "playyt",
                           current_number: int = None,
                           total_number: int = None,
                           done_played: asyncio.Event = None):
    # 處理歌曲資訊
    view: MusicInfoView = await get_ytdlp_infoview(interaction=interaction, 
                                                   query=query, 
                                                   current_number=current_number, 
                                                   total_number=total_number, 
                                                   command=command)
    audio_url = view.url
    duration = view.duration
    await add_infoview(interaction=interaction, view=view)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    voice_client = interaction.guild.voice_client
    if isinstance(interaction.user.voice.channel, dc.StageChannel):
        await interaction.user.voice.channel.guild.me.edit(suppress=False)
    guild = interaction.guild
            
    def safe_callback_factory(view: MusicInfoView):
        def inner_callback(error):
            if view and view.message:
                asyncio.run_coroutine_threadsafe(
                    view.message.delete(),
                    bot.loop
                )
                view.is_deleted = True
                try:
                    asyncio.run_coroutine_threadsafe(
                        all_server_queue[guild.id].get_nowait(), 
                        bot.loop
                    )
                except asyncio.QueueEmpty:
                    pass
                except TypeError:
                    pass

            if done_played:
                done_played.set()
        return inner_callback

    def play_music():
        voice_client.play(
            dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
            after=safe_callback_factory(view)
        )

    # 播放與更新（非同步執行）
    try:       
        await asyncio.get_event_loop().run_in_executor(None, play_music)
        bot.loop.create_task(update_music_embed(guild, voice_client, view.message, duration))
        await done_played.wait()
    finally:
        if not done_played.is_set():
            done_played.set()

async def play_hoyomix_list(interaction: dc.Interaction, game: HoyoGames = None):
    if server_playing_hoyomix.get(interaction.guild.id, False): # playing hoyo list
        await interaction.response.send_message("> 已經在播放Hoyomix歌單中了 | Already playing Hoyomix list!", ephemeral=True)
        return
    status = await play_connection_check(interaction=interaction)
    if status == -1:
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        # playyt ing
        view = ChangeToHoyoView(interaction=interaction, game=game)       
        message = await interaction.edit_original_response(embed=view.embed, view=view, ephemeral=False) 
        view.message = message
        await view.decision_event.wait()
        if not view.yes_or_no:
            return
        
        voice_client.stop()
    
    server_playing_hoyomix[interaction.guild.id] = True
    await interaction.channel.send("> 提示：這個歌單可能不是完整的 | Hint: This playlist may not be complete.\n" +
                                   "> 使用指令`/hoyomixlist`查詢歌單 | Use `/hoyomixlist` to check the list.")
    game_name = game.value
    with open(song_file_dict[game_name], "r", encoding="utf-8") as f:
        songs = [line.strip() for line in f.readlines()]
    
    def shuffle(l: list):
        for i in range(len(l) - 1):
            j = random.randint(i, len(l) - 1)
            l[i], l[j] = l[j], l[i]
        return l
    shuffle(songs)
    
    full_played = True
    for i, song in enumerate(songs):
        if not voice_client or not voice_client.is_connected():
            full_played = False
            break
        event = asyncio.Event()
        await play_single_song(interaction=interaction, 
                               query=song+f" HOYO-MiX",
                               command=f"play{game.name.lower()}", 
                               current_number=i+1,
                               total_number=len(songs), 
                               done_played=event)
        await event.wait()
    
    all_server_queue.pop(interaction.guild.id)
    remove_hoyomix_status(guild=interaction.guild)
    if full_played:
        await interaction.channel.send("> 播放結束啦，要不要再加首歌 | Ended Playing, wanna queue more?\n" +
                                       "> 不加我就要走了喔 | I will go if you don't add anything.")

@bot.tree.command(name="playyt", description="播放一首Youtube歌曲")
@describe(query="關鍵字 | Keyword.")
@describe(skip="是否插播(預設否) | Whether to interrupt current song (default False).")
async def slash_playyt(interaction: dc.Interaction, query: str, skip: bool = False):
    status = await play_connection_check(interaction=interaction)
    if status == -1:
        return
    
    if server_playing_hoyomix.get(interaction.guild.id, False):
        await interaction.followup.send("> 已經在播放Hoyomix歌單中了 | Already playing Hoyomix list!")
        return

    view = await get_ytdlp_infoview(interaction=interaction, query=query, quiet=False)
    await add_infoview(interaction=interaction, view=view, interrupt=skip)
    if not interaction.guild.voice_client.is_playing():
        await play_next_from_queue(interaction=interaction, full_played=True)

@bot.tree.command(name="playgi", description="播放原神的隨機原聲帶內容 | Play a random song from Genshin Impact OST.")
async def slash_playgi(interaction: dc.Interaction):
    await play_hoyomix_list(interaction=interaction, game=HoyoGames.GI)

@bot.tree.command(name="playhsr", description="播放崩鐵的隨機原聲帶內容 | Play a random song from Honkai Star Rail OST.")
async def slash_playhsr(interaction: dc.Interaction): 
    await play_hoyomix_list(interaction=interaction, game=HoyoGames.HSR)

if __name__ == "__main__":
    pass