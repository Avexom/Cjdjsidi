
from functools import wraps
from datetime import datetime
from aiogram.types import Message
from bot.database import database as db

def check_subscription():
    def decorator(func):
        @wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            subscription = await db.get_subscription(message.from_user.id)
            
            if not subscription or subscription.end_date < datetime.now().date():
                await message.answer("⚠️ У вас нет активной подписки! Купите подписку, чтобы использовать эту функцию.")
                return
            
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator
