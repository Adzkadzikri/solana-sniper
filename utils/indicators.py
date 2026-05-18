"""
Technical indicator calculations for the trading bot.
Uses pandas and numpy for efficient computation.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


# ============================================
# Moving Averages
# ============================================
def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


# ============================================
# RSI (Relative Strength Index)
# ============================================
def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI using Wilder's smoothing method.
    
    Args:
        series: Price series (typically close prices)
        period: RSI period (default 14)
        
    Returns:
        RSI values (0-100)
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values.fillna(50)


# ============================================
# MACD
# ============================================
def macd(series: pd.Series, fast: int = 12, slow: int = 26, 
         signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD, Signal line, and Histogram.
    
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


# ============================================
# Bollinger Bands
# ============================================
def bollinger_bands(series: pd.Series, period: int = 20, 
                    std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower


def bollinger_band_width(upper: pd.Series, lower: pd.Series, 
                          middle: pd.Series) -> pd.Series:
    """Calculate Bollinger Band Width (normalized)."""
    return (upper - lower) / middle


# ============================================
# ATR (Average True Range)
# ============================================
def atr(high: pd.Series, low: pd.Series, close: pd.Series, 
        period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period
        
    Returns:
        ATR values
    """
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()


# ============================================
# ADX (Average Directional Index)
# ============================================
def adx(high: pd.Series, low: pd.Series, close: pd.Series, 
        period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate ADX, +DI, and -DI.
    
    Returns:
        Tuple of (adx, plus_di, minus_di)
    """
    # Calculate directional movements
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = pd.Series(np.where(
        (up_move > down_move) & (up_move > 0), up_move, 0.0
    ), index=high.index)
    
    minus_dm = pd.Series(np.where(
        (down_move > up_move) & (down_move > 0), down_move, 0.0
    ), index=high.index)
    
    # Calculate ATR
    atr_values = atr(high, low, close, period)
    
    # Smoothed DI
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / 
                      atr_values.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / 
                       atr_values.replace(0, np.nan))
    
    # Calculate DX and ADX
    di_sum = plus_di + minus_di
    di_diff = (plus_di - minus_di).abs()
    dx = 100 * (di_diff / di_sum.replace(0, np.nan))
    
    adx_values = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    return adx_values.fillna(0), plus_di.fillna(0), minus_di.fillna(0)


# ============================================
# Volume Analysis
# ============================================
def volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
    """Volume Moving Average."""
    return sma(volume, period)


def volume_surge(volume: pd.Series, period: int = 20, 
                  multiplier: float = 2.0) -> pd.Series:
    """Detect volume surges (volume > multiplier * MA)."""
    vol_ma = volume_ma(volume, period)
    return volume > (vol_ma * multiplier)


# ============================================
# Support & Resistance Detection
# ============================================
def find_support_resistance(high: pd.Series, low: pd.Series, 
                             close: pd.Series, lookback: int = 50,
                             tolerance: float = 0.002) -> dict:
    """
    Detect support and resistance levels using pivot points.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        lookback: Number of candles to analyze
        tolerance: Price tolerance for level grouping (0.2%)
        
    Returns:
        Dict with 'support' and 'resistance' lists
    """
    recent_high = high.tail(lookback)
    recent_low = low.tail(lookback)
    current_price = close.iloc[-1]
    
    # Find local minima (support) and maxima (resistance)
    supports = []
    resistances = []
    
    for i in range(2, len(recent_low) - 2):
        # Local minimum → support
        if (recent_low.iloc[i] <= recent_low.iloc[i-1] and 
            recent_low.iloc[i] <= recent_low.iloc[i-2] and
            recent_low.iloc[i] <= recent_low.iloc[i+1] and 
            recent_low.iloc[i] <= recent_low.iloc[i+2]):
            supports.append(recent_low.iloc[i])
        
        # Local maximum → resistance
        if (recent_high.iloc[i] >= recent_high.iloc[i-1] and 
            recent_high.iloc[i] >= recent_high.iloc[i-2] and
            recent_high.iloc[i] >= recent_high.iloc[i+1] and 
            recent_high.iloc[i] >= recent_high.iloc[i+2]):
            resistances.append(recent_high.iloc[i])
    
    # Group nearby levels
    supports = _cluster_levels(supports, tolerance)
    resistances = _cluster_levels(resistances, tolerance)
    
    # Filter: only levels near current price (within 5%)
    supports = [s for s in supports if s < current_price and 
                abs(s - current_price) / current_price < 0.05]
    resistances = [r for r in resistances if r > current_price and 
                   abs(r - current_price) / current_price < 0.05]
    
    # Sort by distance to current price
    supports.sort(reverse=True)  # Nearest support first
    resistances.sort()  # Nearest resistance first
    
    return {'support': supports[:5], 'resistance': resistances[:5]}


def _cluster_levels(levels: list, tolerance: float) -> list:
    """Group nearby price levels into clusters and return averages."""
    if not levels:
        return []
    
    levels = sorted(levels)
    clusters = [[levels[0]]]
    
    for level in levels[1:]:
        if abs(level - clusters[-1][-1]) / clusters[-1][-1] < tolerance:
            clusters[-1].append(level)
        else:
            clusters.append([level])
    
    # Return average of each cluster (weighted by touch count)
    return [sum(c) / len(c) for c in clusters if len(c) >= 1]


# ============================================
# Market Regime Classification
# ============================================
def classify_market_regime(df: pd.DataFrame, 
                           adx_threshold: float = 25,
                           atr_high_pctile: float = 75,
                           atr_low_pctile: float = 25,
                           bbw_squeeze: float = 0.03) -> str:
    """
    Classify current market regime.
    
    Args:
        df: DataFrame with OHLCV data and indicators already calculated
        
    Returns:
        One of: 'trending_up', 'trending_down', 'ranging', 
                'high_volatility', 'low_volatility', 'breakout'
    """
    if len(df) < 50:
        return 'unknown'
    
    close = df['close']
    
    # Calculate indicators if not present
    adx_val = adx(df['high'], df['low'], close, 14)[0].iloc[-1]
    atr_val = atr(df['high'], df['low'], close, 14)
    atr_current = atr_val.iloc[-1]
    atr_pctile = (atr_val.rank(pct=True) * 100).iloc[-1]
    
    ema_9 = ema(close, 9).iloc[-1]
    ema_21 = ema(close, 21).iloc[-1]
    ema_50 = ema(close, 50).iloc[-1]
    
    upper, middle, lower = bollinger_bands(close, 20, 2.0)
    bbw = bollinger_band_width(upper, lower, middle).iloc[-1]
    
    current_price = close.iloc[-1]
    
    # Check for BB squeeze breakout
    if bbw < bbw_squeeze:
        # Check if previous candles were also in squeeze (building pressure)
        prev_bbw = bollinger_band_width(upper, lower, middle).iloc[-5:-1]
        if prev_bbw.mean() < bbw_squeeze:
            return 'breakout'
    
    # Check for high volatility
    if atr_pctile > atr_high_pctile and adx_val < adx_threshold:
        return 'high_volatility'
    
    # Check for trending
    if adx_val > adx_threshold:
        if current_price > ema_50 and ema_9 > ema_21:
            return 'trending_up'
        elif current_price < ema_50 and ema_9 < ema_21:
            return 'trending_down'
    
    # Check for low volatility
    if atr_pctile < atr_low_pctile and adx_val < 20:
        return 'low_volatility'
    
    # Default: ranging
    return 'ranging'


# ============================================
# Divergence Detection
# ============================================
def detect_divergence(price: pd.Series, indicator: pd.Series, 
                       lookback: int = 10) -> Optional[str]:
    """
    Detect bullish or bearish divergence between price and an indicator.
    
    Args:
        price: Price series
        indicator: Indicator series (e.g., RSI)
        lookback: Number of candles to look back
        
    Returns:
        'bullish', 'bearish', or None
    """
    if len(price) < lookback + 2:
        return None
    
    recent_price = price.iloc[-lookback:]
    recent_ind = indicator.iloc[-lookback:]
    
    # Find local lows in price
    price_lows = []
    ind_at_price_lows = []
    for i in range(1, len(recent_price) - 1):
        if (recent_price.iloc[i] < recent_price.iloc[i-1] and 
            recent_price.iloc[i] < recent_price.iloc[i+1]):
            price_lows.append(recent_price.iloc[i])
            ind_at_price_lows.append(recent_ind.iloc[i])
    
    # Bullish divergence: price makes lower low, indicator makes higher low
    if len(price_lows) >= 2:
        if price_lows[-1] < price_lows[-2] and ind_at_price_lows[-1] > ind_at_price_lows[-2]:
            return 'bullish'
    
    # Find local highs in price
    price_highs = []
    ind_at_price_highs = []
    for i in range(1, len(recent_price) - 1):
        if (recent_price.iloc[i] > recent_price.iloc[i-1] and 
            recent_price.iloc[i] > recent_price.iloc[i+1]):
            price_highs.append(recent_price.iloc[i])
            ind_at_price_highs.append(recent_ind.iloc[i])
    
    # Bearish divergence: price makes higher high, indicator makes lower high
    if len(price_highs) >= 2:
        if price_highs[-1] > price_highs[-2] and ind_at_price_highs[-1] < ind_at_price_highs[-2]:
            return 'bearish'
    
    return None
