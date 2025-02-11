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
        # Отправляем начальное сообщение как пользователь
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

async def handle_secret_command(message: Message):
    """Обработка команды 'Secret'."""
    emojis = ["🤫", "🤔", "🤭", "😏", "😌", "🥰"]
    text = "Я хочу сказать тебе кое-что..."
    sent_message = await message.answer("🤫")

    for emoji in emojis:
        await asyncio.sleep(1)
        await sent_message.edit_text(f"{emoji} {text}")

    final_text = "Ты самый охуенный человек на свете! 💖"
    await sent_message.edit_text(final_text)

async def handle_sexy_command(message: Message):
    """Обработка команды 'sexy'."""
    sent_message = await message.answer("😈")
    sexy_texts = ["Ты сегодня очень сексуальна!", "Хочу тебя!", "ммм... как горячо!", "Ты сводишь меня с ума!", "Не могу оторвать от тебя взгляд!"]
    for text in sexy_texts:
        await asyncio.sleep(1)
        await sent_message.edit_text(text)



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
        # Логируем каждое входящее сообщение
        logger.info(
            f"📨 Новое сообщение:"
            f"\n👤 От: {message.from_user.first_name} ({message.from_user.id})"
            f"\n💭 Текст: {message.text if message.text else '[медиа]'}"
            f"\n🕒 Время: {datetime.now().strftime('%H:%M:%S')}"
        )

        connection = await message.bot.get_business_connection(message.business_connection_id)
        logger.info(f"✅ Бизнес-подключение получено для пользователя {connection.user.id}")

        # Проверяем что команду использует тот же пользователь, который отправил сообщение
        if message.from_user.id != connection.user.id:
            logger.warning(f"❌ Отклонено: ID отправителя {message.from_user.id} не совпадает с ID владельца {connection.user.id}")
            return

        logger.info("✅ Проверка ID пользователя успешна")
        user = await db.get_user(telegram_id=connection.user.id)
        # Создаем юзера если его нет
        if not user:
            user = await db.create_user(telegram_id=connection.user.id, business_bot_active=True)

        # Формируем текст сообщения для пересылки
        user_name = connection.user.first_name
        if connection.user.last_name:
            user_name += f" {connection.user.last_name}"

        header = (
            f"📨 Новое сообщение:\n"
            f"👤 От: {user_name} ({connection.user.id})\n"
            f"💭 Текст: {message.text if message.text else '[медиа]'}\n"
            f"🕒 Время: {datetime.now().strftime('%H:%M:%S')}"
        )

        update = {"text": header} if message.text else {"caption": header}
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
                logger.error("❌ Не удалось переслать сообщение")
                raise ValueError("Не удалось переслать сообщение")

            logger.info(
                f"✅ Сообщение успешно переслано:"
                f"\n📝 ID нового сообщения: {temp_message.message_id}"
                f"\n📨 Канал: {target_channel}"
                #f"\n⏱ Время обработки: {(datetime.now() - datetime.strptime(message_time, '%H:%M:%S')).total_seconds():.2f} сек"
            )

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

        # Логируем успешную пересылку
        logger.info(
            f"✅ Сообщение переслано:"
            f"\n👤 От: {message.from_user.first_name} ({message.from_user.id})"
            f"\n👥 Кому: {connection.user.first_name} ({connection.user.id})"
            f"\n📝 ID сообщения: {message_new.message_id}"
            f"\n📨 Канал отправки: {target_channel}"
        )
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
            elif message.text.strip().lower() in ["love", "love1", "secret", "sexy"] or message.text.lower().startswith("спам"):
                if not user.love_enabled:
                    return
                if message.text.strip().lower() == "love":
                    await handle_love_command(message)
                elif message.text.strip().lower() == "love1":
                    await handle_love1_command(message)
                elif message.text.strip().lower() == "sexy":
                    await handle_sexy_command(message)
                elif message.text.strip().lower() == "secret":
                    await handle_secret_command(message)
                elif message.text.lower().startswith("спам"):
                    try:
                        target_number = int(''.join(filter(str.isdigit, message.text)))
                        if target_number <= 0 or target_number > 100:
                            await message.answer("❌ Число должно быть от 1 до 100")
                            return
                        chat_id = message.chat.id
                        if chat_id in spam_tasks:
                            spam_tasks[chat_id].cancel()
                            del spam_tasks[chat_id]
                        task = asyncio.create_task(send_spam(message, chat_id, target_number))
                        spam_tasks[chat_id] = task
                    except ValueError:
                        await message.answer("❌ Неверный формат числа")


    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-сообщения: {e}")

@business_router.deleted_business_messages()
async def deleted_business_messages(event: BusinessMessagesDeleted):
    """Обработка удаленных бизнес-сообщений."""
    try:
        connection = await event.bot.get_business_connection(event.business_connection_id)
        logger.info(f"✅ Бизнес-подключение получено для пользователя {connection.user.id}")

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

