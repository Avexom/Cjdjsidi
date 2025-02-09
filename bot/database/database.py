from datetime import datetime, date
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import (
    ForeignKey, Column, Integer, String, BigInteger, Boolean, Date, DateTime,
    func, select, update, delete, insert, and_
)
from sqlalchemy.orm import declarative_base
from async_lru import alru_cache

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка базы данных
DATABASE_URL = "sqlite+aiosqlite:///database.db"
Base = declarative_base()
engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Модели базы данных
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    business_bot_active = Column(Boolean, nullable=False, default=False)
    active_messages_count = Column(Integer, nullable=False, default=0)
    edited_messages_count = Column(Integer, nullable=False, default=0)
    deleted_messages_count = Column(Integer, nullable=False, default=0)
    channel_index = Column(Integer, nullable=False, default=0)
    is_banned = Column(Boolean, nullable=False, default=False)
    ban_reason = Column(String, nullable=True)
    username = Column(String, nullable=True)

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    from_user_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    temp_message_id = Column(BigInteger, nullable=False)

class MessageEditHistory(Base):
    __tablename__ = 'message_edit_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    message_id = Column(BigInteger, ForeignKey("messages.message_id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    from_user_id = Column(BigInteger, nullable=False)
    temp_message_id = Column(BigInteger, nullable=False)
    date = Column(DateTime, nullable=False)

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    end_date = Column(Date, nullable=False)

class Settings(Base):
    __tablename__ = 'settings'

    name = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

class UserMessageStats(Base):
    __tablename__ = 'user_message_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    to_user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    messages_count = Column(Integer, default=0, nullable=False)

# Контекстный менеджер для управления сессиями
@asynccontextmanager
async def get_db_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise

# Инициализация базы данных
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await create_default_settings()

# Создание настроек по умолчанию
async def create_default_settings():
    async with get_db_session() as session:
        if await session.scalar(select(Settings).where(Settings.name == "subscription_price")) is None:
            await session.execute(
                insert(Settings).values(name="subscription_price", value="30")
            )

# Операции с пользователями
async def create_user(telegram_id: int, business_bot_active: bool = False) -> User:
    """
    Создать нового пользователя с автоматическим назначением channel_index.

    :param telegram_id: ID пользователя в Telegram.
    :param business_bot_active: Активен ли бизнес-бот.
    :return: Созданный пользователь.
    """
    async with get_db_session() as session:
        # Получаем количество существующих пользователей для определения следующего индекса
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar() or 0
        next_index = count % 3  # Используем остаток от деления на 3 (так как у нас 3 текстовых канала)
        
        user = User(telegram_id=telegram_id, business_bot_active=business_bot_active, channel_index=next_index)
        session.add(user)
        return user

async def get_user(telegram_id: int) -> Optional[User]:
    """
    Получить пользователя по его Telegram ID.

    :param telegram_id: ID пользователя в Telegram.
    :return: Объект User или None, если пользователь не найден.
    """
    async with get_db_session() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))

async def update_user_business_bot_active(telegram_id: int, business_bot_active: bool):
    """
    Обновить статус бизнес-бота для пользователя.

    :param telegram_id: ID пользователя в Telegram.
    :param business_bot_active: Новый статус бизнес-бота.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == telegram_id).values(business_bot_active=business_bot_active)
        )

# Операции с сообщениями
async def create_message(user_telegram_id: int, chat_id: int, from_user_id: int, message_id: int, temp_message_id: int) -> Message:
    """
    Создать новое сообщение.

    :param user_telegram_id: ID пользователя в Telegram.
    :param chat_id: ID чата.
    :param from_user_id: ID отправителя.
    :param message_id: ID сообщения.
    :param temp_message_id: Временный ID сообщения.
    :return: Созданное сообщение.
    """
    async with get_db_session() as session:
        message = Message(
            user_telegram_id=user_telegram_id,
            chat_id=chat_id,
            from_user_id=from_user_id,
            message_id=message_id,
            temp_message_id=temp_message_id
        )
        session.add(message)
        return message

async def get_message(message_id: int) -> Optional[Message]:
    """
    Получить сообщение по его ID.

    :param message_id: ID сообщения.
    :return: Объект Message или None, если сообщение не найдено.
    """
    async with get_db_session() as session:
        return await session.scalar(select(Message).where(Message.message_id == message_id))

# Операции с подписками
async def create_subscription(user_telegram_id: int, end_date: date) -> Subscription:
    """
    Создать новую подписку.

    :param user_telegram_id: ID пользователя в Telegram.
    :param end_date: Дата окончания подписки.
    :return: Созданная подписка.
    """
    async with get_db_session() as session:
        subscription = Subscription(user_telegram_id=user_telegram_id, end_date=end_date)
        session.add(subscription)
        return subscription

async def get_subscription(user_telegram_id: int) -> Optional[Subscription]:
    """
    Получить подписку пользователя.

    :param user_telegram_id: ID пользователя в Telegram.
    :return: Объект Subscription или None, если подписка не найдена.
    """
    async with get_db_session() as session:
        return await session.scalar(select(Subscription).where(Subscription.user_telegram_id == user_telegram_id))

async def delete_subscription(user_telegram_id: int):
    """
    Удалить подписку пользователя.

    :param user_telegram_id: ID пользователя в Telegram.
    """
    async with get_db_session() as session:
        await session.execute(delete(Subscription).where(Subscription.user_telegram_id == user_telegram_id))

async def delete_expired_subscriptions():
    """
    Удаляет истекшие подписки из базы данных.
    """
    async with get_db_session() as session:
        try:
            # Удаляем подписки, у которых end_date меньше текущей даты
            await session.execute(
                delete(Subscription).where(Subscription.end_date < datetime.now().date())
            )
            await session.commit()
            logger.info("Expired subscriptions deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting expired subscriptions: {e}")
            await session.rollback()
            raise

# Увеличение счетчиков сообщений
async def increase_active_messages_count(user_telegram_id: int):
    """
    Увеличить счетчик активных сообщений пользователя.

    :param user_telegram_id: ID пользователя в Telegram.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == user_telegram_id).values(active_messages_count=User.active_messages_count + 1)
        )

