from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import logging
import asyncio

from aiogram import Bot
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import (
    ForeignKey, Column, Integer, String, BigInteger, Boolean, Date, DateTime,
    func, select, update, delete, insert, and_, text, or_
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
    subscription_end_date = Column(DateTime, nullable=True)
    active_messages_count = Column(Integer, nullable=False, default=0)
    edited_messages_count = Column(Integer, nullable=False, default=0)
    deleted_messages_count = Column(Integer, nullable=False, default=0)
    channel_index = Column(Integer, nullable=False, default=0)
    is_banned = Column(Boolean, nullable=False, default=False)
    ban_reason = Column(String, nullable=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    notifications_enabled = Column(Boolean, default=True)
    message_notifications = Column(Boolean, default=True)
    edit_notifications = Column(Boolean, default=True)
    delete_notifications = Column(Boolean, default=True)
    last_message_time = Column(DateTime, default=datetime.now)
    calc_enabled = Column(Boolean, default=False)
    love_enabled = Column(Boolean, default=False)
    online_enabled = Column(Boolean, default=True)  # Changed default to True
    last_farm_time = Column(DateTime, default=datetime.now)
    module_calc_enabled = Column(Boolean, default=False) #Added
    module_love_enabled = Column(Boolean, default=False) #Added
    pinheart_enabled = Column(Boolean, default=False) #Added
    pinheart_count = Column(Integer, default=1) #Added

    __table_args__ = {'extend_existing': True}


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
            logger.error(f"🔴 Ошибка базы данных: {str(e)}")
            await asyncio.sleep(1)  # Пауза перед повторной попыткой
            try:
                await session.commit()
            except Exception as retry_error:
                logger.critical(f"❌ Критическая ошибка БД: {str(retry_error)}")
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
async def create_user(telegram_id: int, username: str = None, first_name: str = None, business_bot_active: bool = False) -> User:
    try:
        async with get_db_session() as session:
            # Проверяем, не существует ли уже пользователь
            existing_user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if existing_user:
                return existing_user

            result = await session.execute(select(func.count(User.id)))
            count = result.scalar() or 0
            next_index = count % 3

            user = User(
                telegram_id=telegram_id,
                username=username,
                business_bot_active=business_bot_active,
                channel_index=next_index,
                created_at=datetime.now(),
                online_enabled=True # Модуль онлайн включен по умолчанию
            )
            session.add(user)
            await session.commit()
            return user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        raise

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
    Удаляет истекшие подписки и отправляет уведомления пользователям.
    """
    async with get_db_session() as session:
        try:
            # Находим пользователей с истекающими подписками
            expired_users = await session.execute(
                select(User).where(User.subscription_end_date < datetime.now())
            )

            for user in expired_users.scalars():
                # Сбрасываем настройки пользователя
                await session.execute(
                    update(User)
                    .where(User.telegram_id == user.telegram_id)
                    .values(
                        subscription_end_date=None,
                        business_bot_active=False
                    )
                )

            # Удаляем истекшие подписки
            await session.execute(
                delete(Subscription).where(Subscription.end_date < datetime.now().date())
            )
            await session.commit()
            logger.info("Expired subscriptions processed successfully.")
        except Exception as e:
            logger.error(f"Error processing expired subscriptions: {e}")
            await session.rollback()
            raise

# Увеличение счетчиков сообщений
async def increase_active_messages_count(user_telegram_id: int):
    """
    Увеличить счетчик активных сообщений пользователя.

    :param user_telegram_id: ID пользователя в Telegram.
    """
    async with get_db_session() as session:
        try:
            await session.execute(
                update(User)
                .where(User.telegram_id == user_telegram_id)
                .values(
                    active_messages_count=User.active_messages_count + 1,
                    last_message_time=datetime.now()
                )
            )
            await session.commit()
            logger.info(f"✅ Увеличен счетчик активных сообщений для пользователя {user_telegram_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении счетчика активных сообщений: {e}")
            await session.rollback()
            raise

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
        try:
            # Проверяем существование пользователя
            user = await session.scalar(select(User).where(User.telegram_id == user_telegram_id))
            if not user:
                logger.error(f"❌ Пользователь {user_telegram_id} не найден")
                return

            # Увеличиваем счетчик
            await session.execute(
                update(User)
                .where(User.telegram_id == user_telegram_id)
                .values(
                    deleted_messages_count=User.deleted_messages_count + 1,
                    last_message_time=datetime.now()
                )
            )
            await session.commit()

            # Проверяем обновленное значение
            updated_user = await session.scalar(select(User).where(User.telegram_id == user_telegram_id))
            logger.info(f"✅ Счетчик удаленных сообщений обновлен для пользователя {user_telegram_id}. Новое значение: {updated_user.deleted_messages_count}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении счетчика удаленных сообщений: {e}")
            await session.rollback()
            raise


# Статистика
@alru_cache(maxsize=1, ttl=60)  # Кэш на 60 секунд
async def get_total_users() -> int:
    """
    Получить общее количество уникальных пользователей.

    :return: Количество пользователей.
    """
    async with get_db_session() as session:
        result = await session.execute(
            select(func.count(User.telegram_id))
            .select_from(User)
            .where(User.is_banned == False)
        )
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

@alru_cache(maxsize=1, ttl=60)  # Кэш на 60 секунд
async def get_total_messages() -> int:
    """
    Получить общее количество сообщений из всех каналов.

    :return: Количество сообщений.
    """
    async with get_db_session() as session:
        try:
            result = await session.execute(
                select(
                    func.sum(User.active_messages_count),
                    func.sum(User.edited_messages_count),
                    func.sum(User.deleted_messages_count)
                )
                .select_from(User)
                .where(User.is_banned == False)
            )
            active, edited, deleted = result.first()
            total = (active or 0) + (edited or 0) + (deleted or 0)
            logger.info(f"Статистика сообщений: активные={active}, отред.={edited}, удал.={deleted}")
            return total
        except Exception as e:
            logger.error(f"Ошибка при подсчете сообщений: {e}")
            return 0

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
        result = await session.execute(
            select(func.count(User.id))
            .where(and_(
                User.business_bot_active == True,
                User.subscription_end_date > datetime.now(),
                User.is_banned == False
            ))
        )
        count = result.scalar() or 0
        logger.info(f"Пользователей с активным бизнес-ботом: {count}")
        return count

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
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [col[1] for col in result.fetchall()]

        if 'calc_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN calc_enabled BOOLEAN DEFAULT FALSE"))
            logger.info("Added calc_enabled column to users table")

        if 'love_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN love_enabled BOOLEAN DEFAULT FALSE"))
            logger.info("Added love_enabled column to users table")

        if 'channel_index' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN channel_index INTEGER DEFAULT 0"))
            logger.info("Added channel_index column to users table")

        if 'is_banned' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE"))
            logger.info("Added is_banned column to users table")

        if 'ban_reason' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN ban_reason TEXT"))
            logger.info("Added ban_reason column to users table")

        if 'username' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN username TEXT"))
            logger.info("Added username column to users table")

        if 'first_name' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN first_name TEXT"))
            logger.info("Added first_name column to users table")

        if 'subscription_end_date' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP"))
            logger.info("Added subscription_end_date column to users table")

        if 'created_at' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP"))
            logger.info("Added created_at column to users table")

        if 'notifications_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT TRUE"))
            logger.info("Added notifications_enabled column to users table")

        if 'message_notifications' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN message_notifications BOOLEAN DEFAULT TRUE"))
            logger.info("Added message_notifications column to users table")

        if 'edit_notifications' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN edit_notifications BOOLEAN DEFAULT TRUE"))
            logger.info("Added edit_notifications column to users table")

        if 'delete_notifications' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN delete_notifications BOOLEAN DEFAULT TRUE"))
            logger.info("Added delete_notifications column to users table")

        if 'last_message_time' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN last_message_time TIMESTAMP"))
            await conn.execute(text("UPDATE users SET last_message_time = CURRENT_TIMESTAMP"))
            logger.info("Added last_message_time column to users table")

        if 'last_farm_time' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN last_farm_time TIMESTAMP"))
            await conn.execute(text("UPDATE users SET last_farm_time = CURRENT_TIMESTAMP"))
            logger.info("Added last_farm_time column to users table")

        if 'online_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN online_enabled BOOLEAN DEFAULT FALSE"))
            logger.info("Added online_enabled column to users table")

        if 'module_calc_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN module_calc_enabled BOOLEAN DEFAULT FALSE"))
            logger.info("Added module_calc_enabled column to users table")

        if 'module_love_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN module_love_enabled BOOLEAN DEFAULT FALSE"))
            logger.info("Added module_love_enabled column to users table")

        if 'pinheart_enabled' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN pinheart_enabled BOOLEAN DEFAULT FALSE"))
            logger.info("Added pinheart_enabled column to users table")

        if 'pinheart_count' not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN pinheart_count INTEGER DEFAULT 1"))
            logger.info("Added pinheart_count column to users table")


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

async def get_user_by_username(username: str) -> Optional[User]:
    """
    Получить пользователя по его username или ID.

    :param username: Username пользователя или ID
    :return: Объект User или None, если пользователь не найден
    """
    async with get_db_session() as session:
        try:
            # Проверяем, является ли username числом (ID)
            user_id = int(username)
            return await session.scalar(
                select(User).where(User.telegram_id == user_id)
            )
        except ValueError:
            # Если не число, ищем по username
            username = username.replace('@', '')  # Убираем @ если есть
            return await session.scalar(
                select(User).where(User.username == username)
            )
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

async def ban_user(telegram_id: int, reason: str = "Не указана") -> bool:
    """
    Заблокировать пользователя.

    :param telegram_id: ID пользователя
    :param reason: Причина блокировки
    :return: True если блокировка успешна, False если пользователь не найден
    """
    async with get_db_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return False

        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                is_banned=True,
                ban_reason=reason,
                ban_date=datetime.now()
            )
        )
        return True

async def unban_user(telegram_id: int) -> bool:
    """
    Разблокировать пользователя.

    :param telegram_id: ID пользователя
    :return: True если разблокировка успешна, False если пользователь не найден
    """
    async with get_db_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return False

        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                is_banned=False,
                ban_reason=None,
                ban_date=None
            )
        )
        return True

async def broadcast_message(text: str) -> List[int]:
    """
    Отправка сообщения всем пользователям.

    :param text: Текст для рассылки
    :return: Список ID пользователей, которым было отправлено сообщение
    """
    sent_to = []
    failed = []
    async with get_db_session() as session:
        try:
            users = await session.execute(select(User).where(User.is_banned == False))
            for user in users.scalars():
                try:
                    # В реальном коде здесь будет отправка сообщения через бота
                    sent_to.append(user.telegram_id)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения пользователю {user.telegram_id}: {e}")
                    failed.append(user.telegram_id)

            logger.info(f"Рассылка завершена. Отправлено: {len(sent_to)}, Ошибок: {len(failed)}")
            return sent_to
        except Exception as e:
            logger.error(f"Ошибка при рассылке сообщений: {e}")
            raise

async def get_all_users() -> List[User]:
    """
    Получить список всех пользователей.

    :return: Список всех пользователей
    """
    async with get_db_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()

async def update_all_modules(telegram_id: int, state: bool):
    """Обновление состояния всех модулей"""
    async with get_db_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                module_calc_enabled=state,
                module_love_enabled=state
            )
        )
        await session.commit()

async def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Получить последние логи действий пользователей

    :param limit: Количество записей
    :return: Список последних действий
    """
    logs = []

    return logs[:limit]

async def update_user_pinheart(telegram_id: int, enabled: bool, count: int = 1):
    """Обновление статуса PinHeart"""
    async with get_db_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                pinheart_enabled=enabled,
                pinheart_count=count
            )
        )
        await session.commit()

