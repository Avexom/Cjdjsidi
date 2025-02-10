
import asyncio
import logging
import colorlog
from datetime import datetime

# Настройка логгера
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    style='%'
))

# Настраиваем корневой логгер один раз
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Настраиваем логгер бота
logger = colorlog.getLogger('bot')
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Отключаем передачу логов родительским логгерам
logger.propagate = False
logging.getLogger('aiogram').propagate = False

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import DeleteWebhook
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers.user import user_router
from bot.handlers.business import business_router
from bot.handlers.admin import admin_router
from bot.database.database import init_db, delete_expired_subscriptions, migrate_db
from bot.services.chat_monitor import check_inactive_chats  # Добавили импорт
from config import BOT_TOKEN

# Инициализация бота
bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))

async def main():
    dp = Dispatcher()
    
    # Настраиваем логи внешних библиотек
    for log_name in ['aiosqlite', 'aiogram', 'apscheduler']:
        external_logger = logging.getLogger(log_name)
        external_logger.setLevel(logging.INFO)
        external_logger.addHandler(handler)

    # Подключение роутеров
    for router in [user_router, business_router, admin_router]:
        dp.include_router(router)

    # Инициализация и миграция базы данных
    await init_db()
    await migrate_db()  # Теперь вызываем только один раз

    # Запуск планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_subscriptions, 'interval', hours=1)
    scheduler.add_job(lambda: check_inactive_chats(bot), 'interval', hours=24)
    scheduler.start()

    try:
        # Удаление вебхука и запуск бота
        await bot(DeleteWebhook(drop_pending_updates=True))
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()  # Корректное завершение планировщика

if __name__ == '__main__':
    try:
        logger.info("🚀 Бот запускается...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("⚠️ Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("✅ Бот успешно остановлен")
