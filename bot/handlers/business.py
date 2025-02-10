import re
import asyncio
import logging
import pytz
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted
import random
import asyncio
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Added import for scheduler

import bot.database.database as db
import bot.assets.texts as texts
import bot.keyboards.user as kb

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

business_router = Router()

# Регулярное выражение для проверки математических выражений
math_expression_pattern = re.compile(r'^Кальк [\d+\-*/(). ]+$')



async def handle_math_expression(message: Message):
    """Обработка математических выражений с анимацией."""
    # Получаем информацию о бизнес-подключении
    connection = await message.bot.get_business_connection(message.business_connection_id)

    # Проверяем, что команду использует тот же пользователь, который отправил сообщение
    if message.from_user.id != connection.user.id:
        return

    expression = message.text[len("Кальк "):].strip()
    try:
        # Отправляем начальное сообщение
        calc_message = await message.bot.send_message(chat_id=message.chat.id, text="🔄 Считаю...")

        # Анимация вычисления
        animations = [
            "🧮 Анализирую выражение...",
            "📊 Выполняю вычисления...",
            "⚡️ Почти готово..."
        ]

        for anim in animations:
            await asyncio.sleep(0.5)
            await calc_message.edit_text(anim)

        # Вычисляем результат
        result = eval(expression)

        # Форматируем результат
        if isinstance(result, (int, float)):
            formatted_result = f"{result:,}".replace(",", " ")
        else:
            formatted_result = str(result)

        # Отправляем финальное сообщение
        final_text = f"✨ Выражение: {expression}\n💫 Результат: {formatted_result}"
        await calc_message.edit_text(final_text, reply_to_message_id=message.message_id)

    except Exception as e:
        logger.error(f"Ошибка при вычислении выражения: {e}")
        await calc_message.edit_text("❌ Ошибка при вычислении выражения")

async def handle_love_command(message: Message):
    """Обработка команды 'love'."""
    sent_message = await message.answer("Я")
    for text in ["Я хочу", "Я хочу сказать", "Я хочу сказать, что", "Я хочу сказать, что я", "Я хочу сказать, что я люблю", "Я хочу сказать, что я люблю тебя 💖"]:
        await asyncio.sleep(1)
        await sent_message.edit_text(text)

async def handle_love1_command(message: Message):
    """Обработка команды 'love1'."""
    original_text = "1234567890"
    target_text = "ЯЛюблюТебя"
    sent_message = await message.answer(original_text)
    for i in range(len(target_text)):
        new_text = target_text[:i + 1] + original_text[i + 1:]
        await asyncio.sleep(0.10)
        await sent_message.edit_text(new_text)



@business_router.business_connection()
async def business_connection(event: BusinessConnection):
    """Обработка подключения бизнес-бота."""
    try:
        if event.is_enabled:
            user = await db.get_user(telegram_id=event.user.id)
            if user is None:
                await db.create_user(telegram_id=event.user.id, business_bot_active=True)
            else:
                await db.update_user_business_bot_active(telegram_id=event.user.id, business_bot_active=True)
            try:
                await event.bot.send_message(event.user.id, texts.Texts.CONNECTION_ENABLED, reply_markup=kb.start_connection_keyboard)
            except Exception as send_error:
                if "bot was blocked by the user" in str(send_error):
                    await db.update_user_business_bot_active(telegram_id=event.user.id, business_bot_active=False)
                    logger.warning(f"User {event.user.id} blocked the bot")
                else:
                    raise send_error
        else:
            await db.update_user_business_bot_active(telegram_id=event.user.id, business_bot_active=False)
            try:
                await event.bot.send_message(event.user.id, texts.Texts.CONNECTION_DISABLED)
            except Exception as send_error:
                if "bot was blocked by the user" not in str(send_error):
                    raise send_error
    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-подключения: {e}")

