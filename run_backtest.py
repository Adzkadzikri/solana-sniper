"""
Run Backtest - Main entry point to validate the $40 → $1,000 strategy.

Usage:
    python run_backtest.py
    python run_backtest.py --start 2024-01-01 --end 2025-12-31 --capital 40
"""
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.data_loader import DataLoader
from backtest.engine import BacktestEngine
from backtest.reporter import BacktestReporter
from config.settings import (
    TRADING_PAIRS, BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL
)


def main():
    parser = argparse.ArgumentParser(description='Run trading strategy backtest')
    parser.add_argument('--start', default=BACKTEST_START, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default=BACKTEST_END, help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=INITIAL_CAPITAL, help='Initial capital')
    parser.add_argument('--pairs', nargs='+', default=None, help='Trading pairs')
    parser.add_argument('--no-report', action='store_true', help='Skip HTML report')
    args = parser.parse_args()
    
    pairs = args.pairs or TRADING_PAIRS
    timeframes = ['1h', '4h', '1d']
    
    print(f"\n🤖 Bitget Trading Bot - Backtesting Engine")
    print(f"{'='*50}")
    print(f"  Capital: ${args.capital}")
    print(f"  Period:  {args.start} → {args.end}")
    print(f"  Pairs:   {', '.join(pairs)}")
    print(f"  TFs:     {', '.join(timeframes)}")
    print(f"{'='*50}\n")
    
    # Load data
    loader = DataLoader()
    datasets = {}
    
    for symbol in pairs:
        datasets[symbol] = {}
        for tf in timeframes:
            try:
                df = loader.load(symbol, tf, args.start, args.end)
                if not df.empty:
                    datasets[symbol][tf] = df
                    print(f"  ✅ {symbol} {tf}: {len(df)} candles")
                else:
                    print(f"  ⚠️ {symbol} {tf}: No data")
            except Exception as e:
                print(f"  ❌ {symbol} {tf}: {e}")
    
    # Run backtest
    engine = BacktestEngine(args.capital)
    results = engine.run(datasets, primary_tf='1h')
    
    # Generate report
    if not args.no_report and results:
        reporter = BacktestReporter()
        report_path = reporter.generate(results)
        print(f"\n📄 Open report in browser: file:///{report_path}")
    
    # Return exit code based on target
    if results.get('target_reached'):
        print("\n🎉 BACKTEST PASSED! Strategy achieved $40 → $1,000 target!")
        return 0
    else:
        print(f"\n⚠️ Target not reached. Final: ${results.get('final_equity', 0):.2f}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
