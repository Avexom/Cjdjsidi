
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.database import database as db
from bot.keyboards import user as kb

# Создаем роутер для бизнес-логики
business_router = Router()
logger = logging.getLogger(__name__)

@business_router.message(F.text == "🎮 Модули")
async def handle_business_modules(message: Message):
    """Обработка всех модулей бизнес-бота."""
    try:
        user = await db.get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        if not user.has_active_subscription:
            await message.answer("❌ Требуется подписка для использования модулей")
            return

        # Получаем текущее состояние всех модулей
        modules_state = {
            'modules': user.module_calc_enabled and user.module_love_enabled
        }
        
        await message.answer(
            f"🎮 Модули: {'✅' if modules_state['modules'] else '❌'}\n\n"
            "Используйте кнопку для управления всеми модулями",
            reply_markup=kb.get_modules_keyboard(modules_state)
        )
    except Exception as e:
        logger.error(f"Ошибка в обработке модулей: {e}")
        await message.answer("❌ Произошла ошибка при обработке модулей")
