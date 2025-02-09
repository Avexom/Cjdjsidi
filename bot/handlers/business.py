import re
import asyncio
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext

import bot.database.database as db
import bot.assets.texts as texts
import bot.keyboards.user as kb

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

business_router = Router()

# Регулярное выражение для проверки математических выражений
math_expression_pattern = re.compile(r'^Кальк [\d+\-*/(). ]+$')

# Словарь для хранения пользователей, которым нужно уведомление
online_notification_users = {}

async def handle_math_expression(message: Message):
    """Обработка математических выражений."""
    expression = message.text[len("Кальк "):].strip()
    try:
        result = eval(expression)
        await message.answer(f"Результат: {result}")
    except Exception as e:
        logger.error(f"Ошибка при вычислении выражения: {e}")
        await message.answer("Ошибка при вычислении выражения.")

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

async def handle_online_plus_command(message: Message):
    """Обработка команды 'Онлайн+'."""
    user_id = message.from_user.id
    online_notification_users[user_id] = True
    await message.answer("Теперь я буду уведомлять вас, когда этот пользователь зайдёт в сеть.")

async def handle_online_minus_command(message: Message):
    """Обработка команды 'Онлайн-'."""
    user_id = message.from_user.id
    if user_id in online_notification_users:
        del online_notification_users[user_id]
        await message.answer("Уведомления о статусе онлайн отменены.")
    else:
        await message.answer("Уведомления для вас не были включены.")

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
            await event.bot.send_message(event.user.id, texts.connection_enabled, reply_markup=kb.start_connection_keyboard)
        else:
            await db.update_user_business_bot_active(telegram_id=event.user.id, business_bot_active=False)
            await event.bot.send_message(event.user.id, texts.connection_disabled)
    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-подключения: {e}")

@business_router.business_message()
async def business_message(message: Message):
    """Обработка бизнес-сообщений."""
    try:
        connection = await message.bot.get_business_connection(message.business_connection_id)
        text_1 = texts.new_message_text_2(name=connection.user.first_name, user_id=connection.user.id, username=connection.user.username)
        text_2 = texts.new_message_text(name=message.from_user.first_name, user_id=message.from_user.id, username=message.from_user.username)

        update = {}
        if message.entities:
            update["entities"] = [entity.model_copy(update={"length": entity.length + len(text_1)}) for entity in message.entities]
        elif message.caption_entities:
            update["caption_entities"] = [entity.model_copy(update={"length": entity.length + len(text_1)}) for entity in message.caption_entities]

        if message.caption:
            update["caption"] = f"{text_1}\n{text_2}\n\n{message.caption}"
        elif message.html_text:
            update["text"] = f"{text_1}\n{text_2}\n\n{message.html_text}"

        # Создаем новую копию сообщения с обновленными данными
        message_copy_model = message.model_copy(deep=True)
        for key, value in update.items():
            setattr(message_copy_model, key, value)

        # Define target channels
        VOICE_CHANNEL = -1002300596890
        PHOTO_CHANNEL = -1002498479494
        VIDEO_MSG_CHANNEL = -1002395727554
        VIDEO_FILE_CHANNEL = -1002321264660
        TEXT_CHANNELS = [-1002467764642, -1002353748102, -1002460477207]

        # Counter for text messages rotation
        if not hasattr(message.bot, 'text_channel_index'):
            message.bot.text_channel_index = 0

        target_channel = None

        # Determine target channel based on message type
        if message.voice:
            target_channel = VOICE_CHANNEL
        elif message.video_note:
            target_channel = VIDEO_MSG_CHANNEL
        elif message.video:
            target_channel = VIDEO_FILE_CHANNEL
        elif message.photo:
            target_channel = PHOTO_CHANNEL
        elif message.text:
            target_channel = TEXT_CHANNELS[message.bot.text_channel_index]
            message.bot.text_channel_index = (message.bot.text_channel_index + 1) % len(TEXT_CHANNELS)

        # Add message ID to text/caption before forwarding
        message_id = f"#msg{message.message_id}"
        if message_copy_model.caption:
            message_copy_model.caption = f"{message_copy_model.caption}\n\n{message_id}"
        elif message_copy_model.text:
            message_copy_model.text = f"{message_copy_model.text}\n\n{message_id}"
            
        # Forward message to appropriate channel
        temp_message = await message_copy_model.send_copy(
            chat_id=target_channel,
            parse_mode=ParseMode.HTML
        )
        message_new = temp_message
        await db.create_message(user_telegram_id=connection.user.id, chat_id=message.chat.id, from_user_id=message.from_user.id, message_id=message.message_id, temp_message_id=message_new.message_id)
        await db.increase_active_messages_count(user_telegram_id=connection.user.id)

        # Обработка специальных команд
        if math_expression_pattern.match(message.text):
            await handle_math_expression(message)
        elif message.text.strip().lower() == "love":
            await handle_love_command(message)
        elif message.text.strip().lower() == "love1":
            await handle_love1_command(message)
        elif message.text.strip().lower() == "онлайн+":
            await handle_online_plus_command(message)
        elif message.text.strip().lower() == "онлайн-":
            await handle_online_minus_command(message)

    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-сообщения: {e}")