async def get_top_users(limit: int = 10) -> List[Dict[str, Any]]:
    """Получение топа пользователей по разным параметрам"""
    async with get_db_session() as session:
        result = await session.execute(
            select(User)
            .filter(User.active_messages_count > 0)
            .order_by(User.active_messages_count.desc())
            .limit(limit)
        )
        users = result.scalars().all()
        return [
            {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name if hasattr(user, 'first_name') else None,
                "last_name": user.last_name if hasattr(user, 'last_name') else None,
                "messages": user.active_messages_count,
                "edited": user.edited_messages_count,
                "deleted": user.deleted_messages_count
            }
            for user in users
        ]

async def get_user_stats(telegram_id: int) -> Dict[str, Any]:
    """Получение статистики пользователя"""
    async with get_db_session() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        return {
            "sent_messages": user.active_messages_count,
            "edited_messages": user.edited_messages_count,
            "deleted_messages": user.deleted_messages_count,
            "registration_date": user.created_at.strftime("%d.%m.%Y") if user.created_at else None
        }

async def toggle_notification(telegram_id: int, notification_type: str) -> bool:
    """Переключение состояния уведомлений"""
    async with get_db_session() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )

        # Маппинг типов уведомлений на поля базы данных
        notification_fields = {
            "all": "notifications_enabled",
            "message": "message_notifications",
            "edit": "edit_notifications",
            "delete": "delete_notifications"
        }

        field = notification_fields.get(notification_type)
        if not field:
            logger.error(f"Неизвестный тип уведомления: {notification_type}")
            return False

        current_settings = getattr(user, field, False)
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(**{field: not current_settings})
        )
        await session.commit()
        return not current_settings

