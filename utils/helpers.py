"""
Utility helper functions for the trading bot.
"""
from datetime import datetime, timezone
import math


def timestamp_to_datetime(ts_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime (UTC)."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to millisecond timestamp."""
    return int(dt.timestamp() * 1000)


def round_price(price: float, tick_size: float) -> float:
    """Round price to the nearest tick size."""
    if tick_size <= 0:
        return price
    precision = len(str(tick_size).rstrip('0').split('.')[-1])
    return round(round(price / tick_size) * tick_size, precision)


def round_size(size: float, step_size: float) -> float:
    """Round order size to the nearest step size."""
    if step_size <= 0:
        return size
    precision = len(str(step_size).rstrip('0').split('.')[-1])
    return round(math.floor(size / step_size) * step_size, precision)


def pct_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def calculate_pnl(entry_price: float, exit_price: float, size: float,
                  direction: str, leverage: int = 1) -> float:
    """
    Calculate profit/loss for a futures trade.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        size: Position size in base currency
        direction: 'LONG' or 'SHORT'
        leverage: Leverage multiplier
        
    Returns:
        P/L in USDT
    """
    if direction == 'LONG':
        pnl = (exit_price - entry_price) * size
    else:
        pnl = (entry_price - exit_price) * size
    return pnl


def calculate_liquidation_price(entry_price: float, leverage: int,
                                 direction: str, 
                                 margin_mode: str = 'isolated') -> float:
    """
    Estimate liquidation price for isolated margin.
    
    Note: This is an approximation. Actual liquidation depends on
    maintenance margin, fees, and other factors.
    """
    maintenance_margin_rate = 0.005  # 0.5% (approximate)
    
    if direction == 'LONG':
        liq_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
    else:
        liq_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)
    
    return liq_price


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with comma separators."""
    return f"{value:,.{decimals}f}"


def format_pnl(pnl: float) -> str:
    """Format P/L with sign and color indicator."""
    sign = '+' if pnl >= 0 else ''
    return f"{sign}${pnl:,.2f}"


def format_pct(pct: float) -> str:
    """Format percentage with sign."""
    sign = '+' if pct >= 0 else ''
    return f"{sign}{pct:.2f}%"


def timeframe_to_seconds(timeframe: str) -> int:
    """Convert timeframe string to seconds."""
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
    }
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    return value * units.get(unit, 60)


def timeframe_to_ms(timeframe: str) -> int:
    """Convert timeframe string to milliseconds."""
    return timeframe_to_seconds(timeframe) * 1000


def get_current_timestamp() -> int:
    """Get current UTC timestamp in milliseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def safe_divide(numerator: float, denominator: float, 
                default: float = 0.0) -> float:
    """Safe division that returns default on zero denominator."""
    if denominator == 0:
        return default
    return numerator / denominator
