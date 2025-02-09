from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.exceptions import TelegramBadRequest
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
            await event.answer(texts.Texts.START_NOT_CONNECTED)
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
        await message.answer(texts.Texts.START_CONNECTED, reply_markup=kb.start_connection_keyboard)
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

        # Отправляем заголовок истории
        sent_message = await callback.message.answer(
            text=f"История редактирования сообщения {old_message.message_id}",
            reply_markup=kb.close_keyboard
        )

        success = False
        try:
            # Получаем оригинальное сообщение из истории
            try:
                # Пробуем получить сообщение из разных каналов
                channels = [-1002467764642, -1002353748102, -1002460477207, -1002300596890, -1002498479494, -1002395727554, -1002321264660]
                message_found = False

                for channel in channels:
                    try:
                        forwarded_message = await callback.bot.copy_message(
                            chat_id=callback.message.chat.id,
                            from_chat_id=channel,
                            message_id=old_message.temp_message_id
                        )
                        message_found = True
                        break
                    except Exception:
                        continue

                if message_found:
                    success = True
                else:
                    raise Exception("message not found")
                success = True
            except Exception as e:
                if "message to forward not found" in str(e):
                    # Если сообщение недоступно, продолжаем показывать историю изменений
                    await sent_message.edit_text(
                        "Оригинальное сообщение удалено.\nИстория изменений:",
                        reply_markup=kb.close_keyboard
                    )
                    success = True  # Позволяем показать историю изменений
                else:
                    raise e

            # Отправляем историю изменений из сохраненных сообщений
            if success and message_edit_history.get('message_edit_history'):
                for edit in message_edit_history['message_edit_history']:
                    try:
                        message_found = False
                        for channel in channels:
                            try:
                                await callback.bot.copy_message(
                                    chat_id=callback.message.chat.id,
                                    from_chat_id=channel,
                                    message_id=edit.temp_message_id
                                )
                                message_found = True
                                break
                            except Exception:
                                continue
                        if not message_found:
                            continue
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

@user_router.message(F.text == "⚙️ Функции")
async def functions_menu(message: Message, user: dict):
    await message.delete()
    if not hasattr(functions_menu, 'menu_message'):
        text = (
            "⚙️ Управление функциями:\n\n"
            f"🔔 Уведомления: {'✅ Вкл' if user.notifications_enabled else '❌ Выкл'}\n"
            f"📝 Отслеживание изменений: {'✅ Вкл' if user.edit_notifications else '❌ Выкл'}\n"
            f"🗑 Отслеживание удалений: {'✅ Вкл' if user.delete_notifications else '❌ Выкл'}"
        )
        functions_menu.menu_message = await message.answer(text=text, reply_markup=kb.functions_keyboard)
    else:
        try:
            new_text = (
                "⚙️ Управление функциями:\n\n"
                f"🔔 Уведомления: {'✅ Вкл' if user.notifications_enabled else '❌ Выкл'}\n"
                f"📝 Отслеживание изменений: {'✅ Вкл' if user.edit_notifications else '❌ Выкл'}\n"
                f"🗑 Отслеживание удалений: {'✅ Вкл' if user.delete_notifications else '❌ Выкл'}"
            )

            # Проверяем, изменился ли текст
            try:
                current_text = functions_menu.menu_message.text
                if current_text != new_text:
                    await functions_menu.menu_message.edit_text(text=new_text, reply_markup=kb.functions_keyboard)
            except:
                functions_menu.menu_message = await message.answer(text=new_text, reply_markup=kb.functions_keyboard)
        except Exception as e:
            functions_menu.menu_message = await message.answer(text=new_text, reply_markup=kb.functions_keyboard)

