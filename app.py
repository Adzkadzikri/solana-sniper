import threading
import time
import random
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from solana_sniper.scanner import MemecoinScanner
from solana_sniper.social_tracker import SocialSentimentTracker
from solana_sniper.trader import SolanaTrader
from solana_sniper.database import SniperDatabase
from solana_sniper.telegram_bot import TelegramNotifier
from solana_sniper.wallet_tracker import WalletTracker
from solana_sniper.config import SNIPER_MODE, TARGET_CONTRACT_ADDRESSES, TARGET_WALLETS

app = FastAPI()

# Shared state
bot_logs = []
active_trades = []
past_trades = []
capital_history = []
capital = 100.0
nets_thrown = 0
running = True

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    bot_logs.append(f"[{timestamp}] {message}")
    if len(bot_logs) > 50:
        bot_logs.pop(0)
    print(f"[{timestamp}] {message}")

def bot_loop():
    global capital, nets_thrown, active_trades, past_trades, capital_history, running
    
    # Initialize Core Components
    db = SniperDatabase()
    telegram = TelegramNotifier()
    scanner = MemecoinScanner()
    social = SocialSentimentTracker()
    trader = SolanaTrader(database=db, telegram=telegram)
    wallet_tracker = WalletTracker(TARGET_WALLETS)
    
    add_log(f"🤖 BOT STARTED - Mode: {SNIPER_MODE}")
    telegram.send_alert(f"🤖 <b>Solana Sniper 3.0 Started</b>\nMode: <code>{SNIPER_MODE}</code>\nCapital: ${trader.capital:.2f}")
    
    # Sync state from DB via Trader
    capital = trader.capital
    active_trades = list(trader.active_nets)
    past_trades = list(trader.past_nets)
    capital_history = list(trader.capital_history)
    
    while running and trader.capital >= 1.0 and nets_thrown < 100:
        # Polling delay depends on mode. Mempool Stream is "instant" (simulated 2s here to avoid log spam).
        delay = 2 if SNIPER_MODE == 'MEMPOOL_STREAM' else 15
        time.sleep(delay)
        
        targets = []
        
        if SNIPER_MODE == 'TARGETED':
            if not TARGET_CONTRACT_ADDRESSES:
                add_log("⚠️ TARGET_CONTRACT_ADDRESSES is empty! Add CAs to config.py")
                time.sleep(30)
                continue
            add_log(f"🔍 Scanning specifically for {len(TARGET_CONTRACT_ADDRESSES)} Target CAs...")
            try:
                targets = scanner.search_specific_pairs(TARGET_CONTRACT_ADDRESSES)
            except Exception as e:
                add_log(f"❌ Scanner Error: {e}")
                
        elif SNIPER_MODE == 'COPY_TRADE':
            try:
                targets = wallet_tracker.scan_for_whale_buys()
                if not targets:
                    add_log("⏳ Watching insider wallets... no buys detected.")
            except Exception as e:
                add_log(f"❌ Wallet Tracker Error: {e}")
                
        elif SNIPER_MODE == 'MEMPOOL_STREAM':
            add_log("⚡ [WebSockets] Listening to pending transactions...")
            # Simulate picking up a hyped pair instantly
            if random.random() < 0.15:
                try:
                    targets = [scanner.mock_generate_random_new_coin()]
                    add_log(f"🚀 [WebSockets] Intercepted new pair creation in mempool!")
                except Exception as e:
                    pass
        else:
            add_log("🔍 Scanning Solana blockchain for new Memecoin pairs via REST...")
            try:
                targets = scanner.search_new_pairs()
            except Exception as e:
                add_log(f"❌ Scanner Error: {e}")
            
        if targets:
            for target_coin in targets:
                if trader.capital < 1.0 or nets_thrown >= 100:
                    break
                    
                symbol = target_coin['symbol']
                add_log(f"👀 Detected Pool: ${symbol} (Liq: ${target_coin['liquidity']:.0f})")
                
                # Check Social Hype
                sentiment = social.evaluate_hype(target_coin)
                
                if sentiment['is_approved']:
                    add_log(f"🔥 HYPE CONFIRMED! ${symbol} is trending on X/Twitter!")
                    
                    # Prevent Double Entry on the same token
                    already_active = any(net['address'] == target_coin['address'] for net in trader.active_nets)
                    already_past = any(net['address'] == target_coin['address'] for net in trader.past_nets)
                    if already_active or already_past:
                        add_log(f"⏳ Already processed ${symbol}. Skipping to avoid double entry.")
                        continue
                    
                    # Audit Token Contract for Honeypots
                    add_log(f"🛡️ Auditing ${symbol} contract for Honeypot & Rug risks...")
                    audit = scanner.check_honeypot(target_coin['address'])
                    if not audit['is_safe']:
                        add_log(f"🚨 [AUDIT REJECTED] ${symbol} failed safety check: {audit['reason']}")
                        continue
                        
                    add_log(f"✅ [AUDIT PASSED] {audit['reason']}")
                    success = trader.execute_buy(target_coin)
                    if success:
                        nets_thrown += 1
                        capital = trader.capital
                        active_trades = list(trader.active_nets)
                        capital_history = list(trader.capital_history)
                else:
                    add_log(f"❌ Rejected ${symbol} - Insufficient whale/social support.")
            
        # Check existing bags
        if len(trader.active_nets) > 0:
            add_log("📊 Updating current portfolio prices...")
            trader.check_portfolio_status(scanner)
            capital = trader.capital
            active_trades = list(trader.active_nets)
            past_trades = list(trader.past_nets)
            capital_history = list(trader.capital_history)

    add_log("🏁 Session ended. Target reached or out of capital.")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎣 Solana Sniper 2.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
            max-width: 1200px;
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
            grid-template-columns: 1.2fr 0.8fr 0.8fr;
            gap: 30px;
        }
        @media(max-width: 1024px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        .panel {
            background-color: var(--panel-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            height: 450px;
            display: flex;
            flex-direction: column;
        }
        .panel h2 {
            margin-top: 0;
            font-size: 1.1rem;
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
            white-space: pre-wrap;
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
        .status-tag.rug {
            background-color: rgba(239, 68, 68, 0.1);
            color: var(--danger);
        }
        .status-tag.jackpot {
            background-color: rgba(168, 85, 247, 0.1);
            color: var(--accent-purple);
        }
        .status-tag.tp1 {
            background-color: rgba(20, 241, 149, 0.15);
            color: #14f195;
        }
        .status-tag.tp2 {
            background-color: rgba(251, 191, 36, 0.15);
            color: #fbbf24;
        }
        .status-tag.tp3 {
            background-color: rgba(249, 115, 22, 0.15);
            color: #f97316;
        }
        .status-tag.ath-guard {
            background-color: rgba(239, 68, 68, 0.15);
            color: #f87171;
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
        
        /* Chart container */
        .chart-container {
            width: 100%;
            height: 300px;
            margin-bottom: 30px;
            background-color: var(--panel-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            box-sizing: border-box;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🎣 Solana Sniper 2.0</h1>
                <p style="margin: 5px 0 0 0; color: var(--text-muted)">Hugging Face Space Deployment | FastAPI</p>
            </div>
            <div class="ping-badge">
                <span class="ping-dot"></span> Active
            </div>
        </header>

        <div class="stats-grid">
            <div class="card">
                <h3>💰 Current Wallet Balance</h3>
                <div class="value" id="wallet-cap">$100.00</div>
            </div>
            <div class="card">
                <h3>🕸️ Nets Thrown</h3>
                <div class="value purple" id="nets-thrown">0/100</div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="portfolioChart"></canvas>
        </div>

        <div class="main-content">
            <div class="panel">
                <h2>📜 Bot Live Activity Logs</h2>
                <div class="log-area" id="logs">Waiting for logs...</div>
            </div>
            <div class="panel">
                <h2>🕸️ Active Nets (Holding)</h2>
                <div class="trade-list" id="trades">
                    <div style="color:var(--text-muted); text-align:center; margin-top:50px;">No active nets currently cast.</div>
                </div>
            </div>
            <div class="panel">
                <h2>📜 Past Holdings (History)</h2>
                <div class="trade-list" id="past-trades">
                    <div style="color:var(--text-muted); text-align:center; margin-top:50px;">No trade history yet.</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Setup Chart
        const ctx = document.getElementById('portfolioChart').getContext('2d');
        const portfolioChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Balance ($)',
                    data: [],
                    borderColor: '#14f195',
                    backgroundColor: 'rgba(20, 241, 149, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0,
                    pointHitRadius: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af' }
                    }
                }
            }
        });

        function formatTradeItem(trade, isActive) {
            const caShort = trade.address ? `${trade.address.substring(0, 6)}...${trade.address.substring(trade.address.length - 4)}` : 'UNKNOWN';
            const dexLink = trade.address ? `https://dexscreener.com/solana/${trade.address}` : '#';
            const solscanLink = trade.address ? `https://solscan.io/token/${trade.address}` : '#';
            
            // Map status → badge label, CSS class, border color
            const statusMap = {
                'HOLDING':          { label: '⏳ Holding',       cls: '',          border: 'var(--accent)' },
                'RIDING_TO_5X':     { label: '🚀 Riding → 5x',  cls: 'tp1',       border: '#14f195' },
                'RIDING_TO_20X':    { label: '🔥 Riding → 20x', cls: 'tp2',       border: '#fbbf24' },
                'RIDING_TO_100X':   { label: '🌙 Riding → 100x',cls: 'tp3',       border: '#f97316' },
                'RUGPULL_SOLD':     { label: '💀 Rugpull',       cls: 'rug',       border: 'var(--danger)' },
                'ATH_GUARD_SOLD':   { label: '🚨 ATH Guard',     cls: 'ath-guard', border: '#f87171' },
                'TP4_MOONSHOT_SOLD':{ label: '🎆 Moonshot!',     cls: 'jackpot',   border: 'var(--accent-purple)' },
                'TP4_SOLD':         { label: '🎆 Moonshot!',     cls: 'jackpot',   border: 'var(--accent-purple)' },
            };
            const s = statusMap[trade.status] || { label: trade.status || 'Scanning...', cls: '', border: 'var(--accent)' };
            const statusBadge = `<span class="status-tag ${s.cls}">${s.label}</span>`;
            const borderStyle = `border-left: 4px solid ${s.border};`;
            
            return `
                <div class="trade-item" style="${borderStyle}">
                    <div class="trade-info">
                        <span class="trade-symbol">
                            <a href="${dexLink}" target="_blank" style="color: inherit; text-decoration: none; font-weight: 700; border-bottom: 1px dashed rgba(255,255,255,0.3);">
                                $${trade.symbol} 📊
                            </a>
                        </span>
                        <span class="trade-price" style="margin-top: 4px;">Buy: $${trade.buy_price.toFixed(8)}</span>
                        <span style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace; margin-top: 2px;">
                            CA: <a href="${solscanLink}" target="_blank" style="color: var(--text-muted); text-decoration: none; border-bottom: 1px dotted rgba(255,255,255,0.2);">${caShort}</a>
                        </span>
                    </div>
                    ${statusBadge}
                </div>
            `;
        }

        setInterval(function() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('wallet-cap').innerText = '$' + data.capital.toFixed(2);
                    document.getElementById('nets-thrown').innerText = data.nets_thrown + '/100';
                    
                    // Update Logs
                    const logArea = document.getElementById('logs');
                    logArea.innerHTML = data.logs.join('\\n');
                    logArea.scrollTop = logArea.scrollHeight;
                    
                    // Update Active Trades
                    const tradeList = document.getElementById('trades');
                    if (data.trades.length === 0) {
                        tradeList.innerHTML = '<div style="color:var(--text-muted); text-align:center; margin-top:50px;">No active nets currently cast.</div>';
                    } else {
                        tradeList.innerHTML = data.trades.map(t => formatTradeItem(t, true)).join('');
                    }
                    
                    // Update Past Trades
                    const pastTradeList = document.getElementById('past-trades');
                    if (data.past_trades.length === 0) {
                        pastTradeList.innerHTML = '<div style="color:var(--text-muted); text-align:center; margin-top:50px;">No trade history yet.</div>';
                    } else {
                        pastTradeList.innerHTML = [...data.past_trades].reverse().map(t => formatTradeItem(t, false)).join('');
                    }
                    
                    // Update Chart
                    if (data.capital_history && data.capital_history.length > 0) {
                        const times = data.capital_history.map(item => {
                            const d = new Date(item[0]);
                            return d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds();
                        });
                        const values = data.capital_history.map(item => item[1]);
                        
                        portfolioChart.data.labels = times;
                        portfolioChart.data.datasets[0].data = values;
                        portfolioChart.update();
                    }
                });
        }, 3000);
    </script>
</body>
</html>
"""

@app.get("/")
def home():
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)

@app.get("/api/data")
def get_data():
    return {
        "capital": capital,
        "nets_thrown": nets_thrown,
        "logs": bot_logs,
        "trades": active_trades,
        "past_trades": past_trades,
        "capital_history": capital_history
    }

# FastAPI doesn't use standard __main__ blocks natively for threading cleanly in HF Spaces if run via `uvicorn`,
# so we launch the background thread here on startup.
@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get('PORT', 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
