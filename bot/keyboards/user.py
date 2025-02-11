from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

start_connection_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="💳 Купить подписку")],
        [KeyboardButton(text="⚙️ Функции"), KeyboardButton(text="📱 Модули")],
        [KeyboardButton(text="💬 Поддержка"), KeyboardButton(text="📝 Отзывы")]
    ],
    resize_keyboard=True
)

def get_modules_keyboard(user_settings: dict) -> InlineKeyboardMarkup:
    all_enabled = all(user_settings.values())
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎮 Все модули {'✅' if all_enabled else '❌'}", 
                    callback_data="toggle_all_modules"
                )
            ],
            [InlineKeyboardButton(text=f"❤️ PinHeart {'✅' if user_settings['module_pinheart'] else '❌'}", callback_data="toggle_pinheart")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
        ]
    )

def get_functions_keyboard(user_settings: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔔 {'✅' if user_settings['notifications_enabled'] else '❌'}", 
                                callback_data="toggle_all"),
                InlineKeyboardButton(text=f"📝 {'✅' if user_settings['edit_notifications'] else '❌'}", 
                                callback_data="toggle_edit"),
                InlineKeyboardButton(text=f"🗑 {'✅' if user_settings['delete_notifications'] else '❌'}", 
                                callback_data="toggle_delete")
            ],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
        ]
    )

profile_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]
)

def get_show_history_message_keyboard(message_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Показать историю", callback_data=f"show_history_{message_id}")]
        ]
    )

def get_payment_keyboard(payment_url: str, invoice_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton(text="🔍 Проверить оплату", callback_data=f"check_payment_{invoice_id}")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"delete_invoice_{invoice_id}")]
        ]
    )

close_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]
)

admin_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📝 Логи", callback_data="admin_logs")
        ],
        [
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="💰 Цена подписки", callback_data="admin_price")
        ],
        [
            InlineKeyboardButton(text="🎁 Выдать подписку", callback_data="admin_give_sub"),
            InlineKeyboardButton(text="🚫 Бан", callback_data="admin_ban")
        ],
        [
            InlineKeyboardButton(text="✅ Разбан", callback_data="admin_unban"),
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
        ]
    ]
)

def get_ban_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_ban_{user_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="close")
            ]
        ]
    )

def get_unban_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_unban_{user_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="close")
            ]
        ]
    )

settings_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔔 Настройки уведомлений", callback_data="notifications_settings")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]
)

notifications_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Все уведомления", callback_data="toggle_notification_notifications")],
        [InlineKeyboardButton(text="📨 Новые сообщения", callback_data="toggle_notification_message")],
        [InlineKeyboardButton(text="📝 Редактирование", callback_data="toggle_notification_edit")],
        [InlineKeyboardButton(text="🗑 Удаление", callback_data="toggle_notification_delete")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_settings")],
    ]
)