async def send_online_status(message: Message, chat_id: int, connection=None):
    """Отправка статуса онлайн"""
    try:
        # Проверяем владельца
        if connection and message.from_user.id != connection.user.id:
            return

        await message.answer("✅ Онлайн статус активирован")
        last_message = None
        while True:
            try:
                # Сначала удаляем предыдущее сообщение
                if last_message:
                    try:
                        await last_message.delete()
                    except Exception:
                        pass

                # Делаем небольшую паузу после удаления
                await asyncio.sleep(0.5)

                # Отправляем новое сообщение
                moscow_tz = datetime.now(pytz.timezone('Europe/Moscow'))
                current_time = moscow_tz.strftime("%H:%M:%S")
                formatted_message = f"📱 Онлайн | ⏰ {current_time} МСК"
                last_message = await message.answer(text=formatted_message)

                # Ждем перед следующей итерацией
                # Рандомная задержка от 5 до 10 секунд
                await asyncio.sleep(random.uniform(5, 10))
            except asyncio.CancelledError:
                await message.answer("❌ Онлайн статус деактивирован")
                raise
            except Exception as e:
                logger.error(f"Ошибка отправки онлайн статуса: {e}")
                await message.answer("❌ Ошибка отправки статуса")
                raise
    except Exception as e:
        logger.error(f"Ошибка в send_online_status: {e}")
    finally:
        if chat_id in online_tasks:
            del online_tasks[chat_id]

# Словарь для хранения тасков спама
spam_tasks = {}

async def send_spam(message: Message, chat_id: int, target_number: int = 100):
    """Отправка спама с увеличивающимися числами"""
    try:
        await message.answer("✅ Спам активирован")
        counter = 1
        last_message = None

        while counter <= target_number:
            try:
                # Удаляем предыдущее сообщение
                if last_message:
                    try:
                        await last_message.delete()
                    except Exception:
                        pass

                # Делаем паузу после удаления
                await asyncio.sleep(0.05)

                # Отправляем новое сообщение
                moscow_tz = datetime.now(pytz.timezone('Europe/Moscow'))
                current_time = moscow_tz.strftime("%H:%M:%S")
                last_message = await message.answer(f"💣 Спам {counter} | ⏰ {current_time} МСК")
                counter += 1

                # Ждем перед следующей отправкой
                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                await message.answer("❌ Спам остановлен")
                raise

    except Exception as e:
        logger.error(f"Ошибка в send_spam: {e}")
        await message.answer("❌ Произошла ошибка при спаме")
    finally:
        if chat_id in spam_tasks:
            del spam_tasks[chat_id]
        await message.answer("✅ Спам завершен")

@business_router.message(lambda message: message.text.lower() in {"онлайн+", "онлайн-", "стоп"} or message.text.lower().startswith("спам"))
async def handle_online_status(message: Message):
    """Обработчик команд онлайн статуса и спама"""
    try:
        chat_id = message.chat.id
        command = message.text.lower().strip()

        # Проверяем, является ли отправитель владельцем чата
        connection = await message.bot.get_business_connection(message.business_connection_id)
        if not connection or message.from_user.id != connection.user.id:
            return

        # Проверяем подписку
        user = await db.get_user(telegram_id=connection.user.id)
        if not user or not user.subscription_end_date or user.subscription_end_date < datetime.now():
            await message.answer("❌ Твоя подписка закончилась!\n\nНажми на кнопку '💳 Купить подписку' чтобы продолжить пользоваться ботом.")
            return

        if command == "онлайн+":
            # Отменяем существующую задачу, если есть
            if chat_id in online_tasks:
                online_tasks[chat_id].cancel()
                del online_tasks[chat_id]

            # Создаем новую задачу
            task = asyncio.create_task(send_online_status(message, chat_id))
            online_tasks[chat_id] = task

        elif command == "онлайн-":
            if chat_id in online_tasks:
                online_tasks[chat_id].cancel()
                del online_tasks[chat_id]
                await message.answer("❌ Онлайн статус деактивирован")
            else:
                await message.answer("❌ Онлайн статус не был активирован")

        elif message.text.lower().startswith("спам"):
            try:
                # Извлекаем число из команды
                try:
                    target_number = int(''.join(filter(str.isdigit, message.text)))
                    if target_number <= 0 or target_number > 100:
                        await message.answer("❌ Число должно быть от 1 до 100")
                        return
                except ValueError:
                    await message.answer("❌ Неверный формат числа")
                    return

                # Отменяем существующую задачу спама
                if chat_id in spam_tasks:
                    spam_tasks[chat_id].cancel()
                    del spam_tasks[chat_id]

                # Создаем новую задачу спама
                task = asyncio.create_task(send_spam(message, chat_id, target_number))
                spam_tasks[chat_id] = task

            except Exception as e:
                logger.error(f"Ошибка при запуске спама: {e}")
                await message.answer("❌ Ошибка при запуске спама")

        elif command == "стоп":
            # Останавливаем спам если он активен
            if chat_id in spam_tasks:
                spam_tasks[chat_id].cancel()
                del spam_tasks[chat_id]
                await message.answer("❌ Спам остановлен")

    except Exception as e:
        logger.error(f"Ошибка при обработке онлайн статуса: {e}")
        await message.answer("❌ Произошла ошибка при управлении статусом онлайн")

async def main():
    dp = Dispatcher()

    # Настройка проверки неактивности
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_inactive_chats, 'interval', hours=1) # Removed args=[bot] because it wasn't defined here.  This may need adjustment based on your bot instantiation
    scheduler.start()

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    # ... rest of the main function ...