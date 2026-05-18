"""
Order management system.
Handles position sizing, order execution, and trade lifecycle.
"""
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class Trade:
    """Represents an active or completed trade."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ''
    direction: str = ''  # 'LONG' or 'SHORT'
    strategy: str = ''
    entry_price: float = 0.0
    exit_price: float = 0.0
    size: float = 0.0
    leverage: int = 1
    stop_loss: float = 0.0
    take_profit: float = 0.0
    trailing_stop: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fee_paid: float = 0.0
    status: str = 'pending'  # pending, open, closed, cancelled
    entry_time: datetime = None
    exit_time: datetime = None
    exit_reason: str = ''
    confidence: float = 0.0
    margin_used: float = 0.0
    
    def calculate_pnl(self, current_price: float = None) -> float:
        price = current_price or self.exit_price
        if price == 0 or self.entry_price == 0:
            return 0.0
        if self.direction == 'LONG':
            self.pnl = (price - self.entry_price) * self.size - self.fee_paid
        else:
            self.pnl = (self.entry_price - price) * self.size - self.fee_paid
        if self.margin_used > 0:
            self.pnl_pct = (self.pnl / self.margin_used) * 100
        return self.pnl
    
    def to_dict(self) -> dict:
        return {
            'id': self.id, 'symbol': self.symbol,
            'direction': self.direction, 'strategy': self.strategy,
            'entry_price': self.entry_price, 'exit_price': self.exit_price,
            'size': self.size, 'leverage': self.leverage,
            'stop_loss': self.stop_loss, 'take_profit': self.take_profit,
            'pnl': self.pnl, 'pnl_pct': self.pnl_pct,
            'fee_paid': self.fee_paid, 'status': self.status,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason, 'confidence': self.confidence,
        }


class OrderManager:
    """Manages trade execution, tracking, and lifecycle."""
    
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        self.active_trades: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
    
    def open_trade(self, symbol: str, direction: str, size: float,
                   leverage: int, entry_price: float, stop_loss: float,
                   take_profit: float, strategy: str,
                   confidence: float) -> Optional[Trade]:
        """Open a new trade."""
        trade = Trade(
            symbol=symbol, direction=direction, size=size,
            leverage=leverage, entry_price=entry_price,
            stop_loss=stop_loss, take_profit=take_profit,
            strategy=strategy, confidence=confidence,
            entry_time=datetime.now(timezone.utc), status='open',
            margin_used=(entry_price * size) / leverage,
            fee_paid=entry_price * size * 0.0006,  # Taker fee
        )
        
        # Execute on exchange
        side = 'buy' if direction == 'LONG' else 'sell'
        self.exchange.set_leverage(symbol, leverage)
        order = self.exchange.place_market_order(symbol, side, size)
        
        if order is None:
            trade.status = 'cancelled'
            return None
        
        # Set SL/TP
        close_side = 'sell' if direction == 'LONG' else 'buy'
        if stop_loss > 0:
            self.exchange.set_stop_loss(symbol, close_side, size, stop_loss)
        if take_profit > 0:
            self.exchange.set_take_profit(symbol, close_side, size, take_profit)
        
        self.active_trades[trade.id] = trade
        return trade
    
    def close_trade(self, trade_id: str, exit_price: float,
                    reason: str = 'manual') -> Optional[Trade]:
        """Close an active trade."""
        trade = self.active_trades.get(trade_id)
        if not trade:
            return None
        
        close_side = 'sell' if trade.direction == 'LONG' else 'buy'
        self.exchange.place_market_order(
            trade.symbol, close_side, trade.size, reduce_only=True
        )
        self.exchange.cancel_all_orders(trade.symbol)
        
        trade.exit_price = exit_price
        trade.exit_time = datetime.now(timezone.utc)
        trade.exit_reason = reason
        trade.fee_paid += exit_price * trade.size * 0.0006
        trade.calculate_pnl()
        trade.status = 'closed'
        
        del self.active_trades[trade_id]
        self.trade_history.append(trade)
        self.total_trades += 1
        if trade.pnl >= 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        return trade
    
    def check_stop_loss_tp(self, current_prices: Dict[str, float]):
        """Check and execute SL/TP for all active trades (used in backtest)."""
        trades_to_close = []
        
        for trade_id, trade in self.active_trades.items():
            price = current_prices.get(trade.symbol, 0)
            if price == 0:
                continue
            
            if trade.direction == 'LONG':
                if trade.stop_loss > 0 and price <= trade.stop_loss:
                    trades_to_close.append((trade_id, trade.stop_loss, 'stop_loss'))
                elif trade.take_profit > 0 and price >= trade.take_profit:
                    trades_to_close.append((trade_id, trade.take_profit, 'take_profit'))
            else:
                if trade.stop_loss > 0 and price >= trade.stop_loss:
                    trades_to_close.append((trade_id, trade.stop_loss, 'stop_loss'))
                elif trade.take_profit > 0 and price <= trade.take_profit:
                    trades_to_close.append((trade_id, trade.take_profit, 'take_profit'))
            
            # Trailing stop check
            if trade.trailing_stop > 0:
                if trade.direction == 'LONG' and price <= trade.trailing_stop:
                    trades_to_close.append((trade_id, trade.trailing_stop, 'trailing_stop'))
                elif trade.direction == 'SHORT' and price >= trade.trailing_stop:
                    trades_to_close.append((trade_id, trade.trailing_stop, 'trailing_stop'))
        
        for trade_id, exit_price, reason in trades_to_close:
            self.close_trade(trade_id, exit_price, reason)
    
    def update_trailing_stops(self, current_prices: Dict[str, float],
                              trail_pct: float = 0.003):
        """Update trailing stops for profitable trades."""
        for trade in self.active_trades.values():
            price = current_prices.get(trade.symbol, 0)
            if price == 0:
                continue
            
            if trade.direction == 'LONG':
                new_trail = price * (1 - trail_pct)
                if new_trail > trade.trailing_stop and price > trade.entry_price:
                    trade.trailing_stop = new_trail
            else:
                new_trail = price * (1 + trail_pct)
                if (trade.trailing_stop == 0 or new_trail < trade.trailing_stop) and price < trade.entry_price:
                    trade.trailing_stop = new_trail
    
    def get_position_count(self) -> int:
        return len(self.active_trades)
    
    def get_active_symbols(self) -> list:
        return [t.symbol for t in self.active_trades.values()]
    
    def get_total_exposure(self) -> float:
        return sum(t.margin_used for t in self.active_trades.values())
    
    def get_stats(self) -> dict:
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        total_pnl = sum(t.pnl for t in self.trade_history)
        avg_win = 0
        avg_loss = 0
        wins = [t.pnl for t in self.trade_history if t.pnl > 0]
        losses = [t.pnl for t in self.trade_history if t.pnl < 0]
        if wins:
            avg_win = sum(wins) / len(wins)
        if losses:
            avg_loss = sum(losses) / len(losses)
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        
        return {
            'total_trades': self.total_trades,
            'winning': self.winning_trades,
            'losing': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
        }
