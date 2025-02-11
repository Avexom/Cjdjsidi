
from flask import Flask, render_template, jsonify
from bot.database.database import get_cached_statistics, get_all_users, get_user_message_stats, get_user_stats
import asyncio

app = Flask(__name__)

@app.route('/')
def index():
    stats = asyncio.run(get_cached_statistics())
    users = asyncio.run(get_all_users())
    return render_template('index.html', stats=stats, users=users)

@app.route('/user/<int:user_id>')
def user_stats(user_id):
    user_stats = asyncio.run(get_user_stats(user_id))
    message_stats = asyncio.run(get_user_message_stats(user_id))
    return jsonify({
        'stats': user_stats,
        'messages': message_stats
    })

def run_webview():
    app.run(host='0.0.0.0', port=3000)
