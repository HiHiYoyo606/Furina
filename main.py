import discord as dc
import asyncio  # 加入 asyncio 避免 race condition
import random
from discord.app_commands import describe
from generalmethods import *
from views import *
from objects import *
from geminichat import chat_process_message
from musicfeatures import *
# from googlesearchmethods import GoogleSearchMethods

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
