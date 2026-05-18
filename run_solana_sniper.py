import time
import random
from solana_sniper.scanner import MemecoinScanner
from solana_sniper.social_tracker import SocialSentimentTracker
from solana_sniper.trader import SolanaTrader

def main():
    print("="*60)
    print("🎣 SOLANA MEMECOIN 'TEBAR JALA' SNIPER BOT 🎣")
    print("="*60)
    print("Strategy: 40 Nets of $1.")
    print("Target: 10,000x on a single net.")
    print("="*60)
    
    scanner = MemecoinScanner()
    social = SocialSentimentTracker()
    trader = SolanaTrader()
    
    nets_thrown = 0
    max_nets = 40
    
    print("\n[🤖 BOT STARTED] Listening to Solana blockchain events...")
    
    # Main Sniping Loop
    while trader.capital >= 1.0 and nets_thrown < max_nets:
        time.sleep(2) # Wait for new blocks
        
        # 1. Scan for new coins
        print("\n--- NEW BLOCK DETECTED ---")
        targets = scanner.search_new_pairs()
        
        if not targets:
            print("[⏳ WAITING] No good pairs found right now. Retrying in 10 seconds...")
            time.sleep(10)
            continue
            
        target_coin = targets[0] # Pick the first best target
        print(f"[🔍 DETECTED] New Pool: ${target_coin['symbol']} (Liq: ${target_coin['liquidity']:.0f})")
        
        # 2. Check Social Hype & Whales
        sentiment = social.evaluate_hype(target_coin['symbol'])
        
        if sentiment['is_approved']:
            print(f"[🔥 HYPE CONFIRMED] ${target_coin['symbol']} is trending!")
            # 3. Execute the $1 Buy
            success = trader.execute_buy(target_coin)
            if success:
                nets_thrown += 1
        else:
            print(f"[❌ REJECTED] ${target_coin['symbol']} has no whale support. Ignoring.")
            
        # Periodically check our bags (nets)
        if nets_thrown > 0 and random.random() > 0.3:
            trader.check_portfolio_status(scanner)
            
        if trader.capital >= 10000:
            print("\n" + "="*60)
            print("🚀🚀🚀 GOAL REACHED! $10,000 HIT! SHUTTING DOWN! 🚀🚀🚀")
            print("="*60)
            break
            
    print("\n" + "="*60)
    print(f"🏁 SESSION ENDED.")
    print(f"Total Nets Thrown: {nets_thrown}")
    print(f"Final Capital: ${trader.capital:,.2f}")
    print("="*60)

if __name__ == "__main__":
    main()
