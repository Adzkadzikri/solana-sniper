# solana_sniper/config.py
import os

# ============================================
# TIER 1: The "Tebar Jala" (Spray and Pray) Engine
# ============================================
INITIAL_CAPITAL = 100.0
TRADE_SIZE = 1.0          # $1 per trade. $100 means we cast 100 nets!
MAX_TRADES_PER_DAY = 10   # Don't spend it all at once

# ============================================
# SOLANA SNIPER 3.0 SETTINGS
# ============================================
# 'TARGETED' = Only snipe the CAs in TARGET_CONTRACT_ADDRESSES
# 'SCANNER' = Broad scan for any new memecoin (REST API)
# 'MEMPOOL_STREAM' = Simulate fast WebSocket Mempool stream
# 'COPY_TRADE' = Track whales in TARGET_WALLETS
SNIPER_MODE = os.getenv('SNIPER_MODE', 'TARGETED')

# List of specific Contract Addresses to snipe
TARGET_CONTRACT_ADDRESSES = [
    # "ExampleCA123456789...",
]

# Simulated Trading Fee (0.25% by default)
TRADING_FEE_PCT = 0.0025

# ============================================
# TELEGRAM & DATABASE
# ============================================
DB_NAME = "sniper.db"
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8918956228:AAEnqJ_gzoB0cOwZNmJ1JO-NcvJFePAFQwM')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1614448349')

# ============================================
# JITO MEV & COPY TRADING (Level Pro)
# ============================================
# Simulate sending transaction with Jito Tip to avoid sandwich attacks
JITO_TIP_SOL = 0.005

# List of Whale/Insider Wallets to Copy Trade
TARGET_WALLETS = [
    "WHALEx1234567890abcdefghijklmnopqrstuvwxyz",
    "INSIDERy9876543210zyxwvutsrqponmlkjihgfedc"
]

# ============================================
# Solana Network & APIs
# ============================================
# Use mainnet-beta for real sniping. (Requires Phantom private key in production)
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
PHANTOM_PRIVATE_KEY = os.getenv('PHANTOM_PRIVATE_KEY', 'DUMMY_KEY_FOR_TESTING')

# DexScreener API (Public, no key needed usually for basic search)
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/search?q="

# ============================================
# Sniping Criteria (The 10000x Filter)
# ============================================
MIN_LIQUIDITY_USD = 5000       # Must have at least $5k liquidity (prevents 99% rugs)
MAX_AGE_MINUTES = 60           # Coin must be newer than 1 hour
MIN_VOL_1H_USD = 10000         # Must have volume (Whales are buying)
REQUIRED_SOCIAL_HYPE = 75      # Social sentiment score (0-100)

# ============================================
# Exit Strategy (Do or Die)
# ============================================
TAKE_PROFIT_MULTIPLIER = 100   # 10,000% target! ($1 becomes $100 minimum)
STOP_LOSS_PCT = 0.99           # Basically no stop loss. If it rugs, we lose the $1.
