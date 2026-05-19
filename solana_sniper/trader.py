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
            'secured_capital': False,
            'status': 'HOLDING_FOR_2X'
        })
        
        return True

    def check_portfolio_status(self, scanner):
        """
        Checks real live prices of our paper-traded tokens via DexScreener.
        Implements the Moonbag Strategy (Partial TP at 2x, SL at -90%).
        """
        print(f"\n[📊 PORTFOLIO] Checking the live paper nets ({len(self.active_nets)} active)...")
        
        for net in list(self.active_nets):
            current_price = scanner.get_token_price(net['address'])
            if current_price == 0:
                continue # Price not found right now
                
            multiplier = current_price / net['buy_price']
            current_value = net['invested'] * multiplier
            
            # 1. Stop Loss (SL) at -90% of buy price
            if multiplier < 0.10:
                print(f"   [💀 RUGPULL] ${net['symbol']} dropped 90%. Cashed out sisa value: ${current_value:.2f}.")
                self.capital += current_value
                self.active_nets.remove(net)
                
            # 2. Take Profit 1 (TP1) - Secured Capital at 2x
            elif multiplier >= 2.0 and not net.get('secured_capital', False):
                # Sell 50% of the position to secure the initial $1 investment
                sell_val = 0.5 * net['invested'] * multiplier
                self.capital += sell_val
                
                # Update net state (cut remaining holding size in half, mark as secured)
                net['invested'] = net['invested'] * 0.5
                net['secured_capital'] = True
                net['status'] = 'MOONBAG_RIDING'
                
                print(f"   [🛡️ CAPITAL SECURED] ${net['symbol']} went {multiplier:.1f}x! Sold 50% for ${sell_val:.2f} (Modal Aman!). Sisa 50% dibiarkan terbang.")
                
            # 3. Take Profit 2 (Jackpot TP) - Reached 1000x or more on the Moonbag
            elif net.get('secured_capital', False) and multiplier >= 1000.0:
                print(f"\n   [🎆 JACKPOT!!!] ${net['symbol']} MOONBAG REACHED {multiplier:.0f}x!!!")
                self.capital += current_value
                self.active_nets.remove(net)
                
            else:
                # Still holding or riding
                if net.get('secured_capital', False):
                    print(f"   [⏳ MOONBAG] ${net['symbol']} | Buy: {net['buy_price']:.8f} | Now: {current_price:.8f} | Moonbag Value: ${current_value:.2f}")
                else:
                    print(f"   [⏳ HOLDING] ${net['symbol']} | Buy: {net['buy_price']:.8f} | Now: {current_price:.8f} | Value: ${current_value:.2f}")
                
        print(f"[💰 WALLET] Total Capital Now: ${self.capital:,.2f}")
