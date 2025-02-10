import re
import asyncio
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted, CallbackQuery
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
        calc_message = await message.answer("🔄 Считаю...")

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

async def handle_stars_command(message: Message):
    """Обработка команды 'stars'."""
    frames = ["⭐️", "✨⭐️✨", "⭐️✨⭐️", "✨⭐️✨", "⭐️ Ты сияешь как звезда! ⭐️"]
    sent_message = await message.answer(frames[0])
    for frame in frames:
        await asyncio.sleep(0.7)
        await sent_message.edit_text(frame)

async def handle_hearts_command(message: Message):
    """Обработка команды 'hearts'."""
    frames = ["❤️", "💖", "💝", "💗", "💓", "💕", "💞", "💘", "💖 Моё сердце бьётся для тебя! 💖"]
    sent_message = await message.answer(frames[0])
    for frame in frames:
        await asyncio.sleep(0.5)
        await sent_message.edit_text(frame)



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
            await event.bot.send_message(event.user.id, texts.Texts.CONNECTION_ENABLED, reply_markup=kb.start_connection_keyboard)
        else:
            await db.update_user_business_bot_active(telegram_id=event.user.id, business_bot_active=False)
            await event.bot.send_message(event.user.id, texts.Texts.CONNECTION_DISABLED)
    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-подключения: {e}")

async def create_header_text(sender, receiver) -> str:
    """Создает заголовок сообщения с информацией об отправителе и получателе."""
    sender_name = sender.first_name
    if sender.last_name:
        sender_name += f" {sender.last_name}"
    elif sender.username:
        sender_name = sender.username

    receiver_name = receiver.first_name
    if receiver.last_name:
        receiver_name += f" {receiver.last_name}"
    elif receiver.username:
        receiver_name = receiver.username

    if not receiver_name:
        receiver_name = "Пользователь"

    sender_url = f'https://t.me/{sender.username}' if sender.username else f'tg://user?id={sender.id}'
    receiver_url = f'https://t.me/{receiver.username}' if receiver.username else f'tg://user?id={receiver.id}'

    sender_link = f'<a href="{sender_url}">{sender_name}</a>'
    receiver_link = f'<a href="{receiver_url}">{receiver_name}</a>'

    return f"📨 Новое сообщение\n━━━━━━━━━━━━━━━\n👉 От: {sender_link}\n👤 Кому: {receiver_link}\n\n"

async def prepare_message_update(message: Message, header: str) -> dict:
    """Подготавливает обновление для сообщения."""
    update = {}
    if message.entities:
        update["entities"] = [entity.model_copy(update={"length": entity.length + len(header)}) for entity in message.entities]
    elif message.caption_entities:
        update["caption_entities"] = [entity.model_copy(update={"length": entity.length + len(header)}) for entity in message.caption_entities]

    if message.caption:
        update["caption"] = f"{header}{message.caption}"
    elif message.html_text:
        update["text"] = f"{header}{message.html_text}"
    elif message.voice or message.video_note or message.video:
        media_type = "🎤 Голосовое сообщение" if message.voice else "🎥 Видео-кружок" if message.video_note else "📹 Видео"
        update["caption"] = f"{header}{media_type}"

    return update

async def get_target_channel(message: Message, user) -> int:
    """Определяет целевой канал для сообщения."""
    TEXT_CHANNELS = [-1002460477207, -1002353748102, -1002467764642]

    try:
        logger.info(f"Начало определения канала для юзера {user.telegram_id}")
        logger.info(f"Текущий channel_index пользователя: {user.channel_index}")

        if user.channel_index is None or user.channel_index >= len(TEXT_CHANNELS):
            logger.info("Индекс канала не установлен или невалидный")
            count = await db.get_total_users()
            next_index = count % len(TEXT_CHANNELS)
            logger.info(f"Получено количество пользователей: {count}, новый индекс: {next_index}")

            # Сохраняем новый индекс
            await db.update_user_channel_index(user.telegram_id, next_index)
            logger.info(f"Назначен новый канал {TEXT_CHANNELS[next_index]} для юзера {user.telegram_id}")
            return TEXT_CHANNELS[next_index]

        # Используем существующий индекс
        target_channel = TEXT_CHANNELS[user.channel_index]
        logger.info(f"Используется существующий канал {target_channel} для юзера {user.telegram_id}")
        logger.info(f"Тип сообщения: {message.content_type}")
        return target_channel

    except Exception as e:
        logger.error(f"Ошибка получения канала: {str(e)}")
        logger.error(f"Traceback: {e.__traceback__}")
        logger.info(f"Возвращается дефолтный канал {TEXT_CHANNELS[0]}")
        return TEXT_CHANNELS[0]  # Дефолтный канал при ошибке

    # Используем индекс для определения канала
    target_channel = TEXT_CHANNELS[user.channel_index]
    logger.info(f"User {user.telegram_id} -> Channel {target_channel} (index: {user.channel_index})")
    return target_channel

    MEDIA_CHANNELS = {
        'voice': -1002300596890,
        'photo': -1002498479494,
        'video_note': -1002395727554,
        'video': -1002321264660
    }

    message_type = next((type_ for type_ in ['voice', 'video_note', 'video', 'photo']
                       if hasattr(message, type_) and getattr(message, type_)), 'text')

    if message_type == 'text':
        # Используем индекс канала из базы данных
        return TEXT_CHANNELS[user.channel_index % 3]

    return MEDIA_CHANNELS.get(message_type, TEXT_CHANNELS[0])

