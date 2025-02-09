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
    Создать нового пользователя.

    :param telegram_id: ID пользователя в Telegram.
    :param business_bot_active: Активен ли бизнес-бот.
    :return: Созданный пользователь.
    """
    async with get_db_session() as session:
        user = User(telegram_id=telegram_id, business_bot_active=business_bot_active)
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

# Запуск инициализации базы данных
async def main():
    await init_db()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())