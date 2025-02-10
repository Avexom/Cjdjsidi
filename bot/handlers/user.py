
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
import colorlog
from bot.assets.texts import Texts

logger = colorlog.getLogger('bot')
from bot.database import database as db
from bot.keyboards import user as kb

user_router = Router()

@user_router.message(Command("start"))
async def start_command(message: Message):
    """Обработка команды /start"""
    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await db.create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )
            await message.answer(Texts.START_NOT_CONNECTED)
        else:
            await message.answer(Texts.START_CONNECTED if user.business_bot_active else Texts.START_CONNECTED_NEW)
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")
