# solana_sniper/config.py
import os

# ============================================
# TIER 1: The "Tebar Jala" (Spray and Pray) Engine
# ============================================
INITIAL_CAPITAL = 40.0
TRADE_SIZE = 1.0          # $1 per trade. $40 means we cast 40 nets!
MAX_TRADES_PER_DAY = 10   # Don't spend it all at once

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
