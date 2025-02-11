import asyncio
import logging
from datetime import datetime
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
    logger.info("🚀 Запускаем нахуй эту охуенную систему!")

    # Диспетчер
    dp = Dispatcher()
    logger.info("✨ Диспетчер создан и готов к работе")

    # Подключаем роутеры
    for router in [user_router, business_router, admin_router]:
        dp.include_router(router)
        logger.info(f"📡 Подключен роутер: {router.__class__.__name__}")

    try:
        # База данных
        logger.info("🗄️ Создаём базу данных...")
        await init_db()
        logger.info("✅ База данных создана успешно")

        logger.info("🔄 Делаем миграцию...")
        await migrate_db()
        logger.info("✅ Миграция завершена успешно")
    except Exception as e:
        logger.error(f"❌ Пиздец с базой данных: {e}")
        raise

    # Планировщик
    logger.info("⏰ Настраиваем планировщик задач...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_subscriptions, 'interval', hours=1)

    from bot.handlers.admin import send_stats_message
    scheduler.add_job(send_stats_message, 'interval', minutes=30)
    scheduler.start()
    logger.info("✅ Планировщик запущен")

    # Запуск бота
    logger.info("🤖 Запускаем бота...")
    await bot(DeleteWebhook(drop_pending_updates=True))
    logger.info("🎉 Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

# Настройка перехватчика необработанных исключений
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.error(
        "Необработанное исключение:",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

import sys
sys.excepthook = handle_exception

if __name__ == '__main__':
    try:
        print("\n🔥 ЗАПУСКАЕМ ЭТОГО КРАСАВЧИКА!\n")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n😴 Бот ушёл спать (остановлен)")
    except Exception as e:
        print(f"\n💀 ПИЗДЕЦ: {e}")
    finally:
        print("\n👋 Всем пока!")