"""
Main configuration for Bitget Auto-Trading Bot
All settings can be overridden via .env file
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# ============================================
# API Configuration
# ============================================
BITGET_API_KEY = os.getenv('BITGET_API_KEY', '')
BITGET_SECRET_KEY = os.getenv('BITGET_SECRET_KEY', '')
BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE', '')

# ============================================
# Trading Configuration
# ============================================
INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', '40'))
TARGET_CAPITAL = 1000.0  # Target: $1,000 USDT
PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'

# Trading pairs (USDT-M Perpetual Futures)
TRADING_PAIRS = [
    'BTC/USDT:USDT',
]

# Margin mode: 'isolated' (safer) or 'cross'
MARGIN_MODE = 'isolated'

# ============================================
# Timeframe Configuration
# ============================================
TIMEFRAMES = {
    'scalp': '1m',      # Scalping entries
    'entry': '5m',      # Primary entry signals
    'trend': '15m',     # Trend confirmation
    'bias': '1h',       # Directional bias
}

# How many candles to keep in memory per timeframe
CANDLE_LIMIT = 500

# ============================================
# Money Management Tiers
# ============================================
# Each tier defines behavior based on account equity
MONEY_MANAGEMENT_TIERS = {
    'tier_1_growth': {
        'equity_min': 0,
        'equity_max': 500,
        'mode': 'SEMI_JUDI',
        'risk_per_trade': 0.25,      # 25% of equity (Semi-Judi!)
        'leverage_min': 20,
        'leverage_max': 50,
        'max_positions': 1,
        'description': '🎲 SEMI-JUDI Mode - High Risk High Reward'
    },
    'tier_2_build': {
        'equity_min': 500,
        'equity_max': 2500,
        'mode': 'AGGRESSIVE',
        'risk_per_trade': 0.04,      # 4% of equity
        'leverage_min': 5,
        'leverage_max': 10,
        'max_positions': 1,
        'description': '🔥 Acceleration Mode - Heavy growth'
    },
    'tier_3_compound': {
        'equity_min': 2500,
        'equity_max': 8000,
        'mode': 'BALANCED',
        'risk_per_trade': 0.03,     # 3% of equity
        'leverage_min': 3,
        'leverage_max': 5,
        'max_positions': 1,
        'description': '🔵 Compound Mode - Balanced approach'
    },
    'tier_4_protect': {
        'equity_min': 8000,
        'equity_max': float('inf'),
        'mode': 'PASSIVE',
        'risk_per_trade': 0.05,      # 5% of equity
        'leverage_min': 2,
        'leverage_max': 3,
        'max_positions': 1,
        'description': '🟣 Wealth Mode - Safe cruising to 10k+'
    },
}

# ============================================
# Risk Management
# ============================================
MAX_DRAWDOWN_PCT = float(os.getenv('MAX_DRAWDOWN_PCT', '80')) / 100  # 80%
MAX_DAILY_LOSS_PCT = float(os.getenv('MAX_DAILY_LOSS_PCT', '50')) / 100  # 50%
MAX_TOTAL_EXPOSURE = 0.25  # Max 25% of equity at risk across all positions
MIN_LIQUIDATION_DISTANCE = 0.10  # At least 10% away from liquidation
COOLDOWN_AFTER_MAX_DD_HOURS = 4  # Hours to pause after max drawdown hit

# Win/Lose streak adjustments
WIN_STREAK_BONUS = 0.005        # +0.5% risk per trade after 3 wins
WIN_STREAK_THRESHOLD = 3
LOSE_STREAK_PENALTY = 0.005     # -0.5% risk per trade after 2 losses
LOSE_STREAK_THRESHOLD = 2
DRAWDOWN_FORCE_PASSIVE = 0.35   # 35% DD → force passive mode
DRAWDOWN_STOP_TRADING = 0.60    # 60% DD → stop trading + cooldown

# ============================================
# Fee Structure (Bitget USDT-M Futures)
# ============================================
MAKER_FEE = 0.0002    # 0.02%
TAKER_FEE = 0.0002    # 0.02% (Limit orders assumed on 1D timeframe)
FUNDING_RATE_THRESHOLD = 0.001  # Avoid holding if funding > 0.1%

# ============================================
# Backtest Configuration
# ============================================
BACKTEST_START = '2024-01-01'
BACKTEST_END = '2025-12-31'
BACKTEST_SLIPPAGE = 0.0003  # 0.03% slippage simulation

# ============================================
# Dashboard Configuration
# ============================================
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8888'))
DASHBOARD_HOST = '127.0.0.1'

# ============================================
# Logging
# ============================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = Path(__file__).parent.parent / 'logs'
DATA_DIR = Path(__file__).parent.parent / 'data'

# Create directories
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
