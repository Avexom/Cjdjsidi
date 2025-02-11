
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode
import logging
import asyncio

logger = logging.getLogger('bot')
business_router = Router()

async def send_message_to_channels(bot, channels, message_text):
    sent_messages = []
    for channel in channels:
        max_retries = 3
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                temp_message = await bot.send_message(
                    chat_id=channel,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )
                if temp_message:
                    sent_messages.append(temp_message)
                    break
            except Exception as e:
                logger.error(f"Попытка {attempt + 1}/{max_retries}: Ошибка при отправке в канал {channel}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                continue
    return sent_messages
