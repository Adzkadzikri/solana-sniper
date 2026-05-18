"""
Strategy-specific parameters for each trading strategy.
These are tuned for crypto futures scalping/swing trading.
"""

# ============================================
# Strategy 1: EMA Momentum Scalping
# ============================================
EMA_MOMENTUM = {
    'name': 'EMA Momentum Scalping',
    'enabled': False,
    'weight': 0.0,
    
    # EMA Parameters
    'ema_fast': 50,      # Medium trend
    'ema_slow': 200,     # Golden Cross / Death Cross
    'ema_trend': 200,    # Long-term macro filter
    
    # RSI Parameters
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'rsi_long_min': 50,   # RSI must be > 50 for long
    'rsi_short_max': 50,  # RSI must be < 50 for short
    
    # Volume Filter
    'volume_ma_period': 20,
    'volume_multiplier': 1.2,  # Volume must be 1.2x above MA
    
    # Take Profit / Stop Loss (dynamic, based on ATR)
    'tp_atr_multiplier': 5.0,   # TP = entry ± 5.0 * ATR
    'sl_atr_multiplier': 2.0,   # SL = entry ∓ 2.0 * ATR
    'tp_min_pct': 0.30,         # Min 30% TP
    'tp_max_pct': 1.00,         # Max 100% TP
    'sl_min_pct': 0.10,         # Min 10% SL
    'sl_max_pct': 0.20,         # Max 20% SL
    
    # Entry Timeframe
    'signal_timeframe': '1d',
    'trend_timeframe': '1w',
    
    # Minimum signal confidence to take trade (0-100)
    'min_confidence': 70,
    
    # Market regime: works best in trending markets
    'preferred_regime': ['trending_up', 'trending_down'],
}

# ============================================
# Strategy 2: Bollinger Band Mean Reversion
# ============================================
MEAN_REVERSION = {
    'name': 'Bollinger Band Mean Reversion',
    'enabled': True,
    'weight': 1.0,
    
    # Bollinger Band Parameters
    'bb_period': 20,
    'bb_std': 2.0,
    'bb_squeeze_threshold': 0.02,  # BB width < 2% = squeeze
    
    # RSI for Divergence Detection
    'rsi_period': 14,
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'divergence_lookback': 10,  # Candles to look back for divergence
    
    # MACD Confirmation
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    
    # Take Profit / Stop Loss
    'tp_target': 'middle_band',  # TP at BB middle (EMA20)
    'sl_atr_multiplier': 2.0,    # SL = 2.0 * ATR beyond entry band
    'sl_max_pct': 0.03,          # Max 3% SL
    
    # Entry Timeframe
    'signal_timeframe': '1h',
    'trend_timeframe': '4h',
    
    # Minimum signal confidence
    'min_confidence': 75,
    
    # Market regime: works best in ranging markets
    'preferred_regime': ['ranging', 'low_volatility'],
}

# ============================================
# Strategy 3: Breakout Momentum
# ============================================
BREAKOUT = {
    'name': 'Breakout Momentum',
    'enabled': False,
    'weight': 0.0,
    
    # Support/Resistance Detection
    'sr_lookback': 50,           # Candles to detect S/R levels
    'sr_touch_count': 2,         # Min touches to confirm level
    'sr_tolerance': 0.002,       # 0.2% tolerance for level matching
    
    # Breakout Confirmation
    'breakout_threshold': 0.005,  # Price must break 0.5% beyond S/R
    'volume_surge_multiplier': 2.0,  # Volume must be 2x above average
    'confirmation_candles': 1,    # Wait 1 candle to confirm breakout on high TF
    
    # ATR for Volatility
    'atr_period': 14,
    
    # Take Profit / Stop Loss
    'tp_measured_move': True,     # TP = measured move (consolidation range)
    'tp_atr_multiplier': 4.0,    # Alternative: 4x ATR
    'sl_reentry_pct': 0.02,      # SL if price re-enters range by 2.0%
    
    # Entry Timeframe
    'signal_timeframe': '4h',
    'trend_timeframe': '1d',
    
    # Minimum signal confidence
    'min_confidence': 75,
    
    # Market regime: works best after consolidation
    'preferred_regime': ['breakout', 'high_volatility'],
}

# ============================================
# Market Regime Detection Parameters
# ============================================
MARKET_REGIME = {
    # ADX for trend strength
    'adx_period': 14,
    'adx_trending_threshold': 25,    # ADX > 25 = trending
    'adx_strong_trend': 40,          # ADX > 40 = strong trend
    
    # ATR for volatility classification
    'atr_period': 14,
    'atr_high_vol_percentile': 75,   # Top 25% = high volatility
    'atr_low_vol_percentile': 25,    # Bottom 25% = low volatility
    
    # Bollinger Band Width for squeeze detection
    'bbw_squeeze_threshold': 0.03,   # BBW < 3% = squeeze (potential breakout)
    
    # Regime classification rules:
    # - trending_up: ADX > 25, price > EMA50, EMA9 > EMA21
    # - trending_down: ADX > 25, price < EMA50, EMA9 < EMA21
    # - ranging: ADX < 25, low-medium volatility
    # - high_volatility: ATR in top 25th percentile
    # - low_volatility: ATR in bottom 25th percentile, ADX < 20
    # - breakout: BB squeeze releasing + volume surge
}

# ============================================
# N-Pattern Strategy Configuration
# ============================================
N_PATTERN = {
    'name': 'N-Pattern Breakout',
    'enabled': False,
    'weight': 0.0,
    
    # Peak/Trough Detection
    'lookback_left': 15,         # Bars to the left to confirm a swing point
    'lookback_right': 10,        # Bars to the right to confirm a swing point
    
    # Retracement Rules (Point B to Point C)
    'min_retrace_pct': 0.05,     # Min pullback 5% of impulsive wave A->B
    'max_retrace_pct': 0.85,     # Max pullback 85% of impulsive wave A->B
    
    # Take Profit / Stop Loss (Fixed Risk/Reward via price distance)
    'rr_ratio': 1.0,             # Revert to 1:1 (High Win Rate)
    'tp_atr_multiplier': 1.0,
    'sl_atr_multiplier': 1.0,
    'tp_min_pct': 0.01,
    'tp_max_pct': 0.15,          # Normal max TP
    'sl_min_pct': 0.01,
    'sl_max_pct': 0.15,
    
    # Entry Timeframe
    'signal_timeframe': '1h',
    'trend_timeframe': '1d',     # Macro filter timeframe
    
    # Macro Filter
    'use_macro_filter': True,    # Ensure HTF is trending
    'macro_ema_period': 200,     # Use 200 EMA on HTF
    
    # Minimum signal confidence
    'min_confidence': 70,
}

# ============================================
# Trailing Stop Configuration
# ============================================
TRAILING_STOP = {
    'enabled': False,           # DO OR DIE: Disabled for true Sniper mode
    'activation_pct': 0.20,     # Activate after 20% profit
    'trail_distance_pct': 0.10, # Trail 10% behind price
    'use_atr': True,            
    'atr_trail_multiplier': 3.0, # Trail = 3.0 * ATR behind price
}

# ============================================
# Partial Take Profit (Scale Out)
# ============================================
SCALE_OUT = {
    'enabled': True,
    'levels': [
        {'pct_of_tp': 0.50, 'close_pct': 0.50},  # At 50% of TP, close 50%
        {'pct_of_tp': 1.00, 'close_pct': 1.00},   # At 100% of TP, close rest
    ],
}