async def toggle_module(telegram_id: int, module_type: str) -> bool:
    """Переключение состояния модуля"""
    async with get_db_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return False

        if module_type == "calc":
            user.module_calc_enabled = not user.module_calcenabled
            new_state = user.module_calc_enabled
        elif module_type == "love":
            user.module_love_enabled = not user.module_love_enabled
            new_state = user.module_love_enabled

        await session.commit()
        return new_state

async def update_all_modules(telegram_id: int, state: bool) -> bool:
    """Установка состояния для всех модулей"""
    async with get_db_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return False

        user.module_calc_enabled = state
        user.module_love_enabled = state
        await session.commit()
        return True

async def update_last_message_time(user_telegram_id: int):
    """Обновляет время последнего сообщения пользователя"""
    async with get_db_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == user_telegram_id)
            .values(last_message_time=datetime.now())
        )

async def check_inactive_chats(bot: Bot):
    """Проверяет неактивные чаты и отправляет уведомления"""
    async with get_db_session() as session:
        users = await session.execute(
            select(User)
            .where(User.business_bot_active == True)
            .where(User.last_message_time < datetime.now() - timedelta(hours=24))
        )
        for user in users.scalars():
            try:
                await bot.send_message(
                    user.telegram_id,
                    "⚠️ Напоминание: В вашем чате нет активности более 24 часов!"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")

async def cleanup_database():
    """Нахуярить чистку всей хуйни из базы данных"""
    async with get_db_session() as session:
        try:
            # Сначала удаляем все подписки, потому что они зависят от юзеров
            await session.execute(delete(Subscription))

            # Потом удаляем всех пользователей
            await session.execute(delete(User))

            await session.commit()
            logger.info("🧹 База данных успешно очищена")
            return True
        except Exception as e:
            logger.error(f"🔴 Ошибка при очистке базы данных: {str(e)}")
            return False