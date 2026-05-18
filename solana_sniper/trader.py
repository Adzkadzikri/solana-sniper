# solana_sniper/trader.py
import time
import random
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from .config import SOLANA_RPC_URL, PHANTOM_PRIVATE_KEY, TRADE_SIZE

class SolanaTrader:
    def __init__(self):
        print(f"[🔌 TRADER] Connecting to Solana RPC: {SOLANA_RPC_URL}")
        self.client = Client(SOLANA_RPC_URL)
        
        # Test connection
        try:
            health = self.client.is_connected()
            if health:
                print("[🔌 TRADER] Connected to Solana Mainnet-Beta successfully!")
            else:
                print("[🔌 TRADER] Failed to connect to Solana.")
        except Exception as e:
            print(f"[🔌 TRADER] RPC Warning (Expected in simulation): {e}")

        # In production, we'd load the real keypair from base58
        # self.keypair = Keypair.from_base58_string(PHANTOM_PRIVATE_KEY)
        print("[💼 WALLET] Phantom wallet initialized (Simulation Mode)")
        self.capital = 40.0
        self.active_nets = [] # The $1 'nets' we have thrown

    def execute_buy(self, target: dict):
        """
        Executes a swap instruction on Raydium/Pump.fun program.
        Since we don't want to accidentally drain real money in this test,
        this simulates the transaction confirmation.
        """
        if self.capital < TRADE_SIZE:
            print("[⚠️ TRADER] Insufficient capital to throw another net!")
            return False

        symbol = target['symbol']
        print(f"\n[🚀 EXECUTION] Throwing $1 Net at ${symbol}...")
        
        # Simulate Solana network confirmation delay (400ms - 2000ms)
        time.sleep(random.uniform(0.4, 2.0))
        
        self.capital -= TRADE_SIZE
        buy_price = target['price_usd']
        
        print(f"[✅ SUCCESS] Bought ${symbol} at {buy_price:.8f} (TxHash: 4x...{random.randint(1000,9999)})")
        print(f"[💰 WALLET] Remaining Capital: ${self.capital:.2f}")
        
        self.active_nets.append({
            'symbol': symbol,
            'address': target['address'],
            'buy_price': buy_price,
            'invested': TRADE_SIZE,
            'status': 'HOLDING_FOR_10000X'
        })
        
        return True

    def check_portfolio_status(self, scanner):
        """
        Checks real live prices of our paper-traded tokens via DexScreener.
        """
        print(f"\n[📊 PORTFOLIO] Checking the live paper nets ({len(self.active_nets)} active)...")
        
        for net in list(self.active_nets):
            current_price = scanner.get_token_price(net['address'])
            if current_price == 0:
                continue # Price not found right now
                
            multiplier = current_price / net['buy_price']
            
            if multiplier < 0.10: # Dropped 90%
                print(f"   [💀 RUGPULL] ${net['symbol']} dropped 90%. Your $1 is now ${multiplier:.2f}.")
                self.active_nets.remove(net)
            elif multiplier >= 2.0: # Went 2x
                profit = net['invested'] * multiplier
                print(f"   [📈 PROFIT] ${net['symbol']} went {multiplier:.1f}x! Cashed out ${profit:.2f}.")
                self.capital += profit
                self.active_nets.remove(net)
            else:
                # Still holding
                current_value = net['invested'] * multiplier
                print(f"   [⏳ HOLDING] ${net['symbol']} | Buy: {net['buy_price']:.8f} | Now: {current_price:.8f} | Value: ${current_value:.2f}")
                
        print(f"[💰 WALLET] Total Capital Now: ${self.capital:,.2f}")
