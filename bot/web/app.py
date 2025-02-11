from flask import Flask, render_template, jsonify
from bot.database.database import (
    get_cached_statistics, get_all_users, 
    get_user_message_stats, get_user_stats,
    get_user
)
import asyncio
from datetime import datetime

import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Настройка логирования
handler = RotatingFileHandler('web_errors.log', maxBytes=10000, backupCount=1)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
handler.setLevel(logging.WARNING)
app.logger.addHandler(handler)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return "Упс! Произошла ошибка на сервере. Мы уже работаем над её исправлением.", 500

@app.route('/')
def index():
    stats = asyncio.run(get_cached_statistics())
    users = asyncio.run(get_all_users())
    return render_template('index.html', stats=stats, users=users, now=datetime.now())

@app.route('/user/<int:user_id>')
def user_details(user_id):
    try:
        user = asyncio.run(get_user(user_id))
        if not user:
            return "Пользователь не найден", 404

        stats = asyncio.run(get_user_stats(user_id))
        # Получаем все сообщения пользователя
        messages = asyncio.run(get_user_message_stats(user_id))
        users = asyncio.run(get_all_users())
        users_dict = {u.id: u for u in users}

        if not messages:
            messages = []

        # Группируем сообщения по чатам
        chats = {}
        chat_users = set()  # Множество для хранения уникальных пользователей в чатах
        users_dict = {u.id: u for u in asyncio.run(get_all_users())} # Assuming get_all_users returns a list of user objects with id attribute

    except Exception as e:
        app.logger.error(f"Ошибка при получении данных пользователя: {e}")
        return "Произошла ошибка при загрузке данных", 500
    for msg in messages:
        chat_id = msg.get('to_user_id') if msg.get('from_id') == user_id else msg.get('from_id')
        other_user = users_dict.get(chat_id)
        chats[chat_id] = {
            'other_user_id': chat_id,
            'other_user_name': other_user.first_name if other_user else (msg.get('from_name') or msg.get('to_name') or 'Пользователь'),
            'other_user_username': other_user.username if other_user else None,
            'other_user_photo': other_user.photo_url if other_user and hasattr(other_user, 'photo_url') else None,
            'messages': [],
            'last_activity': None
        }

        # Расширенная обработка текста сообщения
        # Расширенная обработка сообщений
        message_text = msg.get('text', '').strip() if msg.get('text') else ''
        message_type = msg.get('media_type', 'text')
        
        # Обработка разных типов сообщений
        if message_type != 'text':
            media_types = {
                'photo': '📷 Фото',
                'video': '🎥 Видео',
                'voice': '🎤 Голосовое сообщение',
                'document': '📄 Документ',
                'sticker': '😊 Стикер',
                'animation': '�animation Анимация'
            }
            message_text = media_types.get(message_type, f'📎 {message_type.capitalize()}')
            if msg.get('caption'):
                message_text += f"\n{msg.get('caption')}"
        elif msg.get('content'):
            message_text = str(msg.get('content'))
        else:
            message_text = ''

        # Проверяем наличие текста в других полях, если основной текст пустой
        if not message_text:
            for field in ['message', 'raw_text', 'caption']:
                if msg.get(field):
                    message_text = str(msg.get(field)).strip()
                    break

        if not message_text:
            message_text = 'Сообщение без текста'

        chats[chat_id]['messages'].append({
            'text': message_text,
            'time': msg.get('time', datetime.now()),
            'from_id': msg.get('from_id'),
            'to_id': msg.get('to_user_id'),
            'media_type': msg.get('media_type')
        })

    # Сортируем сообщения в каждом чате по времени
    for chat in chats.values():
        chat['messages'].sort(key=lambda x: x['time'])

    return render_template('user_stats.html', 
        user=user,
        stats=stats,
        user_chats=list(chats.values())
    )

@app.route('/webapp')
def webapp():
    return render_template('webapp.html')

@app.route('/api/modules')
def get_modules():
    # Пример модулей, в реальности брать из базы данных
    modules = [
        {"id": "calc", "name": "Калькулятор", "description": "Математические вычисления", "enabled": True},
        {"id": "stats", "name": "Статистика", "description": "Анализ данных", "enabled": False}
    ]
    return jsonify(modules)

@app.route('/api/modules/toggle', methods=['POST'])
def toggle_module():
    data = request.json
    # Здесь логика включения/выключения модуля в базе данных
    return jsonify({"success": True})

def run_webview():
    app.run(host='0.0.0.0', port=3000, debug=False)