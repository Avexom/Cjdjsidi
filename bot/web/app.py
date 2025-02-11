
from flask import Flask, render_template, jsonify
from bot.database.database import (
    get_cached_statistics, get_all_users, 
    get_user_message_stats, get_user_stats,
    get_user
)
import asyncio
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    stats = asyncio.run(get_cached_statistics())
    users = asyncio.run(get_all_users())
    return render_template('index.html', stats=stats, users=users, now=datetime.now())

@app.route('/user/<int:user_id>')
def user_details(user_id):
    user = asyncio.run(get_user(user_id))
    stats = asyncio.run(get_user_stats(user_id))
    
    # Получаем историю сообщений пользователя
    messages = asyncio.run(get_user_message_history(user_id))
    
    # Группируем сообщения по чатам
    chats = {}
    for msg in messages:
        chat_id = msg['chat_id']
        if chat_id not in chats:
            chats[chat_id] = {
                'other_user_name': msg['other_user_name'],
                'messages': []
            }
        chats[chat_id]['messages'].append(msg)
    
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
