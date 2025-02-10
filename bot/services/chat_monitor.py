
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from ..database import database as db

logger = logging.getLogger(__name__)

async def check_inactive_chats(bot: Bot):
    """
    Проверяет неактивные чаты и удаляет их из мониторинга
    """
    try:
        inactive_period = timedelta(days=7)  # Период неактивности
        current_time = datetime.now()
        
        # Получаем все подключения
        connections = await db.get_all_business_connections()
        
        for conn in connections:
            if current_time - conn.last_activity > inactive_period:
                try:
                    # Попытка проверить доступ к чату
                    await bot.get_chat(conn.chat_id)
                except Exception as e:
                    logger.warning(f"Чат {conn.chat_id} недоступен: {str(e)}")
                    # Удаляем недоступное подключение
                    await db.remove_business_connection(conn.user_id, conn.chat_id)
                    
    except Exception as e:
        logger.error(f"Ошибка при проверке неактивных чатов: {str(e)}")
