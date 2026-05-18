"""
Run Bot - Entry point for the live trading bot.

Usage:
    python run_bot.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.trader import Trader
from utils.logger import trade_logger


def main():
    print(r"""
    ╔══════════════════════════════════════════════════╗
    ║  🤖 Bitget Auto-Trading Bot                     ║
    ║  Target: $40 → $1,000 USDT                      ║
    ║  24/7 Automated Derivatives Trading              ║
    ╚══════════════════════════════════════════════════╝
    """)
    
    try:
        trader = Trader()
        trader.start()
    except KeyboardInterrupt:
        trade_logger.log_bot_status('STOP', 'User interrupted')
    except Exception as e:
        trade_logger.logger.critical(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
