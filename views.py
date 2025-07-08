import discord as dc
import math
from generalmethods import get_general_embed, send_new_error_logging
from datetime import datetime, timedelta, timezone
from objects import *
from typing import Optional, Callable, Awaitable

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
        self.pages = asyncio.run_coroutine_threadsafe(self.generate_embeds(user=user), bot.loop).result()
        return None

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
        with open(song_file_dict[game.value], "+r", encoding="utf-8") as f:
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

class MusicInfoView(dc.ui.View):
    def __init__(self, message: dc.Message = None,
                 guild_id: int = None, 
                 title: str = None, 
                 thumbnail: str = None, 
                 uploader: str = None, 
                 duration: int = None,
                 url: str = None):
        super().__init__(timeout=18000)
        self.guild_id = guild_id
        self.uploader = uploader
        self.duration = duration
        self.title = title
        self.thumbnail = thumbnail
        self.url = url
        self.embed = self.generate_embed(title=title, thumbnail=thumbnail, uploader=uploader, duration=duration)
        self.message = message
        self.is_deleted = False
        return None

    def generate_embed(self, title: str, thumbnail: str, uploader: str, duration: int):
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

    @dc.ui.button(label="清空序列 | Clear", style=dc.ButtonStyle.danger, row=1)
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

    @dc.ui.button(label="末曲移除 | Popback", style=dc.ButtonStyle.danger, row=1)
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
            all_server_queue.pop(interaction.guild.id)
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

if __name__ == "__main__":
    pass