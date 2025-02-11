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
                # Проверяем права бота в канале
                bot_member = await bot.get_chat_member(chat_id=channel, user_id=(await bot.me()).id)
                if bot_member.status not in ['administrator', 'creator']:
                    logger.error(f"Бот не имеет прав администратора в канале {channel}")
                    continue

                temp_message = await bot.send_message(
                    chat_id=channel,
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                if temp_message:
                    sent_messages.append(temp_message)
                    logger.info(f"✅ Сообщение успешно отправлено в канал {channel}")
                    break
            except Exception as e:
                error_msg = str(e).lower()
                if "message can't be forwarded" in error_msg:
                    logger.warning(f"Сообщение не может быть переслано в канал {channel} из-за ограничений")
                    break
                elif "bot was kicked" in error_msg or "chat not found" in error_msg:
                    logger.error(f"Бот не имеет доступа к каналу {channel}")
                    break
                else:
                    logger.error(f"Попытка {attempt + 1}/{max_retries}: Ошибка при отправке в канал {channel}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    continue
    return sent_messages