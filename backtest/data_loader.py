"""
Backtesting Data Loader - Downloads and caches historical OHLCV data.
Falls back to synthetic data generation when API is unreachable.
"""
import pandas as pd
import numpy as np
import time
from pathlib import Path
from config.settings import DATA_DIR


class DataLoader:
    """Downloads historical data from Bitget and caches as CSV."""
    
    def __init__(self):
        self.exchange = None
        self._init_exchange()
    
    def _init_exchange(self):
        """Try to initialize exchange, fallback gracefully."""
        try:
            import ccxt
            self.exchange = ccxt.bitget({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'},
                'timeout': 10000,
            })
            self.exchange.load_markets()
            print("  Connected to Bitget API")
        except Exception as e:
            print(f"  Cannot connect to Bitget API: {e}")
            print("  Using synthetic data for backtesting")
            self.exchange = None
    
    def load(self, symbol: str, timeframe: str,
             start: str, end: str) -> pd.DataFrame:
        """Load data from cache, download, or generate synthetic."""
        cache_file = self._cache_path(symbol, timeframe, start, end)
        
        if cache_file.exists():
            print(f"  Loading cached: {cache_file.name}")
            df = pd.read_csv(cache_file, parse_dates=['timestamp'], index_col='timestamp')
            return df
        
        # Try to download from exchange
        if self.exchange:
            try:
                print(f"  Downloading {symbol} {timeframe} ({start} -> {end})...")
                df = self._download(symbol, timeframe, start, end)
                if not df.empty:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    df.to_csv(cache_file)
                    print(f"  Cached: {cache_file.name} ({len(df)} candles)")
                    return df
            except Exception as e:
                print(f"  Download failed: {e}")
        
        # Fallback 1: Try yfinance for real data
        try:
            print(f"  Attempting to download {symbol} {timeframe} from Yahoo Finance...")
            import yfinance as yf
            # Map symbol
            yf_symbol = 'BTC-USD' if 'BTC' in symbol else ('ETH-USD' if 'ETH' in symbol else 'SOL-USD')
            yf_tf = {'1h': '1h', '4h': '1h', '1d': '1d'}.get(timeframe, '1d')
            
            # yfinance max historical for 1h is 730 days, so this might limit 10-year 1h data.
            # But let's fetch what we can. If timeframe is 1d we get all.
            # For backtesting 10 years, 1d is fully available. 1h is only 2 years (730 days max).
            if timeframe in ['1h', '4h']:
                # For 1h, yfinance limits to 730 days. We'll download the max possible.
                period = '730d'
                yf_df = yf.download(yf_symbol, interval='1h', period=period, progress=False)
            else:
                # For 1d, we can get full history.
                yf_df = yf.download(yf_symbol, start=start[:10], end=end[:10], interval='1d', progress=False)
            
            if not yf_df.empty:
                # Standardize columns
                df = pd.DataFrame(index=yf_df.index)
                df.index.name = 'timestamp'
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                else:
                    df.index = df.index.tz_convert('UTC')
                df['open'] = yf_df['Open'].iloc[:, 0] if isinstance(yf_df['Open'], pd.DataFrame) else yf_df['Open']
                df['high'] = yf_df['High'].iloc[:, 0] if isinstance(yf_df['High'], pd.DataFrame) else yf_df['High']
                df['low'] = yf_df['Low'].iloc[:, 0] if isinstance(yf_df['Low'], pd.DataFrame) else yf_df['Low']
                df['close'] = yf_df['Close'].iloc[:, 0] if isinstance(yf_df['Close'], pd.DataFrame) else yf_df['Close']
                df['volume'] = yf_df['Volume'].iloc[:, 0] if isinstance(yf_df['Volume'], pd.DataFrame) else yf_df['Volume']
                
                # Resample 1h to 4h if needed
                if timeframe == '4h' and yf_tf == '1h':
                    df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
                
                print(f"  ✅ Downloaded {len(df)} {timeframe} candles from yfinance")
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(cache_file)
                return df
        except Exception as e:
            print(f"  yfinance download failed: {e}")
        
        # Fallback 2: generate realistic synthetic data
        print(f"  Generating synthetic data for {symbol} {timeframe}...")
        df = self._generate_synthetic(symbol, timeframe, start, end)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file)
        print(f"  Generated: {len(df)} candles")
        return df
    
    def _download(self, symbol: str, timeframe: str,
                  start: str, end: str) -> pd.DataFrame:
        """Download OHLCV data in chunks from exchange."""
        since = int(pd.Timestamp(start, tz='UTC').timestamp() * 1000)
        end_ts = int(pd.Timestamp(end, tz='UTC').timestamp() * 1000)
        
        all_data = []
        if timeframe == '1d':
            limit = 85
        elif timeframe == '1w':
            limit = 12
        else:
            limit = 200
        
        while since < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=limit
                )
                if not ohlcv:
                    break
                all_data.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  Error: {e}, retrying...")
                time.sleep(2)
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)
        df = df[~df.index.duplicated(keep='first')]
        df.sort_index(inplace=True)
        return df
    
    def _generate_synthetic(self, symbol: str, timeframe: str,
                             start: str, end: str) -> pd.DataFrame:
        """
        Generate realistic synthetic OHLCV data based on real crypto
        market characteristics (trends, volatility clusters, mean reversion).
        """
        # Base prices for different symbols
        base_prices = {
            'BTC/USDT:USDT': 42000,
            'ETH/USDT:USDT': 2200,
            'SOL/USDT:USDT': 95,
        }
        base_volumes = {
            'BTC/USDT:USDT': 5000,
            'ETH/USDT:USDT': 50000,
            'SOL/USDT:USDT': 500000,
        }
        
        base_price = base_prices.get(symbol, 1000)
        base_volume = base_volumes.get(symbol, 10000)
        
        # Generate timestamps
        tf_map = {'1m': 'min', '5m': '5min', '15m': '15min', '1h': 'h', '4h': '4h', '1d': 'D'}
        freq = tf_map.get(timeframe, '5min')
        
        timestamps = pd.date_range(start=start, end=end, freq=freq, tz='UTC')
        n = len(timestamps)
        
        if n == 0:
            return pd.DataFrame()
        
        np.random.seed(hash(symbol) % 2**32)
        
        # Generate price series with realistic properties:
        # 1) Geometric Brownian Motion base
        # 2) Regime changes (bull/bear/sideways)
        # 3) Volatility clustering (GARCH-like)
        # 4) Mean reversion tendency
        
        # Regime changes every ~2000-5000 candles
        prices = np.zeros(n)
        prices[0] = base_price
        
        # Volatility (annualized ~60-80% for crypto)
        if timeframe == '5m':
            base_vol = 0.0008  # Per-bar volatility
        elif timeframe == '15m':
            base_vol = 0.0014
        elif timeframe == '1h':
            base_vol = 0.0028
        else:
            base_vol = 0.001
        
        # Generate regime sequence
        regime_length = np.random.randint(1000, 4000)
        current_drift = np.random.choice([-0.00002, 0, 0.00003])
        vol_multiplier = 1.0
        
        for i in range(1, n):
            # Regime change
            if i % regime_length == 0:
                regime_length = np.random.randint(1000, 4000)
                current_drift = np.random.choice(
                    [-0.00004, -0.00002, 0, 0.00001, 0.00003, 0.00005],
                    p=[0.1, 0.15, 0.2, 0.2, 0.2, 0.15]
                )
                vol_multiplier = np.random.uniform(0.5, 2.0)
            
            # GARCH-like vol clustering
            if np.random.random() < 0.02:
                vol_multiplier = np.random.uniform(1.5, 3.0)
            elif np.random.random() < 0.05:
                vol_multiplier = max(0.5, vol_multiplier * 0.95)
            
            vol = base_vol * vol_multiplier
            shock = np.random.normal(current_drift, vol)
            
            # Occasional larger moves (fat tails)
            if np.random.random() < 0.005:
                shock *= np.random.uniform(3, 8) * np.random.choice([-1, 1])
            
            prices[i] = prices[i-1] * (1 + shock)
            prices[i] = max(prices[i], base_price * 0.1)  # Floor
        
        # Generate OHLCV from close prices
        opens = np.roll(prices, 1)
        opens[0] = prices[0]
        
        # Add intra-bar volatility for high/low
        bar_range = np.abs(np.random.normal(0, base_vol * 0.7, n))
        highs = np.maximum(opens, prices) * (1 + bar_range)
        lows = np.minimum(opens, prices) * (1 - bar_range)
        
        # Volume with correlation to price movement
        price_changes = np.abs(np.diff(prices, prepend=prices[0]) / prices)
        volumes = base_volume * (1 + price_changes * 50) * np.random.lognormal(0, 0.5, n)
        
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': volumes,
        }, index=timestamps[:n])
        
        df.index.name = 'timestamp'
        return df
    
    def _cache_path(self, symbol: str, timeframe: str,
                    start: str, end: str) -> Path:
        safe_symbol = symbol.replace('/', '_').replace(':', '_')
        filename = f"{safe_symbol}_{timeframe}_{start}_{end}.csv"
        return DATA_DIR / filename
