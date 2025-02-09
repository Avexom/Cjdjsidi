
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from bot.database import database as db
from bot.keyboards import user as kb

user_router = Router()

@user_router.message(F.text == "🌾 Ферма")
async def show_farm(message: Message):
    """Показывает меню фермы"""
    user = await db.get_user(message.from_user.id)
    plants = json.loads(user.farm_plants)
    
    text = "🌾 Ваша ферма:\n\n"
    text += f"💰 Монеты: {user.farm_coins}\n"
    text += f"🌱 Растения: {len(plants)}/4\n\n"
    
    if plants:
        for i, plant in enumerate(plants, 1):
            grow_time = datetime.strptime(plant['plant_time'], "%Y-%m-%d %H:%M:%S")
            time_left = grow_time + timedelta(hours=plant['grow_hours']) - datetime.now()
            
            if time_left.total_seconds() <= 0:
                status = "🟢 Готово к сбору"
            else:
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                status = f"⏳ Осталось: {hours}ч {minutes}м"
            
            text += f"{i}. {plant['emoji']} {plant['name']} - {status}\n"
    else:
        text += "У вас пока нет растений. Купите семена в магазине! 🏪"
    
    await message.answer(text=text, reply_markup=kb.farm_keyboard)

@user_router.callback_query(F.data == "shop")
async def show_shop(callback: CallbackQuery):
    """Показывает магазин семян"""
    user = await db.get_user(callback.from_user.id)
    text = f"🏪 Магазин семян\n\n💰 Ваши монеты: {user.farm_coins}"
    await callback.message.edit_text(text=text, reply_markup=kb.shop_keyboard)

