from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel, PositiveInt
from async_lru import alru_cache  # Используем async_lru для кэширования

import bot.database.database as db
import bot.assets.texts as texts
import bot.keyboards.user as kb
#from config import HISTORY_GROUP_ID # Removed
from bot.services.payments import create_invoice, check_payment, delete_invoice

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_router = Router()

# Модели для валидации
class PaymentRequest(BaseModel):
    invoice_id: PositiveInt

# Middleware для проверки пользователя
class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = await db.get_user(telegram_id=event.from_user.id)
        if user is None:
            logger.info(f"Новый пользователь: {event.from_user.id}")
            await event.answer(texts.start_not_connected)
            return
        data["user"] = user
        logger.info(f"Пользователь {event.from_user.id} авторизован")
        return await handler(event, data)

user_router.message.middleware(UserMiddleware())

# Кэширование цены подписки
@alru_cache(maxsize=1)  # Используем async_lru для асинхронного кэширования
async def get_cached_subscription_price():
    return await db.get_subscription_price()

# Генерация текста для профиля
async def get_user_profile_text(user, subscription, message):
    return texts.profile_text(
        user_id=user.telegram_id,
        name=message.from_user.first_name,
        subscription_end_date=subscription.end_date if subscription else None,
        count_messages=user.active_messages_count,
        count_messages_deleted=user.deleted_messages_count,
        count_messages_edited=user.edited_messages_count
    )

# Хэндлеры
@user_router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()  # Сброс состояния, если это необходимо
    user = await db.get_user(telegram_id=message.from_user.id)
    if user is None:
        await message.answer(texts.about_bot, parse_mode=ParseMode.HTML)
    elif user.business_bot_active:
        await message.answer(texts.start_connected, reply_markup=kb.start_connection_keyboard)
    else:
        await message.answer(texts.start_not_connected)

@user_router.message(F.text == "👤 Профиль")
async def profile(message: Message, user: dict):
    await message.delete()
    subscription = await db.get_subscription(user_telegram_id=message.from_user.id)
    text = await get_user_profile_text(user, subscription, message)
    await message.answer(text=text, reply_markup=kb.profile_keyboard)

@user_router.message(F.text == "💳 Купить подписку")
async def buy_subscription(message: Message, user: dict):
    await message.delete()
    subscription = await db.get_subscription(user_telegram_id=message.from_user.id)
    if subscription:
        await message.answer(text=texts.Texts.SUBSCRIPTION_BUY_ALREADY_ACTIVE, reply_markup=kb.close_keyboard)
    else:
        me = await message.bot.me()
        price = await get_cached_subscription_price()
        payment_data = await create_invoice(float(price), message.from_user.id, me.username)

        await message.answer(
            text=texts.subscription_buy_text(price=price),
            reply_markup=kb.get_payment_keyboard(payment_data["pay_url"], payment_data["invoice_id"])
        )

@user_router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_handler(callback: CallbackQuery):
    try:
        invoice_id = int(callback.data.split("_")[-1])
        request = PaymentRequest(invoice_id=invoice_id)

        is_paid = await check_payment(request.invoice_id)
        if is_paid:
            await db.create_subscription(user_telegram_id=callback.from_user.id, end_date=datetime.now() + timedelta(days=30))
            await callback.answer(text=texts.subscription_buy_success)
            await callback.message.edit_text(text=texts.subscription_buy_success_text)
            logger.info(f"Пользователь {callback.from_user.id} успешно оплатил подписку.")
        else:
            await callback.answer(text=texts.subscription_buy_failed)
            logger.warning(f"Пользователь {callback.from_user.id} не оплатил подписку.")
    except ValueError as e:
        await callback.answer(text=f"Некорректные данные: {e}")
        logger.error(f"Ошибка при проверке платежа: {e}")
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        await callback.answer(text="Произошла ошибка при проверке платежа.")

@user_router.callback_query(F.data.startswith("delete_invoice_"))
async def delete_invoice_handler(callback: CallbackQuery):
    try:
        await callback.answer()
        await callback.message.delete()
        invoice_id = int(callback.data.split("_")[-1])
        await delete_invoice(invoice_id)
    except ValueError as e:
        await callback.answer(text=f"Некорректные данные: {e}")
    except Exception as e:
        logger.error(f"Ошибка при удалении инвойса: {e}")
        await callback.answer(text="Произошла ошибка при удалении инвойса.")

@user_router.callback_query(F.data.startswith("show_history_"))
async def show_history(callback: CallbackQuery):
    try:
        subscription = await db.get_subscription(user_telegram_id=callback.from_user.id)
        if subscription is None:
            await callback.answer(text=texts.subscription_ended, show_alert=True)
            return

        message_id = callback.data.split("_")[-1]
        message_edit_history = await db.get_message_edit_history(message_id)
        
        if not message_edit_history or not message_edit_history.get('old_message'):
            await callback.answer("История сообщения не найдена", show_alert=True)
            return
            
        old_message = message_edit_history['old_message']
        
        # Сначала отправляем новое сообщение
        sent_message = await callback.message.answer(
            text=f"История редактирования сообщения {old_message.message_id}",
            reply_markup=kb.close_keyboard
        )
        
        success = False
        try:
            # Пробуем отправить оригинальное сообщение
            await callback.bot.copy_message(
                chat_id=callback.message.chat.id,
                from_chat_id=old_message.chat_id,
                message_id=old_message.temp_message_id,
                reply_markup=kb.close_keyboard
            )
            success = True
            
            # Отправляем историю изменений
            if message_edit_history.get('message_edit_history'):
                for edit in message_edit_history['message_edit_history']:
                    try:
                        await callback.bot.copy_message(
                            chat_id=callback.message.chat.id,
                            from_chat_id=edit.chat_id,
                            message_id=edit.temp_message_id,
                            reply_markup=kb.close_keyboard
                        )
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Ошибка при копировании сообщения: {e}")
            if not success:
                await sent_message.edit_text(
                    "К сожалению, оригинальное сообщение недоступно",
                    reply_markup=kb.close_keyboard
                )
        
        # Удаляем оригинальное сообщение только после успешной отправки новых
        await callback.message.delete()
        
    except Exception as e:
        logger.error(f"Ошибка при показе истории: {e}")
        await callback.answer(text="Произошла ошибка при показе истории", show_alert=True)

@user_router.callback_query(F.data == "close")
async def close(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

@user_router.message(F.text == "тест")
async def test(message: Message):
    await db.create_subscription(user_telegram_id=message.from_user.id, end_date=datetime.now() + timedelta(days=30))
    await message.answer(text="Подписка создана")