async def increase_edited_messages_count(user_telegram_id: int):
    """
    Увеличить счетчик отредактированных сообщений пользователя.

    :param user_telegram_id: ID пользователя в Telegram.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == user_telegram_id).values(edited_messages_count=User.edited_messages_count + 1)
        )

async def increase_deleted_messages_count(user_telegram_id: int):
    """
    Увеличить счетчик удаленных сообщений пользователя.

    :param user_telegram_id: ID пользователя в Telegram.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == user_telegram_id).values(deleted_messages_count=User.deleted_messages_count + 1)
        )

# История редактирования сообщений
async def add_message_edit_history(user_telegram_id: int, message_id: int, chat_id: int, from_user_id: int, temp_message_id: int, date: datetime) -> MessageEditHistory:
    """
    Добавить запись в историю редактирования сообщений.

    :param user_telegram_id: ID пользователя в Telegram.
    :param message_id: ID сообщения.
    :param chat_id: ID чата.
    :param from_user_id: ID отправителя.
    :param temp_message_id: Временный ID сообщения.
    :param date: Дата редактирования.
    :return: Созданная запись в истории.
    """
    async with get_db_session() as session:
        history_entry = MessageEditHistory(
            user_telegram_id=user_telegram_id,
            message_id=message_id,
            chat_id=chat_id,
            from_user_id=from_user_id,
            temp_message_id=temp_message_id,
            date=date
        )
        session.add(history_entry)
        return history_entry

async def get_message_edit_history(message_id: int) -> Dict[str, Any]:
    """
    Получить историю редактирования сообщения.

    :param message_id: ID сообщения.
    :return: Словарь с историей редактирования и оригинальным сообщением.
    """
    async with get_db_session() as session:
        # Получаем оригинальное сообщение
        old_message = await session.scalar(select(Message).where(Message.message_id == message_id))

        # Получаем историю редактирования
        history = await session.execute(
            select(MessageEditHistory).where(MessageEditHistory.message_id == message_id)
        )
        history_entries = history.scalars().all()

        return {'old_message': old_message, 'message_edit_history': history_entries}

# Статистика
@alru_cache(maxsize=1)
async def get_total_users() -> int:
    """
    Получить общее количество пользователей.

    :return: Количество пользователей.
    """
    async with get_db_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0

@alru_cache(maxsize=1)
async def get_total_subscriptions() -> int:
    """
    Получить общее количество подписок.

    :return: Количество подписок.
    """
    async with get_db_session() as session:
        result = await session.execute(select(func.count(Subscription.id)))
        return result.scalar() or 0

@alru_cache(maxsize=1)
async def get_total_messages() -> int:
    """
    Получить общее количество сообщений.

    :return: Количество сообщений.
    """
    async with get_db_session() as session:
        result = await session.execute(select(func.sum(User.active_messages_count)))
        return result.scalar() or 0

@alru_cache(maxsize=1)
async def get_total_edited_messages() -> int:
    """
    Получить общее количество отредактированных сообщений.

    :return: Количество отредактированных сообщений.
    """
    async with get_db_session() as session:
        result = await session.execute(select(func.sum(User.edited_messages_count)))
        return result.scalar() or 0

@alru_cache(maxsize=1)
async def get_total_deleted_messages() -> int:
    """
    Получить общее количество удаленных сообщений.

    :return: Количество удаленных сообщений.
    """
    async with get_db_session() as session:
        result = await session.execute(select(func.sum(User.deleted_messages_count)))
        return result.scalar() or 0

@alru_cache(maxsize=1)
async def get_total_users_with_active_business_bot() -> int:
    """
    Получить количество пользователей с активным бизнес-ботом.

    :return: Количество пользователей.
    """
    async with get_db_session() as session:
        result = await session.execute(select(func.count(User.id)).where(User.business_bot_active == True))
        return result.scalar() or 0

