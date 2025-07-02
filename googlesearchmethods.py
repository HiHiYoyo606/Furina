import asyncio
import logging
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from generalmethods import send_new_error_logging

load_dotenv()
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

async def google_search(query: str, num_results: int = 10, start_index: int = 1):
    """使用 Google Custom Search API 搜尋圖片並回傳圖片 URL 列表。"""
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_CSE_ID:
        await send_new_error_logging("缺少 Google Search API Key 或 CSE ID，無法執行圖片搜尋。")
        return []
    try:
        # googleapiclient is blocking, run in executor
        loop = asyncio.get_running_loop()
        service = await loop.run_in_executor(None, lambda: build("customsearch", "v1", developerKey=GOOGLE_SEARCH_API_KEY))
        # The search call might also be blocking
        result = await loop.run_in_executor(None, lambda: service.cse().list(
            q=query,
            cx=GOOGLE_CSE_ID,
            searchType='image', # Specify image search
            num=min(num_results, 10), # Ensure num is never more than 10
            start=start_index,       # Starting index for results
            safe='high'         # Optional: filter results ('medium', 'off')
        ).execute())

        # Extract image links from results
        items = result.get('items', [])
        image_urls = [item.get('link') for item in items if item.get('link')] # Ensure link exists
        return image_urls
    except HttpError as e:
        error_details = e.content.decode('utf-8') if e.content else '(No details)'
        log_message = f"Google Search API 發生 HTTP 錯誤: {e.resp.status} - {error_details}"
        if e.resp.status == 429:
            log_message += " (可能已達每日查詢配額)"
        await send_new_error_logging(log_message)
        return []
    except Exception as e:
        logging.exception(f"執行 Google 圖片搜尋時發生未預期的錯誤: {e}")
    
    return []