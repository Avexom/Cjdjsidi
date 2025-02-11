
import logging
from datetime import datetime
from pathlib import Path

# Настраиваем логгер для веб-диалогов
web_logger = logging.getLogger('web_dialogues')
web_logger.setLevel(logging.INFO)

# Создаем форматтер для веб-логов
formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Создаем файловый обработчик
web_log_file = Path('web_dialogues.log')
file_handler = logging.FileHandler(web_log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
web_logger.addHandler(file_handler)

def log_dialogue(sender_id, sender_name, receiver_id, receiver_name, message_text):
    """
    Логирование диалога между пользователями
    
    Args:
        sender_id (int): ID отправителя
        sender_name (str): Имя отправителя
        receiver_id (int): ID получателя
        receiver_name (str): Имя получателя
        message_text (str): Текст сообщения
    """
    log_entry = (
        f"💬 ДИАЛОГ\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📤 Отправитель: {sender_name} (ID: {sender_id})\n"
        f"📥 Получатель: {receiver_name} (ID: {receiver_id})\n"
        f"📝 Сообщение: {message_text}\n"
        f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━"
    )
    web_logger.info(log_entry)
