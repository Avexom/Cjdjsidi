from datetime import datetime, timedelta
from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, TelegramObject
from aiogram.fsm.context import FSMContext
from aiogram.enums.parse_mode import ParseMode
import bot.database.database as db
import logging
from pydantic import BaseModel, PositiveInt, confloat
from async_lru import alru_cache  # Импортируем alru_cache

from config import ADMIN_IDS

admin_router = Router()
logger = logging.getLogger(__name__)

# Модели для валидации
class GiveSubscriptionRequest(BaseModel):
    user_id: PositiveInt
    days: PositiveInt

class SetPriceRequest(BaseModel):
    price: confloat(gt=0)

# Middleware для проверки прав администратора
class AdminMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        if event.from_user.id not in ADMIN_IDS:
            await event.answer("У вас нет прав администратора.")
            return
        return await handler(event, data)

admin_router.message.middleware(AdminMiddleware())

# Кэширование статистики с помощью async_lru
@alru_cache(maxsize=1)  # Используем alru_cache для асинхронного кэширования
async def get_cached_statistics():
    return {
        "total_users": await db.get_total_users(),
        "total_subscriptions": await db.get_total_subscriptions(),
        "total_users_with_active_business_bot": await db.get_total_users_with_active_business_bot(),
        "total_messages": await db.get_total_messages(),
        "total_edited_messages": await db.get_total_edited_messages(),
        "total_deleted_messages": await db.get_total_deleted_messages(),
        "subscription_price": await db.get_subscription_price(),
    }

# Генерация текста для админ-панели
async def generate_admin_panel_text(stats):
    return f"""
<b>Панель администратора</b>

<b>Стоимость подписки:</b> {stats['subscription_price']}$

<b>Команды администратора:</b>
- /give айди_пользователя количество_дней - выдать подписку пользователю
- /price цена - установить цену подписки
- /ban айди_пользователя причина - заблокировать пользователя
- /unban айди_пользователя - разблокировать пользователя
- /broadcast текст - отправить сообщение всем пользователям
- /stats - подробная статистика использования
- /logs - последние ошибки бота

📊 <b>Статистика бота</b>
- Всего пользователей: {stats['total_users']}
- Пользователей с подпиской: {stats['total_subscriptions']}
- Пользователей с активным бизнес-ботом: {stats['total_users_with_active_business_bot']}
- Всего отслеживаемых сообщений: {stats['total_messages']}
- Отредактированных сообщений: {stats['total_edited_messages']}
- Удаленных сообщений: {stats['total_deleted_messages']}
"""

# Хэндлеры
from aiogram.types import CallbackQuery
from bot.keyboards.user import admin_keyboard

@admin_router.message(F.text == "/admin")
async def admin_panel(message: Message):
    try:
        stats = await get_cached_statistics()
        text = await generate_admin_panel_text(stats)
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("Произошла ошибка при получении статистики.")

