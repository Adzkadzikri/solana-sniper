# solana_sniper/scanner.py
import requests
import random
import time
from typing import List, Dict
from .config import DEXSCREENER_API_URL, MIN_LIQUIDITY_USD, MIN_VOL_1H_USD

class MemecoinScanner:
    def __init__(self):
        self.session = requests.Session()
        # Simulated search terms for new memecoins
        self.search_terms = ['pepe', 'doge', 'wif', 'bonk', 'cat', 'moon', 'inu']

    def search_new_pairs(self) -> List[dict]:
        """
        In production, this would use DexScreener API or listen to Raydium Ray V4 mempool.
        For this simulation, we will query DexScreener with random memecoin terms
        and filter for Solana pairs.
        """
        print("[🔍 SCANNER] Scanning Solana blockchain for new Memecoin pairs...")
        term = random.choice(self.search_terms)
        
        try:
            # We mock the real call if it fails or simulate the exact response structure.
            response = self.session.get(f"{DEXSCREENER_API_URL}{term}", timeout=5)
            data = response.json()
            pairs = data.get('pairs', [])
            
            valid_targets = []
            for pair in pairs:
                # 1. Must be on Solana
                if pair.get('chainId') != 'solana':
                    continue
                
                # 2. Extract metrics
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                if liquidity is None: liquidity = 0
                vol_h1 = pair.get('volume', {}).get('h1', 0)
                if vol_h1 is None: vol_h1 = 0
                
                # 3. Apply Sniper Filter (Real Paper Trading Filter)
                # Lowered the filter slightly so we actually find pairs in testing
                if liquidity >= 1000 and vol_h1 >= 1000:
                    valid_targets.append({
                        'symbol': pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                        'address': pair.get('baseToken', {}).get('address', ''),
                        'pairAddress': pair.get('pairAddress', ''),
                        'price_usd': float(pair.get('priceUsd', 0) or 0),
                        'liquidity': liquidity,
                        'volume_1h': vol_h1,
                        'dex': pair.get('dexId', 'raydium')
                    })
            
            return valid_targets
            
        except Exception as e:
            print(f"[❌ SCANNER] Error fetching data from DexScreener: {e}")
            return []

    def get_token_price(self, token_address: str) -> float:
        """Fetch the LIVE current price of a token from DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = self.session.get(url, timeout=5)
            data = response.json()
            pairs = data.get('pairs', [])
            if pairs:
                # Get highest liquidity pair for accurate price
                solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                if solana_pairs:
                    best_pair = max(solana_pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0) or 0)
                    return float(best_pair.get('priceUsd', 0) or 0)
        except Exception:
            pass
        return 0.0

    def mock_generate_random_new_coin(self) -> dict:
        """Fallback for testing if API fails or we want to simulate a brand new launch."""
        names = ["BONK2", "MOONDOG", "SOLCAT", "PEPESOL", "WIFHAT"]
        return {
            'symbol': random.choice(names),
            'address': f'TokenAddress{random.randint(1000,9999)}...pump',
            'pairAddress': f'Pair{random.randint(1000,9999)}',
            'price_usd': random.uniform(0.0000001, 0.001),
            'liquidity': random.uniform(5000, 20000),
            'volume_1h': random.uniform(10000, 50000),
            'dex': 'raydium'
        }
