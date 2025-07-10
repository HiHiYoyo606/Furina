import discord as dc
import asyncio
import math
import logging
from generalmethods import get_general_embed
from datetime import datetime, timedelta, timezone
from objects import bot

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
            # Page 一般指令
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
            get_general_embed(message="自1.3.7版本起不支援語音指令 | Voice commands are not supported since version 1.3.7.", color=dc.Color.blue(), title="語音指令 | Voice Commands"),

            # Page 管理指令
            get_general_embed(message={
                "/createrole": "創建一個身分組(需擁有管理身分組權限) | Create a role.(Requires manage roles permission)",
                "/deleterole": "刪除一個身分組(需擁有管理身分組權限) | Delete a role.(Requires manage roles permission)",
                "/deletemessage": "刪除一定數量的訊息(需擁有管理訊息權限) | Delete a certain number of messages.(Requires manage messages permission)",
            }, color=dc.Color.blue(), title="管理指令 | Manage Commands"),

            # Page 操作說明
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

if __name__ == "__main__":
    pass