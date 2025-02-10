
import os
from typing import List

# ID групп для хранения истории сообщений
HISTORY_GROUP_IDS = [
    -1002467764642,  # Основная группа
    -1002353748102,  # Резервная группа 1
    -1002460477207,  # Резервная группа 2 
    -1002300596890,  # Резервная группа 3
    -1002498479494,  # Резервная группа 4
    -1002395727554,  # Резервная группа 5
    -1002321264660   # Резервная группа 6
]

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