@business_router.business_message()
async def business_message(message: Message):
    """Обработка бизнес-сообщений."""
    try:
        connection = await message.bot.get_business_connection(message.business_connection_id)
        user = await db.get_user(telegram_id=connection.user.id)
        if not user:
            return

        # Проверяем подписку
        if not user.subscription_end_date or user.subscription_end_date < datetime.now():
            await message.answer("❌ Твоя подписка закончилась!\n\nНажми на кнопку '💳 Купить подписку' чтобы продолжить пользоваться ботом.")
            return
        text_1 = f"👤 От: {connection.user.first_name}"
        text_2 = texts.Texts.new_message_text(name=message.from_user.first_name, user_id=message.from_user.id, username=message.from_user.username)

        update = {}
        if message.entities:
            update["entities"] = [entity.model_copy(update={"length": entity.length + len(text_1)}) for entity in message.entities]
        elif message.caption_entities:
            update["caption_entities"] = [entity.model_copy(update={"length": entity.length + len(text_1)}) for entity in message.caption_entities]

        # Получаем имена отправителя и получателя с учетом всех возможных полей
        sender_name = message.from_user.first_name
        if message.from_user.last_name:
            sender_name += f" {message.from_user.last_name}"
        elif message.from_user.username:
            sender_name = message.from_user.username

        # Получаем информацию о получателе из connection
        receiver_name = connection.user.first_name
        if connection.user.last_name:
            receiver_name += f" {connection.user.last_name}"
        elif connection.user.username:
            receiver_name = connection.user.username

        if not receiver_name:
            receiver_name = "Пользователь"

        # Создаем HTML-ссылки на пользователей с учетом username
        sender_username = message.from_user.username
        receiver_username = connection.user.username

        sender_url = f'https://t.me/{sender_username}' if sender_username else f'tg://user?id={message.from_user.id}'
        receiver_url = f'https://t.me/{receiver_username}' if receiver_username else f'tg://user?id={connection.user.id}'

        sender_link = f'<a href="{sender_url}">{sender_name}</a>'
        receiver_link = f'<a href="{receiver_url}">{receiver_name}</a>'
        header = f"📨 Новое сообщение\n━━━━━━━━━━━━━━━\n👉 От: {sender_link}\n👤 Кому: {receiver_link}\n\n"

        if message.caption:
            update["caption"] = f"{header}{message.caption}"
        elif message.html_text:
            update["text"] = f"{header}{message.html_text}"
        elif message.voice or message.video_note or message.video:
            if message.voice:
                media_type = "🎤 Голосовое сообщение"
            elif message.video_note:
                media_type = "🎥 Видео-кружок"
            else:
                media_type = "📹 Видео"
            update["caption"] = f"{header}{media_type}"

        message_copy_model = message.model_copy(update=update)

        # Определяем каналы для разных типов сообщений
        CHANNELS = {
            'voice': -1002300596890,
            'photo': -1002498479494,
            'video_note': -1002395727554,
            'video': -1002321264660,
            'text': [-1002467764642, -1002353748102, -1002460477207],
            'default': -1002467764642  # Резервный канал
        }

        # Добавляем кэширование каналов
        if not hasattr(business_message, '_channels_cache'):
            business_message._channels_cache = CHANNELS

        # Получаем пользователя из базы
        user = await db.get_user(telegram_id=connection.user.id)
        if user is None:
            user = await db.create_user(telegram_id=connection.user.id, business_bot_active=True)

        # Определяем тип сообщения и канал
        message_type = next((type_ for type_ in ['voice', 'video_note', 'video', 'photo']
                           if hasattr(message, type_) and getattr(message, type_)), 'text')

        target_channel = None
        try:
            if message_type == 'text':
                channel_index = user.channel_index % len(CHANNELS['text'])
                target_channel = CHANNELS['text'][channel_index]
            else:
                target_channel = CHANNELS[message_type]

            if not target_channel:
                raise ValueError("Канал не определен")

            # Пробуем переслать сообщение
            for attempt in range(3):  # Делаем 3 попытки
                try:
                    temp_message = await message_copy_model.send_copy(
                        chat_id=target_channel,
                        parse_mode=ParseMode.HTML
                    )
                    if temp_message:
                        break
                except Exception as e:
                    if attempt == 2:  # Последняя попытка
                        raise e
                    await asyncio.sleep(1)  # Пауза перед следующей попыткой

            if not temp_message:
                raise ValueError("Не удалось переслать сообщение")

        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {str(e)}")
            # Используем резервный канал при ошибке
            try:
                temp_message = await message_copy_model.send_copy(
                    chat_id=CHANNELS['text'][0],
                    parse_mode=ParseMode.HTML
                )
            except Exception as backup_error:
                logger.critical(f"Критическая ошибка при пересылке: {str(backup_error)}")
                return
        message_new = temp_message
        await db.create_message(user_telegram_id=connection.user.id, chat_id=message.chat.id, from_user_id=message.from_user.id, message_id=message.message_id, temp_message_id=message_new.message_id)
        await db.increase_active_messages_count(user_telegram_id=connection.user.id)
        await db.increment_messages_count(from_user_id=message.from_user.id, to_user_id=connection.user.id)

        # Обработка специальных команд с проверкой состояния модулей
        if message.text:
            # Проверка на команду "Онлайн+"
            if message.text.strip() == "Онлайн+":
                chat_id = message.chat.id
                if chat_id in online_tasks:
                    # Если задача уже существует, останавливаем её
                    online_tasks[chat_id].cancel()
                    del online_tasks[chat_id]
                else:
                    # Создаем новую задачу для отправки статуса
                    task = asyncio.create_task(send_online_status(message, chat_id, connection))
                    online_tasks[chat_id] = task
                return

            if math_expression_pattern.match(message.text):
                if not user.calc_enabled:
                    return
                await handle_math_expression(message)
            elif message.text.strip().lower() in ["love", "love1"]:
                if not user.love_enabled:
                    return
                if message.text.strip().lower() == "love":
                    await handle_love_command(message)
                else:
                    await handle_love1_command(message)


    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-сообщения: {e}")

