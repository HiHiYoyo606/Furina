"""
@bot.tree.command(name="status", description="確認芙寧娜是否在線 | Check if Furina is online.")
async def slash_status(interaction: dc.Interaction):
    # 確認芙寧娜是否在線
    # 回傳: None
    await interaction.response.send_message("# :white_check_mark::droplet:", ephemeral=True)
    await send_new_info_logging(bot=bot, message=f"{interaction.user} has used /status")
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
