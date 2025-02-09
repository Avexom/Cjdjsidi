
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
import colorlog
from bot.assets import texts

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
            await message.answer(texts.Texts.START_NOT_CONNECTED)
        else:
            await message.answer(texts.Texts.START_CONNECTED, reply_markup=kb.start_connection_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")

@user_router.message(F.text == "👤 Профиль")
async def profile_command(message: Message):
    """Обработка кнопки Профиль"""
    try:
        user = await db.get_user(message.from_user.id)
        if user:
            profile_text = await texts.Texts.generate_profile_text(
                name=message.from_user.first_name,
                user_id=message.from_user.id,
                subscription_status="Активна" if user.subscription_end and user.subscription_end > datetime.now() else "Неактивна",
                count_messages=await db.count_user_messages(message.from_user.id),
                count_messages_deleted=0,  # Тут нужно добавить подсчет из БД
                count_messages_edited=0    # Тут нужно добавить подсчет из БД
            )
            await message.answer(profile_text, reply_markup=kb.profile_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@user_router.message(F.text == "⚙️ Функции")
async def functions_command(message: Message):
    """Обработка кнопки Функции"""
    try:
        await message.answer("Выберите функции для настройки:", reply_markup=kb.functions_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении функций: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@user_router.message(F.text == "📱 Модули")
async def modules_command(message: Message):
    """Обработка кнопки Модули"""
    try:
        await message.answer("Выберите модули для настройки:", reply_markup=kb.modules_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении модулей: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@user_router.callback_query(F.data == "close")
async def close_keyboard(callback: CallbackQuery):
    """Обработка кнопки закрытия"""
    await callback.message.delete()



