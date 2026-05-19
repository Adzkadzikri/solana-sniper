# app.py
import threading
import time
import random
from flask import Flask, render_template_string, jsonify
from solana_sniper.scanner import MemecoinScanner
from solana_sniper.social_tracker import SocialSentimentTracker
from solana_sniper.trader import SolanaTrader

app = Flask(__name__)

# Shared state
bot_logs = []
active_trades = []
capital = 40.0
nets_thrown = 0
running = True

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    bot_logs.append(f"[{timestamp}] {message}")
    if len(bot_logs) > 50:
        bot_logs.pop(0)
    print(f"[{timestamp}] {message}")

def bot_loop():
    global capital, nets_thrown, active_trades, running
    add_log("🤖 BOT STARTED - Listening to Solana blockchain events...")
    
    scanner = MemecoinScanner()
    social = SocialSentimentTracker()
    trader = SolanaTrader()
    
    while running and trader.capital >= 1.0 and nets_thrown < 40:
        time.sleep(15)  # Scan every 15 seconds to be polite to API limits
        
        add_log("🔍 Scanning Solana blockchain for new Memecoin pairs...")
        try:
            targets = scanner.search_new_pairs()
        except Exception as e:
            add_log(f"❌ Scanner Error: {e}")
            continue
            
        if not targets:
            add_log("⏳ No hyped pairs found in this block. Waiting...")
            continue
            
        target_coin = targets[0]
        symbol = target_coin['symbol']
        add_log(f"👀 Detected New Pool: ${symbol} (Liq: ${target_coin['liquidity']:.0f})")
        
        # Check Social Hype
        sentiment = social.evaluate_hype(symbol)
        
        if sentiment['is_approved']:
            add_log(f"🔥 HYPE CONFIRMED! ${symbol} is trending on X/Twitter!")
            success = trader.execute_buy(target_coin)
            if success:
                nets_thrown += 1
                capital = trader.capital
                active_trades = trader.active_nets
                add_log(f"🚀 Paper Bought ${symbol} at {target_coin['price_usd']:.8f}")
        else:
            add_log(f"❌ Rejected ${symbol} - Insufficient whale/social support.")
            
        # Check existing bags
        if nets_thrown > 0:
            add_log("📊 Updating current portfolio prices...")
            trader.check_portfolio_status(scanner)
            capital = trader.capital
            active_trades = trader.active_nets

    add_log("🏁 Session ended. Target reached or out of capital.")

# HTML Dashboard Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎣 Solana Sniper Net Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --panel-bg: #151c2c;
            --accent: #14f195;
            --accent-purple: #9945ff;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --danger: #ef4444;
        }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            max-width: 900px;
            width: 100%;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--panel-bg);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        h1 {
            margin: 0;
            font-size: 2.2rem;
            background: linear-gradient(to right, var(--accent), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background-color: var(--panel-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }
        .card h3 {
            margin: 0 0 10px 0;
            color: var(--text-muted);
            font-size: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .card .value {
            font-size: 2rem;
            font-weight: 800;
            color: var(--accent);
        }
        .card .value.purple {
            color: var(--accent-purple);
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr;
            gap: 30px;
        }
        @media(min-width: 768px) {
            .main-content {
                grid-template-columns: 1.2fr 0.8fr;
            }
        }
        .panel {
            background-color: var(--panel-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            height: 400px;
            display: flex;
            flex-direction: column;
        }
        .panel h2 {
            margin-top: 0;
            font-size: 1.3rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .log-area {
            flex-grow: 1;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9rem;
            color: #34d399;
            background-color: #0b0f19;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.02);
            line-height: 1.5;
        }
        .trade-list {
            flex-grow: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .trade-item {
            background-color: var(--bg-color);
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid var(--accent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .trade-info {
            display: flex;
            flex-direction: column;
        }
        .trade-symbol {
            font-weight: 600;
        }
        .trade-price {
            font-size: 0.8rem;
            color: var(--text-muted);
        }
        .status-tag {
            background-color: rgba(20, 241, 149, 0.1);
            color: var(--accent);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .ping-badge {
            background-color: rgba(20, 241, 149, 0.2);
            color: var(--accent);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .ping-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.8; }
        }
    </style>
    <script>
        setInterval(function() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('wallet-cap').innerText = '$' + data.capital.toFixed(2);
                    document.getElementById('nets-thrown').innerText = data.nets_thrown + '/40';
                    
                    // Update Logs
                    const logArea = document.getElementById('logs');
                    logArea.innerHTML = data.logs.join('\\n');
                    logArea.scrollTop = logArea.scrollHeight;
                    
                    // Update Trades
                    const tradeList = document.getElementById('trades');
                    tradeList.innerHTML = '';
                    if (data.trades.length === 0) {
                        tradeList.innerHTML = '<div style="color:var(--text-muted); text-align:center; margin-top:50px;">No active nets currently cast.</div>';
                    } else {
                        data.trades.forEach(trade => {
                            tradeList.innerHTML += `
                                <div class="trade-item">
                                    <div class="trade-info">
                                        <span class="trade-symbol">$${trade.symbol}</span>
                                        <span class="trade-price">Buy: ${trade.buy_price.toFixed(8)}</span>
                                    </div>
                                    <span class="status-tag">Snipping...</span>
                                </div>
                            `;
                        });
                    }
                });
        }, 3000);
    </script>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🎣 Solana Sniper Net</h1>
                <p style="margin: 5px 0 0 0; color: var(--text-muted)">Live 24/7 Paper Trading Dashboard</p>
            </div>
            <div class="ping-badge">
                <span class="ping-dot"></span> Active
            </div>
        </header>

        <div class="stats-grid">
            <div class="card">
                <h3>💰 Current Wallet Balance</h3>
                <div class="value" id="wallet-cap">${{ capital }}</div>
            </div>
            <div class="card">
                <h3>🕸️ Nets Thrown</h3>
                <div class="value purple" id="nets-thrown">{{ nets_thrown }}/40</div>
            </div>
        </div>

        <div class="main-content">
            <div class="panel">
                <h2>📜 Bot Live Activity Logs</h2>
                <pre class="log-area" id="logs">{{ logs }}</pre>
            </div>
            <div class="panel">
                <h2>🕸️ Active Nets (Holding)</h2>
                <div class="trade-list" id="trades">
                    <div style="color:var(--text-muted); text-align:center; margin-top:50px;">No active nets currently cast.</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    log_string = "\n".join(bot_logs)
    return render_template_string(
        DASHBOARD_HTML, 
        capital=f"{capital:.2f}", 
        nets_thrown=nets_thrown, 
        logs=log_string
    )

@app.route('/api/data')
def get_data():
    return jsonify({
        'capital': capital,
        'nets_thrown': nets_thrown,
        'logs': bot_logs,
        'trades': active_trades
    })

if __name__ == '__main__':
    # Start bot thread
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    
    # Start web app (Dynamic port for Hugging Face/Render support)
    import os
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port)
