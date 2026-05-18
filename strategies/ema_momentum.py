"""
Strategy 1: EMA Momentum Scalping
Primary strategy (60% weight) - Best for trending markets.
Uses EMA crossover + RSI + Volume confirmation.
"""
import pandas as pd
from typing import Optional
from strategies.base_strategy import BaseStrategy, Signal
from config.strategy_params import EMA_MOMENTUM
from utils.indicators import ema, rsi, volume_ma, atr


class EMAMomentumStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__('EMA Momentum Scalping', EMA_MOMENTUM)
    
    def generate_signal(self, df: pd.DataFrame, symbol: str,
                        trend_df: pd.DataFrame = None) -> Optional[Signal]:
        if len(df) < 60:
            return None
        
        p = self.params
        close = df['close']
        
        # Calculate indicators
        ema_fast = ema(close, p['ema_fast'])
        ema_slow = ema(close, p['ema_slow'])
        ema_trend_line = ema(close, p['ema_trend'])
        rsi_val = rsi(close, p['rsi_period'])
        vol_ma = volume_ma(df['volume'], p['volume_ma_period'])
        
        # Current values
        price = close.iloc[-1]
        ema_f = ema_fast.iloc[-1]
        ema_s = ema_slow.iloc[-1]
        ema_t = ema_trend_line.iloc[-1]
        rsi_now = rsi_val.iloc[-1]
        vol_now = df['volume'].iloc[-1]
        vol_avg = vol_ma.iloc[-1]
        
        # Previous values for crossover detection
        ema_f_prev = ema_fast.iloc[-2]
        ema_s_prev = ema_slow.iloc[-2]
        
        # Higher timeframe trend filter
        trend_bias = 'neutral'
        if trend_df is not None and len(trend_df) > 50:
            ht_ema9 = ema(trend_df['close'], 9).iloc[-1]
            ht_ema21 = ema(trend_df['close'], 21).iloc[-1]
            if ht_ema9 > ht_ema21:
                trend_bias = 'bullish'
            elif ht_ema9 < ht_ema21:
                trend_bias = 'bearish'
        
        # Volume filter
        vol_ok = vol_now > (vol_avg * p['volume_multiplier']) if vol_avg > 0 else True
        
        signal = None
        confidence = 0.0
        direction = ''
        reason_parts = []
        
        # === LONG CONDITIONS ===
        price_prev = close.iloc[-2]
        fresh_ema_cross_long = ema_f_prev <= ema_s_prev and ema_f > ema_s
        fresh_price_cross_long = price_prev <= ema_f_prev and price > ema_f and ema_f > ema_s
        
        if fresh_ema_cross_long or fresh_price_cross_long:
            direction = 'LONG'
            confidence = 80.0
            reason_parts.append(f'EMA{p["ema_fast"]}>EMA{p["ema_slow"]}')
            
            if fresh_ema_cross_long:
                confidence += 20
                reason_parts.append('Golden Cross')
            
            if price > ema_t:
                confidence += 10
            
            if trend_bias == 'bullish':
                confidence += 10
            elif trend_bias == 'bearish':
                confidence -= 10
        
        # === SHORT CONDITIONS ===
        fresh_ema_cross_short = ema_f_prev >= ema_s_prev and ema_f < ema_s
        fresh_price_cross_short = price_prev >= ema_f_prev and price < ema_f and ema_f < ema_s
        
        if fresh_ema_cross_short or fresh_price_cross_short:
            direction = 'SHORT'
            confidence = 80.0
            reason_parts.append(f'EMA{p["ema_fast"]}<EMA{p["ema_slow"]}')
            
            if fresh_ema_cross_short:
                confidence += 20
                reason_parts.append('Death Cross')
            
            if price < ema_t:
                confidence += 10
            
            if trend_bias == 'bearish':
                confidence += 10
            elif trend_bias == 'bullish':
                confidence -= 10
        
        if not direction or confidence < self.min_confidence:
            return None
        
        # Calculate SL/TP
        sl, tp = self._calculate_atr_stops(
            df, price, direction,
            p['tp_atr_multiplier'], p['sl_atr_multiplier'],
            p['tp_min_pct'], p['tp_max_pct'],
            p['sl_min_pct'], p['sl_max_pct']
        )
        
        return Signal(
            symbol=symbol, direction=direction, strategy=self.name,
            confidence=min(confidence, 100),
            entry_price=price, stop_loss=sl, take_profit=tp,
            reason=' | '.join(reason_parts),
            timeframe=p['signal_timeframe']
        )
    
    def get_regime_compatibility(self, regime: str) -> float:
        scores = {
            'trending_up': 1.0, 'trending_down': 1.0,
            'ranging': 0.3, 'high_volatility': 0.6,
            'low_volatility': 0.2, 'breakout': 0.5, 'unknown': 0.4
        }
        return scores.get(regime, 0.3)
