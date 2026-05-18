"""
Strategy 3: Breakout Momentum
Tertiary strategy (15% weight) - Best after consolidation.
"""
import pandas as pd
from typing import Optional
from strategies.base_strategy import BaseStrategy, Signal
from config.strategy_params import BREAKOUT
from utils.indicators import (
    atr, volume_ma, volume_surge, find_support_resistance,
    bollinger_bands, bollinger_band_width, ema
)


class BreakoutStrategy(BaseStrategy):
    
    def __init__(self):
        super().__init__('Breakout Momentum', BREAKOUT)
    
    def generate_signal(self, df: pd.DataFrame, symbol: str,
                        trend_df: pd.DataFrame = None) -> Optional[Signal]:
        if len(df) < 60:
            return None
        
        p = self.params
        close = df['close']
        price = close.iloc[-1]
        
        # Find S/R levels
        sr = find_support_resistance(
            df['high'], df['low'], close,
            p['sr_lookback'], p['sr_tolerance']
        )
        
        resistances = sr['resistance']
        supports = sr['support']
        
        if not resistances and not supports:
            return None
        
        # Volume surge check
        vol_surge = volume_surge(
            df['volume'], 20, p['volume_surge_multiplier']
        )
        has_volume = vol_surge.iloc[-1]
        
        # ATR for measured move
        atr_val = atr(df['high'], df['low'], close, p['atr_period']).iloc[-1]
        
        direction = ''
        confidence = 0.0
        reason_parts = []
        breakout_level = 0
        
        # === LONG BREAKOUT: Price breaks above resistance ===
        if resistances:
            nearest_res = resistances[0]
            breakout_pct = (price - nearest_res) / nearest_res
            
            if breakout_pct > p['breakout_threshold']:
                # Confirm: previous candles were below
                prev_below = all(
                    close.iloc[-(i+2)] < nearest_res 
                    for i in range(min(p['confirmation_candles'], len(close)-2))
                )
                
                if prev_below:
                    direction = 'LONG'
                    confidence = 55.0
                    breakout_level = nearest_res
                    reason_parts.append(f'Break above R={nearest_res:.0f}')
                    
                    if has_volume:
                        confidence += 20
                        reason_parts.append('Volume surge')
                    
                    # BB squeeze release
                    upper, middle, lower = bollinger_bands(close, 20, 2.0)
                    bbw = bollinger_band_width(upper, lower, middle)
                    if len(bbw) > 5 and bbw.iloc[-5:].mean() < 0.03:
                        confidence += 15
                        reason_parts.append('BB squeeze breakout')
                    
                    # Strong candle body
                    body_pct = abs(df['close'].iloc[-1] - df['open'].iloc[-1]) / price
                    if body_pct > 0.005:
                        confidence += 10
                        reason_parts.append('Strong candle')
        
        # === SHORT BREAKOUT: Price breaks below support ===
        if not direction and supports:
            nearest_sup = supports[0]
            breakout_pct = (nearest_sup - price) / nearest_sup
            
            if breakout_pct > p['breakout_threshold']:
                prev_above = all(
                    close.iloc[-(i+2)] > nearest_sup 
                    for i in range(min(p['confirmation_candles'], len(close)-2))
                )
                
                if prev_above:
                    direction = 'SHORT'
                    confidence = 55.0
                    breakout_level = nearest_sup
                    reason_parts.append(f'Break below S={nearest_sup:.0f}')
                    
                    if has_volume:
                        confidence += 20
                        reason_parts.append('Volume surge')
                    
                    upper, middle, lower = bollinger_bands(close, 20, 2.0)
                    bbw = bollinger_band_width(upper, lower, middle)
                    if len(bbw) > 5 and bbw.iloc[-5:].mean() < 0.03:
                        confidence += 15
                        reason_parts.append('BB squeeze breakout')
                    
                    body_pct = abs(df['close'].iloc[-1] - df['open'].iloc[-1]) / price
                    if body_pct > 0.005:
                        confidence += 10
                        reason_parts.append('Strong candle')
        
        if not direction or confidence < self.min_confidence:
            return None
        
        # Calculate SL/TP - measured move
        if direction == 'LONG':
            sl = breakout_level * (1 - p['sl_reentry_pct'])
            tp = price + (atr_val * p['tp_atr_multiplier'])
        else:
            sl = breakout_level * (1 + p['sl_reentry_pct'])
            tp = price - (atr_val * p['tp_atr_multiplier'])
        
        return Signal(
            symbol=symbol, direction=direction, strategy=self.name,
            confidence=min(confidence, 100),
            entry_price=price, stop_loss=sl, take_profit=tp,
            reason=' | '.join(reason_parts),
            timeframe=p['signal_timeframe']
        )
    
    def get_regime_compatibility(self, regime: str) -> float:
        scores = {
            'trending_up': 0.5, 'trending_down': 0.5,
            'ranging': 0.2, 'high_volatility': 0.7,
            'low_volatility': 0.3, 'breakout': 1.0, 'unknown': 0.3
        }
        return scores.get(regime, 0.3)
