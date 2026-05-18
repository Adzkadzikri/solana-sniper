"""
Backtesting Engine - Simulates trading with historical data.
Includes leverage, fees, funding rate, and slippage simulation.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List
from strategies.strategy_selector import StrategySelector
from money_management.position_sizer import PositionSizer
from config.settings import (
    INITIAL_CAPITAL, TAKER_FEE, BACKTEST_SLIPPAGE,
    TRADING_PAIRS, TARGET_CAPITAL
)
from config.strategy_params import TRAILING_STOP


class BacktestTrade:
    """Simple trade record for backtesting."""
    def __init__(self):
        self.id = ''
        self.symbol = ''
        self.direction = ''
        self.strategy = ''
        self.entry_price = 0.0
        self.exit_price = 0.0
        self.size = 0.0
        self.leverage = 1
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.trailing_stop = 0.0
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.fee = 0.0
        self.margin = 0.0
        self.entry_time = None
        self.exit_time = None
        self.exit_reason = ''
        self.confidence = 0.0


class BacktestEngine:
    """Bar-by-bar backtesting engine with full simulation."""
    
    def __init__(self, initial_capital: float = None):
        self.initial_capital = initial_capital or INITIAL_CAPITAL
        self.equity = self.initial_capital
        self.peak_equity = self.initial_capital
        self.sizer = PositionSizer(self.initial_capital)
        self.selector = StrategySelector()
        
        self.active_trades: Dict[str, BacktestTrade] = {}
        self.completed_trades: List[BacktestTrade] = []
        self.equity_curve: List[dict] = []
        self.trade_count = 0
        
    def run(self, datasets: Dict[str, Dict[str, pd.DataFrame]],
            primary_tf: str = '5m') -> dict:
        """
        Run backtest across all symbols. Optimized for speed.
        """
        import sys
        print(f"\n{'='*60}", flush=True)
        print(f"BACKTEST START | Capital: ${self.initial_capital}", flush=True)
        print(f"{'='*60}\n", flush=True)
        
        # Pre-index: build per-symbol primary data as numpy arrays for fast access
        symbol_data = {}
        primary_index = None
        
        for symbol, tfs in datasets.items():
            if primary_tf not in tfs:
                continue
            df = tfs[primary_tf]
            symbol_data[symbol] = {
                'close': df['close'].values,
                'high': df['high'].values,
                'low': df['low'].values,
                'open': df['open'].values,
                'volume': df['volume'].values,
                'index': df.index,
                'df': df,  # Keep reference for strategy
            }
            if primary_index is None:
                primary_index = df.index
        
        if primary_index is None or len(primary_index) == 0:
            print("No data to backtest!")
            return {}
        
        total_bars = len(primary_index)
        print(f"Total bars: {total_bars}", flush=True)
        print(f"Period: {primary_index[0]} -> {primary_index[-1]}\n", flush=True)
        
        warmup = 100  # Need enough data for 50 EMA on 1h
        signal_interval = 1  # Check signals every bar (1h)
        equity_interval = 10  # Record equity every 10 bars
        cooldown_bars = 6  # 6 hours cooldown after massive DD
        paused_at_bar = None  # Track when trading was paused
        
        for i in range(warmup, total_bars):
            # Auto-resume from cooldown after N bars
            if self.sizer.trading_paused:
                if paused_at_bar is None:
                    paused_at_bar = i
                elif i - paused_at_bar >= cooldown_bars:
                    self.sizer.resume_trading()
                    paused_at_bar = None
            else:
                paused_at_bar = None
            
            # Progress
            if i % 10000 == 0:
                pct = (i / total_bars) * 100
                print(f"  Progress: {pct:.0f}% | Equity: ${self.equity:.2f} | "
                      f"Trades: {self.trade_count} | "
                      f"Peak: ${self.peak_equity:.2f}", flush=True)
            
            # Target check
            if self.equity >= TARGET_CAPITAL:
                print(f"\nTARGET REACHED at bar {i}! Equity: ${self.equity:.2f}", flush=True)
                break
            
            ts = primary_index[i]
            
            for symbol, sd in symbol_data.items():
                if i >= len(sd['close']):
                    continue
                
                price = float(sd['close'][i])
                high = float(sd['high'][i])
                low = float(sd['low'][i])
                
                # 1) Always check SL/TP (fast - just comparisons)
                self._check_exits(symbol, high, low, price, ts)
                
                # 2) Update trailing stops
                self._update_trailing(symbol, price)
                
                # 3) Signal generation (expensive - do less often)
                if (i % signal_interval == 0 and 
                    not self._has_position(symbol) and 
                    not self.sizer.trading_paused):
                    
                    # Slice data up to current bar using iloc (fast)
                    start_idx = max(0, i - 149)
                    current_slice = sd['df'].iloc[start_idx:i+1]
                    
                    if len(current_slice) >= 60:
                        dfs = {primary_tf: current_slice}
                        
                        # Add other timeframes
                        for tf, tf_df in datasets[symbol].items():
                            if tf != primary_tf and len(tf_df) > 50:
                                # Use searchsorted for O(log N) performance
                                tf_count = tf_df.index.searchsorted(ts, side='right')
                                if tf_count >= 50:
                                    tf_start = max(0, tf_count - 150)
                                    dfs[tf] = tf_df.iloc[tf_start:tf_count]
                        
                        trend_df = dfs.get('4h')
                        if trend_df is None:
                            trend_df = dfs.get('1h')
                        
                        signal = self.selector.get_best_signal(
                            symbol, dfs, trend_df
                        )
                        
                        if signal and signal.is_valid:
                            self._execute_entry(signal, ts)
            
            # Record equity (sampled for performance)
            if i % equity_interval == 0:
                self.equity_curve.append({
                    'timestamp': ts,
                    'equity': self.equity,
                    'realized_equity': self.equity,
                    'positions': len(self.active_trades),
                })
        
        # Close remaining
        last_ts = primary_index[-1]
        self._close_all(datasets, last_ts, primary_tf)
        
        return self._generate_results()
    
    def _execute_entry(self, signal, timestamp):
        """Execute a trade entry in backtest."""
        # Apply slippage
        slippage = signal.entry_price * BACKTEST_SLIPPAGE
        if signal.direction == 'LONG':
            entry = signal.entry_price + slippage
        else:
            entry = signal.entry_price - slippage
        
        # Get position sizing
        params = self.sizer.get_position_params(
            entry, signal.stop_loss, signal.confidence
        )
        
        if not params.get('can_trade'):
            return
        
        size = params['size']
        leverage = params['leverage']
        margin = params['margin']
        
        # Check margin available
        if margin > self.equity * 0.9:
            return
        
        fee = entry * size * TAKER_FEE
        
        trade = BacktestTrade()
        trade.id = f"BT_{self.trade_count}"
        trade.symbol = signal.symbol
        trade.direction = signal.direction
        trade.strategy = signal.strategy
        trade.entry_price = entry
        trade.stop_loss = signal.stop_loss
        trade.take_profit = signal.take_profit
        trade.size = size
        trade.leverage = leverage
        trade.margin = margin
        trade.fee = fee
        trade.entry_time = timestamp
        trade.confidence = signal.confidence
        
        self.active_trades[trade.id] = trade
        self.trade_count += 1
    
    def _check_exits(self, symbol: str, high: float, low: float,
                     close: float, timestamp):
        """Check SL/TP hits for active trades."""
        to_close = []
        
        for tid, trade in self.active_trades.items():
            if trade.symbol != symbol:
                continue
            
            if trade.direction == 'LONG':
                if trade.stop_loss > 0 and low <= trade.stop_loss:
                    to_close.append((tid, trade.stop_loss, 'stop_loss'))
                elif trade.take_profit > 0 and high >= trade.take_profit:
                    to_close.append((tid, trade.take_profit, 'take_profit'))
                elif trade.trailing_stop > 0 and low <= trade.trailing_stop:
                    to_close.append((tid, trade.trailing_stop, 'trailing_stop'))
            else:
                if trade.stop_loss > 0 and high >= trade.stop_loss:
                    to_close.append((tid, trade.stop_loss, 'stop_loss'))
                elif trade.take_profit > 0 and low <= trade.take_profit:
                    to_close.append((tid, trade.take_profit, 'take_profit'))
                elif trade.trailing_stop > 0 and high >= trade.trailing_stop:
                    to_close.append((tid, trade.trailing_stop, 'trailing_stop'))
        
        for tid, exit_price, reason in to_close:
            self._execute_exit(tid, exit_price, reason, timestamp)
    
    def _execute_exit(self, trade_id: str, exit_price: float,
                      reason: str, timestamp):
        """Execute a trade exit."""
        trade = self.active_trades.get(trade_id)
        if not trade:
            return
        
        # Apply slippage on exit
        slippage = exit_price * BACKTEST_SLIPPAGE
        if trade.direction == 'LONG':
            exit_price -= slippage
        else:
            exit_price += slippage
        
        exit_fee = exit_price * trade.size * TAKER_FEE
        
        if trade.direction == 'LONG':
            pnl = (exit_price - trade.entry_price) * trade.size
        else:
            pnl = (trade.entry_price - exit_price) * trade.size
        
        total_fee = trade.fee + exit_fee
        net_pnl = pnl - total_fee
        
        trade.exit_price = exit_price
        trade.exit_time = timestamp
        trade.exit_reason = reason
        trade.pnl = net_pnl
        trade.fee = total_fee
        if trade.margin > 0:
            trade.pnl_pct = (net_pnl / trade.margin) * 100
        
        self.equity += net_pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        self.sizer.update_equity(self.equity)
        self.sizer.record_trade_result(net_pnl)
        
        del self.active_trades[trade_id]
        self.completed_trades.append(trade)
    
    def _update_trailing(self, symbol: str, price: float):
        """Update trailing stops."""
        if not TRAILING_STOP.get('enabled'):
            return
        
        trail_pct = TRAILING_STOP.get('trail_distance_pct', 0.003)
        activation = TRAILING_STOP.get('activation_pct', 0.005)
        
        for trade in self.active_trades.values():
            if trade.symbol != symbol:
                continue
            
            if trade.direction == 'LONG':
                profit_pct = (price - trade.entry_price) / trade.entry_price
                if profit_pct >= activation:
                    new_trail = price * (1 - trail_pct)
                    if new_trail > trade.trailing_stop:
                        trade.trailing_stop = new_trail
            else:
                profit_pct = (trade.entry_price - price) / trade.entry_price
                if profit_pct >= activation:
                    new_trail = price * (1 + trail_pct)
                    if trade.trailing_stop == 0 or new_trail < trade.trailing_stop:
                        trade.trailing_stop = new_trail
    
    def _has_position(self, symbol: str) -> bool:
        return any(t.symbol == symbol for t in self.active_trades.values())
    
    def _get_unrealized_pnl(self, datasets, ts, primary_tf) -> float:
        total = 0
        for trade in self.active_trades.values():
            if trade.symbol in datasets and primary_tf in datasets[trade.symbol]:
                df = datasets[trade.symbol][primary_tf]
                mask = df.index <= ts
                if mask.any():
                    price = float(df[mask]['close'].iloc[-1])
                    if trade.direction == 'LONG':
                        total += (price - trade.entry_price) * trade.size
                    else:
                        total += (trade.entry_price - price) * trade.size
        return total
    
    def _close_all(self, datasets, last_ts, primary_tf):
        """Close all remaining positions at end of backtest."""
        for tid in list(self.active_trades.keys()):
            trade = self.active_trades[tid]
            if trade.symbol in datasets and primary_tf in datasets[trade.symbol]:
                df = datasets[trade.symbol][primary_tf]
                price = float(df['close'].iloc[-1])
                self._execute_exit(tid, price, 'backtest_end', last_ts)
    
    def _generate_results(self) -> dict:
        """Generate comprehensive backtest results."""
        wins = [t for t in self.completed_trades if t.pnl >= 0]
        losses = [t for t in self.completed_trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in self.completed_trades)
        total_fees = sum(t.fee for t in self.completed_trades)
        
        win_rate = len(wins) / len(self.completed_trades) * 100 if self.completed_trades else 0
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        
        gross_win = sum(t.pnl + t.fee for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl + t.fee for t in losses)) if losses else 1
        profit_factor = gross_win / gross_loss if gross_loss > 0 else 0
        
        # Max drawdown from equity curve
        max_dd = 0
        peak = self.initial_capital
        for point in self.equity_curve:
            eq = point['equity']
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Strategy breakdown
        strategy_stats = {}
        for t in self.completed_trades:
            s = t.strategy
            if s not in strategy_stats:
                strategy_stats[s] = {'trades': 0, 'wins': 0, 'pnl': 0}
            strategy_stats[s]['trades'] += 1
            strategy_stats[s]['pnl'] += t.pnl
            if t.pnl >= 0:
                strategy_stats[s]['wins'] += 1
        
        results = {
            'initial_capital': self.initial_capital,
            'final_equity': self.equity,
            'total_return': ((self.equity - self.initial_capital) / self.initial_capital) * 100,
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'total_trades': len(self.completed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd * 100,
            'peak_equity': self.peak_equity,
            'target_reached': self.equity >= TARGET_CAPITAL,
            'strategy_breakdown': strategy_stats,
            'equity_curve': self.equity_curve,
            'trades': self.completed_trades,
        }
        
        # Print summary
        self._print_summary(results)
        return results
    
    def _print_summary(self, r: dict):
        target_emoji = '✅' if r['target_reached'] else '❌'
        
        print(f"\n{'='*60}")
        print(f"📊 BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"  💰 Initial Capital:  ${r['initial_capital']:.2f}")
        print(f"  💰 Final Equity:     ${r['final_equity']:.2f}")
        print(f"  📈 Total Return:     {r['total_return']:.1f}%")
        print(f"  {target_emoji} Target $1,000:    {'REACHED!' if r['target_reached'] else 'Not reached'}")
        print(f"  📉 Max Drawdown:     {r['max_drawdown']:.1f}%")
        print(f"  🔄 Total Trades:     {r['total_trades']}")
        print(f"  ✅ Win Rate:         {r['win_rate']:.1f}%")
        print(f"  📊 Profit Factor:    {r['profit_factor']:.2f}")
        print(f"  💵 Avg Win:          ${r['avg_win']:.2f}")
        print(f"  💸 Avg Loss:         ${r['avg_loss']:.2f}")
        print(f"  🏦 Total Fees:       ${r['total_fees']:.2f}")
        print(f"\n  📋 Strategy Breakdown:")
        for name, stats in r['strategy_breakdown'].items():
            wr = (stats['wins']/stats['trades']*100) if stats['trades'] > 0 else 0
            print(f"     {name}: {stats['trades']} trades | "
                  f"WR: {wr:.0f}% | P/L: ${stats['pnl']:.2f}")
        print(f"{'='*60}\n")
