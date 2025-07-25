import random
from objects import bot, developers_id
from discord.app_commands import describe
from views import *
from generalmethods import *

@bot.tree.command(name="help", description="顯示說明訊息 | Show the informations.")
async def slash_help(interaction: dc.Interaction):
    """顯示說明訊息"""
    """回傳: None"""

    view = HelpView()
    await interaction.response.send_message(
        embed=view.pages[0], view=view, ephemeral=True
    )

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /help.")

@bot.tree.command(name="version", description="查詢Furina的版本 | Check Furina's version.")
async def slash_version(interaction: dc.Interaction):
    """查詢Furina的版本"""
    """回傳: None"""
    await interaction.response.send_message(f"> 版本 | Version: {VERSION}")

@bot.tree.command(name="randomnumber", description="抽一個區間內的數字 | Get a random number in a range.")
@describe(min_value="隨機數字的最小值(預設 1) | The minimum value for the random number. (default 1)")
@describe(max_value="隨機數字的最大值(預設 100) | The maximum value for the random number. (default 100)")
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

@bot.tree.command(name="createrole", description="創建一個身分組(需擁有管理身分組權限) | Create a role. (Requires manage roles permission)")
@describe(role_name="身分組的名稱 | The name of the role.")
@describe(r="rgb紅色碼(0~255 預設0) | r value. (0~255, default 0)")
@describe(g="rgb綠色碼(0~255 預設0) | g value. (0~255, default 0)")
@describe(b="rgb藍色碼(0~255 預設0) | b value. (0~255, default 0)")
@describe(hoist="是否分隔顯示(預設不分隔) | Whether to hoist the role. (default False)")
@describe(mentionable="是否可提及(預設是) | Whether the role can be mentioned. (default True)")
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

@bot.tree.command(name="deleterole", description="刪除一個身分組(需擁有管理身分組權限) | Delete a role. (Requires manage roles permission)")
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

@bot.tree.command(name="deletemessage", description="刪除一定數量的訊息(需擁有管理訊息權限) | Delete a certain number of messages. (Requires manage messages permission)")
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
    pages = await view.get_pages()
    await interaction.response.send_message(view=view, embed=pages[0], ephemeral=False)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /whois to view {user.name}'s infomation.")

@bot.tree.command(name="serverinfo", description="顯示伺服器資訊 | Show server information.")
@describe(roleperpage="每頁顯示的身分組數量(預設10) | The number of roles to display per page. (default 10)")
async def slash_server_info(interaction: dc.Interaction, roleperpage: int = 10):
    """顯示伺服器資訊"""
    """回傳: None"""
    if isinstance(interaction.channel, dc.DMChannel):
        await interaction.response.send_message("> 這個指令只能用在伺服器中 | This command can only be used in a server.", ephemeral=True)
        return
    
    view = ServerInfoView(interaction, role_per_page=roleperpage)
    await interaction.response.send_message(embed=view.pages[0], view=view, ephemeral=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /serverinfo to view server \"{interaction.guild.name}\".")

@bot.tree.command(name="channelinfo", description="顯示頻道資訊 | Show channel information.")
@describe(channel_id="要查詢的頻道ID(留空則為當前頻道) | The id of the channel to be queried. (leave empty for current channel)")
async def slash_channel_info(interaction: dc.Interaction, channel_id: str = None):
    if channel_id is None:
        channel_id = interaction.channel.id

    if isinstance(channel_id, str) and not channel_id.isdigit():
        await interaction.response.send_message("> 這不是一個有效的ID | This is not a valid ID.")
        return
    
    channel_id = int(channel_id)
    view = ChannelInfoView(channel_id)
    embed = await view.get_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
@describe(channel_id="要新增的頻道的ID(留空則為當前頻道) | The ID of the channel to add. (leave empty for current channel)")
async def slash_add_channel(interaction: dc.Interaction, channel_id: str = None):
    """新增一個和芙寧娜對話的頻道"""
    """回傳: None"""
    if channel_id is None:
        channel_id = str(interaction.channel.id)
    if not channel_id.isdigit():
        await interaction.response.send_message("> 這不是一個有效的ID | This is not a valid ID.")

    channel_list = [e for e in (await GoogleSheet.get_all_channels_from_gs())]
    if channel_id not in channel_list:
        GoogleSheet.add_channel_to_gs(channel_id)
        await interaction.response.send_message(f"> ✅已新增頻道 `{channel_id}`")
    else:
        await interaction.response.send_message("> ⚠️此頻道ID 已存在", ephemeral=True)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /addchannel with {channel_id} added.")

@bot.tree.command(name="removechannel", description="從名單中刪除一個頻道ID | Remove a channel ID from the list.")
@describe(channel_id="要刪除的頻道ID(留空則為當前頻道) | The ID of the channel to remove (leave empty for current channel).")
async def slash_remove_channel(interaction: dc.Interaction, channel_id: str = None):
    """從名單中刪除一個頻道ID"""
    """回傳: None"""
    if channel_id is None:
        channel_id = interaction.channel.id

    if isinstance(channel_id, str) and not channel_id.isdigit():
        await interaction.response.send_message("> 這不是一個有效的ID | This is not a valid ID.")
        return
    
    try:
        all_channels = await GoogleSheet.get_all_channels_from_gs()
        if channel_id in all_channels:
            GoogleSheet.remove_channel_from_gs(channel_id)
            await interaction.response.send_message(f"> 已移除頻道 `{channel_id}` | Removed channel `{channel_id}`.")
        else:
            await interaction.response.send_message("> 此頻道不在名單上 | This channel is not in the list.", ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message("> 尚未建立頻道資料，無法刪除 | The data for channels does not exist.", ephemeral=True)

    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /removechannel with {channel_id} removed.")

@bot.tree.command(name="reporterror", description="回報你所發現的錯誤 | Report an error you found.")
@describe(content="錯誤內容 | Error content.")
async def slash_report_error(interaction: dc.Interaction, content: str):
    """回報你所發現的錯誤"""
    """回傳: None"""
    await add_error(bot=bot, interaction=interaction, content=content)

@bot.tree.command(name="serving", description="查詢Furina存在的所有伺服器(僅限Furina的開發者) | Check Furina's servers. (Only for Furina's developers)")
async def slash_serving(interaction: dc.Interaction):
    """查詢Furina存在的所有伺服器"""
    """回傳: None"""

    if interaction.user.id not in developers_id:
        await interaction.response.send_message("> 此指令僅限Furina的開發者使用 | This command is only for Furina's developers.", ephemeral=True)
        return
    
    guilds = bot.guilds
    guild_names = ["> " + guild.name for guild in guilds]
    await interaction.response.send_message("\n".join(guild_names))

@bot.tree.command(name="fixederror", description="向使用者回報錯誤已修復(僅限Furina的開發者) | Report an error has been fixed. (Only for Furina's developers)")
@describe(hashcode="錯誤代碼 | Error code.")
@describe(hint="給使用者的提示 | Hint for the user.")
async def slash_fixed_error(interaction: dc.Interaction, hashcode: str, hint: str = None):
    await fix_error(bot=bot, interaction=interaction, hashcode=hashcode, hint=hint)

if __name__ == "__main__":
    pass