# Операции с настройками
async def set_subscription_price(price: float):
    """
    Установить цену подписки.

    :param price: Новая цена подписки.
    """
    async with get_db_session() as session:
        await session.execute(
            update(Settings).where(Settings.name == "subscription_price").values(value=str(price))
        )

async def get_subscription_price() -> float:
    """
    Получить текущую цену подписки.

    :return: Цена подписки.
    """
    async with get_db_session() as session:
        result = await session.scalar(select(Settings).where(Settings.name == "subscription_price"))
        return float(result.value) if result else 0.0

# Миграция базы данных
async def migrate_db():
    """Добавляет новые колонки в существующие таблицы"""
    async with engine.begin() as conn:
        result = await conn.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in result.fetchall()]
        
        if 'channel_index' not in columns:
            await conn.execute("ALTER TABLE users ADD COLUMN channel_index INTEGER DEFAULT 0")
            logger.info("Added channel_index column to users table")
            
        if 'is_banned' not in columns:
            await conn.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE")
            logger.info("Added is_banned column to users table")
            
        if 'ban_reason' not in columns:
            await conn.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT")
            logger.info("Added ban_reason column to users table")
            
        if 'username' not in columns:
            await conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
            logger.info("Added username column to users table")

# Запуск инициализации базы данных
async def main():
    await init_db()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
async def reset_channel_indexes():
    """
    Сбросить channel_index для всех пользователей на 0
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).values(channel_index=0)
        )


async def update_user_channel_index(telegram_id: int, channel_index: int):
    """
    Обновить индекс канала пользователя.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == telegram_id).values(channel_index=channel_index)
        )

async def increment_messages_count(from_user_id: int, to_user_id: int):
    """
    Увеличить счетчик сообщений между пользователями
    """
    async with get_db_session() as session:
        stats = await session.scalar(
            select(UserMessageStats).where(
                and_(
                    UserMessageStats.from_user_id == from_user_id,
                    UserMessageStats.to_user_id == to_user_id
                )
            )
        )
        if stats:
            await session.execute(
                update(UserMessageStats)
                .where(
                    and_(
                        UserMessageStats.from_user_id == from_user_id,
                        UserMessageStats.to_user_id == to_user_id
                    )
                )
                .values(messages_count=UserMessageStats.messages_count + 1)
            )
        else:
            stats = UserMessageStats(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                messages_count=1
            )
            session.add(stats)

async def get_user_message_stats(user_id: int) -> List[Dict[str, Any]]:
    """
    Получить статистику сообщений пользователя
    """
    async with get_db_session() as session:
        stats = await session.execute(
            select(UserMessageStats).where(
                 or_(
                    UserMessageStats.from_user_id == user_id,
                    UserMessageStats.to_user_id == user_id
                )
            )
        )
        return [
            {
                'from_user_id': stat.from_user_id,
                'to_user_id': stat.to_user_id,
                'messages_count': stat.messages_count
            }
            for stat in stats.scalars()
        ]

async def ban_user(telegram_id: int, reason: str = "Не указана"):
    """
    Заблокировать пользователя.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == telegram_id)
            .values(is_banned=True, ban_reason=reason)
        )

async def unban_user(telegram_id: int):
    """
    Разблокировать пользователя.
    """
    async with get_db_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == telegram_id)
            .values(is_banned=False, ban_reason=None)
        )

async def broadcast_message(text: str) -> List[int]:
    """
    Отправка сообщения всем пользователям.
    
    :param text: Текст для рассылки
    :return: Список ID пользователей, которым было отправлено сообщение
    """
    sent_to = []
    async with get_db_session() as session:
        users = await session.execute(select(User))
        # Since actual message sending logic is not provided in the context of this database code snippet,
        # I will create a placeholder function `notify_user` that can be implemented for actual sending logic.
        async def notify_user(user_id: int, message_text: str) -> bool:
            # This function is a placeholder for where you would implement the actual message-sending logic.
            # It should return True if the message was sent successfully, False otherwise.
            # For now, we'll assume all sends succeed for demonstration purposes.
            return True

        # Send message to all users
        for user in users.scalars():
            if await notify_user(user.telegram_id, text):  # Potentially a real send function
                sent_to.append(user.telegram_id)
        for user in users.scalars():
            sent_to.append(user.telegram_id)
            
    return sent_to

async def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Получить последние логи действий пользователей
    
    :param limit: Количество записей
    :return: Список последних действий
    """
    logs = []
    async with get_db_session() as session:
        # Получаем последние изменения сообщений
        edit_history = await session.execute(
            select(MessageEditHistory)
            .order_by(MessageEditHistory.date.desc())
            .limit(limit)
        )
        
        for entry in edit_history.scalars():
            logs.append({
                'type': 'edit',
                'user_id': entry.user_telegram_id,
                'message_id': entry.message_id,
                'date': entry.date
            })
            
    return logs[:limit]