async def send_message_to_channel(message_copy_model: Message, target_channel: int) -> Message:
    """Отправляет сообщение в канал с повторными попытками."""
    for attempt in range(3):
        try:
            temp_message = await message_copy_model.send_copy(
                chat_id=target_channel,
                parse_mode=ParseMode.HTML
            )
            if temp_message:
                return temp_message
        except Exception as e:
            if attempt == 2:
                raise e
            await asyncio.sleep(1)
    raise ValueError("Не удалось переслать сообщение")

@business_router.business_message()
async def business_message(message: Message):
    """Обработка бизнес-сообщений."""
    try:
        connection = await message.bot.get_business_connection(message.business_connection_id)
        user = await db.get_user(telegram_id=connection.user.id)
        if not user:
            return
        header = await create_header_text(message.from_user, connection.user)
        update = await prepare_message_update(message, header)

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

        try:
            logger.info(f"Начинаем пересылку сообщения от пользователя {message.from_user.id}")
            logger.info(f"Тип сообщения: {message.content_type}")
            logger.info(f"Текущий channel_index пользователя: {user.channel_index}")
            
            # Определяем целевой канал
            if message.content_type == 'text':
                target_channel = CHANNELS['text'][user.channel_index if user.channel_index is not None else 0]
                logger.info(f"Выбран текстовый канал: {target_channel}")
            else:
                target_channel = CHANNELS.get(message.content_type, CHANNELS['default'])
                logger.info(f"Выбран канал для {message.content_type}: {target_channel}")

            # Пересылаем сообщение
            logger.info(f"Пересылаем сообщение в канал {target_channel}")
            logger.info(f"Тип сообщения: {message.content_type}")

            target_channel = await get_target_channel(message, user)
            logger.info(f"Выбран целевой канал: {target_channel}")

            try:
                message_new = await send_message_to_channel(message_copy_model, target_channel)
                logger.info(f"Сообщение успешно переслано, новый message_id: {message_new.message_id}")
            except Exception as forward_error:
                logger.error(f"Ошибка при пересылке: {str(forward_error)}")
                raise forward_error

            if not message_new:
                error_msg = "Не удалось переслать сообщение"
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {str(e)}")
            # Используем резервный канал при ошибке
            try:
                message_new = await message_copy_model.send_copy(
                    chat_id=CHANNELS['text'][0],
                    parse_mode=ParseMode.HTML
                )
            except Exception as backup_error:
                logger.critical(f"Критическая ошибка при пересылке: {str(backup_error)}")
                return
        await db.create_message(user_telegram_id=connection.user.id, chat_id=message.chat.id, from_user_id=message.from_user.id, message_id=message.message_id, temp_message_id=message_new.message_id)
        await db.increase_active_messages_count(user_telegram_id=connection.user.id)
        await db.increment_messages_count(from_user_id=message.from_user.id, to_user_id=connection.user.id)

        # Обработка специальных команд с проверкой состояния модулей
        if message.text:
            if math_expression_pattern.match(message.text):
                if not user.calc_enabled:
                    return
                await handle_math_expression(message)

            elif message.text.strip().lower() in ["love", "love1", "stars", "hearts"]:
                if not user.love_enabled:
                    return
                if message.text.strip().lower() == "love":
                    await handle_love_command(message)
                elif message.text.strip().lower() == "love1":
                    await handle_love1_command(message)
                elif message.text.strip().lower() == "stars":
                    await handle_stars_command(message)
                else:
                    await handle_hearts_command(message)


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
                    # Проверяем настройки пользователя
                    user = await db.get_user(connection.user.id)
                    if not user.notifications_enabled or not user.delete_notifications:
                        return

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

