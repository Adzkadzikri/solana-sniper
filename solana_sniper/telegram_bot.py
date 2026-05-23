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

    @staticmethod
    def _format_duration(ms_start, ms_end=None):
        """Converts millisecond timestamps into a human-readable duration string."""
        import time as _time
        if not ms_start:
            return "?"
        end = ms_end if ms_end else _time.time() * 1000
        seconds = int((end - ms_start) / 1000)
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m {seconds % 60}s"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h {minutes % 60}m"
        days = hours // 24
        return f"{days}d {hours % 24}h"

    @staticmethod
    def _get_status_label(net):
        """Returns a human-readable label + emoji for a net's status."""
        status = net.get('status', '')
        labels = {
            'RUGPULL_SOLD':     ('💀', 'RUGPULL'),
            'ATH_GUARD_SOLD':   ('🚨', 'ATH GUARD SELL'),
            'TP4_MOONSHOT_SOLD':('🎆', 'MOONSHOT 100x'),
            'HOLDING':          ('⏳', 'HOLDING'),
            'RIDING_TO_5X':     ('🚀', 'RIDING → 5x'),
            'RIDING_TO_20X':    ('🔥', 'RIDING → 20x'),
            'RIDING_TO_100X':   ('🌙', 'MOONBAG → 100x'),
        }
        # TP partial sells
        if status not in labels:
            if 'TP4' in status:
                return ('🎆', 'TP4 (100x)')
            if 'TP3' in status:
                return ('🔥', 'TP3 (20x)')
            if 'TP2' in status:
                return ('💸', 'TP2 (5x)')
            if 'TP1' in status:
                return ('🛡️', 'TP1 (2x)')
            return ('✅', status)
        return labels[status]

    def _cmd_nets(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap...", chat_id=chat_id)
            return
        t = self._trader
        
        if not t.active_nets:
            self.send_alert(
                "🕸️ <b>Active Nets (Holding)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>No active nets currently cast.\n"
                "Bot sedang scan peluang...</i>",
                chat_id=chat_id
            )
            return
        
        import time as _time
        now_ms = _time.time() * 1000
        
        lines = [f"🕸️ <b>Active Nets ({len(t.active_nets)} Holding)</b>\n{'━' * 24}"]
        
        for i, net in enumerate(t.active_nets, 1):
            emoji, label = self._get_status_label(net)
            ca_short = (
                net['address'][:6] + '...' + net['address'][-4:]
                if len(net.get('address', '')) > 10 else net.get('address', '?')
            )

            buy_price  = net.get('buy_price', 0) or 0
            orig_inv   = net.get('original_invested', net.get('invested', 1)) or 1

            # Current multiplier from ATH price (best-known price)
            ath_price  = net.get('ath_price', buy_price) or buy_price
            ath_mult   = (ath_price / buy_price) if buy_price > 0 else 1.0

            # Unrealized P/L % based on current invested value vs original
            curr_inv   = net.get('invested', orig_inv)
            pnl_pct    = ((curr_inv / orig_inv) - 1) * 100 if orig_inv > 0 else 0
            pnl_arrow  = "📈" if pnl_pct >= 0 else "📉"
            pnl_str    = f"{pnl_arrow} {pnl_pct:+.1f}%"

            # Hold duration
            buy_ts  = net.get('buy_timestamp')
            duration = self._format_duration(buy_ts, now_ms)

            # TPs achieved
            tps_done = sum([
                net.get('tp1_done', False),
                net.get('tp2_done', False),
                net.get('tp3_done', False),
                net.get('tp4_done', False),
            ])
            tp_bar = "✅" * tps_done + "⬜" * (4 - tps_done)

            lines.append(
                f"\n{emoji} <b>#{i} ${net['symbol']}</b>  —  <code>{label}</code>\n"
                f"   ⏱ Hold: <b>{duration}</b>\n"
                f"   💰 Invested: ${orig_inv:.3f}  →  Remaining: ${curr_inv:.3f}\n"
                f"   📊 P/L: <b>{pnl_str}</b>   ATH: {ath_mult:.2f}x\n"
                f"   🎯 TPs: {tp_bar}  ({tps_done}/4 hit)\n"
                f"   🔑 Buy @ ${buy_price:.8f}\n"
                f"   📋 CA: <code>{ca_short}</code>"
            )
        
        self.send_alert("\n".join(lines), chat_id=chat_id)

    def _cmd_history(self, chat_id):
        if not self._trader:
            self.send_alert("⏳ Bot belum siap...", chat_id=chat_id)
            return
        t = self._trader
        
        if not t.past_nets:
            self.send_alert("📜 <b>Past Holdings (History)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n<i>Belum ada riwayat trade.</i>", chat_id=chat_id)
            return
        
        recent = list(reversed(t.past_nets[-10:]))
        lines = [f"📜 <b>Past Holdings — Last {len(recent)} Trades</b>\n{'━' * 24}"]

        for i, net in enumerate(recent, 1):
            emoji, label = self._get_status_label(net)

            buy_price  = net.get('buy_price', 0) or 0
            sell_price = net.get('sell_price', 0) or 0
            orig_inv   = net.get('original_invested', net.get('invested', 1)) or 1

            # P/L% from sell_price vs buy_price
            if sell_price > 0 and buy_price > 0:
                pnl_mult = sell_price / buy_price
                pnl_pct  = (pnl_mult - 1) * 100
            else:
                # Fallback: estimate from invested remaining
                curr_inv = net.get('invested', 0) or 0
                pnl_pct  = ((curr_inv / orig_inv) - 1) * 100 if orig_inv > 0 else 0
                pnl_mult = pnl_pct / 100 + 1

            pnl_arrow  = "📈" if pnl_pct >= 0 else "📉"
            pnl_str    = f"{pnl_arrow} {pnl_pct:+.1f}% ({pnl_mult:.2f}x)"

            # Hold duration
            buy_ts  = net.get('buy_timestamp')
            duration = self._format_duration(buy_ts) if buy_ts else "?"

            # TPs achieved badge
            tps_done = sum([
                net.get('tp1_done', False),
                net.get('tp2_done', False),
                net.get('tp3_done', False),
                net.get('tp4_done', False),
            ])
            tp_badges = []
            if net.get('tp1_done'): tp_badges.append("TP1✅")
            if net.get('tp2_done'): tp_badges.append("TP2✅")
            if net.get('tp3_done'): tp_badges.append("TP3✅")
            if net.get('tp4_done'): tp_badges.append("TP4✅")
            tp_str = "  ".join(tp_badges) if tp_badges else "—"

            buy_line  = f"${buy_price:.8f}"
            sell_line = f"${sell_price:.8f}" if sell_price > 0 else "N/A"

            lines.append(
                f"\n{emoji} <b>#{i} ${net['symbol']}</b>\n"
                f"   🏷️ Label: <b>{label}</b>\n"
                f"   ⏱ Hold: {duration}\n"
                f"   📊 P/L: <b>{pnl_str}</b>\n"
                f"   🎯 TPs Hit: {tp_str}\n"
                f"   🔑 Buy: {buy_line}  →  Sell: {sell_line}"
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

