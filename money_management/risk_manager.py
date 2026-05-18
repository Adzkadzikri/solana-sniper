"""
Risk Manager - Anti-liquidation and exposure controls.
"""
from datetime import datetime, timezone, timedelta
from config.settings import (
    MAX_TOTAL_EXPOSURE, MAX_DAILY_LOSS_PCT, MIN_LIQUIDATION_DISTANCE,
    COOLDOWN_AFTER_MAX_DD_HOURS, FUNDING_RATE_THRESHOLD
)
from utils.logger import trade_logger
from utils.helpers import calculate_liquidation_price


class RiskManager:
    """Enforces risk rules to prevent liquidation and excessive losses."""
    
    def __init__(self, position_sizer):
        self.sizer = position_sizer
        self.daily_pnl = 0.0
        self.daily_start_equity = 0.0
        self.last_daily_reset = None
        self.cooldown_until = None
        self._reset_daily()
    
    def can_open_trade(self, symbol: str, direction: str, margin: float,
                       leverage: int, entry_price: float,
                       current_positions: list,
                       funding_rate: float = 0.0) -> dict:
        """
        Check if a new trade passes all risk rules.
        Returns dict with 'allowed' bool and 'reason' string.
        """
        self._check_daily_reset()
        
        # Check cooldown
        if self.cooldown_until and datetime.now(timezone.utc) < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now(timezone.utc)).seconds // 60
            return {'allowed': False, 'reason': f'Cooldown active ({remaining}min left)'}
        
        # Check if trading is paused
        if self.sizer.trading_paused:
            self._start_cooldown()
            return {'allowed': False, 'reason': 'Trading paused (max drawdown)'}
        
        # Check max positions
        max_pos = self.sizer.get_max_positions()
        if len(current_positions) >= max_pos:
            return {'allowed': False, 'reason': f'Max positions reached ({max_pos})'}
        
        # Check daily loss limit
        daily_loss_limit = self.daily_start_equity * MAX_DAILY_LOSS_PCT
        if self.daily_pnl < 0 and abs(self.daily_pnl) >= daily_loss_limit:
            return {'allowed': False, 'reason': f'Daily loss limit hit (${abs(self.daily_pnl):.2f})'}
        
        # Check total exposure
        total_margin = sum(p.get('margin', 0) for p in current_positions) + margin
        if total_margin > self.sizer.equity * MAX_TOTAL_EXPOSURE * 10:
            return {'allowed': False, 'reason': 'Total exposure too high'}
        
        # Check liquidation distance
        liq_price = calculate_liquidation_price(entry_price, leverage, direction)
        liq_distance = abs(entry_price - liq_price) / entry_price
        if liq_distance < MIN_LIQUIDATION_DISTANCE:
            return {'allowed': False, 
                    'reason': f'Liquidation too close ({liq_distance:.1%})'}
        
        # Check correlation (no same-direction on same pair)
        for pos in current_positions:
            if pos.get('symbol') == symbol:
                return {'allowed': False, 'reason': f'Already have position on {symbol}'}
        
        # Check funding rate
        if abs(funding_rate) > FUNDING_RATE_THRESHOLD:
            trade_logger.log_risk_event(
                'HIGH FUNDING', f'{symbol} funding={funding_rate:.4%}'
            )
            # Don't block, just warn - funding rate is factored into decisions
        
        return {'allowed': True, 'reason': 'All checks passed'}
    
    def record_daily_pnl(self, pnl: float):
        """Add P/L to daily tracker."""
        self._check_daily_reset()
        self.daily_pnl += pnl
    
    def _check_daily_reset(self):
        """Reset daily counters at midnight UTC."""
        now = datetime.now(timezone.utc).date()
        if self.last_daily_reset != now:
            self.daily_pnl = 0.0
            self.daily_start_equity = self.sizer.equity
            self.last_daily_reset = now
    
    def _reset_daily(self):
        self.last_daily_reset = datetime.now(timezone.utc).date()
        self.daily_start_equity = self.sizer.equity
    
    def _start_cooldown(self):
        """Start cooldown period after max drawdown."""
        self.cooldown_until = (
            datetime.now(timezone.utc) + 
            timedelta(hours=COOLDOWN_AFTER_MAX_DD_HOURS)
        )
        trade_logger.log_risk_event(
            'COOLDOWN', f'{COOLDOWN_AFTER_MAX_DD_HOURS}h cooldown started'
        )
    
    def end_cooldown(self):
        """Manually end cooldown and resume trading."""
        self.cooldown_until = None
        self.sizer.resume_trading()
    
    def get_status(self) -> dict:
        return {
            'daily_pnl': self.daily_pnl,
            'daily_limit': self.daily_start_equity * MAX_DAILY_LOSS_PCT,
            'cooldown_active': bool(
                self.cooldown_until and 
                datetime.now(timezone.utc) < self.cooldown_until
            ),
            **self.sizer.get_status()
        }
