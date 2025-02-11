from datetime import datetime
from string import Template
from config import HISTORY_GROUP_ID

class Texts:
    START_NOT_CONNECTED = "👋 Привет! Я буду следить за сообщениями в чатах."
    START_CONNECTED = "✅ Бот уже подключен и готов к работе!"
    START_CONNECTED_NEW = "✅ Бот подключен и готов к работе!"
    SUBSCRIPTION_BUY_ALREADY_ACTIVE = "У вас уже есть активная подписка!"
    CONNECTION_ENABLED = "✅ <b>Бизнес-бот активирован!</b>"
    CONNECTION_DISABLED = "❌ <b>Бизнес-бот деактивирован.</b>"
    SUBSCRIPTION_ENDED = "⏰ <b>Ваша подписка истекла, бот отключен.</b>"
    SUBSCRIPTION_BUY_FAILED = "❌ <b>Оплата не найдена.</b>"
    SUBSCRIPTION_BUY_SUCCESS = "✅ Оплата прошла успешно!"
    SUBSCRIPTION_BUY_SUCCESS_TEXT = "🎉 <b>Оплата прошла успешно!</b> Подписка активирована на 30 дней."

    ABOUT_BOT = """
    🔥 <b>Ебать, ты попал куда надо!</b>

    <b>Этот бот - твой личный шпион в Telegram! Не проебешь ни одного сообщения, даже если его удалят или отредактируют. 
    Идеально подходит для тех, кто хочет быть в курсе всего и контролировать каждое движение! 🕵️‍♂️</b>

    <b>Что умеет эта охуенная штука:</b>
    🚀 Палит все измененные сообщения
    💣 Сохраняет удаленные сообщения
    📊 Выдает сочную статистику активности
    🎮 Простое управление через удобное меню

    <b>Фишки и плюшки:</b>
    ⚡️ Работает 24/7 без перерывов
    🔒 Полная конфиденциальность 
    🎯 Мгновенные уведомления
    🌟 Регулярные обновления

    <b>Хватит думать - жми на кнопку и погнали! 🚀</b>
    """

    @staticmethod
    def subscription_buy_text(price: str) -> str:
        return f"💳 Стоимость подписки: {price} RUB"

    profile_template = Template("""
👾 <b>Профиль пользователя:</b> $first_name
━━━━━━━━━━━━━━━
🪪 <b>ID:</b> $user_id

⏳ <b>Подписка до:</b> $subscription_status

📈 <b>Статистика активности:</b>
📨 Отслеживаемых сообщений: $count_messages
🗑 Перехвачено удаленных: $count_messages_deleted
✏️ Изменённых сообщений: $count_messages_edited

💫 Спасибо что выбрали нас! 
━━━━━━━━━━━━━━━
""")

    SUPPORT_TEXT = """
✨ Присоединяйтесь к нашему комьюнити!
• Задавайте вопросы
• Делитесь впечатлениями 
• Предлагайте новые функции
• Общайтесь с другими пользователями
"""

    REVIEWS_TEXT = """
💫 Почему нам доверяют:
• Мгновенная поддержка 24/7
• Регулярные обновления
• Учитываем пожелания пользователей
• Защита ваших данных
"""

    @staticmethod
    def profile_text(user_id: int, first_name: str, subscription_end_date: datetime | None,
                    count_messages: int, count_messages_deleted: int, count_messages_edited: int) -> str:
        subscription_status = (
            subscription_end_date.strftime('%d.%m.%Y') if subscription_end_date else "Не активна"
        )
        return Texts.profile_template.substitute(
            first_name=first_name,
            user_id=user_id,
            subscription_status=subscription_status,
            count_messages=count_messages,
            count_messages_deleted=count_messages_deleted,
            count_messages_edited=count_messages_edited,
        )

    @staticmethod
    def generate_user_link(name: str, user_id: int, username: str | None) -> str:
        url = f'tg://openmessage?user_id={user_id}' if username is None else f'https://t.me/{username}'
        return f'<a href="{url}">{name}</a>'

    @staticmethod
    def new_message_text(name: str, user_id: int, username: str | None) -> str:
        user_link = f'<a href="tg://user?id={user_id}">{name}</a>'
        return f"📨 Уведомление о сообщении\nОт: {user_link}"

    @staticmethod
    def new_message_text_2(name: str, user_id: int, username: str | None) -> str:
        user_link = f'<a href="tg://user?id={user_id}">{name}</a>'
        return f"📨 Новое сообщение\n👤 От: {user_link}"

    @staticmethod
    def deleted_message_text(name: str, user_id: int, username: str | None, deleted_text: str = "") -> str:
        user_link = f'<a href="tg://user?id={user_id}">{name}</a>'
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"""🗑 {user_link} удалил для тебя сообщение\n\nУдаленное сообщение:\n{deleted_text}\n\n⏰ Время удаления: {current_time}"""

    @staticmethod
    def edited_message_text(name: str, user_id: int, username: str | None) -> str:
        user_link = Texts.generate_user_link(name, user_id, username)
        return f"Пользователь {user_link} изменил сообщение"

    @staticmethod
    def generate_message_text(name: str, user_id: int, username: str | None, action: str) -> str:
        user_link = Texts.generate_user_link(name, user_id, username)
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

    CHAT_ID_1 = -1002491226301  # Первый чат
    CHAT_ID_2 = -1002336493942  # Второй чат