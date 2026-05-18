"""
Strategy Selector - Market regime detection and strategy routing.
Automatically picks the best strategy for current market conditions.
"""
import pandas as pd
from typing import Optional, List
from strategies.base_strategy import Signal
from strategies.ema_momentum import EMAMomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy
from strategies.n_pattern import NPatternBreakout
from utils.indicators import classify_market_regime
from utils.logger import trade_logger


class StrategySelector:
    """Routes market data to the most appropriate strategy based on regime."""
    
    def __init__(self):
        self.strategies = [
            EMAMomentumStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
            NPatternBreakout(params=__import__('config.strategy_params', fromlist=['N_PATTERN']).N_PATTERN)
        ]
        self.current_regime = 'unknown'
    
    def get_best_signal(self, symbol: str, dfs: dict,
                        trend_df: pd.DataFrame = None) -> Optional[Signal]:
        """
        Evaluate all strategies and return the best signal.
        
        Args:
            symbol: Trading pair
            dfs: Dict of {timeframe: DataFrame}
            trend_df: Higher timeframe data for trend filter
        """
        # Detect market regime from 5m data
        df_5m = dfs.get('5m')
        if df_5m is None:
            df_5m = dfs.get('15m')
        if df_5m is not None and len(df_5m) > 50:
            self.current_regime = classify_market_regime(df_5m)
        
        best_signal = None
        best_score = 0
        
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            
            # Get the right timeframe data for this strategy
            tf = strategy.params.get('signal_timeframe', '5m')
            df = dfs.get(tf, df_5m)
            if df is None or df.empty:
                continue
            
            # Regime compatibility score
            regime_score = strategy.get_regime_compatibility(self.current_regime)
            
            # Generate signal
            signal = strategy.generate_signal(df, symbol, trend_df)
            if signal is None or not signal.is_valid:
                continue
            
            # Weighted score = confidence * regime_compatibility * strategy_weight
            total_score = signal.confidence * regime_score * strategy.weight
            
            if total_score > best_score and signal.confidence >= strategy.min_confidence:
                best_score = total_score
                best_signal = signal
        
        if best_signal:
            trade_logger.log_signal(
                symbol, best_signal.direction, best_signal.strategy,
                best_signal.confidence, best_signal.entry_price
            )
            trade_logger.logger.info(
                f"🌍 Market Regime: {self.current_regime} | "
                f"Score: {best_score:.1f}"
            )
        
        return best_signal
