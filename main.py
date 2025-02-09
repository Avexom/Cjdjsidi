import asyncio
import logging
import colorlog
from datetime import datetime

# Настройка логгера
logger = colorlog.getLogger('bot')

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import DeleteWebhook
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers.user import user_router
from bot.handlers.business import business_router
from bot.handlers.admin import admin_router
from bot.database.database import init_db, delete_expired_subscriptions, migrate_db # Now includes migrate_db
from config import BOT_TOKEN

# Инициализация бота
bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))

async def main():
    dp = Dispatcher()

    # Настройка цветного вывода в консоль
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        '%(asctime)s %(log_color)s%(levelname)-8s%(reset)s %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    ))

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Настройка логгера бота
    logger = colorlog.getLogger('bot')
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    # Настраиваем логи внешних библиотек
    for log_name in ['aiosqlite', 'aiogram', 'apscheduler']:
        external_logger = logging.getLogger(log_name)
        external_logger.setLevel(logging.INFO)
        external_logger.addHandler(console_handler)
    
    # Добавляем свои логи
    logger.info('🚀 Бот запущен')
    
    @dp.message()
    async def log_message(message: Message, *args):
        username = message.from_user.username or message.from_user.first_name
        logger.info(f'📨 Сообщение от @{username}')

    # Подключение роутеров
    for router in [user_router, business_router, admin_router]:
        dp.include_router(router)

    # Инициализация базы данных
    await init_db()
    await migrate_db() # Added migration call

    # Запуск планировщика для удаления истёкших подписок
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_subscriptions, 'interval', hours=1)
    scheduler.start()

    # Удаление вебхука и запуск бота
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        logger.critical(f"Детали ошибки: {str(e)}")
    finally:
        logger.info("Бот успешно остановлен")