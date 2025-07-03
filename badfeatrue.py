"""
@bot.tree.command(name="status", description="確認芙寧娜是否在線 | Check if Furina is online.")
async def slash_status(interaction: dc.Interaction):
    # 確認芙寧娜是否在線
    # 回傳: None
    await interaction.response.send_message("# :white_check_mark::droplet:", ephemeral=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /status")
"""

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