@business_router.edited_business_message()
async def edited_business_message(message: Message):
    """Обработка измененных бизнес-сообщений."""
    try:
        # Получаем информацию о подключении
        connection = await message.bot.get_business_connection(message.business_connection_id)
        if not connection:
            logger.error("Не удалось получить информацию о подключении")
            return

        # Проверяем подписку
        user = await db.get_user(telegram_id=connection.user.id)
        subscription = await db.get_subscription(connection.user.id)

        message_old = await db.get_message(message.message_id)
        if message_old and user and subscription:
            # Проверяем настройки пользователя
            if not user.notifications_enabled or not user.edit_notifications:
                return

            # Получаем имя пользователя и время
            username = message.from_user.username if message.from_user.username else message.from_user.first_name
            user_link = f'<a href="tg://user?id={message.from_user.id}">{username}</a>'
            current_time = datetime.now().strftime("%H:%M:%S")

            notification_text = f"✏️ {user_link} отредактировал сообщение\n⏰ Время редактирования: {current_time}"
            await message.bot.send_message(
                chat_id=connection.user.id,
                text=notification_text,
                parse_mode=ParseMode.HTML
            )

            # Создаем текст для истории редактирования
            history_header = f"📝 Отредактированное сообщение\n👤 От: {user_link}\n⏰ Время: {current_time}\n\n"

            update = {}
            if message.caption_entities:
                update["caption_entities"] = [entity.model_copy(update={"length": entity.length + len(history_header)}) for entity in message.caption_entities]
            if message.caption:
                update["caption"] = f"{history_header}{message.caption}"
            elif message.html_text:
                update["text"] = f"{history_header}{message.html_text}"

            message_copy_model = message.model_copy(update=update)
            temp_message = await message_copy_model.send_copy(chat_id=HISTORY_GROUP_ID, parse_mode=ParseMode.HTML)

            await db.increase_edited_messages_count(user_telegram_id=message_old.user_telegram_id)
            await db.add_message_edit_history(user_telegram_id=message_old.user_telegram_id, message_id=message.message_id, chat_id=message.chat.id, from_user_id=message.from_user.id, temp_message_id=temp_message.message_id, date=datetime.now())
            await message.bot.copy_message(chat_id=message_old.user_telegram_id, from_chat_id=HISTORY_GROUP_ID, message_id=temp_message.message_id, reply_markup=kb.get_show_history_message_keyboard(message.message_id))
    except Exception as e:
        logger.error(f"Ошибка при обработке измененного сообщения: {e}")



async def check_inactive_chats(bot: Bot): # Placeholder function
    """Checks for inactive chats and sends notifications (implementation needed)."""
    #  This function requires implementation details based on your specific requirements.
    #  It should query the database for inactive chats and send appropriate notifications using the bot.
    pass


from config import BOT_TOKEN, HISTORY_GROUP_ID
import random

async def main():
    dp = Dispatcher()

    # Настройка проверки неактивности
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_inactive_chats, 'interval', hours=1) # Removed args=[bot] because it wasn't defined here.  This may need adjustment based on your bot instantiation
    scheduler.start()

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    # ... rest of the main function ...
async def keep_online(bot: Bot, user_id: int):
    """Функция для поддержания онлайн статуса через Router_business"""
    while True:
        try:
            # Получаем подключение для конкретного пользователя
            connection = await bot.get_business_connection(user_id)
            if connection and connection.is_enabled:
                # Имитируем активность через Router_business
                await bot.send_chat_action(chat_id=connection.user.id, action="typing")
            await asyncio.sleep(5)  # Обновляем каждые 5 секунд
        except Exception as e:
            logger.error(f"Ошибка в keep_online: {e}")
            await asyncio.sleep(5)

# Добавим словарь для хранения тасков
online_tasks = {}

@business_router.callback_query(F.data == "toggle_always_online")
async def toggle_always_online(callback: CallbackQuery):
    """Включение/выключение вечного онлайна"""
    try:
        user_id = callback.from_user.id
        user = await db.get_user(telegram_id=user_id)

        if user_id in online_tasks:
            # Выключаем вечный онлайн
            online_tasks[user_id].cancel()
            del online_tasks[user_id]
            await callback.answer("🔴 Вечный онлайн выключен!")
        else:
            # Включаем вечный онлайн
            task = asyncio.create_task(keep_online(callback.bot, user_id))
            online_tasks[user_id] = task
            await callback.answer("🟢 Вечный онлайн включен!")

    except Exception as e:
        logger.error(f"Ошибка в toggle_always_online: {e}")
        await callback.answer("❌ Произошла ошибка!")