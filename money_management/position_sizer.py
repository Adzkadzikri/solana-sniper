"""
Dynamic Position Sizer - Adaptive money management.
Switches between aggressive and passive modes based on equity and streaks.
"""
from config.settings import (
    MONEY_MANAGEMENT_TIERS, WIN_STREAK_BONUS, WIN_STREAK_THRESHOLD,
    LOSE_STREAK_PENALTY, LOSE_STREAK_THRESHOLD, DRAWDOWN_FORCE_PASSIVE,
    DRAWDOWN_STOP_TRADING
)
from utils.logger import trade_logger


class PositionSizer:
    """Calculates position size, leverage, and trading mode dynamically."""
    
    def __init__(self, initial_capital: float = 40.0):
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.peak_equity = initial_capital
        self.current_tier = None
        self.current_mode = 'AGGRESSIVE'
        self.win_streak = 0
        self.lose_streak = 0
        self.risk_adjustment = 0.0
        self.forced_passive = False
        self.trading_paused = False
        self._update_tier()
    
    def update_equity(self, new_equity: float):
        """Update equity and recalculate tier/mode."""
        self.equity = new_equity
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity
            self.forced_passive = False
        self._update_tier()
        self._check_drawdown()
    
    def record_trade_result(self, pnl: float):
        """Update streak counters after a trade."""
        if pnl >= 0:
            self.win_streak += 1
            self.lose_streak = 0
            if self.win_streak >= WIN_STREAK_THRESHOLD:
                self.risk_adjustment = min(
                    self.risk_adjustment + WIN_STREAK_BONUS,
                    0.015  # Max +1.5% bonus
                )
        else:
            self.lose_streak += 1
            self.win_streak = 0
            if self.lose_streak >= LOSE_STREAK_THRESHOLD:
                self.risk_adjustment = max(
                    self.risk_adjustment - LOSE_STREAK_PENALTY,
                    -0.01  # Max -1% penalty
                )
    
    def get_position_params(self, entry_price: float, stop_loss: float,
                            signal_confidence: float = 70) -> dict:
        """
        Calculate position size and leverage for a trade.
        
        Returns:
            Dict with 'size', 'leverage', 'margin', 'risk_amount', 'can_trade'
        """
        if self.trading_paused:
            return {'can_trade': False, 'reason': 'Trading paused (cooldown)'}
        
        tier = self.current_tier
        if tier is None:
            return {'can_trade': False, 'reason': 'No tier available'}
        
        # Base risk per trade from tier
        base_risk = tier['risk_per_trade']
        adjusted_risk = max(0.005, base_risk + self.risk_adjustment)
        
        if self.forced_passive:
            adjusted_risk = min(adjusted_risk, 0.01)
        
        # Confidence scaling (lower confidence = smaller position)
        confidence_factor = min(signal_confidence / 100, 1.0)
        final_risk = adjusted_risk * confidence_factor
        
        # Risk amount in USDT
        risk_amount = self.equity * final_risk
        
        # Calculate SL distance
        sl_distance_pct = abs(entry_price - stop_loss) / entry_price
        if sl_distance_pct == 0:
            sl_distance_pct = 0.005  # Default 0.5%
        
        # Leverage selection
        if self.forced_passive:
            leverage = tier['leverage_min']
        else:
            leverage = int(tier['leverage_min'] + 
                          (tier['leverage_max'] - tier['leverage_min']) * 
                          confidence_factor)
            leverage = max(tier['leverage_min'], min(tier['leverage_max'], leverage))
        
        # Position size calculation
        # risk_amount = size * sl_distance_pct * entry_price (approx)
        # size = risk_amount / (sl_distance_pct * entry_price)
        position_value = risk_amount / sl_distance_pct
        margin_required = position_value / leverage
        size = position_value / entry_price
        
        # Safety: margin should not exceed available equity fraction
        max_margin = self.equity * 0.3  # Max 30% of equity per position
        if margin_required > max_margin:
            margin_required = max_margin
            position_value = margin_required * leverage
            size = position_value / entry_price
            risk_amount = size * sl_distance_pct * entry_price
        
        return {
            'can_trade': True,
            'size': size,
            'leverage': leverage,
            'margin': margin_required,
            'risk_amount': risk_amount,
            'risk_pct': final_risk * 100,
            'mode': self.current_mode,
            'tier': tier['description'],
        }
    
    def get_max_positions(self) -> int:
        if self.current_tier:
            return self.current_tier['max_positions']
        return 1
    
    def _update_tier(self):
        """Determine current tier based on equity."""
        for name, tier in MONEY_MANAGEMENT_TIERS.items():
            if tier['equity_min'] <= self.equity < tier['equity_max']:
                self.current_tier = tier
                if not self.forced_passive:
                    self.current_mode = tier['mode']
                return
    
    def _check_drawdown(self):
        """Check drawdown levels and enforce risk controls."""
        if self.peak_equity <= 0:
            return
        
        drawdown = (self.peak_equity - self.equity) / self.peak_equity
        
        if drawdown >= DRAWDOWN_STOP_TRADING:
            self.trading_paused = True
            self.forced_passive = True
            self.current_mode = 'STOPPED'
            trade_logger.log_risk_event(
                'MAX DRAWDOWN',
                f'DD={drawdown:.1%} | Trading paused for cooldown'
            )
        elif drawdown >= DRAWDOWN_FORCE_PASSIVE:
            self.forced_passive = True
            self.current_mode = 'PASSIVE'
            trade_logger.log_risk_event(
                'HIGH DRAWDOWN',
                f'DD={drawdown:.1%} | Forced passive mode'
            )
    
    def resume_trading(self):
        """Resume trading after cooldown."""
        self.trading_paused = False
        # Reset local peak equity so the drawdown check doesn't immediately pause again
        self.peak_equity = self.equity 
        self._update_tier()
    
    def get_drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0
        return (self.peak_equity - self.equity) / self.peak_equity
    
    def get_status(self) -> dict:
        return {
            'equity': self.equity,
            'peak_equity': self.peak_equity,
            'drawdown': self.get_drawdown(),
            'mode': self.current_mode,
            'tier': self.current_tier['description'] if self.current_tier else 'N/A',
            'win_streak': self.win_streak,
            'lose_streak': self.lose_streak,
            'risk_adjustment': self.risk_adjustment,
            'paused': self.trading_paused,
        }
