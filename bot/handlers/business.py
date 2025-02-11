
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
import logging
import asyncio
from ..database import database as db

logger = logging.getLogger('bot')
business_router = Router()

async def send_message_to_channels(bot: Bot, channels: list, message: Message):
    """
    Пересылает сообщение в указанные каналы
    """
    sent_messages = []
    for channel in channels:
        max_retries = 3
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                # Пытаемся переслать сообщение
                forwarded = await message.forward(chat_id=channel)
                if forwarded:
                    sent_messages.append(forwarded)
                    logger.info(f"✅ Сообщение успешно переслано в канал {channel}")
                    break
            except Exception as e:
                error_msg = str(e).lower()
                if "message can't be forwarded" in error_msg:
                    try:
                        # Если пересылка не удалась, пробуем отправить копию
                        copied = await message.copy_to(chat_id=channel)
                        if copied:
                            sent_messages.append(copied)
                            logger.info(f"✅ Копия сообщения отправлена в канал {channel}")
                            break
                    except Exception as copy_error:
                        logger.error(f"❌ Ошибка при копировании сообщения: {copy_error}")
                elif "bot was kicked" in error_msg or "chat not found" in error_msg:
                    logger.error(f"❌ Бот не имеет доступа к каналу {channel}")
                    break
                else:
                    logger.error(f"Попытка {attempt + 1}/{max_retries}: Ошибка при отправке в канал {channel}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    continue
    return sent_messages

@business_router.message()
async def handle_business_message(message: Message, bot: Bot):
    """
    Обрабатывает входящие бизнес сообщения
    """
    try:
        user = await db.get_user(message.from_user.id)
        if not user or not user.business_bot_active:
            return

        channels = await db.get_user_channels(message.from_user.id)
        if not channels:
            await message.answer("❌ У вас нет настроенных каналов для пересылки")
            return

        sent = await send_message_to_channels(bot, channels, message)
        if sent:
            await message.answer(f"✅ Сообщение переслано в {len(sent)} каналов")
        else:
            await message.answer("❌ Не удалось переслать сообщение")

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке бизнес сообщения: {e}")
        await message.answer("❌ Произошла ошибка при пересылке сообщения")
