import pandas as pd
import numpy as np
from typing import Optional
from strategies.base_strategy import BaseStrategy, Signal
from utils.indicators import atr

class NPatternBreakout(BaseStrategy):
    """
    N-Pattern (Measured Move) Breakout Strategy.
    Detects an A-B-C pullback structure and buys the breakout of B.
    Maintains a strict Risk/Reward ratio defined by rr_ratio (e.g. 1:10).
    """
    
    def __init__(self, params: dict):
        super().__init__('N-Pattern Breakout', params)
    
    def get_regime_compatibility(self, regime: str) -> float:
        """Best in trending markets."""
        if regime in ['bull_trend', 'bear_trend']:
            return 1.0
        elif regime in ['bull_volatile', 'bear_volatile']:
            return 0.7
        return 0.2
    
    def generate_signal(self, df: pd.DataFrame, symbol: str,
                        trend_df: pd.DataFrame = None) -> Optional[Signal]:
        if len(df) < 50:
            return None
            
        p = self.params
        left = p.get('lookback_left', 15)
        right = p.get('lookback_right', 10)
        use_macro = p.get('use_macro_filter', False)
        ema_period = p.get('macro_ema_period', 200)
        
        # Check macro trend if enabled
        is_bull_macro = True
        is_bear_macro = True
        if use_macro and trend_df is not None and len(trend_df) >= ema_period:
            # We can't use talib if not installed, so just use pandas ema
            htf_ema = trend_df['close'].ewm(span=ema_period, adjust=False).mean()
            current_htf_close = trend_df['close'].iloc[-1]
            current_ema = htf_ema.iloc[-1]
            
            is_bull_macro = current_htf_close > current_ema
            is_bear_macro = current_htf_close < current_ema
        
        # Calculate pivots using rolling window
        # For a high pivot, the high must be the maximum over the window (left + right)
        highs = df['high'].values
        lows = df['low'].values
        
        peaks = []
        troughs = []
        
        for i in range(len(highs) - 50, len(highs) - right):
            if highs[i] == np.max(highs[i-left:i+right+1]):
                peaks.append((i, highs[i]))
            if lows[i] == np.min(lows[i-left:i+right+1]):
                troughs.append((i, lows[i]))
        
        if len(peaks) < 1 or len(troughs) < 2:
            return None
        
        # Get current price
        price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        
        # Look for LONG N-Pattern (Bullish Measured Move)
        # Structure: Trough (A) -> Peak (B) -> Trough (C)
        # C must be > A, and C must be < B.
        # We need the most recent C to be after B, and B to be after A.
        
        latest_c_idx, c_val = troughs[-1]
        
        # Find B (the peak just before C)
        valid_b = [p for p in peaks if p[0] < latest_c_idx]
        if not valid_b:
            return None
        latest_b_idx, b_val = valid_b[-1]
        
        # Find A (the trough just before B)
        valid_a = [t for t in troughs if t[0] < latest_b_idx]
        if not valid_a:
            return None
        latest_a_idx, a_val = valid_a[-1]
        
        # Check N-Pattern rules
        if c_val <= a_val:
            return None  # C must be a Higher Low
        
        impulse = b_val - a_val
        retrace = b_val - c_val
        if impulse <= 0:
            return None
            
        retrace_pct = retrace / impulse
        if not (p['min_retrace_pct'] <= retrace_pct <= p['max_retrace_pct']):
            return None # Retracement is too shallow or too deep
            
        # Is the pattern still active? (We haven't broken below C)
        if df['low'].iloc[latest_c_idx:].min() < c_val:
            return None
            
        # --- LONG TRIGGER (Stop Limit simulation) ---
        # Did we just break above B?
        if prev_price <= b_val and price > b_val:
            if not is_bull_macro:
                return None  # Rejected by macro filter
                
            rr_ratio = p.get('rr_ratio', 1.0)
            sl_dist = price - c_val
            sl = c_val
            tp = price + (sl_dist * rr_ratio)
            
            return Signal(
                symbol=symbol,
                direction='LONG',
                strategy=self.name,
                confidence=85.0,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                reason=f'N-Pattern Breakout B=${b_val:.0f}',
                timeframe=p['signal_timeframe']
            )
            
        # Look for SHORT N-Pattern (Bearish Measured Move)
        # Structure: Peak (A) -> Trough (B) -> Peak (C)
        latest_c_peak_idx, c_peak_val = peaks[-1]
        
        valid_b_trough = [t for t in troughs if t[0] < latest_c_peak_idx]
        if not valid_b_trough:
            return None
        latest_b_trough_idx, b_trough_val = valid_b_trough[-1]
        
        valid_a_peak = [p for p in peaks if p[0] < latest_b_trough_idx]
        if not valid_a_peak:
            return None
        latest_a_peak_idx, a_peak_val = valid_a_peak[-1]
        
        # Check Short N-Pattern rules
        if c_peak_val >= a_peak_val:
            return None # C must be a Lower High
            
        impulse_short = a_peak_val - b_trough_val
        retrace_short = c_peak_val - b_trough_val
        if impulse_short <= 0:
            return None
            
        retrace_short_pct = retrace_short / impulse_short
        if not (p['min_retrace_pct'] <= retrace_short_pct <= p['max_retrace_pct']):
            return None
            
        if df['high'].iloc[latest_c_peak_idx:].max() > c_peak_val:
            return None # Pattern invalidated
            
        # --- SHORT TRIGGER ---
        if prev_price >= b_trough_val and price < b_trough_val:
            if not is_bear_macro:
                return None  # Rejected by macro filter
                
            rr_ratio = p.get('rr_ratio', 1.0)
            sl_dist = c_peak_val - price
            sl = c_peak_val
            tp = price - (sl_dist * rr_ratio)
            
            return Signal(
                symbol=symbol,
                direction='SHORT',
                strategy=self.name,
                confidence=85.0,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                reason=f'N-Pattern Breakdown B=${b_trough_val:.0f}',
                timeframe=p['signal_timeframe']
            )

        return None
