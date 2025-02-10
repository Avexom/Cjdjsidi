
import os
from typing import List

# Загружаем токены из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ Блять, укажи BOT_TOKEN в переменных окружения!")

CRYPTO_PAY_API_TOKEN = os.getenv("CRYPTO_PAY_API_TOKEN")
if not CRYPTO_PAY_API_TOKEN:
    raise ValueError("❌ Сука, где CRYPTO_PAY_API_TOKEN?!")

# Админские ID из строки с разделителями в список
ADMIN_IDS: List[int] = [
    int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",")
    if id_.strip().isdigit()
]
if not ADMIN_IDS:
    raise ValueError("❌ Ебать, добавь хотя бы одного админа!")

# ID группы для истории из env
HISTORY_GROUP_ID = int(os.getenv("HISTORY_GROUP_ID", "0"))
if HISTORY_GROUP_ID == 0:
    raise ValueError("❌ Пиздец, укажи HISTORY_GROUP_ID!")
