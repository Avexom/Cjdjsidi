
from flask import Flask, render_template_string
from pathlib import Path
import logging

app = Flask(__name__)

@app.route('/')
def index():
    # Читаем лог-файл
    log_file = Path('web_dialogues.log')
    if log_file.exists():
        logs = log_file.read_text(encoding='utf-8').split('\n')
    else:
        logs = ['Логи пока отсутствуют']
    
    # HTML шаблон
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Логи диалогов</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial; margin: 20px; background: #f0f0f0; }
            .log-entry { 
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .log-entry pre {
                margin: 0;
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
        <h1>Логи диалогов</h1>
        {% for log in logs %}
            {% if log.strip() %}
            <div class="log-entry">
                <pre>{{ log }}</pre>
            </div>
            {% endif %}
        {% endfor %}
        <script>
            setTimeout(() => window.location.reload(), 5000);
        </script>
    </body>
    </html>
    '''
    return render_template_string(template, logs=logs)

def run_webserver():
    app.run(host='0.0.0.0', port=3000)
