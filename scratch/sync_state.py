import requests
import json

space_api_url = "https://jncjs-solana-sniper.hf.space/api/data"
kvdb_url = "https://kvdb.io/W4M8jncjssolanasniper99/state"

print("[SYNC] Fetching current running state from Hugging Face Space...")
try:
    response = requests.get(space_api_url, timeout=10)
    if response.status_code == 200:
        state = response.json()
        print("[SYNC] Successfully retrieved running state:")
        print(json.dumps(state, indent=2))
        
        # We need to map 'trades' from response to 'active_trades' in our KVDB schema
        backup_data = {
            'capital': state.get('capital', 40.0),
            'active_trades': state.get('trades', []),
            'nets_thrown': state.get('nets_thrown', 0)
        }
        
        print("[SYNC] Pushing state to persistent cloud KVDB...")
        post_resp = requests.post(kvdb_url, json=backup_data, timeout=10)
        if post_resp.status_code == 200 or post_resp.status_code == 201:
            print("[SYNC] State successfully backed up to KVDB! We are ready to redeploy safely.")
        else:
            print(f"[SYNC] Failed to push to KVDB: {post_resp.status_code} - {post_resp.text}")
    else:
        print(f"[SYNC] Space API returned status code: {response.status_code}. Is it running?")
except Exception as e:
    print(f"[SYNC] Error syncing state: {e}")