@admin_router.message(F.text.startswith("/give"))
async def give_subscription(message: Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer("Используйте формат: /give айди_пользователя количество_дней")
            return

        request = GiveSubscriptionRequest(user_id=int(args[1]), days=int(args[2]))

        if await db.get_user(request.user_id) is None:
            await message.answer("Пользователь не найден.")
            return

        await db.create_subscription(user_telegram_id=request.user_id, end_date=datetime.now() + timedelta(days=request.days))
        await message.answer(f"Подписка выдана пользователю {request.user_id} на {request.days} дней.")
    except ValueError as e:
        await message.answer(f"Некорректные данные: {e}")
    except Exception as e:
        logger.error(f"Ошибка при выдаче подписки: {e}")
        await message.answer("Произошла ошибка при выдаче подписки.")

@admin_router.message(F.text.startswith("/price"))
async def set_subscription_price(message: Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте формат: /price цена")
            return

        request = SetPriceRequest(price=float(args[1]))
        await db.set_subscription_price(request.price)
        await message.answer(f"Цена подписки установлена на {request.price}$.")
    except ValueError as e:
        await message.answer(f"Некорректная цена: {e}")
    except Exception as e:
        logger.error(f"Ошибка при установке цены подписки: {e}")
        await message.answer("Произошла ошибка при установке цены подписки.")
@admin_router.message(Command("reset_channels"))
async def reset_channels(message: Message):
    try:
        await db.reset_channel_indexes()
        await message.answer("Индексы каналов успешно сброшены для всех пользователей.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при сбросе индексов: {e}")

# New admin commands
@admin_router.message(F.text.startswith("/ban"))
async def ban_user(message: Message):
    try:
        args = message.text.split()
        if len(args) < 3:
            await message.answer("Используйте формат: /ban айди_пользователя причина")
            return
        user_id = int(args[1])
        reason = " ".join(args[2:])
        await db.ban_user(user_id, reason)
        await message.answer(f"Пользователь {user_id} заблокирован. Причина: {reason}")
    except Exception as e:
        await message.answer(f"Ошибка при блокировке пользователя: {e}")

@admin_router.message(F.text.startswith("/unban"))
async def unban_user(message: Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте формат: /unban айди_пользователя")
            return
        user_id = int(args[1])
        await db.unban_user(user_id)
        await message.answer(f"Пользователь {user_id} разблокирован.")
    except Exception as e:
        await message.answer(f"Ошибка при разблокировке пользователя: {e}")

@admin_router.message(F.text.startswith("/broadcast"))
async def broadcast_message(message: Message):
    try:
        text = message.text[len("/broadcast "):]
        await db.broadcast_message(text)
        await message.answer("Сообщение успешно разослано всем пользователям.")
    except Exception as e:
        await message.answer(f"Ошибка при рассылке сообщения: {e}")


@admin_router.message(Command("stats"))
async def detailed_stats(message: Message):
    try:
        stats = await get_cached_statistics()
        detailed_stats_text = f"""
        Подробная статистика:
        - Всего пользователей: {stats['total_users']}
        - Пользователей с подпиской: {stats['total_subscriptions']}
        - Пользователей с активным бизнес-ботом: {stats['total_users_with_active_business_bot']}
        - Всего сообщений: {stats['total_messages']}
        - Отредактированных сообщений: {stats['total_edited_messages']}
        - Удаленных сообщений: {stats['total_deleted_messages']}
        """
        await message.answer(detailed_stats_text)
    except Exception as e:
        await message.answer(f"Ошибка при получении статистики: {e}")


@admin_router.message(Command("logs"))
async def show_logs(message: Message):
    try:
        logs = await db.get_recent_logs() # Assumed function in db.py
        log_message = "\n".join(logs) or "Нет записей в логах."
        await message.answer(f"Последние ошибки бота:\n{log_message}")
    except Exception as e:
        await message.answer(f"Ошибка при получении логов: {e}")
# Callback handlers
@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    await callback.answer()
    await detailed_stats(callback.message)

@admin_router.callback_query(F.data == "admin_logs")
async def admin_logs_callback(callback: CallbackQuery):
    await callback.answer()
    await show_logs(callback.message)

from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введите текст для рассылки:")
    await state.set_state(AdminStates.waiting_for_broadcast)

@admin_router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_text(message: Message, state: FSMContext):
    try:
        users = await db.broadcast_message(message.text)
        sent_count = 0
        for user_id in users:
            try:
                await message.bot.send_message(chat_id=user_id, text=message.text)
                sent_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

        await message.answer(f"Сообщение разослано {sent_count} пользователям из {len(users)}")
    except Exception as e:
        await message.answer(f"Ошибка при рассылке сообщения: {e}")
    finally:
        await state.clear()

@admin_router.callback_query(F.data == "admin_price")
async def admin_price_callback(callback: CallbackQuery):
    """Обработчик нажатия кнопки установки цены подписки"""
    await callback.answer()
    await callback.message.answer("Введите новую цену подписки в формате:\n/price сумма")

@admin_router.callback_query(F.data == "admin_give")
async def admin_give_callback(callback: CallbackQuery):
    """Обработчик нажатия кнопки выдачи подписки"""
    await callback.answer()
    await callback.message.answer("Введите данные в формате:\n/give айди_пользователя количество_дней")

@admin_router.callback_query(F.data == "admin_ban")
async def admin_ban_callback(callback: CallbackQuery):
    """Обработчик нажатия кнопки бана пользователя"""
    await callback.answer()
    await callback.message.answer("Введите данные в формате:\n/ban айди_пользователя причина")

@admin_router.callback_query(F.data == "admin_unban")
async def admin_unban_callback(callback: CallbackQuery):
    """Обработчик нажатия кнопки разбана пользователя"""
    await callback.answer()
    await callback.message.answer("Введите данные в формате:\n/unban айди_пользователя")