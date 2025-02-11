
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
    Пересылает сообщение в указанные каналы с повторными попытками
    """
    sent_messages = []
    for channel in channels:
        max_retries = 3
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                # Сначала пробуем переслать
                forwarded = await message.forward(chat_id=channel)
                if forwarded:
                    sent_messages.append(forwarded)
                    logger.info(f"✅ Блять, сообщение успешно переслано в канал {channel}")
                    break
            except Exception as e:
                error_msg = str(e).lower()
                if "message can't be forwarded" in error_msg:
                    try:
                        # Если пересылка не прокатила, пробуем copy_to
                        copied = await message.copy_to(chat_id=channel)
                        if copied:
                            sent_messages.append(copied)
                            logger.info(f"✅ Хуячим копию сообщения в канал {channel}")
                            break
                    except Exception as copy_error:
                        logger.error(f"❌ Бля, ошибка при копировании: {copy_error}")
                elif "bot was kicked" in error_msg or "chat not found" in error_msg:
                    logger.error(f"❌ Нахуй, бота выпнули из канала {channel}")
                    break
                else:
                    logger.error(f"Попытка {attempt + 1}/{max_retries}: Ошибка отправки в канал {channel}: {e}")
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
            await message.answer("❌ У тебя нет настроенных каналов, еблан!")
            return

        sent = await send_message_to_channels(bot, channels, message)
        if sent:
            await message.answer(f"✅ Охуенно! Сообщение переслано в {len(sent)} каналов")
        else:
            await message.answer("❌ Бля, не удалось переслать сообщение никуда")

    except Exception as e:
        logger.error(f"❌ Пизда рулю, ошибка в бизнес сообщении: {e}")
        await message.answer("❌ Произошла какая-то хуйня при пересылке сообщения")