@user_router.callback_query(F.data.startswith("toggle_module_"))
async def toggle_module_handler(callback: CallbackQuery):
    module = callback.data.replace("toggle_module_", "")
    new_state = await db.toggle_module(callback.from_user.id, module)

    # Получаем обновленные данные пользователя после изменения
    updated_user = await db.get_user(telegram_id=callback.from_user.id)

    text = (
        "📱 Управление модулями:\n\n"
        f"🔢 Калькулятор: {'✅ Вкл' if updated_user.calc_enabled else '❌ Выкл'}\n"
        f"❤️ Love: {'✅ Вкл' if updated_user.love_enabled else '❌ Выкл'}"
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=kb.modules_keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise

    await callback.answer(f"Модуль {'включен ✅' if new_state else 'выключен ❌'}")

@user_router.callback_query(F.data.startswith("toggle_"))
async def toggle_function(callback: CallbackQuery):
    function = callback.data.split("_", 1)[1]
    user = await db.get_user(telegram_id=callback.from_user.id)

    if function == "all_notifications":
        new_state = not user.notifications_enabled
        await db.toggle_notification(user.telegram_id, "notifications")
    elif function == "edit_tracking":
        new_state = not user.edit_notifications
        await db.toggle_notification(user.telegram_id, "edit")
    elif function == "delete_tracking":
        new_state = not user.delete_notifications
        await db.toggle_notification(user.telegram_id, "delete")
    else:
        await callback.answer("Неизвестная функция")
        return

    await callback.answer(f"Функция {'включена ✅' if new_state else 'выключена ❌'}")

    # Получаем обновленные данные пользователя
    updated_user = await db.get_user(telegram_id=callback.from_user.id)

    new_text = (
        "⚙️ Управление функциями:\n\n"
        f"🔔 Уведомления: {'✅ Вкл' if updated_user.notifications_enabled else '❌ Выкл'}\n"
        f"📝 Отслеживание изменений: {'✅ Вкл' if updated_user.edit_notifications else '❌ Выкл'}\n"
        f"🗑 Отслеживание удалений: {'✅ Вкл' if updated_user.delete_notifications else '❌ Выкл'}"
    )

    if callback.message.text != new_text:
        await callback.message.edit_text(text=new_text, reply_markup=kb.functions_keyboard)

@user_router.callback_query(F.data == "close")
async def close(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

@user_router.message(F.text == "📱 Модули")
async def modules_menu(message: Message, user: dict):
    """Показывает меню модулей"""
    await message.delete()
    text = (
        "📱 Управление модулями:\n\n"
        f"🔢 Калькулятор: {'✅ Вкл' if user.calc_enabled else '❌ Выкл'}\n"
        f"❤️ Love: {'✅ Вкл' if user.love_enabled else '❌ Выкл'}"
    )
    await message.answer(text=text, reply_markup=kb.modules_keyboard)

@user_router.callback_query(F.data == "module_calc")
async def calculator_module(callback: CallbackQuery):
    """Открывает калькулятор"""
    await callback.answer()
    await callback.message.edit_text(
        "🔢 Калькулятор\n\nДля использования напишите:\nКальк <выражение>\n\nПример: Кальк 2 + 2",
        reply_markup=kb.close_keyboard
    )

@user_router.callback_query(F.data == "module_love")
async def love_module(callback: CallbackQuery):
    """Открывает модуль Love"""
    await callback.answer()
    await callback.message.edit_text(
        "❤️ Love\n\nДля использования напишите:\nLove <имя1> <имя2>\n\nПример: Love Иван Мария",
        reply_markup=kb.close_keyboard
    )

@user_router.message(F.text == "тест")
async def test(message: Message):
    await db.create_subscription(user_telegram_id=message.from_user.id, end_date=datetime.now() + timedelta(days=30))
    await message.answer(text="Подписка создана")


@user_router.message(F.text == "📊 Статистика")
async def show_user_stats(message: Message, user: dict):
    """Показывает статистику пользователя"""
    await message.delete()
    stats = await db.get_user_stats(user.telegram_id)
    text = (
        f"📊 Ваша статистика:\n\n"
        f"Отправлено сообщений: {stats['sent_messages']}\n"
        f"Изменено сообщений: {stats['edited_messages']}\n"
        f"Удалено сообщений: {stats['deleted_messages']}\n"
        f"Дата регистрации: {stats['registration_date']}"
    )
    await message.answer(text=text, reply_markup=kb.close_keyboard)

@user_router.message(F.text == "⚙️ Настройки")
async def settings(message: Message):
    """Показывает меню настроек"""
    await message.delete()
    text = "⚙️ Настройки:\n\nВыберите, что хотите настроить:"
    await message.answer(text=text, reply_markup=kb.settings_keyboard)

@user_router.message(F.text == "❓ Помощь")
async def help_command(message: Message):
    """Показывает справку по командам"""
    await message.delete()
    text = (
        "🤖 Доступные команды:\n\n"
        "👤 Профиль - информация о вашем профиле\n"
        "📊 Статистика - ваша статистика\n"
        "⚙️ Настройки - настройки бота\n"
        "❓ Помощь - эта справка\n"
        "💳 Купить подписку - приобрести подписку"
    )
    await message.answer(text=text, reply_markup=kb.close_keyboard)

@user_router.callback_query(F.data == "notifications_settings")
async def notification_settings(callback: CallbackQuery):
    """Настройки уведомлений"""
    await callback.answer()
    user = await db.get_user(telegram_id=callback.from_user.id)
    text = (
        "🔔 Настройки уведомлений:\n\n"
        f"Все уведомления: {'✅' if user.notifications_enabled else '❌'}\n"
        f"Новые сообщения: {'✅' if user.message_notifications else '❌'}\n"
        f"Редактирование: {'✅' if user.edit_notifications else '❌'}\n"
        f"Удаление: {'✅' if user.delete_notifications else '❌'}"
    )
    await callback.message.edit_text(text=text, reply_markup=kb.notifications_keyboard)

@user_router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    """Возврат в основные настройки"""
    await callback.answer()
    text = "⚙️ Настройки:\n\nВыберите, что хотите настроить:"
    await callback.message.edit_text(text=text, reply_markup=kb.settings_keyboard)

@user_router.callback_query(F.data.startswith("toggle_notification_"))
async def toggle_notification(callback: CallbackQuery):
    """Включение/выключение определенного типа уведомлений"""
    notification_type = callback.data.split("_")[-1]
    current_state = await db.toggle_notification(callback.from_user.id, notification_type)
    await callback.answer(f"Уведомления {'включены' if current_state else 'выключены'}")
    await notification_settings(callback)

@user_router.message(F.text.startswith("Кальк"))
async def calculator(message: Message, user: dict):
    """Обработчик калькулятора"""
    if not user.calc_enabled:
        await message.answer("❌ Модуль калькулятора отключен. Включите его в настройках модулей.")
        return