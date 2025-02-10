
import os
from typing import List

# Токены и API ключи (загружаем из Secrets)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CRYPTO_PAY_API_TOKEN = os.environ.get("CRYPTO_PAY_API_TOKEN")

# Админы и группы
ADMIN_IDS: List[int] = [8115432365]  # ID админов

# ID групп для хранения истории
MAIN_HISTORY_GROUP = -1002467764642  # Основная группа

BACKUP_HISTORY_GROUPS = [
    -1002353748102,  # Резервная группа 1
    -1002460477207,  # Резервная группа 2 
    -1002300596890,  # Резервная группа 3
    -1002498479494,  # Резервная группа 4
    -1002395727554,  # Резервная группа 5
    -1002321264660   # Резервная группа 6
]

# Для обратной совместимости
HISTORY_GROUP_IDS = [MAIN_HISTORY_GROUP] + BACKUP_HISTORY_GROUPS