@business_router.deleted_business_messages()
async def deleted_business_messages(event: BusinessMessagesDeleted):
    """Обработка удаленных бизнес-сообщений."""
    try:
        connection = await event.bot.get_business_connection(event.business_connection_id)
        for message_id in event.message_ids:
                message_old = await db.get_message(message_id)
                if message_old:
                    await db.increase_deleted_messages_count(user_telegram_id=connection.user.id)
                    current_time = datetime.now().strftime("%H:%M:%S")
                    username = event.chat.username if event.chat.username else event.chat.first_name
                    user_link = f'<a href="tg://user?id={event.chat.id}">{username}</a>'

                    deleted_text = ""
                    if message_old and message_old.temp_message_id:
                        try:
                            # Список каналов, где может быть сообщение
                            channels = [-1002467764642, -1002353748102, -1002460477207, -1002300596890, -1002498479494, -1002395727554, -1002321264660]
                            message_found = False

                            # Пробуем найти и переслать сообщение из каждого канала
                            for channel in channels:
                                try:
                                    # Пересылаем оригинальное сообщение
                                    await event.bot.copy_message(
                                        chat_id=connection.user.id,
                                        from_chat_id=channel,
                                        message_id=message_old.temp_message_id
                                    )
                                    message_found = True

                                    # Отправляем информацию об удалении
                                    username = event.chat.username if event.chat.username else event.chat.first_name
                                    user_link = f'<a href="tg://user?id={event.chat.id}">{username}</a>'
                                    info_text = f"🗑 {user_link} удалил это сообщение\n⏰ Время удаления: {current_time}"
                                    await event.bot.send_message(
                                        chat_id=connection.user.id,
                                        text=info_text,
                                        parse_mode=ParseMode.HTML
                                    )
                                    break
                                except Exception:
                                    continue

                            if not message_found:
                                # Отправляем только одно уведомление, если сообщение не найдено
                                text = f"🗑 {user_link} удалил для тебя сообщение\n⏰ Время удаления: {current_time}\n⚠️ Оригинальное сообщение недоступно"
                                await event.bot.send_message(
                                    chat_id=connection.user.id,
                                    text=text,
                                    parse_mode=ParseMode.HTML
                                )

                        except Exception as e:
                            logger.error(f"Не удалось переслать удаленное сообщение: {e}")
                            # Отправляем уведомление об ошибке только если не удалось отправить сообщение
                            text = f"🗑 {user_link} удалил для тебя сообщение\n⏰ Время удаления: {current_time}"
                            await event.bot.send_message(
                                chat_id=connection.user.id,
                                text=text,
                                parse_mode=ParseMode.HTML
                            )
    except Exception as e:
        logger.error(f"Ошибка при обработке удаленных сообщений: {e}")


