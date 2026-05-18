"""
Structured logging system for the trading bot.
Provides colored console output and JSON file logging.
"""
import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config.settings import LOG_DIR, LOG_LEVEL


# ============================================
# Color codes for console output
# ============================================
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


# ============================================
# Custom Formatter for Console
# ============================================
class ColoredFormatter(logging.Formatter):
    """Colored console formatter with emoji indicators."""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.RED + Colors.BOLD,
    }
    
    LEVEL_ICONS = {
        logging.DEBUG: '🔍',
        logging.INFO: '📋',
        logging.WARNING: '⚠️',
        logging.ERROR: '❌',
        logging.CRITICAL: '🔥',
    }
    
    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        icon = self.LEVEL_ICONS.get(record.levelno, '•')
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Format the message
        formatted = (
            f"{Colors.DIM}{timestamp}{Colors.RESET} "
            f"{icon} "
            f"{color}{record.getMessage()}{Colors.RESET}"
        )
        
        return formatted


# ============================================
# JSON Formatter for File Logging
# ============================================
class JSONFormatter(logging.Formatter):
    """JSON file formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'trade_data'):
            log_entry['trade_data'] = record.trade_data
        if hasattr(record, 'equity'):
            log_entry['equity'] = record.equity
        if hasattr(record, 'signal'):
            log_entry['signal'] = record.signal
            
        return json.dumps(log_entry, default=str)


# ============================================
# Logger Setup
# ============================================
def setup_logger(name: str = 'trading_bot') -> logging.Logger:
    """
    Create and configure the main logger.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console Handler (colored)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    # File Handler (JSON, rotated daily, max 10MB)
    log_file = LOG_DIR / f'{name}.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30,  # Keep 30 days
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Trade-specific log file
    trade_log_file = LOG_DIR / 'trades.log'
    trade_handler = RotatingFileHandler(
        trade_log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=60,
        encoding='utf-8'
    )
    trade_handler.setFormatter(JSONFormatter())
    trade_handler.setLevel(logging.INFO)
    logger.addHandler(trade_handler)
    
    return logger


# ============================================
# Trade-specific logging helpers
# ============================================
class TradeLogger:
    """Helper class for logging trade-specific events with rich formatting."""
    
    def __init__(self):
        self.logger = setup_logger('trading_bot')
    
    def log_signal(self, symbol: str, direction: str, strategy: str, 
                   confidence: float, price: float):
        """Log a trading signal."""
        emoji = '🟢' if direction == 'LONG' else '🔴'
        self.logger.info(
            f"{emoji} SIGNAL | {symbol} {direction} | "
            f"Strategy: {strategy} | Confidence: {confidence:.0f}% | "
            f"Price: ${price:,.2f}"
        )
    
    def log_entry(self, symbol: str, direction: str, size: float, 
                  price: float, leverage: int, sl: float, tp: float):
        """Log a trade entry."""
        emoji = '📈' if direction == 'LONG' else '📉'
        self.logger.info(
            f"{emoji} ENTRY | {symbol} {direction} | "
            f"Size: {size:.4f} | Price: ${price:,.2f} | "
            f"Leverage: {leverage}x | SL: ${sl:,.2f} | TP: ${tp:,.2f}"
        )
    
    def log_exit(self, symbol: str, direction: str, pnl: float, 
                 pnl_pct: float, reason: str):
        """Log a trade exit."""
        emoji = '✅' if pnl >= 0 else '❌'
        color_sign = '+' if pnl >= 0 else ''
        self.logger.info(
            f"{emoji} EXIT | {symbol} {direction} | "
            f"P/L: {color_sign}${pnl:,.2f} ({color_sign}{pnl_pct:.2f}%) | "
            f"Reason: {reason}"
        )
    
    def log_equity(self, equity: float, peak: float, drawdown: float, 
                   mode: str, tier: str):
        """Log equity update."""
        self.logger.info(
            f"💰 EQUITY: ${equity:,.2f} | Peak: ${peak:,.2f} | "
            f"DD: {drawdown:.2f}% | Mode: {mode} | Tier: {tier}"
        )
    
    def log_risk_event(self, event_type: str, details: str):
        """Log risk management event."""
        self.logger.warning(
            f"🛡️ RISK | {event_type} | {details}"
        )
    
    def log_bot_status(self, status: str, details: str = ''):
        """Log bot status changes."""
        icons = {
            'START': '🚀', 'STOP': '🛑', 'PAUSE': '⏸️',
            'RESUME': '▶️', 'ERROR': '💥', 'COOLDOWN': '❄️'
        }
        icon = icons.get(status, '📋')
        self.logger.info(f"{icon} BOT {status} | {details}")


# Singleton instance
trade_logger = TradeLogger()
