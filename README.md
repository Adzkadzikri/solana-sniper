# 🤖 Bitget Auto-Trading Bot

**$40 → $1,000 USDT Challenge** — Automated 24/7 derivatives trading bot for Bitget Exchange.

## ⚡ Quick Start

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
# Copy and edit the environment file
copy .env.example .env
# Edit .env with your Bitget API credentials
```

### 3. Run Backtest (Validate Strategy)
```bash
python run_backtest.py
```
This will download historical data, run the strategy simulation, and generate an HTML report.

### 4. Run Live Bot
```bash
python run_bot.py
```
The bot will start trading automatically on Bitget futures.

> ⚠️ **IMPORTANT:** Set `PAPER_TRADING=true` in `.env` first to test without real money!

---

## 📊 Strategy Overview

The bot uses **3 complementary strategies** that are automatically selected based on market conditions:

| Strategy | Allocation | Market Condition |
|----------|-----------|-----------------|
| 🔵 EMA Momentum Scalping | 60% | Trending markets |
| 🟣 Bollinger Band Mean Reversion | 25% | Ranging markets |
| 🟢 Breakout Momentum | 15% | After consolidation |

### Adaptive Money Management

| Account Tier | Equity | Mode | Risk/Trade | Leverage |
|:---:|:---:|:---:|:---:|:---:|
| 🟢 Growth | $40-$100 | AGGRESSIVE | 3% | 7-10x |
| 🟡 Build | $100-$300 | MODERATE | 2% | 5-7x |
| 🔵 Compound | $300-$600 | BALANCED | 1.5% | 3-5x |
| 🟣 Protect | $600-$1000 | PASSIVE | 1% | 3x |

### Risk Controls
- ✅ Max drawdown: 15% → auto-stop + cooldown
- ✅ Daily loss limit: 5% → stop trading for the day
- ✅ Liquidation distance: minimum 10% from liq price
- ✅ Win/lose streak adjustments
- ✅ Trailing stops for profit protection

---

## 🖥️ Dashboard

Open `http://127.0.0.1:8888` in your browser when the bot is running to see:
- Real-time equity & P/L
- Active positions
- Risk status & mode
- Performance statistics

---

## 📁 Project Structure

```
├── config/          # Configuration & parameters
├── core/            # Exchange, data feed, orders
├── strategies/      # 3 trading strategies + selector
├── money_management/# Position sizing & risk controls
├── backtest/        # Backtesting engine & reports
├── bot/             # Live trading loop & dashboard server
├── dashboard/       # Web monitoring UI
├── utils/           # Logging, indicators, helpers
├── run_backtest.py  # Run backtest
└── run_bot.py       # Run live bot
```

---

## ⚠️ Disclaimer

Futures trading involves significant risk. This bot is provided for educational purposes. Past backtest performance does not guarantee future results. Only trade with money you can afford to lose.
