from objects import *
from generalmethods import *
from views_and_musicfuncs import *
from discord.app_commands import describe

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
    await voice_client.disconnect()
    
    if voice_client.is_playing():
        queue = all_server_queue[interaction.guild.id]
        snapshot = list(queue._queue)
        for view in snapshot:
            if hasattr(view, "message") and view.message and not view.is_deleted:
                await view.message.delete()
        not_playing_process(id=interaction.guild.id)
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
async def slash_hoyomixlist(interaction: dc.Interaction):
    view = HoyomixSongsListView(game=None, songs_per_page=None)
    await interaction.response.send_message(embed=view.pages[0], view=view)

@bot.tree.command(name="playyt", description="播放一首Youtube歌曲")
@describe(query="關鍵字 | Keyword.")
@describe(skip="是否插播(預設否) | Whether to interrupt current song (default False).")
@describe(startm="開始播放的分鐘數(預設0) | The number of minutes to start playing (default 0).")
@describe(starts="開始播放的秒數(預設0) | The number of seconds to start playing (default 0).")
async def slash_playyt(interaction: dc.Interaction, query: str, skip: bool = False, startm: int = 0, starts: int = 0):
    status = await play_connection_check(interaction=interaction)
    if status == -1:
        return
    
    if server_playing_hoyomix.get(interaction.guild.id, False):
        await interaction.followup.send("> 已經在播放Hoyomix歌單中了 | Already playing Hoyomix list!")
        return

    view = await get_ytdlp_infoview(interaction=interaction, query=query, quiet=False, start_m=startm, start_s=starts)
    await add_infoview(interaction=interaction, view=view, interrupt=skip)
    if not interaction.guild.voice_client.is_playing() and is_actually_playing.count(interaction.guild.id) == 0:
        await play_next_from_queue(interaction=interaction, full_played=True)

@bot.tree.command(name="playgi", description="播放原神的隨機原聲帶內容 | Play a random song from Genshin Impact OST.")
@describe(shuffle="是否打亂順序(預設是) | Whether to shuffle the order of songs. (default True)")
async def slash_playgi(interaction: dc.Interaction, shuffle: bool = True):
    await play_hoyomix_list(interaction=interaction, game=HoyoGames.GI, shuffle=shuffle)

@bot.tree.command(name="playhsr", description="播放崩鐵的隨機原聲帶內容 | Play a random song from Honkai Star Rail OST.")
@describe(shuffle="是否打亂順序(預設是) | Whether to shuffle the order of songs. (default True)")
async def slash_playhsr(interaction: dc.Interaction, shuffle: bool = True): 
    await play_hoyomix_list(interaction=interaction, game=HoyoGames.HSR, shuffle=shuffle)

if __name__ == "__main__":
    pass