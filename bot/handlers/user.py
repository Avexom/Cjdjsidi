
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
            await message.answer(Texts.START_NOT_CONNECTED, reply_markup=kb.start_connection_keyboard)
        else:
            await message.answer(
                Texts.START_CONNECTED if user.business_bot_active else Texts.START_CONNECTED_NEW,
                reply_markup=kb.start_connection_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")

@user_router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Профиль не найден")
            return
        
        profile_text = Texts.profile_text(
            user_id=user.telegram_id,
            name=user.first_name,
            subscription_end_date=user.subscription_end_date,
            count_messages=user.count_messages,
            count_messages_deleted=user.count_messages_deleted,
            count_messages_edited=user.count_messages_edited
        )
        await message.answer(profile_text, reply_markup=kb.profile_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}")
        await message.answer("❌ Произошла ошибка при загрузке профиля")

@user_router.message(F.text == "💳 Купить подписку")
async def buy_subscription_handler(message: Message):
    try:
        user = await db.get_user(message.from_user.id)
        if user and user.subscription_end_date and user.subscription_end_date > datetime.now():
            await message.answer(Texts.SUBSCRIPTION_BUY_ALREADY_ACTIVE)
            return
            
        price = await db.get_subscription_price()
        await message.answer(
            Texts.subscription_buy_text(str(price)),
            reply_markup=kb.get_payment_keyboard("payment_url", 123)  # Замените на реальные значения
        )
    except Exception as e:
        logger.error(f"Ошибка при покупке подписки: {e}")
        await message.answer("❌ Произошла ошибка при создании платежа")

@user_router.message(F.text == "⚙️ Функции")
async def functions_handler(message: Message):
    await message.answer("Выберите функцию:", reply_markup=kb.functions_keyboard)

@user_router.message(F.text == "📱 Модули")
async def modules_handler(message: Message):
    await message.answer("Выберите модуль:", reply_markup=kb.modules_keyboard)
