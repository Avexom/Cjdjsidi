from datetime import datetime, timedelta
from aiogram import Router, F, BaseMiddleware
from aiogram.types import Message, TelegramObject
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

📊 <b>Статистика бота</b>
- Всего пользователей: {stats['total_users']}
- Пользователей с подпиской: {stats['total_subscriptions']}
- Пользователей с активным бизнес-ботом: {stats['total_users_with_active_business_bot']}
- Всего отслеживаемых сообщений: {stats['total_messages']}
- Отредактированных сообщений: {stats['total_edited_messages']}
- Удаленных сообщений: {stats['total_deleted_messages']}
"""

# Хэндлеры
@admin_router.message(F.text == "/admin")
async def admin_panel(message: Message):
    try:
        stats = await get_cached_statistics()  # Используем кэшированную статистику
        text = await generate_admin_panel_text(stats)
        await message.answer(text, parse_mode=ParseMode.HTML)
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
