import discord as dc
from generalmethods import get_general_embed, send_new_error_logging, get_server_queue
from datetime import datetime, timedelta, timezone
from objects import *

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

class MusicInfoView(dc.ui.View):
    def __init__(self, message: dc.Message = None,
                 guild_id: int = None, 
                 title: str = None, 
                 thumbnail: str = None, 
                 uploader: str = None, 
                 duration: int = None,
                 url: str = None):
        super().__init__(timeout=18000)
        self.message = message
        self.guild_id = guild_id
        self.uploader = uploader
        self.duration = duration
        self.title = title
        self.thumbnail = thumbnail
        self.url = url

        self.embed = self.generate_embed(title=title, thumbnail=thumbnail, uploader=uploader, duration=duration)

    def generate_embed(self, title: str, thumbnail: str, uploader: str, duration: int):
        embed = get_general_embed(
            message=f"**{title}**\n",
            color=0x1DB954,
            title="🎶正在播放 | Now Playing",
        )
        embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="上傳者 | Uploader", value=uploader, inline=False)
        embed.add_field(name="⏳進度 | Progress", value="🔘□□□□□□□□□□□□□□", inline=False)

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
        playback_status[interaction.guild.id] = "paused"
        await interaction.response.send_message("> 已暫停播放序列 | Paused the play queue.", ephemeral=True)

    @dc.ui.button(label="▶️ 恢復 | Resume", style=dc.ButtonStyle.green, row=0)
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
            playback_status[interaction.guild.id] = "playing"

            await interaction.response.send_message("> 音樂已恢復播放 | Playback resumed.", ephemeral=True)
        except Exception as e:
            send_new_error_logging(f"[{interaction.guild.name}] Error resuming playback: {e}", to_discord=False)

    @dc.ui.button(label="⏭ 跳過 | Skip", style=dc.ButtonStyle.primary, row=0)
    async def skip(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("> 目前沒有歌曲正在播放 | No song is currently playing.", ephemeral=True)
            return

        voice_client.stop()
        await interaction.response.send_message("> 已跳過當前歌曲 | Skipped the current song.", ephemeral=False)

    @dc.ui.button(label="查看序列 | Queue", style=dc.ButtonStyle.secondary, row=1)
    async def queue(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return

        queue = all_server_queue[interaction.guild.id]
        if queue.empty():
            await interaction.response.send_message("> 播放序列是空的喔！| The queue is currently empty.", ephemeral=True)
            return

        items = list(queue._queue)
        titles = [f"{i+1}. {view.title}" for i, view in enumerate(items)]
        message = "\n".join("> " + titles)
        await interaction.response.send_message(f"當前播放序列 | Current play queue:\n{message}", ephemeral=False)

    @dc.ui.button(label="清空序列 | Clear", style=dc.ButtonStyle.danger, row=1)
    async def clear(self, interaction: dc.Interaction, button: dc.ui.Button):
        if isinstance(interaction.channel, dc.DMChannel):
            await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
            return
        
        queue = get_server_queue(interaction.guild.id)
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

        queue = get_server_queue(interaction.guild.id)
        if queue.empty():
            await interaction.response.send_message("> 播放序列是空的喔 | The queue is currently empty.", ephemeral=True)
            return
        poped_song = queue._queue.pop()
        
        await interaction.response.send_message(f"> 已將 {poped_song[1]} 移出播放序列。| Removed {poped_song[1]} from the queue.", ephemeral=False)

if __name__ == "__main__":
    pass