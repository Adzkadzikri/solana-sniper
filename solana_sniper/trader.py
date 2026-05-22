# solana_sniper/trader.py
import time
import random
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from .config import SOLANA_RPC_URL, PHANTOM_PRIVATE_KEY, TRADE_SIZE, TRADING_FEE_PCT, JITO_TIP_SOL

class SolanaTrader:
    def __init__(self, database, telegram):
        print(f"[🔌 TRADER] Connecting to Solana RPC: {SOLANA_RPC_URL}")
        self.client = Client(SOLANA_RPC_URL)
        self.db = database
        self.telegram = telegram
        
        # Test connection
        try:
            health = self.client.is_connected()
            if health:
                print("[🔌 TRADER] Connected to Solana Mainnet-Beta successfully!")
            else:
                print("[🔌 TRADER] Failed to connect to Solana.")
        except Exception as e:
            print(f"[🔌 TRADER] RPC Warning (Expected in simulation): {e}")

        print("[💼 WALLET] Phantom wallet initialized (Simulation Mode)")
        
        # Load state from Database
        active, past, hist, cap = self.db.load_state()
        self.capital = cap
        self.active_nets = active
        self.past_nets = past
        self.capital_history = hist
        
        if not self.capital_history:
            self.capital_history.append([time.time() * 1000, self.capital])
            self.db.add_capital_history(self.capital_history[-1][0], self.capital)
            
        print(f"[💾 DATABASE] Loaded {len(self.active_nets)} active nets and {len(self.past_nets)} past nets. Capital: ${self.capital:.2f}")

    def execute_buy(self, target: dict):
        if self.capital < TRADE_SIZE:
            print("[⚠️ TRADER] Insufficient capital to throw another net!")
            return False

        symbol = target['symbol']
        print(f"\n[🚀 EXECUTION] Throwing $1 Net at ${symbol}...")
        
        # Simulate Jito Block Engine Bundle
        print(f"   [⚡ JITO MEV] Sending bundled transaction with {JITO_TIP_SOL} SOL tip to validators...")
        
        time.sleep(random.uniform(0.4, 2.0))
        
        self.capital -= TRADE_SIZE
        actual_invested = TRADE_SIZE * (1 - TRADING_FEE_PCT)
        buy_price = target['price_usd']
        
        # Update state & DB
        now_ts = time.time() * 1000
        self.capital_history.append([now_ts, self.capital])
        self.db.add_capital_history(now_ts, self.capital)
        
        print(f"[✅ SUCCESS] Bought ${symbol} at {buy_price:.8f} (TxHash: 4x...{random.randint(1000,9999)})")
        
        new_net = {
            'symbol': symbol,
            'address': target['address'],
            'buy_price': buy_price,
            'invested': actual_invested,
            'original_invested': actual_invested,
            'ath_price': buy_price,
            'tp1_done': False,
            'tp2_done': False,
            'tp3_done': False,
            'tp4_done': False,
            'status': 'HOLDING'
        }
        self.active_nets.append(new_net)
        self.db.save_active_nets(self.active_nets)
        
        # Send Telegram Alert
        self.telegram.alert_buy(symbol, target['address'], buy_price, actual_invested)
        
        return True

    def check_portfolio_status(self, scanner):
        print(f"\n[📊 PORTFOLIO] Checking the live paper nets ({len(self.active_nets)} active)...")
        
        changed = False
        
        for net in list(self.active_nets):
            current_price = scanner.get_token_price(net['address'])
            if current_price == 0:
                continue
                
            multiplier = current_price / net['buy_price']
            current_value = net['invested'] * multiplier

            # Update ATH
            if current_price > net['ath_price']:
                net['ath_price'] = current_price
                changed = True

            ath_multiplier = net['ath_price'] / net['buy_price']
            drawdown_from_ath = (current_price / net['ath_price']) if net['ath_price'] > 0 else 1.0

            # Stop Loss
            if multiplier < 0.10:
                net_sell_val = current_value * (1 - TRADING_FEE_PCT)
                print(f"   [💀 RUGPULL] ${net['symbol']} dropped 90% from buy. Cashed out sisa: ${net_sell_val:.2f}.")
                self.capital += net_sell_val
                now_ts = time.time() * 1000
                self.capital_history.append([now_ts, self.capital])
                self.db.add_capital_history(now_ts, self.capital)
                
                net['status'] = 'RUGPULL_SOLD'
                self.past_nets.append(net)
                self.active_nets.remove(net)
                self.db.save_past_net(net)
                self.telegram.alert_panic(net['symbol'], net_sell_val, "RUGPULL STOP LOSS")
                changed = True
                continue

            # ATH Guard
            if ath_multiplier >= 2.0 and drawdown_from_ath <= 0.60:
                net_sell_val = current_value * (1 - TRADING_FEE_PCT)
                print(f"   [🚨 ATH GUARD] ${net['symbol']} peaked at {ath_multiplier:.1f}x but crashed -40% from peak! Panic sell sisa: ${net_sell_val:.2f}.")
                self.capital += net_sell_val
                now_ts = time.time() * 1000
                self.capital_history.append([now_ts, self.capital])
                self.db.add_capital_history(now_ts, self.capital)
                
                net['status'] = 'ATH_GUARD_SOLD'
                self.past_nets.append(net)
                self.active_nets.remove(net)
                self.db.save_past_net(net)
                self.telegram.alert_panic(net['symbol'], net_sell_val, "ATH GUARD PANIC SELL")
                changed = True
                continue

            # TP4
            if not net['tp4_done'] and multiplier >= 100.0:
                net_sell_val = current_value * (1 - TRADING_FEE_PCT)
                print(f"\n   [🎆 TP4 MOONSHOT!!!] ${net['symbol']} hit {multiplier:.1f}x! Selling ALL remaining for ${net_sell_val:.2f}! 🚀🌙")
                self.capital += net_sell_val
                now_ts = time.time() * 1000
                self.capital_history.append([now_ts, self.capital])
                self.db.add_capital_history(now_ts, self.capital)
                
                net['tp4_done'] = True
                net['invested'] = 0
                net['status'] = 'TP4_MOONSHOT_SOLD'
                self.past_nets.append(net)
                self.active_nets.remove(net)
                self.db.save_past_net(net)
                self.telegram.alert_tp("TP4 (100x Moonshot!)", multiplier, net['symbol'], net_sell_val)
                changed = True
                continue

            # TP3
            if not net['tp3_done'] and multiplier >= 20.0:
                portion_value = 0.25 * current_value
                net_sell_val = portion_value * (1 - TRADING_FEE_PCT)
                self.capital += net_sell_val
                now_ts = time.time() * 1000
                self.capital_history.append([now_ts, self.capital])
                self.db.add_capital_history(now_ts, self.capital)
                
                net['invested'] *= 0.75
                net['tp3_done'] = True
                net['status'] = 'RIDING_TO_100X'
                self.telegram.alert_tp("TP3 (20x)", multiplier, net['symbol'], net_sell_val)
                changed = True

            # TP2
            if not net['tp2_done'] and multiplier >= 5.0:
                portion_value = 0.25 * current_value
                net_sell_val = portion_value * (1 - TRADING_FEE_PCT)
                self.capital += net_sell_val
                now_ts = time.time() * 1000
                self.capital_history.append([now_ts, self.capital])
                self.db.add_capital_history(now_ts, self.capital)
                
                net['invested'] *= 0.75
                net['tp2_done'] = True
                if not net['tp3_done']:
                    net['status'] = 'RIDING_TO_20X'
                self.telegram.alert_tp("TP2 (5x)", multiplier, net['symbol'], net_sell_val)
                changed = True

            # TP1
            if not net['tp1_done'] and multiplier >= 2.0:
                portion_value = 0.25 * current_value
                net_sell_val = portion_value * (1 - TRADING_FEE_PCT)
                self.capital += net_sell_val
                now_ts = time.time() * 1000
                self.capital_history.append([now_ts, self.capital])
                self.db.add_capital_history(now_ts, self.capital)
                
                net['invested'] *= 0.75
                net['tp1_done'] = True
                if not net['tp2_done']:
                    net['status'] = 'RIDING_TO_5X'
                self.telegram.alert_tp("TP1 (2x)", multiplier, net['symbol'], net_sell_val)
                changed = True

            if net in self.active_nets:
                status_icon = {
                    'HOLDING': '⏳',
                    'RIDING_TO_5X': '🚀',
                    'RIDING_TO_20X': '🔥',
                    'RIDING_TO_100X': '🌙',
                }.get(net['status'], '⏳')
                print(f"   [{status_icon} {net['status']}] ${net['symbol']} | {multiplier:.2f}x | Value: ${current_value:.2f}")

        if changed:
            self.db.save_active_nets(self.active_nets)
                
        print(f"[💰 WALLET] Total Capital Now: ${self.capital:,.2f}")
