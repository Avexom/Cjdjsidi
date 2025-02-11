
from flask import Flask, render_template
from bot.database.database import get_cached_statistics
import asyncio

app = Flask(__name__)

@app.route('/')
def index():
    # Получаем статистику асинхронно
    stats = asyncio.run(get_cached_statistics())
    return render_template('index.html', stats=stats)

def run_webview():
    app.run(host='0.0.0.0', port=3000)
