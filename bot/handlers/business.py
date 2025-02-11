from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
import logging
from ..database import database as db

logger = logging.getLogger('bot')
business_router = Router()

@business_router.message()
async def handle_business_message(message: Message, bot: Bot):
    """
    Обрабатывает входящие бизнес сообщения
    """
    try:
        # Проверяем, активен ли бизнес-бот для пользователя
        user = await db.get_user(message.from_user.id)
        if not user or not user.business_bot_active:
            return

        # Получаем список каналов пользователя
        channels = await db.get_user_channels(message.from_user.id) 
        if not channels:
            await message.answer("❌ У вас нет настроенных каналов для пересылки")
            return

        # Пересылаем сообщение в каждый канал
        success_count = 0
        for channel in channels:
            try:
                await message.forward(chat_id=channel)
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка при пересылке в канал {channel}: {e}")
                continue

        if success_count > 0:
            await message.answer(f"✅ Сообщение переслано в {success_count} каналов")
        else:
            await message.answer("❌ Не удалось переслать сообщение")

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке бизнес сообщения: {e}")
        await message.answer("❌ Произошла ошибка при пересылке сообщения")