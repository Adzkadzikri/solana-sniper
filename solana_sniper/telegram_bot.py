import requests
import time
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SNIPER_MODE

class TelegramNotifier:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        
        # Reference to trader state (set later by app.py)
        self._trader = None
        self._nets_thrown = 0
        
        # Test if token is configured
        if not self.token or self.token == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or not self.chat_id:
            print("[📱 TELEGRAM] Bot Token or Chat ID not configured. Running in Mock Mode.")
            self.is_active = False
        else:
            print("[📱 TELEGRAM] Initialized successfully. Real alerts & commands are ON.")
            self.is_active = True
            self._register_commands()

    def _register_commands(self):
        """Register bot commands so they show up in Telegram's menu."""
        if not self.is_active:
            return
        try:
            commands = [
                {"command": "status", "description": "📊 Status lengkap bot (wallet, nets, mode)"},
                {"command": "wallet", "description": "💰 Lihat saldo wallet saat ini"},
                {"command": "nets", "description": "🕸️ Lihat semua posisi aktif"},
                {"command": "history", "description": "📜 Riwayat trade terakhir"},
                {"command": "profit", "description": "💎 Hitung total profit/loss"},
                {"command": "mode", "description": "⚙️ Lihat mode sniper saat ini"},
                {"command": "help", "description": "❓ Daftar semua perintah"},
            ]
            requests.post(
                f"{self.base_url}/setMyCommands",
                json={"commands": commands},
                timeout=5
            )
        except Exception as e:
            print(f"[📱 TELEGRAM] Failed to register commands: {e}")

    def link_trader(self, trader, nets_thrown_ref):
        """Links the trader object so commands can read live state."""
        self._trader = trader
        self._nets_thrown = nets_thrown_ref

    def send_alert(self, message: str, is_html=True, chat_id=None):
        """Sends a message to the configured Telegram Chat."""
        target_chat = chat_id or self.chat_id
        print(f"\n[📱 TELEGRAM LOG] -> Chat {target_chat}")
        
        if not self.is_active:
            return False
            
        payload = {
            "chat_id": target_chat,
            "text": message,
            "disable_web_page_preview": True
        }
        
        if is_html:
            payload["parse_mode"] = "HTML"
            
        try:
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=5)
            if response.status_code != 200:
                print(f"[📱 TELEGRAM] Failed to send: {response.text}")
                return False
            return True
        except Exception as e:
            print(f"[📱 TELEGRAM] Exception: {e}")
            return False

    # ──────────────────────────────────────────
    # COMMAND POLLING & HANDLERS
    # ──────────────────────────────────────────
    def poll_commands(self, nets_thrown: int = 0):
        """Call this periodically from bot_loop to check for user commands."""
        if not self.is_active:
            return
        self._nets_thrown = nets_thrown
            
        try:
            url = f"{self.base_url}/getUpdates?offset={self.last_update_id + 1}&timeout=0"
            resp = requests.get(url, timeout=3)
            if resp.status_code != 200:
                return
            data = resp.json()
            results = data.get("result", [])
            
            for update in results:
                self.last_update_id = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = msg.get("chat", {}).get("id")
                
                if not text or not chat_id:
                    continue
                
                cmd = text.split()[0].lower().replace("@", "").split("@")[0]
                
                if cmd == "/start" or cmd == "/help":
                    self._cmd_help(chat_id)
                elif cmd == "/status":
                    self._cmd_status(chat_id)
                elif cmd == "/wallet":
                    self._cmd_wallet(chat_id)
                elif cmd == "/nets":
                    self._cmd_nets(chat_id)
                elif cmd == "/history":
                    self._cmd_history(chat_id)
                elif cmd == "/profit":
                    self._cmd_profit(chat_id)
                elif cmd == "/mode":
                    self._cmd_mode(chat_id)
                    
        except Exception as e:
            # Silent fail — don't crash bot loop for telegram polling issues
            pass

    def _cmd_help(self, chat_id):
        msg = (
            "🎣 <b>Solana Sniper 3.0 — Command Menu</b>\n\n"
            "/status — 📊 Status lengkap bot\n"
            "/wallet — 💰 Saldo wallet\n"
            "/nets — 🕸️ Posisi aktif (holding)\n"
            "/history — 📜 Riwayat trade\n"
            "/profit — 💎 Total profit/loss\n"
            "/mode — ⚙️ Mode sniper aktif\n"
            "/help — ❓ Menu ini\n"
        )
        self.send_alert(msg, chat_id=chat_id)

    def _cmd_status(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap. Tunggu sebentar...", chat_id=chat_id)
            return
        t = self._trader
        active = len(t.active_nets)
        past = len(t.past_nets)
        
        # Calculate P/L
        initial = 100.0
        pnl = t.capital - initial
        pnl_pct = (pnl / initial) * 100
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        msg = (
            f"📊 <b>BOT STATUS</b>\n"
            f"{'━' * 24}\n\n"
            f"💰 <b>Wallet:</b> ${t.capital:,.2f}\n"
            f"{pnl_emoji} <b>P/L:</b> {'+' if pnl >= 0 else ''}{pnl:,.2f} ({pnl_pct:+.1f}%)\n\n"
            f"🕸️ <b>Nets Thrown:</b> {self._nets_thrown}/100\n"
            f"📌 <b>Active Positions:</b> {active}\n"
            f"📜 <b>Past Trades:</b> {past}\n\n"
            f"⚙️ <b>Mode:</b> <code>{SNIPER_MODE}</code>\n"
            f"🤖 <b>Status:</b> {'🟢 Running' if t.capital >= 1.0 else '🔴 Stopped'}"
        )
        self.send_alert(msg, chat_id=chat_id)

    def _cmd_wallet(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap...", chat_id=chat_id)
            return
        t = self._trader
        initial = 100.0
        pnl = t.capital - initial
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        
        msg = (
            f"💰 <b>WALLET BALANCE</b>\n"
            f"{'━' * 24}\n\n"
            f"💵 <b>Saldo:</b> ${t.capital:,.2f}\n"
            f"{pnl_emoji} <b>Dari modal awal ($100):</b> {'+' if pnl >= 0 else ''}${pnl:,.2f}\n\n"
            f"🕸️ <b>Nets Thrown:</b> {self._nets_thrown}/100\n"
            f"📌 <b>Holding:</b> {len(t.active_nets)} posisi"
        )
        self.send_alert(msg, chat_id=chat_id)

    def _cmd_nets(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap...", chat_id=chat_id)
            return
        t = self._trader
        
        if not t.active_nets:
            self.send_alert("🕸️ <b>Tidak ada posisi aktif saat ini.</b>\n\nBot sedang menunggu peluang...", chat_id=chat_id)
            return
        
        lines = [f"🕸️ <b>ACTIVE POSITIONS ({len(t.active_nets)})</b>\n{'━' * 24}\n"]
        
        status_emoji = {
            'HOLDING': '⏳', 'RIDING_TO_5X': '🚀',
            'RIDING_TO_20X': '🔥', 'RIDING_TO_100X': '🌙',
        }
        
        for i, net in enumerate(t.active_nets, 1):
            emoji = status_emoji.get(net.get('status', ''), '⏳')
            ca_short = net['address'][:6] + '...' + net['address'][-4:] if len(net.get('address', '')) > 10 else net.get('address', '?')
            lines.append(
                f"\n{emoji} <b>#{i} ${net['symbol']}</b>\n"
                f"   Status: <code>{net.get('status', 'HOLDING')}</code>\n"
                f"   Buy: ${net['buy_price']:.8f}\n"
                f"   Invested: ${net.get('invested', 0):.3f}\n"
                f"   CA: <code>{ca_short}</code>"
            )
        
        self.send_alert("\n".join(lines), chat_id=chat_id)

    def _cmd_history(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap...", chat_id=chat_id)
            return
        t = self._trader
        
        if not t.past_nets:
            self.send_alert("📜 <b>Belum ada riwayat trade.</b>", chat_id=chat_id)
            return
        
        lines = [f"📜 <b>TRADE HISTORY (Last 10)</b>\n{'━' * 24}\n"]
        
        status_emoji = {
            'RUGPULL_SOLD': '💀', 'ATH_GUARD_SOLD': '🚨',
            'TP4_MOONSHOT_SOLD': '🎆', 'TP4_SOLD': '🎆',
        }
        
        recent = t.past_nets[-10:]  # Last 10
        for i, net in enumerate(reversed(recent), 1):
            emoji = status_emoji.get(net.get('status', ''), '✅')
            lines.append(
                f"\n{emoji} <b>#{i} ${net['symbol']}</b> — <code>{net.get('status', '?')}</code>\n"
                f"   Buy: ${net['buy_price']:.8f}"
            )
        
        self.send_alert("\n".join(lines), chat_id=chat_id)

    def _cmd_profit(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap...", chat_id=chat_id)
            return
        t = self._trader
        initial = 100.0
        pnl = t.capital - initial
        pnl_pct = (pnl / initial) * 100
        
        # Count wins/losses
        wins = sum(1 for n in t.past_nets if 'TP' in n.get('status', ''))
        losses = sum(1 for n in t.past_nets if 'RUG' in n.get('status', '') or 'ATH' in n.get('status', ''))
        total = len(t.past_nets)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        if pnl >= 0:
            bar = "🟩" * min(int(pnl_pct / 10), 20)
            emoji = "💎"
        else:
            bar = "🟥" * min(int(abs(pnl_pct) / 10), 20)
            emoji = "💔"
            
        msg = (
            f"{emoji} <b>PROFIT / LOSS REPORT</b>\n"
            f"{'━' * 24}\n\n"
            f"💵 <b>Modal Awal:</b> ${initial:,.2f}\n"
            f"💰 <b>Saldo Sekarang:</b> ${t.capital:,.2f}\n"
            f"📊 <b>P/L:</b> {'+' if pnl >= 0 else ''}${pnl:,.2f} ({pnl_pct:+.1f}%)\n\n"
            f"{bar}\n\n"
            f"✅ <b>Wins:</b> {wins}\n"
            f"❌ <b>Losses:</b> {losses}\n"
            f"🎯 <b>Win Rate:</b> {win_rate:.0f}%\n"
            f"🕸️ <b>Total Trades:</b> {total}"
        )
        self.send_alert(msg, chat_id=chat_id)

    def _cmd_mode(self, chat_id):
        mode_info = {
            'TARGETED': '🎯 Targeted — Snipe specific Contract Addresses',
            'SCANNER': '🔍 Scanner — Broad scan via DexScreener REST API',
            'MEMPOOL_STREAM': '⚡ Mempool Stream — Simulated WebSocket real-time',
            'COPY_TRADE': '🐋 Copy Trade — Following whale wallets',
        }
        desc = mode_info.get(SNIPER_MODE, SNIPER_MODE)
        msg = (
            f"⚙️ <b>SNIPER MODE</b>\n"
            f"{'━' * 24}\n\n"
            f"<b>Active:</b> <code>{SNIPER_MODE}</code>\n"
            f"{desc}\n\n"
            f"<i>Ubah mode di config.py lalu restart bot.</i>"
        )
        self.send_alert(msg, chat_id=chat_id)

    # ──────────────────────────────────────────
    # ALERT HELPERS (same as before)
    # ──────────────────────────────────────────
    def alert_buy(self, symbol: str, address: str, price: float, invested: float):
        msg = (
            f"🟢 <b>NEW SNIPE EXECUTED</b>\n\n"
            f"<b>Token:</b> ${symbol}\n"
            f"<b>CA:</b> <code>{address}</code>\n"
            f"<b>Price:</b> ${price:.8f}\n"
            f"<b>Size:</b> ${invested:.2f}\n\n"
            f"<i>Jito Bundle sent. Waiting for Moonbag...</i> 🚀"
        )
        self.send_alert(msg)

    def alert_tp(self, tier: str, multiplier: float, symbol: str, sold_val: float):
        emoji = "🛡️" if "TP1" in tier else ("💸" if "TP2" in tier else ("🔥" if "TP3" in tier else "🎆"))
        msg = (
            f"{emoji} <b>TAKE PROFIT HIT: {tier}</b>\n\n"
            f"<b>Token:</b> ${symbol}\n"
            f"<b>Multiplier:</b> {multiplier:.1f}x\n"
            f"<b>Secured:</b> ${sold_val:.2f}\n"
        )
        self.send_alert(msg)

    def alert_panic(self, symbol: str, sold_val: float, type_str: str):
        msg = (
            f"🚨 <b>{type_str} TRIGGERED</b>\n\n"
            f"<b>Token:</b> ${symbol}\n"
            f"<b>Secured:</b> ${sold_val:.2f}\n"
            f"<i>Position closed fully.</i>"
        )
        self.send_alert(msg)

