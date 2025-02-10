
import asyncio
import logging
import colorlog
from datetime import datetime

def setup_logger(name: str, level=logging.INFO) -> colorlog.Logger:
    """Настройка логгера с цветным форматированием"""
    logger = colorlog.getLogger(name)
    if not logger.handlers:  # Проверяем есть ли уже handlers
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        ))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger

# Настраиваем логгеры
logger = setup_logger('bot')
for log_name in ['aiogram', 'aiosqlite', 'apscheduler']:
    setup_logger(log_name)

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import DeleteWebhook
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers.user import user_router
from bot.handlers.business import business_router
from bot.handlers.admin import admin_router
from bot.database.database import init_db, delete_expired_subscriptions, migrate_db
from bot.services.chat_monitor import check_inactive_chats
from config import BOT_TOKEN

# Инициализация бота с отключенным превью ссылок
bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))

async def shutdown(dp: Dispatcher, scheduler: AsyncIOScheduler):
    """Корректное завершение работы"""
    logger.info("🛑 Останавливаем бота...")
    await dp.storage.close()
    await bot.session.close()
    scheduler.shutdown(wait=True)

async def main():
    """Основная функция запуска бота"""
    dp = Dispatcher()
    
    # Подключаем все роутеры
    for router in [user_router, business_router, admin_router]:
        dp.include_router(router)

    try:
        # Инициализация БД
        logger.info("🗄 Инициализация базы данных...")
        await init_db()
        await migrate_db()

        # Настройка и запуск планировщика
        logger.info("⏰ Запуск планировщика задач...")
        scheduler = AsyncIOScheduler()
        scheduler.add_job(delete_expired_subscriptions, 'interval', hours=1)
        scheduler.add_job(lambda: check_inactive_chats(bot), 'interval', hours=24)
        scheduler.start()

        # Запуск бота
        logger.info("🚀 Запуск бота...")
        await bot(DeleteWebhook(drop_pending_updates=True))
        await dp.start_polling(bot)

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {str(e)}", exc_info=True)
    finally:
        await shutdown(dp, scheduler)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("⚠️ Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"❌ Неожиданная ошибка: {str(e)}", exc_info=True)
    finally:
        logger.info("✅ Бот успешно остановлен")
