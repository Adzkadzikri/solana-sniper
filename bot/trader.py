"""
Live Trading Bot - 24/7 automated trading loop.
"""
import time
import signal
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.exchange import ExchangeClient
from core.data_feed import DataFeed
from core.order_manager import OrderManager
from strategies.strategy_selector import StrategySelector
from money_management.position_sizer import PositionSizer
from money_management.risk_manager import RiskManager
from config.settings import (
    TRADING_PAIRS, TIMEFRAMES, INITIAL_CAPITAL, 
    PAPER_TRADING, TARGET_CAPITAL, CANDLE_LIMIT
)
from config.strategy_params import TRAILING_STOP
from utils.logger import trade_logger
from utils.helpers import timeframe_to_seconds


class Trader:
    """Main trading bot that runs 24/7."""
    
    def __init__(self):
        self.running = False
        self.exchange = ExchangeClient()
        self.data_feed = DataFeed(self.exchange)
        self.order_manager = OrderManager(self.exchange)
        self.selector = StrategySelector()
        self.sizer = PositionSizer(INITIAL_CAPITAL)
        self.risk_manager = RiskManager(self.sizer)
        
        # State
        self.cycle_count = 0
        self.last_signal_time = {}
        self.signal_cooldown = 300  # 5 min between signals per symbol
        
        # Graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
    
    def start(self):
        """Start the trading bot."""
        trade_logger.log_bot_status('START', 
            f'Capital: ${INITIAL_CAPITAL} | Paper: {PAPER_TRADING} | '
            f'Pairs: {len(TRADING_PAIRS)} | Target: ${TARGET_CAPITAL}')
        
        # Initialize exchange
        self.exchange.initialize()
        
        # Setup margin mode and leverage for all pairs
        for symbol in TRADING_PAIRS:
            self.exchange.set_margin_mode(symbol)
        
        # Load initial data
        timeframe_list = list(set(TIMEFRAMES.values()))
        self.data_feed.initialize_all(TRADING_PAIRS, timeframe_list, CANDLE_LIMIT)
        
        # Update equity from exchange
        if not PAPER_TRADING:
            balance = self.exchange.get_balance()
            if balance['total'] > 0:
                self.sizer.update_equity(balance['total'])
                trade_logger.log_equity(
                    balance['total'], self.sizer.peak_equity,
                    self.sizer.get_drawdown() * 100,
                    self.sizer.current_mode,
                    self.sizer.current_tier['description'] if self.sizer.current_tier else 'N/A'
                )
        
        trade_logger.log_bot_status('START', '🤖 Bot is now running!')
        
        self.running = True
        self._main_loop()
    
    def _main_loop(self):
        """Main trading loop."""
        cycle_interval = timeframe_to_seconds(TIMEFRAMES['entry'])  # 5m = 300s
        
        while self.running:
            try:
                self.cycle_count += 1
                cycle_start = time.time()
                
                # 1) Refresh market data
                self._refresh_data()
                
                # 2) Update equity
                self._update_equity()
                
                # 3) Check & manage existing positions
                self._manage_positions()
                
                # 4) Look for new trade signals
                self._scan_for_signals()
                
                # 5) Check if target reached
                if self.sizer.equity >= TARGET_CAPITAL:
                    trade_logger.log_bot_status('STOP',
                        f'🎯 TARGET REACHED! Equity: ${self.sizer.equity:.2f}')
                    self.running = False
                    break
                
                # 6) Log status periodically
                if self.cycle_count % 12 == 0:  # Every hour (12 * 5min)
                    trade_logger.log_equity(
                        self.sizer.equity, self.sizer.peak_equity,
                        self.sizer.get_drawdown() * 100,
                        self.sizer.current_mode,
                        self.sizer.current_tier['description'] if self.sizer.current_tier else 'N/A'
                    )
                
                # Wait for next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(10, cycle_interval - elapsed)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                self._shutdown()
                break
            except Exception as e:
                trade_logger.logger.error(f"💥 Main loop error: {e}")
                time.sleep(30)  # Wait before retry
    
    def _refresh_data(self):
        """Refresh candle data for all pairs and timeframes."""
        for symbol in TRADING_PAIRS:
            for tf_name, tf in TIMEFRAMES.items():
                try:
                    self.data_feed.get_candles(symbol, tf, CANDLE_LIMIT)
                except Exception as e:
                    trade_logger.logger.debug(f"Data refresh error {symbol} {tf}: {e}")
    
    def _update_equity(self):
        """Update equity from exchange balance + unrealized P/L."""
        if PAPER_TRADING:
            return
        
        try:
            balance = self.exchange.get_balance()
            positions = self.exchange.get_positions()
            
            total = balance['total']
            for pos in positions:
                total += pos.get('unrealized_pnl', 0)
            
            if total > 0:
                self.sizer.update_equity(total)
        except Exception:
            pass
    
    def _manage_positions(self):
        """Manage existing positions - trailing stops, etc."""
        if not self.order_manager.active_trades:
            return
        
        current_prices = {}
        for symbol in TRADING_PAIRS:
            price = self.data_feed.get_latest_price(symbol)
            if price > 0:
                current_prices[symbol] = price
        
        # Update trailing stops
        if TRAILING_STOP.get('enabled'):
            self.order_manager.update_trailing_stops(
                current_prices,
                TRAILING_STOP.get('trail_distance_pct', 0.003)
            )
    
    def _scan_for_signals(self):
        """Scan all pairs for trading signals."""
        if self.sizer.trading_paused:
            return
        
        for symbol in TRADING_PAIRS:
            # Signal cooldown check
            last = self.last_signal_time.get(symbol, 0)
            if time.time() - last < self.signal_cooldown:
                continue
            
            # Skip if already have position
            if symbol in self.order_manager.get_active_symbols():
                continue
            
            # Build multi-timeframe data
            dfs = {}
            for tf_name, tf in TIMEFRAMES.items():
                df = self.data_feed.candles.get(symbol, {}).get(tf)
                if df is not None and not df.empty:
                    dfs[tf] = df
            
            if not dfs:
                continue
            
            # Get signal
            trend_df = dfs.get('1h')
            if trend_df is None:
                trend_df = dfs.get('15m')
            signal = self.selector.get_best_signal(symbol, dfs, trend_df)
            
            if signal and signal.is_valid:
                self._execute_signal(signal)
                self.last_signal_time[symbol] = time.time()
    
    def _execute_signal(self, signal):
        """Execute a trading signal after risk checks."""
        # Position sizing
        params = self.sizer.get_position_params(
            signal.entry_price, signal.stop_loss, signal.confidence
        )
        
        if not params.get('can_trade'):
            trade_logger.logger.info(
                f"⏭️ Signal skipped: {params.get('reason', 'Unknown')}")
            return
        
        # Risk check
        current_positions = [
            {'symbol': t.symbol, 'margin': t.margin_used}
            for t in self.order_manager.active_trades.values()
        ]
        
        funding_rate = 0
        try:
            funding_rate = self.exchange.fetch_funding_rate(signal.symbol)
        except Exception:
            pass
        
        risk_check = self.risk_manager.can_open_trade(
            signal.symbol, signal.direction, params['margin'],
            params['leverage'], signal.entry_price,
            current_positions, funding_rate
        )
        
        if not risk_check['allowed']:
            trade_logger.logger.info(
                f"🛡️ Trade blocked: {risk_check['reason']}")
            return
        
        # Execute trade
        trade = self.order_manager.open_trade(
            symbol=signal.symbol,
            direction=signal.direction,
            size=params['size'],
            leverage=params['leverage'],
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy=signal.strategy,
            confidence=signal.confidence,
        )
        
        if trade:
            trade_logger.log_entry(
                signal.symbol, signal.direction, params['size'],
                signal.entry_price, params['leverage'],
                signal.stop_loss, signal.take_profit
            )
    
    def _shutdown(self, *args):
        """Graceful shutdown."""
        trade_logger.log_bot_status('STOP', 'Shutting down...')
        self.running = False
    
    def get_status(self) -> dict:
        """Get current bot status for dashboard."""
        return {
            'running': self.running,
            'cycle': self.cycle_count,
            'equity': self.sizer.equity,
            'peak_equity': self.sizer.peak_equity,
            'drawdown': self.sizer.get_drawdown() * 100,
            'mode': self.sizer.current_mode,
            'tier': self.sizer.current_tier['description'] if self.sizer.current_tier else 'N/A',
            'active_positions': self.order_manager.get_position_count(),
            'total_trades': self.order_manager.total_trades,
            'win_rate': (self.order_manager.winning_trades / 
                        max(1, self.order_manager.total_trades) * 100),
            'regime': self.selector.current_regime,
            'paper_trading': PAPER_TRADING,
            'stats': self.order_manager.get_stats(),
            'risk': self.risk_manager.get_status(),
        }
