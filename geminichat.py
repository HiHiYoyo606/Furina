import discord as dc
import asyncio
import logging
from generalmethods import GoogleSheet
from discord.ext import commands
from generalmethods import send_new_error_logging, send_new_info_logging
from google.generativeai import GenerativeModel

async def chat_fetch_full_history(bot: commands.Bot, channel: dc.TextChannel, retry_attempts: int = 0) -> list:
    """取得頻道的完整歷史訊息"""
    """回傳: [{"role": "user", "parts": "訊息內容"}]..."""
    try:
        history, messages = channel.history(limit=100), []
        async for message in history:  # 限制讀取最近 100 則
            if message.content.startswith("$re"):
                break
            
            if message.content.startswith("$skip"):
                continue
            if message.interaction_metadata is not None:
                continue
            
            role = "user" if message.author != bot.user else "model"
            messages.append({"role": role, "parts": [message.content]})

        messages.reverse()  # 讓對話順序從舊到新
        return messages
    
    except dc.HTTPException as e:
        if e.status != 429:
            await send_new_error_logging(bot=bot, message=f"HTTP error fetching history: {e.status} - {e.text}")
            return []
        
        retry_after = int(e.response.headers.get("Retry-After", 1))
        logging.warning(f"The request reached the rate limit! Retrying in {retry_after} seconds.")
        
        # 增加一點緩衝時間，避免剛好在邊界又觸發
        await asyncio.sleep(retry_after + 1)
        retry_attempts += 1
        return await chat_fetch_full_history(channel, retry_attempts)
    
    except Exception as e:
        await send_new_error_logging(bot=bot, message=f"Error fetching history: {e}")
        return []
    
async def chat_ask_question(model: GenerativeModel, bot: commands.Bot, question: dc.Message) -> str:
    """啟用Gemini詢問問題並回傳答案"""
    """回傳: 詢問的答案(string)"""
    # Persona prompts - consider moving to a config file or constants at the top
    PERSONA_PROMPT_BASE = "You are 'Furina de Fontaine' from the game 'Genshin Impact'."
    PERSONA_PROMPT_RELATIONSHIP = " and you are the user's girlfriend (deeply in love with them)."
    PERSONA_PROMPT_FORMATTING = "1. Format your response using Markdown. You are talking to them, not sending them message."
    PERSONA_PROMPT_LANGUAGE = "2. Answer in the same language as the user (if your response is in 中文,  you can ONLY USE 繁體中文-台灣(ZHTW), NOT ALLOWED TO USE the zhcn)."
    PERSONA_PROMPT_CONTEXT = "4. The new response's background depends on the previous history."
    PERSONA_PROMPT_CONCISENESS = "5. It's better not to say too much sentence in one message, you can wait the user provide more questions."

    user_name = question.author.name
    await send_new_info_logging(bot=bot, message=f"{user_name} has sent a question")
    full_history = await chat_fetch_full_history(bot=bot, channel=question.channel)
    
    system_prompt = f"{PERSONA_PROMPT_BASE}{PERSONA_PROMPT_RELATIONSHIP}"
    system_prompt += f"{PERSONA_PROMPT_FORMATTING}"
    system_prompt += f"{PERSONA_PROMPT_LANGUAGE}"
    system_prompt += f"3. The question is asked by {user_name}."
    system_prompt += f"{PERSONA_PROMPT_CONTEXT}"
    system_prompt += f"{PERSONA_PROMPT_CONCISENESS}"
    system_prompt += f"Question: {question.content}"

    real_question = system_prompt.strip()
    chat = model.start_chat(history=full_history)
    response = chat.send_message(real_question)

    return response.text

async def chat_sent_message_to_channel(bot: commands.Bot, original_message: dc.Message, message_to_send: str) -> None:
    """確保不超過 Discord 2000 字限制下發送訊息"""
    """回傳: None"""
    
    max_length = 2000
    for i in range(0, len(message_to_send), max_length):
        chunk = message_to_send[i:i + max_length]
        await original_message.channel.send(chunk)
        await asyncio.sleep(3)
    
    await send_new_info_logging(bot=bot, message=f"Furina has successfully sent message")

async def chat_process_message(bot: commands.Bot, model: GenerativeModel, message: dc.Message) -> None:
    """處理收到的訊息並產生回應"""
    """回傳: None"""
    TARGET_CHANNEL_IDS = await GoogleSheet.get_all_channels_from_gs()

    if message.author.id == bot.user.id:
        return  # 忽略自己發送的訊息
    
    # 測試區 
    if message.content.startswith("$ids"):
        await message.channel.send("```" + str(TARGET_CHANNEL_IDS) + f"```")
    # 測試區結尾
    
    if not (message.channel.id in TARGET_CHANNEL_IDS or isinstance(message.channel, dc.DMChannel)):
        return  # 忽略非目標頻道訊息
    if message.content.startswith("$skip") or message.content.startswith("$re"):
        return  # 忽略 $skip 指令
    
    try:
        response = await chat_ask_question(model=model, bot=bot, question=message)
        response_strip = response.strip()
        if not response_strip:
            await message.channel.send("Oops! I didn't get a response.")
            raise Exception("Empty response")
        
        await chat_sent_message_to_channel(bot, message, response_strip)
    except Exception as e:
        await send_new_error_logging(bot, f"Error processing message: {e}")