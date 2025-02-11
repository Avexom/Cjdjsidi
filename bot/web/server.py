
from flask import Flask, render_template_string
from datetime import datetime
import bot.database.database as db
from config import ADMIN_IDS

app = Flask(__name__)

@app.route('/admin')
async def admin_panel():
    stats = {
        "total_users": await db.get_total_users(),
        "total_subscriptions": await db.get_total_subscriptions(),
        "total_messages": await db.get_total_messages(),
        "total_deleted_messages": await db.get_total_deleted_messages(),
        "subscription_price": await db.get_subscription_price()
    }
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Panel</title>
        <style>
            body {
                background: #000;
                color: #fff;
                font-family: 'Courier New', monospace;
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                animation: backgroundPulse 10s ease infinite;
            }
            
            @keyframes backgroundPulse {
                0% { background: #000000; }
                50% { background: #0a0a2a; }
                100% { background: #000000; }
            }
            
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: rgba(0,0,0,0.7);
                border-radius: 10px;
                box-shadow: 0 0 20px #0ff,
                           0 0 30px #0ff,
                           0 0 40px #0ff;
                animation: glowPulse 2s ease-in-out infinite;
            }
            
            @keyframes glowPulse {
                0% { box-shadow: 0 0 20px #0ff, 0 0 30px #0ff, 0 0 40px #0ff; }
                50% { box-shadow: 0 0 25px #f0f, 0 0 35px #f0f, 0 0 45px #f0f; }
                100% { box-shadow: 0 0 20px #0ff, 0 0 30px #0ff, 0 0 40px #0ff; }
            }
            
            h1 {
                text-align: center;
                color: #0ff;
                text-shadow: 0 0 10px #0ff,
                           0 0 20px #0ff;
                margin-bottom: 30px;
            }
            
            .stat-box {
                background: rgba(0,0,0,0.8);
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border: 1px solid #0ff;
                transition: all 0.3s ease;
            }
            
            .stat-box:hover {
                transform: translateX(10px);
                border-color: #f0f;
                box-shadow: 0 0 15px #f0f;
            }
            
            .stat-label {
                color: #0ff;
                font-weight: bold;
            }
            
            .stat-value {
                color: #fff;
                float: right;
                text-shadow: 0 0 5px #fff;
            }
            
            .last-update {
                text-align: center;
                color: #666;
                margin-top: 20px;
                font-size: 0.8em;
            }
            
            @keyframes textFlicker {
                0% { opacity: 0.8; }
                50% { opacity: 1; }
                100% { opacity: 0.8; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Admin Panel</h1>
            
            <div class="stat-box">
                <span class="stat-label">Total Users</span>
                <span class="stat-value">{{ stats['total_users'] }}</span>
            </div>
            
            <div class="stat-box">
                <span class="stat-label">Active Subscriptions</span>
                <span class="stat-value">{{ stats['total_subscriptions'] }}</span>
            </div>
            
            <div class="stat-box">
                <span class="stat-label">Total Messages</span>
                <span class="stat-value">{{ stats['total_messages'] }}</span>
            </div>
            
            <div class="stat-box">
                <span class="stat-label">Deleted Messages</span>
                <span class="stat-value">{{ stats['total_deleted_messages'] }}</span>
            </div>
            
            <div class="stat-box">
                <span class="stat-label">Subscription Price</span>
                <span class="stat-value">${{ stats['subscription_price'] }}</span>
            </div>
            
            <div class="last-update">
                Last updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}
            </div>
        </div>
        <script>
            setTimeout(() => window.location.reload(), 30000);
        </script>
    </body>
    </html>
    '''
    return render_template_string(template, stats=stats, datetime=datetime)

def run_webserver():
    app.run(host='0.0.0.0', port=3000)
