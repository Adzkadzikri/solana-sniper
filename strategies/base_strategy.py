"""
Abstract base class for all trading strategies.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class Signal:
    """Represents a trading signal from a strategy."""
    symbol: str = ''
    direction: str = ''       # 'LONG' or 'SHORT'
    strategy: str = ''
    confidence: float = 0.0   # 0-100
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    leverage: int = 1
    reason: str = ''
    timeframe: str = ''
    
    @property
    def is_valid(self) -> bool:
        return (self.direction in ('LONG', 'SHORT') and 
                self.confidence > 0 and self.entry_price > 0)


class BaseStrategy(ABC):
    """Abstract base class that all strategies must implement."""
    
    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params
        self.enabled = params.get('enabled', True)
        self.weight = params.get('weight', 0.5)
        self.min_confidence = params.get('min_confidence', 60)
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, symbol: str,
                        trend_df: pd.DataFrame = None) -> Optional[Signal]:
        """
        Generate a trading signal from market data.
        
        Args:
            df: Primary timeframe OHLCV DataFrame
            symbol: Trading pair symbol
            trend_df: Higher timeframe DataFrame for trend filter
            
        Returns:
            Signal object or None if no signal
        """
        pass
    
    @abstractmethod
    def get_regime_compatibility(self, regime: str) -> float:
        """
        How well does this strategy perform in the given market regime?
        
        Returns:
            Compatibility score 0.0 - 1.0
        """
        pass
    
    def _calculate_atr_stops(self, df: pd.DataFrame, entry_price: float,
                              direction: str, tp_mult: float, sl_mult: float,
                              tp_min: float, tp_max: float,
                              sl_min: float, sl_max: float) -> tuple:
        """Calculate ATR-based SL and TP with min/max bounds."""
        from utils.indicators import atr
        
        atr_val = atr(df['high'], df['low'], df['close'], 14).iloc[-1]
        
        if direction == 'LONG':
            raw_tp = entry_price + (atr_val * tp_mult)
            raw_sl = entry_price - (atr_val * sl_mult)
            tp_pct = (raw_tp - entry_price) / entry_price
            sl_pct = (entry_price - raw_sl) / entry_price
        else:
            raw_tp = entry_price - (atr_val * tp_mult)
            raw_sl = entry_price + (atr_val * sl_mult)
            tp_pct = (entry_price - raw_tp) / entry_price
            sl_pct = (raw_sl - entry_price) / entry_price
        
        # Clamp to bounds
        tp_pct = max(tp_min, min(tp_max, tp_pct))
        sl_pct = max(sl_min, min(sl_max, sl_pct))
        
        if direction == 'LONG':
            tp = entry_price * (1 + tp_pct)
            sl = entry_price * (1 - sl_pct)
        else:
            tp = entry_price * (1 - tp_pct)
            sl = entry_price * (1 + sl_pct)
        
        return sl, tp
