from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


start_connection_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Профиль")
        ],
        [
            KeyboardButton(text="💳 Купить подписку")
        ]
    ],
    resize_keyboard=True
)

profile_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
        ]
    ]
)

def get_show_history_message_keyboard(message_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Показать историю", callback_data=f"show_history_{message_id}")
            ]
        ]
    )

def get_payment_keyboard(payment_url: str, invoice_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Оплатить", url=payment_url)
            ],
            [
                InlineKeyboardButton(text="🔍 Проверить оплату", callback_data=f"check_payment_{invoice_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Закрыть", callback_data=f"delete_invoice_{invoice_id}")
            ]
        ]

    )

close_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
        ]
    ]
)
