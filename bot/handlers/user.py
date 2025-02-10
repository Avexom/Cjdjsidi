import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
        subscription = await db.get_subscription(message.from_user.id)
        if user:
            profile_text = texts.Texts.profile_text(
                name=message.from_user.first_name,
                user_id=message.from_user.id,
                subscription_end_date=subscription.end_date if subscription else None,
                count_messages=user.active_messages_count,
                count_messages_deleted=user.deleted_messages_count,
                count_messages_edited=user.edited_messages_count
            )
            await message.answer(profile_text, reply_markup=kb.profile_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@user_router.message(F.text == "⚙️ Функции")
async def functions_command(message: Message):
    """Обработка кнопки Функции"""
    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Не удалось найти ваш профиль. Используйте /start для регистрации.")
            return
            
        notification_status = "🔔 Вкл." if user.notifications_enabled else "🔕 Выкл."
        edit_status = "✅ Вкл." if user.edit_notifications else "❌ Выкл."
        delete_status = "✅ Вкл." if user.delete_notifications else "❌ Выкл."
        
        text = f"⚙️ Настройки функций:\n\n" \
               f"🔔 Уведомления: {notification_status}\n" \
               f"📝 Отслеживание изменений: {edit_status}\n" \
               f"🗑 Отслеживание удалений: {delete_status}"
               
        await message.answer(text, reply_markup=kb.get_functions_keyboard(
            notifications_enabled=user.notifications_enabled,
            edit_enabled=user.edit_notifications,
            delete_enabled=user.delete_notifications
        ))
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

@user_router.callback_query(F.data == "toggle_all_notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Обработка включения/выключения всех уведомлений"""
    try:
        settings = await db.toggle_notification(callback.from_user.id, "notifications")
        
        notification_status = "🔔 Вкл." if settings["notifications_enabled"] else "🔕 Выкл."
        edit_status = "✅ Вкл." if settings["edit_notifications"] else "❌ Выкл."
        delete_status = "✅ Вкл." if settings["delete_notifications"] else "❌ Выкл."
        
        text = f"⚙️ Настройки функций:\n\n" \
               f"🔔 Уведомления: {notification_status}\n" \
               f"📝 Отслеживание изменений: {edit_status}\n" \
               f"🗑 Отслеживание удалений: {delete_status}"
               
        await callback.message.edit_text(
            text=text,
            reply_markup=kb.get_functions_keyboard(
                notifications_enabled=settings["notifications_enabled"],
                edit_enabled=settings["edit_notifications"],
                delete_enabled=settings["delete_notifications"]
            )
        )
        await callback.answer("Настройки уведомлений обновлены! ✅")
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек уведомлений: {e}")
        await callback.answer("Произошла ошибка 😢 Попробуйте позже.")

@user_router.callback_query(F.data == "toggle_edit_tracking")
async def toggle_edit_tracking(callback: CallbackQuery):
    """Обработка включения/выключения отслеживания изменений"""
    try:
        settings = await db.toggle_notification(callback.from_user.id, "edit")
        
        notification_status = "🔔 Вкл." if settings["notifications_enabled"] else "🔕 Выкл."
        edit_status = "✅ Вкл." if settings["edit_notifications"] else "❌ Выкл."
        delete_status = "✅ Вкл." if settings["delete_notifications"] else "❌ Выкл."
        
        text = f"⚙️ Настройки функций:\n\n" \
               f"🔔 Уведомления: {notification_status}\n" \
               f"📝 Отслеживание изменений: {edit_status}\n" \
               f"🗑 Отслеживание удалений: {delete_status}"
               
        await callback.message.edit_text(
            text=text,
            reply_markup=kb.get_functions_keyboard(
                notifications_enabled=settings["notifications_enabled"],
                edit_enabled=settings["edit_notifications"],
                delete_enabled=settings["delete_notifications"]
            )
        )
        await callback.answer("Отслеживание изменений обновлено! ✅")
    except Exception as e:
        logger.error(f"Ошибка при обновлении отслеживания изменений: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

@user_router.callback_query(F.data == "toggle_delete_tracking")
async def toggle_delete_tracking(callback: CallbackQuery):
    """Обработка включения/выключения отслеживания удалений"""
    try:
        settings = await db.toggle_notification(callback.from_user.id, "delete")
        
        notification_status = "🔔 Вкл." if settings["notifications_enabled"] else "🔕 Выкл."
        edit_status = "✅ Вкл." if settings["edit_notifications"] else "❌ Выкл."
        delete_status = "✅ Вкл." if settings["delete_notifications"] else "❌ Выкл."
        
        text = f"⚙️ Настройки функций:\n\n" \
               f"🔔 Уведомления: {notification_status}\n" \
               f"📝 Отслеживание изменений: {edit_status}\n" \
               f"🗑 Отслеживание удалений: {delete_status}"
               
        await callback.message.edit_text(
            text=text,
            reply_markup=kb.get_functions_keyboard(
                notifications_enabled=settings["notifications_enabled"],
                edit_enabled=settings["edit_notifications"],
                delete_enabled=settings["delete_notifications"]
            )
        )
        await callback.answer("Отслеживание удалений обновлено! ✅")
    except Exception as e:
        logger.error(f"Ошибка при обновлении отслеживания удалений: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

@user_router.message(F.text == "💳 Купить подписку")
async def buy_subscription(message: Message):
    """Обработка кнопки покупки подписки"""
    try:
        from bot.services.payments import create_invoice
        price = await db.get_subscription_price()
        payment_data = await create_invoice(price, message.from_user.id, message.bot.username)
        if not payment_data["invoice_id"]:
            raise Exception("Не удалось создать платёж")
        await message.answer(
            "Выберите удобный способ оплаты:",
            reply_markup=kb.get_payment_keyboard(payment_url, invoice_id)
        )
    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        await message.answer("Произошла ошибка при создании платежа. Попробуйте позже.")

@user_router.callback_query(F.data.startswith("toggle_module_"))
async def toggle_module(callback: CallbackQuery):
    """Обработка включения/выключения модулей"""
    try:
        module = callback.data.split("_")[-1]
        user = await db.get_user(callback.from_user.id)

        if module == "calc":
            new_state = not user.calc_enabled
            await db.update_user(callback.from_user.id, calc_enabled=new_state)
            status = "включен ✅" if new_state else "выключен ❌"
            await callback.answer(f"Калькулятор {status}")

        elif module == "love":
            new_state = not user.love_enabled
            await db.update_user(callback.from_user.id, love_enabled=new_state)
            status = "включен ✅" if new_state else "выключен ❌"
            await callback.answer(f"Модуль Love {status}")

        # Получаем актуальное состояние модулей
        updated_user = await db.get_user(callback.from_user.id)
        updated_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🔢 Калькулятор {'✅' if updated_user.calc_enabled else '❌'}", 
                    callback_data="toggle_module_calc"
                )],
                [InlineKeyboardButton(
                    text=f"❤️ Love {'✅' if updated_user.love_enabled else '❌'}", 
                    callback_data="toggle_module_love"
                )],
                [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
            ]
        )
        await callback.message.edit_reply_markup(reply_markup=updated_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при переключении модуля: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")