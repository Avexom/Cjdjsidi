
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
    message_stats = asyncio.run(get_user_message_stats(user_id))
    return render_template('user_stats.html', 
        user=user,
        stats=stats,
        message_history=message_stats
    )

def run_webview():
    app.run(host='0.0.0.0', port=3000, debug=False)
