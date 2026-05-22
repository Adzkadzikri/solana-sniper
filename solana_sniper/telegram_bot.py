import requests
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        # Test if token is configured
        if not self.token or self.token == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or not self.chat_id:
            print("[📱 TELEGRAM] Bot Token or Chat ID not configured. Running in Mock Mode.")
            self.is_active = False
        else:
            print("[📱 TELEGRAM] Initialized successfully. Real alerts are ON.")
            self.is_active = True

    def send_alert(self, message: str, is_html=True):
        """Sends a message to the configured Telegram Chat."""
        # Always print to console first
        print(f"\n[📱 TELEGRAM MOCK LOG]\n{message}\n")
        
        if not self.is_active:
            return False
            
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True
        }
        
        if is_html:
            payload["parse_mode"] = "HTML"
            
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            if response.status_code != 200:
                print(f"[📱 TELEGRAM] Failed to send message: {response.text}")
                return False
            return True
        except Exception as e:
            print(f"[📱 TELEGRAM] Exception sending message: {e}")
            return False

    # Helper methods for specific events
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
