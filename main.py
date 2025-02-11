
import asyncio
import logging
import colorlog
import traceback
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Настройка охуенного логирования
error_file_handler = RotatingFileHandler(
    'errors.log',
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=10,
    encoding='utf-8'
)
error_file_handler.setFormatter(logging.Formatter(
    '='*50 + '\n'
    '[%(asctime)s] %(levelname)s\n'
    'В модуле: %(module)s\n'
    'Функция: %(funcName)s\n'
    'Строка: %(lineno)d\n'
    'Сообщение: %(message)s\n'
    'Стек вызовов:\n%(stack_info)s\n'
    'Traceback:\n%(exc_info)s\n' +
    '='*50 + '\n'
))
error_file_handler.setLevel(logging.ERROR)

# Отдельный файл для действий бота
debug_file_handler = RotatingFileHandler(
    'bot_actions.log',
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=5,
    encoding='utf-8'
)
debug_file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s'
))
debug_file_handler.setLevel(logging.INFO)

# Настройка перехватчика необработанных исключений
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger = logging.getLogger('root')
    logger.error(
        "Необработанное исключение:",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

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
bot_logger.addHandler(error_file_handler)
bot_logger.addHandler(debug_file_handler)

user_logger = colorlog.getLogger('user')
user_logger.addHandler(error_file_handler)
user_logger.addHandler(debug_file_handler)
user_logger.addHandler(file_handler)
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
    dp = Dispatcher()

    # Подключение роутеров
    for router in [user_router, business_router, admin_router]:
        dp.include_router(router)

    # Сначала создаем базу данных
    try:
        await init_db()
        bot_logger.info("✅ База данных успешно создана")
        # Только потом делаем миграцию
        await migrate_db()
        bot_logger.info("✅ Миграция успешно выполнена")
    except Exception as e:
        bot_logger.error(f"❌ Ошибка при инициализации базы данных: {e}")
        raise

    # Запуск планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_subscriptions, 'interval', hours=1)
    
    # Добавляем задачу отправки статистики каждые 30 минут
    from bot.handlers.admin import send_stats_message
    scheduler.add_job(send_stats_message, 'interval', minutes=30)
    
    scheduler.start()

    # Запуск бота
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        print("\n🚀 Запуск бота...\n")
        bot_logger.info("⚡️ Инициализация систем...")
        bot_logger.info("📊 Подключение к базе данных...")
        bot_logger.info("👤 Проверка пользовательских систем...")
        asyncio.run(main())
    except KeyboardInterrupt:
        bot_logger.warning("⚠️ Бот остановлен пользователем")
    except Exception as e:
        bot_logger.critical(f"❌ Критическая ошибка: {e}")
    finally:
        bot_logger.info("✅ Бот успешно остановлен")
