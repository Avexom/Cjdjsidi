
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
        messages = asyncio.run(get_user_message_stats(user_id))
        
        if not messages:
            messages = []
            
        # Группируем сообщения по чатам
        chats = {}
        
    except Exception as e:
        app.logger.error(f"Ошибка при получении данных пользователя: {e}")
        return "Произошла ошибка при загрузке данных", 500
    for msg in messages:
        chat_id = msg.get('to_user_id') if msg.get('from_id') == user_id else msg.get('from_id')
        if chat_id not in chats:
            chats[chat_id] = {
                'other_user_name': msg.get('from_name') or msg.get('to_name') or 'Пользователь',
                'messages': []
            }
        
        # Улучшенная обработка текста сообщения
        message_text = msg.get('text', '')
        if not message_text and msg.get('media_type'):
            message_text = f"[{msg.get('media_type', 'Файл')}]"
            
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

def run_webview():
    app.run(host='0.0.0.0', port=3000, debug=False)
