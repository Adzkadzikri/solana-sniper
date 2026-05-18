"""
Market data feed management.
Handles fetching, caching, and streaming OHLCV data.
"""
import pandas as pd
import numpy as np
import time
from typing import Dict, Optional
from utils.logger import trade_logger
from utils.helpers import timeframe_to_ms


class DataFeed:
    """Manages market data across multiple symbols and timeframes."""
    
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        self.candles: Dict[str, Dict[str, pd.DataFrame]] = {}
        self._last_update: Dict[str, Dict[str, float]] = {}
    
    def fetch_candles(self, symbol: str, timeframe: str, 
                      limit: int = 500) -> pd.DataFrame:
        """Fetch OHLCV candles and return as DataFrame."""
        raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not raw:
            return pd.DataFrame()
        
        df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)
        
        # Cache
        if symbol not in self.candles:
            self.candles[symbol] = {}
        self.candles[symbol][timeframe] = df
        
        if symbol not in self._last_update:
            self._last_update[symbol] = {}
        self._last_update[symbol][timeframe] = time.time()
        
        return df
    
    def get_candles(self, symbol: str, timeframe: str, 
                    limit: int = 500) -> pd.DataFrame:
        """Get candles from cache or fetch if stale."""
        tf_ms = timeframe_to_ms(timeframe)
        stale_threshold = tf_ms / 1000 * 0.8
        
        last = self._last_update.get(symbol, {}).get(timeframe, 0)
        if time.time() - last > stale_threshold:
            return self.fetch_candles(symbol, timeframe, limit)
        
        cached = self.candles.get(symbol, {}).get(timeframe)
        if cached is not None and not cached.empty:
            return cached
        return self.fetch_candles(symbol, timeframe, limit)
    
    def update_candle(self, symbol: str, timeframe: str,
                      candle: list):
        """Update the latest candle from real-time data."""
        if symbol not in self.candles or timeframe not in self.candles[symbol]:
            return
        
        df = self.candles[symbol][timeframe]
        ts = pd.Timestamp(candle[0], unit='ms', tz='UTC')
        new_row = pd.DataFrame(
            [[candle[1], candle[2], candle[3], candle[4], candle[5]]],
            columns=['open', 'high', 'low', 'close', 'volume'],
            index=pd.DatetimeIndex([ts], name='timestamp')
        )
        
        if ts in df.index:
            df.loc[ts] = new_row.iloc[0]
        else:
            self.candles[symbol][timeframe] = pd.concat([df, new_row]).tail(500)
        
        self._last_update[symbol][timeframe] = time.time()
    
    def get_latest_price(self, symbol: str) -> float:
        """Get the latest close price for a symbol."""
        df = self.candles.get(symbol, {}).get('5m')
        if df is not None and not df.empty:
            return float(df['close'].iloc[-1])
        
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker.get('last', 0)
    
    def initialize_all(self, symbols: list, timeframes: list, limit: int = 500):
        """Pre-fetch candles for all symbols and timeframes."""
        total = len(symbols) * len(timeframes)
        count = 0
        for symbol in symbols:
            for tf in timeframes:
                count += 1
                trade_logger.logger.info(
                    f"📊 Loading data [{count}/{total}]: {symbol} {tf}"
                )
                self.fetch_candles(symbol, tf, limit)
                time.sleep(0.5)  # Rate limiting