async def check_inactive_chats(bot: Bot): # Placeholder function
    """Checks for inactive chats and sends notifications (implementation needed)."""
    #  This function requires implementation details based on your specific requirements.
    #  It should query the database for inactive chats and send appropriate notifications using the bot.
    pass


from config import BOT_TOKEN, HISTORY_GROUP_ID

# Словарь для хранения тасков онлайн-статуса
online_tasks = {}

async def send_online_status(message: Message, chat_id: int, connection: BusinessConnection):
    """Отправка статуса онлайн"""
    try:
        await message.answer("✅ Онлайн статус активирован")
        while True:
            try:
                moscow_tz = datetime.now().astimezone(pytz.timezone('Europe/Moscow'))
                current_time = moscow_tz.strftime("%H:%M:%S")
                formatted_message = f"📱 Онлайн | ⏰ {current_time} МСК"
                await message.answer(text=formatted_message)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                await message.answer("❌ Онлайн статус деактивирован")
                if chat_id in online_tasks:
                    del online_tasks[chat_id]
                return
            except Exception as e:
                logger.error(f"Ошибка отправки онлайн статуса: {e}")
                if chat_id in online_tasks:
                    del online_tasks[chat_id]
                return
    except Exception as e:
        logger.error(f"Глобальная ошибка онлайн статуса: {e}")
        if chat_id in online_tasks:
            del online_tasks[chat_id]

@business_router.message(F.text.casefold().in_({"онлайн+", "онлайн-", "онл+", "онл-"}))
async def handle_online_status(message: Message):
    try:
        # Проверяем, что команду отправил владелец чата
        connection = await message.bot.get_business_connection(message.business_connection_id)
        if not connection or connection.user.id != message.from_user.id:
            return
            
        user = await db.get_user(message.from_user.id)
        if not user or not user.online_enabled:
            return

        chat_id = message.chat.id

        command = message.text.lower().strip()
        if command in ["онлайн+", "онл+"]:
            if chat_id in online_tasks:
                online_tasks[chat_id].cancel()
            task = asyncio.create_task(send_online_status(message, chat_id, connection))
            online_tasks[chat_id] = task
            await message.answer("✅ Онлайн статус активирован")
        elif command in ["онлайн-", "онл-"]:
            if chat_id in online_tasks:
                online_tasks[chat_id].cancel()
                del online_tasks[chat_id]
                await message.answer("❌ Онлайн статус деактивирован")
    except Exception as e:
        logger.error(f"Ошибка при обработке онлайн статуса: {e}")
    try:
        # Проверяем подписку отправителя
        user = await db.get_user(telegram_id=message.from_user.id)

        # Проверяем подписку и активацию модуля
        if not user or not user.subscription_end_date or user.subscription_end_date < datetime.now():
            await message.answer("❌ У вас нет активной подписки!")
            return

        if not user.online_enabled:  # Проверка включен ли модуль
            await message.answer("❌ Модуль онлайн-статуса отключен!")
            return

        chat_id = message.chat.id  # ID текущего чата
        connection = await message.bot.get_business_connection(message.business_connection_id)

        if message.text in ["Онлайн+", "Онл+"]:
            # Останавливаем предыдущий таск, если есть
            if chat_id in online_tasks and not online_tasks[chat_id].done():
                online_tasks[chat_id].cancel()

            # Создаем новый таск
            task = asyncio.create_task(send_online_status(message, chat_id, connection))
            online_tasks[chat_id] = task
            await message.answer("✅ Онлайн статус активирован")
            return  # Добавлен return для предотвращения дальнейшего выполнения
        
        elif message.text in ["Онлайн-", "Онл-"]:
            if chat_id in online_tasks:
                task = online_tasks[chat_id]
                task.cancel()  # Сразу отменяем таск
                del online_tasks[chat_id]  # Сразу удаляем из словаря
                await message.answer("❌ Онлайн статус деактивирован")
            return

    except Exception as e:
        logger.error(f"Ошибка активации онлайн статуса: {e}")
        await message.answer("❌ Произошла ошибка при активации статуса онлайн")

async def main():
    dp = Dispatcher()

    # Настройка проверки неактивности
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_inactive_chats, 'interval', hours=1) # Removed args=[bot] because it wasn't defined here.  This may need adjustment based on your bot instantiation
    scheduler.start()

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    # ... rest of the main function ...