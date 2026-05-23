import requests
import time

TOKEN = '8918956228:AAEnqJ_gzoB0cOwZNmJ1JO-NcvJFePAFQwM'
CHAT_ID = '1614448349'
BASE = f'https://api.telegram.org/bot{TOKEN}'

print("=== Telegram Bot Diagnostics ===")

# 1. Check bot info
r = requests.get(f'{BASE}/getMe')
info = r.json().get('result', {})
print(f"Bot: @{info.get('username')} - {info.get('first_name')}")

# 2. Check webhook
r = requests.get(f'{BASE}/getWebhookInfo')
wh = r.json().get('result', {})
print(f"Webhook URL: '{wh.get('url', 'none')}'")
print(f"Pending updates: {wh.get('pending_update_count', 0)}")

# 3. Check getUpdates
r = requests.get(f'{BASE}/getUpdates?limit=10')
updates = r.json().get('result', [])
print(f"Pending updates in queue: {len(updates)}")
for u in updates:
    msg = u.get('message', {})
    print(f"  [update_id={u['update_id']}] Text='{msg.get('text','')}' from chat_id={msg.get('chat',{}).get('id')}")

# 4. Send test message
print("\nSending test message to user...")
r = requests.post(f'{BASE}/sendMessage', json={
    'chat_id': CHAT_ID,
    'parse_mode': 'HTML',
    'text': (
        '<b>Solana Sniper 3.0 ONLINE</b>\n\n'
        'Bot sudah aktif! Coba kirim perintah:\n'
        '/start /status /wallet /nets /history /profit /mode /help\n\n'
        '<i>Bot akan merespons dalam 2-3 detik.</i>'
    )
})
print(f"Send status: {r.status_code} ok={r.json().get('ok')}")
print("\nDone. Coba kirim /status ke bot sekarang!")
