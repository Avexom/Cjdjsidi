from datetime import datetime
from string import Template

class Texts:
    START_NOT_CONNECTED = "👋 <b>Добро пожаловать!</b> Чтобы начать пользоваться ботом, подключите его к своему аккаунту."
    START_CONNECTED = "🎉 <b>Вы успешно подключили бота!</b> Выберите действие из меню ниже."
    CONNECTION_ENABLED = "✅ <b>Бизнес-бот активирован!</b>"
    CONNECTION_DISABLED = "❌ <b>Бизнес-бот деактивирован.</b>"
    SUBSCRIPTION_ENDED = "⏰ <b>Ваша подписка истекла, бот отключен.</b>"
    subscription_buy_already_active = "🔔 У вас уже есть активная подписка!"
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

def subscription_buy_text(price: str) -> str:
    """
    Возвращает текст для покупки подписки.
    """
    return f"""
💰 Стоимость подписки: <b>{price}$</b>

Нажмите кнопку "<b>Оплатить</b>" ниже, чтобы перейти к оплате.

После оплаты, нажмите кнопку "<b>Проверить оплату</b>" ниже, чтобы подтвердить оплату.
"""

profile_template = Template("""
👤 <b>Профиль пользователя:</b> $name

🆔 <b>ID:</b> $user_id

📅 <b>Подписка до:</b> $subscription_status

📊 <b>Статистика:</b>
- Отслеживаемых сообщений: $count_messages
- Перехвачено удаленных сообщений: $count_messages_deleted
- Перехвачено редактированных сообщений: $count_messages_edited
""")

def profile_text(
    user_id: int,
    name: str,
    subscription_end_date: datetime | None,
    count_messages: int,
    count_messages_deleted: int,
    count_messages_edited: int,
) -> str:
    """
    Возвращает текст профиля пользователя.
    """
    subscription_status = (
        subscription_end_date.strftime('%d.%m.%Y') if subscription_end_date else "Не активна"
    )
    return profile_template.substitute(
        name=name,
        user_id=user_id,
        subscription_status=subscription_status,
        count_messages=count_messages,
        count_messages_deleted=count_messages_deleted,
        count_messages_edited=count_messages_edited,
    )

def generate_user_link(name: str, user_id: int, username: str | None) -> str:
    """
    Генерирует ссылку на пользователя.

    :param name: Имя пользователя для отображения.
    :param user_id: ID пользователя в Telegram.
    :param username: Юзернейм пользователя (если есть).
    :return: Строка с HTML-ссылкой на пользователя.
    """
    url = f'tg://openmessage?user_id={user_id}' if username is None else f'https://t.me/{username}'
    return f'<a href="{url}">{name}</a>'

def new_message_text(name: str, user_id: int, username: str | None) -> str:
    """
    Возвращает текст для нового сообщения.
    """
    user_link = generate_user_link(name, user_id, username)
    return f"Сообщение от пользователя {user_link}"

def new_message_text_2(name: str, user_id: int, username: str | None) -> str:
    """
    Возвращает альтернативный текст для нового сообщения.
    """
    user_link = generate_user_link(name, user_id, username)
    return f"👇 Сообщение для пользователя {user_link} 👇"

def deleted_message_text(name: str, user_id: int, username: str | None) -> str:
    """
    Возвращает текст для удаленного сообщения.
    """
    user_link = generate_user_link(name, user_id, username)
    return f"Пользователь {user_link} удалил сообщение"

def edited_message_text(name: str, user_id: int, username: str | None) -> str:
    """
    Возвращает текст для измененного сообщения.
    """
    user_link = generate_user_link(name, user_id, username)
    return f"Пользователь {user_link} изменил сообщение"

def generate_message_text(name: str, user_id: int, username: str | None, action: str) -> str:
    """
    Генерирует текст для нового, измененного или удаленного сообщения.
    
    :param name: Имя пользователя.
    :param user_id: ID пользователя.
    :param username: Юзернейм пользователя (опционально).
    :param action: Тип действия ("new", "edited", "deleted").
    :return: Сгенерированный текст.
    """
    user_link = generate_user_link(name, user_id, username)
    if action == "new":
        return f"Сообщение от пользователя {user_link}"
    elif action == "new_alt":
        return f"👇 Сообщение для пользователя {user_link} 👇"
    elif action == "edited":
        return f"Пользователь {user_link} изменил сообщение"
    elif action == "deleted":
        return f"Пользователь {user_link} удалил сообщение"
    else:
        raise ValueError("Неподдерживаемый тип действия")