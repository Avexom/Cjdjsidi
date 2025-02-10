from datetime import datetime
from string import Template

class Texts:
    START_NOT_CONNECTED = "👋 <b>Добро пожаловать!</b> Чтобы начать пользоваться ботом, подключите его к своему аккаунту."
    START_CONNECTED = "🎉 <b>С возвращением!</b> Выберите действие из меню ниже."
    CONNECTION_ENABLED = "✅ <b>Бизнес-бот активирован!</b>"
    CONNECTION_DISABLED = "❌ <b>Бизнес-бот деактивирован.</b>"
    SUBSCRIPTION_ENDED = "⏰ <b>Ваша подписка истекла, бот отключен.</b>"
    SUBSCRIPTION_BUY_ALREADY_ACTIVE = "🔔 У вас уже есть активная подписка!"
    SUBSCRIPTION_BUY_FAILED = "❌ <b>Оплата не найдена.</b>"
    SUBSCRIPTION_BUY_SUCCESS = "✅ Оплата прошла успешно!"
    SUBSCRIPTION_BUY_SUCCESS_TEXT = "🎉 <b>Оплата прошла успешно!</b> Подписка активирована на 30 дней."

    ABOUT_BOT = """
    👋 <b>Добро пожаловать!</b>

    <b>Этот бот предназначен для управления бизнес-процессами и улучшения взаимодействия с клиентами. 
    Он позволяет отслеживать изменения сообщений, удаленные сообщения и предоставляет статистику по активности.</b>

    <b>Основные функции:</b>
    - Отслеживание изменений сообщений
    - Уведомления о удаленных сообщениях
    - Подробная статистика активности
    - Удобное управление подписками

    <b>Подключите бота к вашему аккаунту и начните использовать все его возможности!</b>
    """

    @staticmethod
    def subscription_buy_text(price: str) -> str:
        return f"""
💰 Стоимость подписки: <b>{price}$</b>

Нажмите кнопку "<b>Оплатить</b>" ниже, чтобы перейти к оплате.

После оплаты, нажмите кнопку "<b>Проверить оплату</b>" ниже, чтобы подтвердить оплату.
"""

    @staticmethod
    def profile_text(
        user_id: int,
        name: str,
        subscription_end_date: datetime | None,
        count_messages: int,
        count_messages_deleted: int,
        count_messages_edited: int,
    ) -> str:
        subscription_status = (
            subscription_end_date.strftime('%d.%m.%Y') if subscription_end_date else "Не активна"
        )
        return Template("""
👤 <b>Профиль пользователя:</b> $name

🆔 <b>ID:</b> $user_id

📅 <b>Подписка до:</b> $subscription_status

📊 <b>Статистика:</b>
- Отслеживаемых сообщений: $count_messages
- Перехвачено удаленных сообщений: $count_messages_deleted
- Перехвачено редактированных сообщений: $count_messages_edited
""").substitute(
            name=name,
            user_id=user_id,
            subscription_status=subscription_status,
            count_messages=count_messages,
            count_messages_deleted=count_messages_deleted,
            count_messages_edited=count_messages_edited,
        )

    @staticmethod
    def get_current_time() -> str:
        """Возвращает текущее время в формате HH:MM:SS"""
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def generate_user_link(name: str, user_id: int, username: str | None) -> str:
        """Генерирует HTML-ссылку на пользователя"""
        name = name.replace("<", "&lt;").replace(">", "&gt;")  # Экранируем HTML
        url = f'tg://openmessage?user_id={user_id}' if not username else f'https://t.me/{username}'
        return f'<a href="{url}">{name}</a>'

    @staticmethod
    def new_message_text(name: str, user_id: int, username: str | None) -> str:
        user_link = Texts.generate_user_link(name, user_id, username)
        return f"📨 Уведомление о сообщении\nОт: {user_link}"

    @staticmethod
    def new_message_text_2(name: str, user_id: int, username: str | None) -> str:
        user_link = Texts.generate_user_link(name, user_id, username)
        return f"👇 Сообщение для пользователя {user_link} 👇"

    @staticmethod
    def deleted_message_text(name: str, user_id: int, username: str | None, deleted_text: str = "") -> str:
        user_link = Texts.generate_user_link(name, user_id, username)
        current_time = Texts.get_current_time()
        return f"""🗑 {user_link} удалил для тебя сообщение

Удаленное сообщение:
{deleted_text}

⏰ Время удаления: {current_time}"""

    @staticmethod
    def edited_message_text(name: str, user_id: int, username: str | None) -> str:
        """Генерирует текст для отредактированного сообщения"""
        user_link = Texts.generate_user_link(name, user_id, username)
        current_time = Texts.get_current_time()
        return f"""✏️ {user_link} отредактировал сообщение
⏰ Время редактирования: {current_time}"""

    @staticmethod
    def generate_message_text(name: str, user_id: int, username: str | None, action: str) -> str:
        """Генерирует текст сообщения в зависимости от действия"""
        user_link = Texts.generate_user_link(name, user_id, username)

        message_types = {
            "new": f"Сообщение от пользователя {user_link}",
            "new_alt": f"👇 Сообщение для пользователя {user_link} 👇",
            "edited": f"Пользователь {user_link} изменил сообщение",
            "deleted": f"Пользователь {user_link} удалил сообщение"
        }

        if action not in message_types:
            raise ValueError(f"Неподдерживаемый тип действия: {action}")

        return message_types[action]