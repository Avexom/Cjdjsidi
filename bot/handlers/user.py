import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging
import colorlog
import asyncio
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

@user_router.message(F.text.casefold() == "онлайн+")
async def online_command(message: Message):

@user_router.callback_query(F.data == "close")
async def close_callback(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Ошибка при закрытии сообщения: {e}")
        await callback.answer("Не удалось закрыть сообщение")

    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Профиль не найден")
            return

        # Включаем модуль онлайн
        await db.toggle_module(message.from_user.id, "online")
        await message.answer("✅ Модуль 'Онлайн' включен!")

    except Exception as e:
        logger.error(f"Ошибка при включении модуля онлайн: {e}")
        await message.answer("❌ Произошла ошибка")

@user_router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    logger.info(f"🔘 Юзер {message.from_user.id} нажал кнопку 'Профиль'")
    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Профиль не найден")
            return

        profile_text = Texts.profile_text(
            user_id=user.telegram_id,
            first_name=message.from_user.first_name or user.first_name or "Неизвестный пользователь",
            subscription_end_date=user.subscription_end_date,
            count_messages=user.active_messages_count,
            count_messages_deleted=user.deleted_messages_count,
            count_messages_edited=user.edited_messages_count
        )
        await message.answer(profile_text, reply_markup=kb.profile_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}")
        await message.answer("❌ Произошла ошибка при загрузке профиля")

from aiogram.fsm.context import FSMContext

@user_router.message(F.text == "💳 Купить подписку")
async def buy_subscription_handler(message: Message, state: FSMContext):
    logger.info(f"🔘 Юзер {message.from_user.id} нажал кнопку 'Купить подписку'")
    try:
        user = await db.get_user(message.from_user.id)
        if user and user.subscription_end_date and user.subscription_end_date > datetime.now():
            await message.answer(Texts.SUBSCRIPTION_BUY_ALREADY_ACTIVE)
            return

        from bot.services.payments import create_invoice

        price = await db.get_subscription_price()
        bot_info = await message.bot.get_me()
        invoice = await create_invoice(price, message.from_user.id, bot_info.username)

        if not invoice["pay_url"]:
            await message.answer("❌ Ошибка при создании платежа")
            return

        # Сохраняем invoice_id для последующей проверки
        await state.update_data(invoice_id=invoice["invoice_id"])

        await message.answer(
            Texts.subscription_buy_text(str(price)),
            reply_markup=kb.get_payment_keyboard(invoice["pay_url"], invoice["invoice_id"])
        )

        # Запускаем проверку платежа
        asyncio.create_task(check_payment_status(message, invoice["invoice_id"]))
    except Exception as e:
        logger.error(f"Ошибка при покупке подписки: {e}")
        await message.answer("❌ Произошла ошибка при создании платежа")

@user_router.message(F.text == "⚙️ Функции")
async def functions_handler(message: Message):
    logger.info(f"🔘 Юзер {message.from_user.id} нажал кнопку 'Функции'")
    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Профиль не найден")
            return

        # Проверяем подписку
        if not user.subscription_end_date or user.subscription_end_date < datetime.now():
            await message.answer("❌ Твоя подписка закончилась!\n\nНажми на кнопку '💳 Купить подписку' чтобы получить доступ к функциям.")
            return

        user_settings = {
            'notifications_enabled': user.notifications_enabled,
            'edit_notifications': user.edit_notifications,
            'delete_notifications': user.delete_notifications
        }
        await message.answer("Выберите функцию:", reply_markup=kb.get_functions_keyboard(user_settings))
    except Exception as e:
        logger.error(f"Ошибка при отображении функций: {e}")
        await message.answer("❌ Произошла ошибка при загрузке функций")

@user_router.callback_query(lambda c: c.data.startswith("toggle_") and not c.data.startswith("toggle_module_"))
async def toggle_function_handler(callback: CallbackQuery):
    try:
        function_type = callback.data.replace("toggle_", "")
        user = await db.get_user(callback.from_user.id)
        if not user:
            await callback.answer("❌ Профиль не найден")
            return

        new_state = await db.toggle_notification(callback.from_user.id, function_type)

        user_settings = {
            'notifications_enabled': user.notifications_enabled,
            'edit_notifications': user.edit_notifications,
            'delete_notifications': user.delete_notifications
        }

        # Обновляем состояние для конкретной функции
        if function_type == "all":
            user_settings['notifications_enabled'] = new_state
        elif function_type == "edit":
            user_settings['edit_notifications'] = new_state
        elif function_type == "delete":
            user_settings['delete_notifications'] = new_state

        try:
            await callback.message.edit_text(
                "Выберите функцию:",
                reply_markup=kb.get_functions_keyboard(user_settings)
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                raise
        await callback.answer(f"{'✅ Включено' if new_state else '❌ Выключено'}")

    except Exception as e:
        logger.error(f"Ошибка при переключении функции: {e}")
        await callback.answer("❌ Произошла ошибка")

@user_router.callback_query(lambda c: c.data.startswith("check_payment_"))
async def check_payment_callback(callback: CallbackQuery):
    try:
        invoice_id = int(callback.data.replace("check_payment_", ""))
        from bot.services.payments import check_payment
        from sqlalchemy import update
        from bot.database.database import User

        if await check_payment(invoice_id):
            # Платеж успешен
            end_date = datetime.now() + timedelta(days=30)
            await db.create_subscription(
                user_telegram_id=callback.from_user.id,
                end_date=end_date
            )
            # Обновляем дату окончания подписки в таблице users
            async with db.get_db_session() as session:
                await session.execute(
                    update(User)
                    .where(User.telegram_id == callback.from_user.id)
                    .values(subscription_end_date=end_date)
                )
            await callback.message.edit_text("🎉 Оплата прошла успешно! Подписка активирована на 30 дней.")
        else:
            await callback.answer("❌ Оплата еще не поступила. Попробуйте позже.", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при проверке оплаты: {e}")
        await callback.answer("❌ Произошла ошибка при проверке оплаты", show_alert=True)

@user_router.message(F.text == "💬 Поддержка")
async def support_handler(message: Message):
    logger.info(f"🔘 Юзер {message.from_user.id} нажал кнопку 'Поддержка'")
    """Обработчик кнопки поддержки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Чат поддержки", url="https://t.me/+Q1L5k9NvsRdkNzVi")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
        ]
    )
    await message.answer(Texts.SUPPORT_TEXT, reply_markup=keyboard)

@user_router.message(F.text == "📝 Отзывы")
async def reviews_handler(message: Message):
    logger.info(f"🔘 Юзер {message.from_user.id} нажал кнопку 'Отзывы'")
    """Обработчик кнопки отзывов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Канал с отзывами", url="https://t.me/+VEgXUlw1NZA1MDcy")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
        ]
    )
    await message.answer(Texts.REVIEWS_TEXT, reply_markup=keyboard)

@user_router.message(F.text == "📱 Модули")
async def modules_handler(message: Message):
    logger.info(f"🔘 Юзер {message.from_user.id} нажал кнопку 'Модули'")
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Профиль не найден")
        return

    # Проверяем подписку
    if not user.subscription_end_date or user.subscription_end_date < datetime.now():
        await message.answer("❌ Твоя подписка закончилась!\n\nНажми на кнопку '💳 Купить подписку' чтобы получить доступ к модулям.")
        return

    user_settings = {
        'module_calc': user.module_calc_enabled if hasattr(user, 'module_calc_enabled') else False,
        'module_love': user.module_love_enabled if hasattr(user, 'module_love_enabled') else False
    }
    await message.answer("Выберите модуль:", reply_markup=kb.get_modules_keyboard(user_settings))
async def check_payment_status(message: Message, invoice_id: int):
    """Проверяем статус платежа и выдаем подписку"""
    from bot.services.payments import check_payment, delete_invoice

    max_attempts = 60  # 30 минут (проверка каждые 30 секунд)
    attempt = 0

    while attempt < max_attempts:
        if await check_payment(invoice_id):
            # Платеж успешен
            await db.create_subscription(
                user_telegram_id=message.from_user.id,
                end_date=datetime.now() + timedelta(days=30)
            )
            await message.answer("🎉 Оплата прошла успешно! Подписка активирована на 30 дней.")
            await delete_invoice(invoice_id)
            return

        attempt += 1
        await asyncio.sleep(30)  # Ждем 30 секунд между проверками

    # Если платеж не прошел за отведенное время
    await message.answer("❌ Время ожидания оплаты истекло. Попробуйте снова.")
    await delete_invoice(invoice_id)
@user_router.callback_query(lambda c: c.data.startswith("toggle_module_"))
async def toggle_module_handler(callback: CallbackQuery):
    try:
        module_type = callback.data.replace("toggle_module_", "")
        user = await db.get_user(callback.from_user.id)
        if not user:
            await callback.answer("❌ Профиль не найден")
            return

        # Проверяем подписку
        if not user.subscription_end_date or user.subscription_end_date < datetime.now():
            await callback.answer("❌ Требуется подписка для использования модулей", show_alert=True)
            return

        new_state = await db.toggle_module(callback.from_user.id, module_type)
        logger.info(f"🔄 Пользователь {callback.from_user.id} переключил модуль {module_type} в состояние: {new_state}")

        # Обновляем объект пользователя после изменения
        user = await db.get_user(callback.from_user.id)

        user_settings = {
            'module_calc': user.calc_enabled,
            'module_love': user.love_enabled
        }
        user_settings[f'module_{module_type}'] = new_state

        try:
            await callback.message.edit_text(
                "Выберите модуль:",
                reply_markup=kb.get_modules_keyboard(user_settings)
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                raise

        await callback.answer(f"Модуль {module_type} {'✅ включен' if new_state else '❌ выключен'}")
    except Exception as e:
        logger.error(f"Ошибка при переключении модуля: {e}")
        await callback.answer("❌ Произошла ошибка")