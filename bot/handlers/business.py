
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime

from bot.database import database as db
from bot.keyboards import user as kb

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

@business_router.callback_query(lambda c: c.data == "toggle_all_modules")
async def toggle_all_modules_handler(callback: CallbackQuery):
    try:
        user = await db.get_user(callback.from_user.id)
        if not user:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        if not user.has_active_subscription:
            await callback.answer("❌ Требуется подписка для использования модулей", show_alert=True)
            return

        # Определяем текущее состояние
        current_state = user.module_calc_enabled and user.module_love_enabled
        new_state = not current_state

        # Обновляем состояние всех модулей
        async with db.get_db_session() as session:
            user.module_calc_enabled = new_state
            user.module_love_enabled = new_state
            await session.commit()

        # Обновляем клавиатуру
        modules_state = {'modules': new_state}
        await callback.message.edit_text(
            f"🎮 Модули: {'✅' if new_state else '❌'}\n\n"
            "Используйте кнопку для управления всеми модулями",
            reply_markup=kb.get_modules_keyboard(modules_state)
        )
        
        await callback.answer("✅ Состояние модулей обновлено", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при переключении модулей: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
