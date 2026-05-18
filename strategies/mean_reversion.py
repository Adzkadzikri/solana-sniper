"""
Strategy 2: Bollinger Band Mean Reversion
Secondary strategy (25% weight) - Best for ranging markets.
"""
import pandas as pd
from typing import Optional
from strategies.base_strategy import BaseStrategy, Signal
from config.strategy_params import MEAN_REVERSION
from utils.indicators import (
    bollinger_bands, rsi, macd, atr, ema, detect_divergence
)


class MeanReversionStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__('BB Mean Reversion', MEAN_REVERSION)
    
    def generate_signal(self, df: pd.DataFrame, symbol: str,
                        trend_df: pd.DataFrame = None) -> Optional[Signal]:
        if len(df) < 50:
            return None
        
        p = self.params
        close = df['close']
        
        upper, middle, lower = bollinger_bands(close, p['bb_period'], p['bb_std'])
        rsi_val = rsi(close, p['rsi_period'])
        macd_line, macd_sig, macd_hist = macd(
            close, p['macd_fast'], p['macd_slow'], p['macd_signal']
        )
        atr_val = atr(df['high'], df['low'], close, 14)
        
        price = close.iloc[-1]
        rsi_now = rsi_val.iloc[-1]
        bb_upper = upper.iloc[-1]
        bb_lower = lower.iloc[-1]
        bb_mid = middle.iloc[-1]
        macd_h = macd_hist.iloc[-1]
        macd_h_prev = macd_hist.iloc[-2]
        
        direction = ''
        confidence = 0.0
        reason_parts = []
        
        # === LONG: Price at/below lower BB ===
        if price <= bb_lower and rsi_now < p['rsi_oversold']:
            direction = 'LONG'
            confidence = 55.0
            reason_parts.append(f'Price at lower BB')
            reason_parts.append(f'RSI={rsi_now:.0f} oversold')
            
            # Bullish divergence bonus
            div = detect_divergence(close, rsi_val, p['divergence_lookback'])
            if div == 'bullish':
                confidence += 20
                reason_parts.append('Bullish divergence')
            
            # MACD turning up
            if macd_h > macd_h_prev:
                confidence += 10
                reason_parts.append('MACD turning up')
            
            # Price wick rejection (long lower shadow)
            body = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
            lower_shadow = min(df['close'].iloc[-1], df['open'].iloc[-1]) - df['low'].iloc[-1]
            if lower_shadow > body * 1.5:
                confidence += 10
                reason_parts.append('Wick rejection')
        
        # === SHORT: Price at/above upper BB ===
        elif price >= bb_upper and rsi_now > p['rsi_overbought']:
            direction = 'SHORT'
            confidence = 55.0
            reason_parts.append(f'Price at upper BB')
            reason_parts.append(f'RSI={rsi_now:.0f} overbought')
            
            div = detect_divergence(close, rsi_val, p['divergence_lookback'])
            if div == 'bearish':
                confidence += 20
                reason_parts.append('Bearish divergence')
            
            if macd_h < macd_h_prev:
                confidence += 10
                reason_parts.append('MACD turning down')
            
            body = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
            upper_shadow = df['high'].iloc[-1] - max(df['close'].iloc[-1], df['open'].iloc[-1])
            if upper_shadow > body * 1.5:
                confidence += 10
                reason_parts.append('Wick rejection')
        
        if not direction or confidence < self.min_confidence:
            return None
        
        # TP = middle band, SL = ATR-based
        if direction == 'LONG':
            tp = bb_mid
            sl_dist = atr_val.iloc[-1] * p['sl_atr_multiplier']
            sl = price - sl_dist
            sl_pct = (price - sl) / price
            if sl_pct > p['sl_max_pct']:
                sl = price * (1 - p['sl_max_pct'])
        else:
            tp = bb_mid
            sl_dist = atr_val.iloc[-1] * p['sl_atr_multiplier']
            sl = price + sl_dist
            sl_pct = (sl - price) / price
            if sl_pct > p['sl_max_pct']:
                sl = price * (1 + p['sl_max_pct'])
        
        return Signal(
            symbol=symbol, direction=direction, strategy=self.name,
            confidence=min(confidence, 100),
            entry_price=price, stop_loss=sl, take_profit=tp,
            reason=' | '.join(reason_parts),
            timeframe=p['signal_timeframe']
        )
    
    def get_regime_compatibility(self, regime: str) -> float:
        scores = {
            'trending_up': 0.2, 'trending_down': 0.2,
            'ranging': 1.0, 'high_volatility': 0.4,
            'low_volatility': 0.8, 'breakout': 0.1, 'unknown': 0.4
        }
        return scores.get(regime, 0.3)