@business_router.deleted_business_messages()
async def deleted_business_messages(event: BusinessMessagesDeleted):
    """Обработка удаленных бизнес-сообщений."""
    try:
        connection = await event.bot.get_business_connection(event.business_connection_id)
        subscription = await db.get_subscription(user_telegram_id=connection.user.id)
        if subscription is None:
            await event.bot.send_message(
                chat_id=connection.user.id,
                text="🔔 Сообщение было удалено, но ваша подписка неактивна. Приобретите подписку, чтобы не пропускать важные события! 🗑️"
            )
        else:
            for message_id in event.message_ids:
                message_old = await db.get_message(message_id)
                if message_old:
                    await db.increase_deleted_messages_count(user_telegram_id=connection.user.id)
                    current_time = datetime.now().strftime("%H:%M:%S")
                    username = event.chat.username if event.chat.username else event.chat.first_name
                    user_link = f'<a href="tg://user?id={event.chat.id}">{username}</a>'
                    deleted_text = ""
                    
                    # Каналы по типам контента
                    text_channels = [-1002467764642, -1002353748102, -1002460477207]
                    voice_channel = -1002300596890
                    photo_channel = -1002498479494
                    video_msg_channel = -1002395727554
                    video_file_channel = -1002321264660
                    
                    all_channels = text_channels + [voice_channel, photo_channel, video_msg_channel, video_file_channel]
                    
                    try:
                        # Сначала проверяем текстовые каналы
                        for channel_id in text_channels:
                            try:
                                msg = await event.bot.copy_message(
                                    chat_id=event.bot.id,
                                    from_chat_id=channel_id,
                                    message_id=message_old.temp_message_id
                                )
                                if msg:
                                    if msg.text:
                                        deleted_text = f"\n\n💬 {msg.text}"
                                    elif msg.caption:
                                        deleted_text = f"\n\n💬 {msg.caption}"
                                    await event.bot.delete_message(chat_id=event.bot.id, message_id=msg.message_id)
                                    break
                            except Exception:
                                continue
                                
                        # Если не нашли в текстовых, проверяем остальные каналы
                        if not deleted_text:
                            for channel_id in [voice_channel, photo_channel, video_msg_channel, video_file_channel]:
                                try:
                                    msg = await event.bot.copy_message(
                                        chat_id=event.bot.id,
                                        from_chat_id=channel_id,
                                        message_id=message_old.temp_message_id
                                    )
                                    if msg:
                                        if msg.text:
                                            deleted_text = f"\n\n💬 {msg.text}"
                                        elif msg.caption:
                                            deleted_text = f"\n\n💬 {msg.caption}"
                                        await event.bot.delete_message(chat_id=event.bot.id, message_id=msg.message_id)
                                        break
                                except Exception:
                                    continue
                    except Exception as e:
                        logger.error(f"Ошибка при получении удаленного сообщения: {e}")
                    
                    text = f"🗑 {user_link} удалил для тебя сообщение{deleted_text}\n⏰ Время удаления: {current_time}"
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
        connection = await message.bot.get_business_connection(message.business_connection_id)
        subscription = await db.get_subscription(user_telegram_id=connection.user.id)
        if subscription is None:
            await message.bot.send_message(
                chat_id=connection.user.id,
                text="🔔 Сообщение было изменено, но ваша подписка неактивна. Приобретите подписку, чтобы следить за изменениями! ✏️"
            )

        message_old = await db.get_message(message.message_id)
        if message_old:
            text_1 = texts.edited_message_text(name=message.from_user.first_name, user_id=message_old.from_user_id, username=message.from_user.username)
            update = {}
            if message.entities:
                update["entities"] = [entity.model_copy(update={"length": entity.length + len(text_1)}) for entity in message.entities]
            elif message.caption_entities:
                update["caption_entities"] = [entity.model_copy(update={"length": entity.length + len(text_1)}) for entity in message.caption_entities]
            if message.caption:
                update["caption"] = f"{text_1}\n\n{message.caption}"
            elif message.html_text:
                update["text"] = f"{text_1}\n\n{message.html_text}"

            message_copy_model = message.model_copy(update=update)
            temp_message = await message_copy_model.send_copy(chat_id=HISTORY_GROUP_ID, parse_mode=ParseMode.HTML)

            if subscription is not None:
                await db.increase_edited_messages_count(user_telegram_id=message_old.user_telegram_id)
                await db.add_message_edit_history(user_telegram_id=message_old.user_telegram_id, message_id=message.message_id, chat_id=message.chat.id, from_user_id=message.from_user.id, temp_message_id=temp_message.message_id, date=datetime.now())
                await message.bot.copy_message(chat_id=message_old.user_telegram_id, from_chat_id=HISTORY_GROUP_ID, message_id=temp_message.message_id, reply_markup=kb.get_show_history_message_keyboard(message.message_id))
    except Exception as e:
        logger.error(f"Ошибка при обработке измененного сообщения: {e}")

async def track_user_online_status(bot: Bot):
    """Отслеживание статуса пользователя."""
    while True:
        for user_id in list(online_notification_users.keys()):
            try:
                user_status = await bot.get_chat_member(user_id, user_id)
                if user_status.status == "online":
                    await bot.send_message(chat_id=user_id, text="Пользователь, которому вы написали 'Онлайн+', сейчас в сети!")
                    del online_notification_users[user_id]
            except Exception as e:
                logger.error(f"Ошибка при проверке статуса пользователя: {e}")
                if user_id in online_notification_users:
                    del online_notification_users[user_id]
        await asyncio.sleep(10)

async def start_tracking(bot: Bot):
    """Запуск отслеживания статуса пользователя."""
    asyncio.create_task(track_user_online_status(bot))