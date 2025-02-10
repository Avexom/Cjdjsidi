
import asyncio
import logging
import colorlog
from datetime import datetime

# Настройка форматтеров для разных типов логов
bot_handler = colorlog.StreamHandler()
bot_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s[%(asctime)s] BOT: %(message)s',
    datefmt='%H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

user_handler = colorlog.StreamHandler()
user_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s[%(asctime)s] USER: %(message)s',
    datefmt='%H:%M:%S',
    log_colors={
        'DEBUG': 'blue',
        'INFO': 'white',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

# Настройка логгеров
bot_logger = colorlog.getLogger('bot')
bot_logger.handlers.clear()
bot_logger.addHandler(bot_handler)
bot_logger.setLevel(logging.INFO)
bot_logger.propagate = False

user_logger = colorlog.getLogger('user')
user_logger.handlers.clear()
user_logger.addHandler(user_handler)
user_logger.setLevel(logging.INFO)
user_logger.propagate = False

# Отключаем логи aiogram
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
from config import BOT_TOKEN

# Инициализация бота
bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))

async def main():
    # Запускаем миграцию базы данных
    await migrate_db()
    
    dp = Dispatcher()

    # Подключение роутеров
    for router in [user_router, business_router, admin_router]:
        dp.include_router(router)

    # Инициализация и миграция базы данных
    await init_db()
    await migrate_db()

    # Запуск планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_subscriptions, 'interval', hours=1)
    scheduler.start()

    # Запуск бота
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        bot_logger.info("🚀 Бот запускается...")
        user_logger.info("👤 Проверка логов пользователя")
        asyncio.run(main())
    except KeyboardInterrupt:
        bot_logger.warning("⚠️ Бот остановлен пользователем")
    except Exception as e:
        bot_logger.critical(f"❌ Критическая ошибка: {e}")
    finally:
        bot_logger.info("✅ Бот успешно остановлен")
