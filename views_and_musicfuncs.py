import discord as dc
import asyncio
import math
import logging
import random
from generalmethods import get_general_embed, send_new_info_logging, send_new_error_logging, not_playing_process
from datetime import datetime, timedelta, timezone
from objects import bot, song_file_dict, all_server_queue, server_playing_hoyomix, is_actually_playing, TOTAL_BLOCKS, HoyoGames
from typing import Optional, Callable, Awaitable
from yt_dlp import YoutubeDL as ytdlp

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s",
)
class PaginatedViewBase(dc.ui.View):
    def __init__(self, timeout=120):
        super().__init__(timeout=timeout)
        self.pages: list[dc.Embed] = []  # 子類別需填寫
        self.current = 0

    @dc.ui.button(label="上一頁 | Previous page", style=dc.ButtonStyle.gray, row=0)
    async def previous(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @dc.ui.button(label="下一頁 | Next page", style=dc.ButtonStyle.gray, row=0)
    async def next(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self) 

class HelpView(PaginatedViewBase):
    def __init__(self):
        super().__init__(timeout=120)
        self.pages = self.generate_embeds()

    def generate_embeds(self):
        embeds = [ 
            # 📘 Page 一般指令
            get_general_embed(message={
                "/help": "顯示說明訊息 | Show the informations.",
                "/version": "查詢Furina的版本 | Check Furina's version.",
                "/randomnumber": "抽一個區間內的數字 | Random a number.",
                "/randomcode": "生成一個亂碼 | Generate a random code.",
                "/rockpaperscissors": "和芙寧娜玩剪刀石頭布 | Play rock paper scissors with Furina.",
                "/whois": "顯示特定成員在伺服器內的資訊 | Show a member's infomation in server.",
                "/serverinfo": "顯示伺服器資訊 | Show server information.",
                "/addchannel": "新增一個和芙寧娜對話的頻道 | Add a chat channel with Furina.",
                "/removechannel": "從名單中刪除一個頻道 | Remove a channel ID from the list.",
                "/reporterror": "回報你所發現的錯誤 | Report an error you found."
            }, color=dc.Color.blue(), title="一般指令 | Normal Commands"),

            # Page 語音指令
            get_general_embed(message={
                "/join": "加入語音頻道 | Join a voice channel.",
                "/leave": "離開語音頻道 | Leave a voice channel.",
                "/queue": "查看播放序列 | Check the play queue.",
                "/hoyomixlist": "查看Furina收錄的Hoyomix歌單 | Check Furina's Hoyomix list.",
                "/playyt": "播放一首Youtube歌曲 | Play a song with Youtube.",
                "/playgi": "播放原神的隨機原聲帶內容 | Play a random song from Genshin Impact OST.",
                "/playhsr": "播放崩鐵的隨機原聲帶內容 | Play a random song from Honkai Star Rail OST.",
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

class MemberInfoView(PaginatedViewBase):
    def __init__(self, user: dc.Member):
        super().__init__(timeout=120)
        self.page_task = asyncio.create_task(self.generate_embeds(user=user))
        self.pages = None
        return None
    
    async def get_pages(self):
        if not self.pages:
            self.pages = await self.page_task
        return self.pages

    async def generate_embeds(self, user: dc.Member):
        embeds = []
        gmt8 = datetime.now(tz=timezone(timedelta(hours=8)))
        infomations_page1 = {
            "伺服器暱稱 | Nickname": user.display_name, 
            "用戶名稱 | User Name": user.name,
            "用戶ID | User ID": user.id,
            "加入日期 | Joined At": user.joined_at.strftime("%Y-%m-%d"),
            "加入天數 | Duration": str((gmt8 - user.joined_at).days),
            "帳號創建日期 | Created At": user.created_at.strftime("%Y-%m-%d"),
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

        return embeds 

class ServerInfoView(PaginatedViewBase):
    def __init__(self, interaction: dc.Interaction, role_per_page: int = 10):
        super().__init__(timeout=120)
        self.pages = self.generate_embeds(guild=interaction.guild, role_per_page=role_per_page)
        return None
    
    def generate_embeds(self, guild: dc.Guild, role_per_page: int = 10):
        infomations = {
            "伺服器名稱 | Server Name": guild.name,
            "成員數量 | Member Count": str(guild.member_count),
            "擁有者 | Owner": guild.owner.mention,
            "創建日期 | Created At": guild.created_at.strftime("%Y-%m-%d"),
            "描述 | Description": guild.description if guild.description else None,
            "身分組數量 | Role Count": str(len(guild.roles)),
            "頻道數量 | Channel Count": str(len(guild.channels)),
            "語音頻道數量 | Voice Channel Count": str(len(guild.voice_channels)),
            "文字頻道數量 | Text Channel Count": str(len(guild.text_channels)),
            "表情符號數量 | Emoji Count": str(len(guild.emojis)),
        }

        roles = [role.mention for role in guild.roles if role != guild.default_role]
        roles.reverse()  # 管理員通常在後面，反過來比較清楚

        if roles:
            role_info_pages = []
            total_page = max(1, math.ceil(len(roles) / role_per_page))

            for i in range(0, len(roles), role_per_page):
                page_index = i // role_per_page + 1
                role_chunk = roles[i:i + role_per_page]
                role_text = "\n".join(role_chunk) if role_chunk else "> 無身分組 | No roles found"
                page_note = f"\n身分組第 {page_index} / {total_page} 頁 | Role pages {page_index} / {total_page}"
                role_info_pages.append({"身分組 | Roles": role_text + page_note})

        icon = guild.icon.url if guild.icon else None
        banner = guild.banner.url if guild.banner else None

        embeds = [get_general_embed(
            infomations, dc.Color.blue(), "伺服器資訊 | Server Information", icon=icon, banner=banner
        )]

        for page in role_info_pages:
            embeds.append(get_general_embed(
                page, dc.Color.blue(), "伺服器資訊 | Server Information", icon=icon, banner=banner
            ))

        return embeds 
    
    @dc.ui.button(label="首頁 | First Page", style=dc.ButtonStyle.secondary, row=0)
    async def first(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.current = 0
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

class HoyomixSongsListView(PaginatedViewBase):
    def __init__(self, game: HoyoGames, songs_per_page: int = 10):
        super().__init__(timeout=300)
        with open(song_file_dict[game.value], "r", encoding="utf-8") as f:
            self.songs = [line.strip() for line in f.readlines() if line.strip()]
        self.game = game
        self.pages = self.generate_embeds(songs_per_page=songs_per_page)
        return None

    def generate_embeds(self, songs_per_page: int = 10):
        embeds = []
        total_pages = (len(self.songs) + songs_per_page - 1) // songs_per_page

        for i in range(total_pages):
            current_page_songs = self.songs[i * songs_per_page : (i + 1) * songs_per_page]
            embed = get_general_embed(
                message="\n".join(current_page_songs+[f"第 {i+1} / {total_pages} 頁 | Page {i+1} / {total_pages}"]),
                title=f"{self.game.value} 歌曲清單 | {self.game.value} Song List"
            )
            embeds.append(embed)
        return embeds

class LyricsView(PaginatedViewBase):
    def __init__(self, song_name: str, lyrics: str):
        super().__init__(timeout=None)
        self.song_name = song_name
        self.lyrics = lyrics
        self.pages = self.generate_embeds()
        return None

    def generate_embeds(self):
        embeds = []
        lyrics_list = self.lyrics.split("\n")
        for i in range(0, len(lyrics_list), 10):
            page_number = f"{i//10+1} / {math.ceil(len(lyrics_list)/10)}"
            embed = get_general_embed(
                message="\n".join(lyrics_list[i:i+10])+f"\n第 {page_number} 頁 | Page {page_number}",
                title=f"{self.song_name} 的歌詞 | Lyrics of {self.song_name}"
            )
            embeds.append(embed)
        return embeds
    
    async def search_lyrics(query: str):
        pass  

class MusicInfoView(dc.ui.View):
    def __init__(self, message: dc.Message = None,
                 guild_id: int = None, 
                 title: str = None, 
                 thumbnail: str = None, 
                 uploader: str = None, 
                 duration: int = None,
                 url: str = None, 
                 start_m: int = 0, 
                 start_s: int = 0, 
                 game: HoyoGames = None):
        super().__init__(timeout=18000)
        self.guild_id =         guild_id
        self.uploader =         uploader
        self.duration =         duration
        self.title =            title
        self.thumbnail =        thumbnail
        self.url =              url
        self.embed =            self.generate_embed(title=title, thumbnail=thumbnail, uploader=uploader, duration=duration)
        self.message =          message
        self.is_deleted =       False
        self.start_time =       datetime.now()
        self.start_m =          start_m
        self.start_s =          start_s
        self.played_seconds =   start_m * 60 + start_s
        self.lyrics_view =      None
        self.game =             game
        return None

    def generate_embed(self, title: str, thumbnail: str, uploader: str, duration: int = None):
        embed = get_general_embed(
            message=f"**{title}**\n",
            color=0x1DB954,
            title="🎶正在播放 | Now Playing",
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="上傳者 | Uploader", value=uploader, inline=False)
        embed.add_field(name="⏳進度 | Progress", value="🔘" + "□"*(TOTAL_BLOCKS-1), inline=False)

        return embed

    @dc.ui.button(label="⏸ 暫停 | Pause", style=dc.ButtonStyle.primary, row=0)
    async def pause(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return
    
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("> 我目前不在語音頻道中喔 | I'm not connected to any voice channel.", ephemeral=True)
            return
        
        if not voice_client.is_playing():
            await interaction.response.send_message("> 沒有歌曲可暫停 | No song to pause.", ephemeral=True)
            return
    
        voice_client.pause()
        self.played_seconds += int((datetime.now() - self.start_time).total_seconds())
        await interaction.response.send_message("> 已暫停播放序列 | Paused the play queue.", ephemeral=True)

    @dc.ui.button(label="▶️ 恢復 | Resume", style=dc.ButtonStyle.success, row=0)
    async def resume(self, interaction: dc.Interaction, button: dc.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("> 我目前不在語音頻道中喔 | I'm not connected to any voice channel.", ephemeral=True)
            return

        if voice_client.is_playing():
            await interaction.response.send_message("> 音樂正在播放中，不需要恢復 | Already playing!", ephemeral=True)
            return
        
        try:
            voice_client.resume()
            if self.message:
                bot.loop.create_task(update_music_embed(interaction.guild, voice_client, self.message, self.duration, self.played_seconds))
            self.start_time = datetime.now()
            await interaction.response.send_message("> 音樂已恢復播放 | Playback resumed.", ephemeral=True)
        except Exception as e:
            send_new_error_logging(f"[{interaction.guild.name}] Error resuming playback: {e}", to_discord=False)

    @dc.ui.button(label="⏭ 跳過 | Skip", style=dc.ButtonStyle.danger, row=0)
    async def skip(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("> 目前沒有歌曲正在播放 | No song is currently playing.", ephemeral=True)
            return
        
        if self.message:
            await self.message.delete()
            self.message = None
            self.is_deleted = True
        voice_client.stop()
        await interaction.channel.send("> 已跳過當前歌曲 | Skipped the current song.")

    @dc.ui.button(label="查看序列 | Queue", style=dc.ButtonStyle.secondary, row=1)
    async def queue(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return
        if server_playing_hoyomix.get(interaction.guild.id, False):
            await interaction.response.send_message("> Hoyomix序列是隨機的 | The Hoyomix queue is random.")
            return

        queue = all_server_queue[interaction.guild.id]
        if queue.empty():
            await interaction.response.send_message("> 播放序列是空的喔！| The queue is currently empty.", ephemeral=True)
            return

        items = list(queue._queue)
        message = "\n".join(f"> {i+1}. {view.title}" for i, view in enumerate(items))
        await interaction.response.send_message(f"> 當前播放序列 | Current play queue:\n{message}", ephemeral=False)

    @dc.ui.button(label="查詢歌詞 | Lyrics", style=dc.ButtonStyle.secondary, row=1)
    async def get_lyric(self, interaction: dc.Interaction, button: dc.ui.Button):
        await interaction.response.send_message("> 此功能還在施工中 | This feature is under construction.", ephemeral=True)
        return
    
        lyrics = await search_lyrics(self.title)

        if lyrics:
            view = LyricsView(song_name=self.title, lyrics=lyrics)
            self.lyrics_view = view
            await interaction.followup.send(embed=view.pages[0], view=view, ephemeral=True)
        else:
            await interaction.followup.send(content="> 沒找到歌詞 😢", ephemeral=True)
    
    @dc.ui.button(label="查詢Hoyomix歌單 | Hoyomix list", style=dc.ButtonStyle.secondary, row=1)
    async def get_hoyomix_list(self, interaction: dc.Interaction, button: dc.ui.Button):
        if self.game is None:
            await interaction.response.send_message("> 只有Hoyomix歌單支援此功能 | Only Hoyomix list supports this feature.")
            return
        
        await send_hoyomix_list(interaction=interaction, game_type=self.game, songs_per_page=10)

    @dc.ui.button(label="清空序列 | Clear", style=dc.ButtonStyle.danger, row=2)
    async def clear(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return
        
        if server_playing_hoyomix.get(interaction.guild.id, False):
            await interaction.response.send_message("> Hoyomix序列無法人工刪減 | The Hoyomix queue cannot be manually removed.")
            return
        
        queue = all_server_queue[interaction.guild.id]
        if queue.empty():
            await interaction.response.send_message("> 播放序列是空的喔 | The queue is currently empty.", ephemeral=True)
            return

        cleared = 0
        while not queue.empty():
            queue.get_nowait()
            cleared += 1

        await interaction.response.send_message(f"> 已清空播放序列，共移除 {cleared} 首歌曲 | Cleared queue ({cleared} songs removed).", ephemeral=False)

    @dc.ui.button(label="末曲移除 | Popback", style=dc.ButtonStyle.danger, row=2)
    async def popback(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("> 目前沒有歌曲正在播放 | No song is currently playing.", ephemeral=True)
            return
        if server_playing_hoyomix.get(interaction.guild.id, False):
            await interaction.response.send_message("> Hoyomix序列無法人工刪減 | The Hoyomix queue cannot be manually removed.")
            return

        queue = all_server_queue[interaction.guild.id]
        if queue.empty():
            await interaction.response.send_message("> 播放序列是空的喔 | The queue is currently empty.", ephemeral=True)
            return
        poped_song: MusicInfoView = queue._queue.pop()
        
        await interaction.response.send_message(f"> 已將 {poped_song.title} 移出播放序列。| Removed {poped_song.title} from the queue.", ephemeral=False)

    @dc.ui.button(label="結束播放 | Leave", style=dc.ButtonStyle.danger, row=2)
    async def leave(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message("> 我目前不在語音頻道中喔 | I'm not connected to any voice channel.", ephemeral=True)
            return
        
        self.is_deleted = True
        if voice_client.is_playing():
            queue = all_server_queue[interaction.guild.id]
            snapshot = list(queue._queue)
            for view in snapshot:
                if hasattr(view, "message") and view.message and not view.is_deleted:
                    await view.message.delete()
            
            not_playing_process(interaction.guild.id)
            interaction.guild.voice_client.stop()

        await voice_client.disconnect()
        await interaction.channel.send("> 我走了，再見~ | Bye~~")

class WarningView(dc.ui.View):
    def __init__(self, 
                 message: str = None,
                 color: dc.Color = dc.Color.yellow, 
                 title: str = "警告 | Warning"):
        super().__init__(timeout=300)
        self.embed = self.generate_embed(message=message, color=color, title=title)
        self.message : dc.Message = None
        self.yes_or_no = False
        return None

    def generate_embed(self, message: str, color: dc.Color, title: str):
        embed = get_general_embed(
            message=message,
            color=color,
            title=title,
        )
        return embed

class ChangeToHoyoView(WarningView):
    def __init__(
        self,
        interaction: dc.Interaction,
        game: HoyoGames,
        on_confirm: Optional[Callable[[dc.Interaction], Awaitable[None]]] = None
    ):
        super().__init__(
            message="這麼做會停止正在播放的YT歌曲，你確定嗎 | Are you sure you want to stop the currently playing YT song?",
            color=dc.Color.orange(),
            title="播放切換確認 | Confirm Playback Switch"
        )
        self.interaction = interaction
        self.game = game
        self.on_confirm = on_confirm
        self.decision_event = asyncio.Event()

    @dc.ui.button(label="是 | Yes", style=dc.ButtonStyle.danger)
    async def confirm(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.yes_or_no = True
        if self.on_confirm:
            await self.on_confirm(interaction)
        await self.message.delete()
        await interaction.response.send_message("> 正在切換... | Changing...", ephemeral=True)
        self.decision_event.set()

    @dc.ui.button(label="否 | No", style=dc.ButtonStyle.secondary)
    async def cancel(self, interaction: dc.Interaction, button: dc.ui.Button):
        self.yes_or_no = False
        await self.message.delete()
        await interaction.response.send_message("> 已取消播放 | Cancelled playback.", ephemeral=True)
        self.decision_event.set()

async def send_hoyomix_list(interaction: dc.Interaction, game_type: HoyoGames | str, songs_per_page: int):
    game = game_type if isinstance(game_type, HoyoGames) else HoyoGames[game_type]
    songs_per_page = min(50, max(10, songs_per_page))
    view = HoyomixSongsListView(game=game, songs_per_page=songs_per_page)
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
                             quiet: bool = True, 
                             start_m: int = 0, 
                             start_s: int = 0, 
                             game_type: HoyoGames = None):
    """
    Get ytdlp informations, push it to the queue.
    Parameters:
        interaction (dc.Interaction): Interaction object.
        query (str): query to search.
        current_number (int, optional): current number in the queue. Defaults to None.
        total_number (int, optional): total number in the queue. Defaults to None.
        command (str, optional): command name. Defaults to "playyt".
        start_m (int, optional): start minute. Defaults to 0.
        start_s (int, optional): start second. Defaults to 0.
        game_type (HoyoGames, optional): game type. Defaults to None.
    
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
                         url=audio_url, 
                         start_m=start_m, 
                         start_s=start_s, 
                         game=game_type)
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
    is_actually_playing.append(interaction.guild.id)

    if queue.empty() and voice_client is not None and not voice_client.is_playing():
        not_playing_process(id=guild_id)
        await interaction.channel.send("> 播放結束啦，要不要再加首歌 | Ended Playing, wanna queue more?\n" +
                                       "> 不加我就要走了喔 | I will go if you don't add anything.")

    if isinstance(interaction.user.voice.channel, dc.StageChannel):
        await interaction.user.voice.channel.guild.me.edit(suppress=False)
    # 拿出下一首 view
    view: MusicInfoView = await queue.get()
    audio_url = view.url
    duration = view.duration
    start_time = view.start_m*60 + view.start_s
    if not view.message:
        view.message = await interaction.channel.send(embed=view.embed, view=view)
    voice_client = interaction.guild.voice_client
    # 如果斷線就重新建立語音通道
    if not voice_client or not voice_client.is_connected():
        try:
            await interaction.user.voice.channel.connect()
        except dc.ClientException as e:
            if "Not connected" in str(e):
                logging.warning(f"{interaction.guild.name} 播放失敗，準備重新連線")
                voice_client.cleanup()
                await voice_client.connect(...)
    voice_client = interaction.guild.voice_client

    before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    if start_time != 0:
        before_options+=f" -ss {start_time}"

    ffmpeg_options = {
        'before_options': before_options,
        'options': '-vn'
    }

    full_played = False
    def safe_callback_factory(view: MusicInfoView):
        def inner_callback(error):
            nonlocal full_played
            full_played = True
            try:
                is_actually_playing.remove(interaction.guild.id)
            except ValueError:
                pass

            if view and view.message:
                bot.loop.create_task(view.message.delete())
                view.is_deleted = True

            # 播完接下一首（遞迴）
            bot.loop.create_task(play_next_from_queue(interaction, full_played))
        return inner_callback

    def play_music():
        try:
            voice_client.play(
                dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
                after=safe_callback_factory(view)
            )
        except dc.ClientException as e:
            logging.warning(f"{interaction.guild.name} play 播放失敗: {e}")

    await asyncio.get_event_loop().run_in_executor(None, play_music)
    bot.loop.create_task(update_music_embed(interaction.guild, voice_client, view.message, duration, start_time))

async def play_single_song(interaction: dc.Interaction, 
                           query: str,
                           command: str = "playyt",
                           current_number: int = None,
                           total_number: int = None,
                           done_played: asyncio.Event = None, 
                           game_type: HoyoGames = None):
    # 處理歌曲資訊
    view: MusicInfoView = await get_ytdlp_infoview(interaction=interaction, 
                                                   query=query, 
                                                   current_number=current_number, 
                                                   total_number=total_number, 
                                                   command=command, 
                                                   game_type=game_type
                                                   )
    audio_url = view.url
    duration = view.duration
    await add_infoview(interaction=interaction, view=view)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    voice_client = interaction.guild.voice_client

    # 如果斷線就重新建立語音通道
    if not voice_client or not voice_client.is_connected():
        try:
            voice_client.connect()
        except dc.ClientException as e:
            if "Not connected" in str(e):
                logging.warning(f"{interaction.guild.name} 播放失敗，準備重新連線")
                voice_client.cleanup()
                await voice_client.connect(...)
    
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
        try:
            voice_client.play(
                dc.FFmpegPCMAudio(audio_url, **ffmpeg_options, executable="./ffmpeg.exe"),
                after=safe_callback_factory(view)
            )
        except dc.ClientException as e:
            logging.warning(f"{interaction.guild.name} play 播放失敗: {e}")
            if done_played:
                done_played.set()

    # 播放與更新（非同步執行）
    try:       
        await asyncio.get_event_loop().run_in_executor(None, play_music)
        bot.loop.create_task(update_music_embed(guild, voice_client, view.message, duration))
        await done_played.wait()
    finally:
        if not done_played.is_set():
            done_played.set()

async def play_hoyomix_list(interaction: dc.Interaction, game: HoyoGames = None, shuffle: bool = True):
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
        asyncio.sleep(0.5)
    
    server_playing_hoyomix[interaction.guild.id] = True
    await interaction.channel.send("> 提示：使用指令`/hoyomixlist`查詢歌單 | Use `/hoyomixlist` to check the list.")
    game_name = game.value
    with open(song_file_dict[game_name], "r", encoding="utf-8") as f:
        songs = [line.strip() for line in f.readlines()]
    
    def shuffle_list(l: list):
        for i in range(len(l) - 1):
            j = random.randint(i, len(l) - 1)
            l[i], l[j] = l[j], l[i]
        return l
    if shuffle:
        shuffle_list(songs)

    full_played = True
    is_actually_playing.append(interaction.guild.id)
    try:
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
                                done_played=event, 
                                game_type=game)
            await event.wait()
    finally:
        not_playing_process(id=interaction.guild.id)
        if full_played:
            await interaction.channel.send("> 播放結束啦，要不要再加首歌 | Ended Playing, wanna queue more?\n" +
                                        "> 不加我就要走了喔 | I will go if you don't add anything.")

async def update_music_embed(guild: dc.Guild, voice_client: dc.VoiceClient, message: dc.Message, duration: int, start_second: int = 0):
    def make_bar(progress):
        filled = min(int(progress / duration * TOTAL_BLOCKS), TOTAL_BLOCKS - 1)
        bar = "■" * filled + "🔘" + "□" * (TOTAL_BLOCKS - filled - 1)
        return f"{bar}  `{int(progress) // 60}m{int(progress) % 60}s / {duration // 60}m{duration % 60}s`"
    
    start_time = asyncio.get_event_loop().time()
    played_seconds = start_second
    while played_seconds < duration:
        if not voice_client or not voice_client.is_connected() or not voice_client.is_playing():
            break

        if voice_client.is_paused():
            start_time = int(asyncio.get_event_loop().time() + start_second)
            continue

        played_seconds = int(asyncio.get_event_loop().time() - start_time + start_second)

        try:
            if not message:
                break
            embed = message.embeds[0]
            embed.set_field_at(1, name="⏳進度 | Progress", value=make_bar(played_seconds), inline=False)
            await message.edit(embed=embed)
        except dc.errors.HTTPException as e:
            if e.status == 429:
                retry_after = int(e.retry_after) if e.retry_after else 5
                await asyncio.sleep(retry_after)
                continue
        except dc.NotFound:
            logging.warning(f"[{guild.name}] 播放訊息已消失，無法更新進度。")
            break
        except Exception as e:
            logging.error(f"[{guild.name}] 更新 embed 失敗：{e}")
            break

        await asyncio.sleep(1)

if __name__ == "__main__":
    pass