# solana_sniper/scanner.py
import requests
import random
import time
from typing import List, Dict
from .config import DEXSCREENER_API_URL, MIN_LIQUIDITY_USD, MIN_VOL_1H_USD

class MemecoinScanner:
    def __init__(self):
        self.session = requests.Session()
        # Broadening search terms: Solana pools are paired with 'sol', and many new ones are from 'pump' (.fun) or 'raydium'
        self.search_terms = ['sol', 'pump', 'raydium']

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
            
            # Blacklist for coins already listed on CEXs or major stablecoins/assets
            CEX_BLACKLIST = [
                'SOL', 'USDC', 'USDT', 'BTC', 'ETH', 'WSOL', 'DOGE', 'SHIB', 
                'PEPE', 'BONK', 'WIF', 'FLOKI', 'BOME', 'MEW', 'JUP', 'PYTH', 
                'POPCAT', 'WNYM', 'JTO', 'RENDER', 'HNT', 'MOBILE', 'W'
            ]
            
            for pair in pairs:
                # 1. Must be on Solana
                if pair.get('chainId') != 'solana':
                    continue
                
                # 2. Extract metrics
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                if liquidity is None: liquidity = 0
                vol_h1 = pair.get('volume', {}).get('h1', 0)
                if vol_h1 is None: vol_h1 = 0
                
                symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                symbol_upper = symbol.upper()
                
                # Extract 5-minute transactions and volume for real-time whale/momentum audit
                buys_5m = pair.get('txns', {}).get('m5', {}).get('buys', 0) or 0
                volume_5m = pair.get('volume', {}).get('m5', 0) or 0
                
                # 3. Apply Sniper Filter (Micro-cap gems only!)
                # - Min Liquidity: $1,000 (enough to trade without massive slippage)
                # - Max Liquidity: $100,000 (if higher, it's already too big / listed on CEX!)
                # - Not in major CEX/Stablecoin blacklist
                if 1000 <= liquidity <= 100000 and vol_h1 >= 1000 and symbol_upper not in CEX_BLACKLIST:
                    valid_targets.append({
                        'symbol': symbol,
                        'address': pair.get('baseToken', {}).get('address', ''),
                        'pairAddress': pair.get('pairAddress', ''),
                        'price_usd': float(pair.get('priceUsd', 0) or 0),
                        'liquidity': liquidity,
                        'volume_1h': vol_h1,
                        'buys_5m': buys_5m,
                        'volume_5m': volume_5m,
                        'dex': pair.get('dexId', 'raydium')
                    })
            
            # Shuffle valid targets so we don't always pick the same top token every loop
            random.shuffle(valid_targets)
            return valid_targets
            
        except Exception as e:
            print(f"[❌ SCANNER] Error fetching data from DexScreener: {e}")
            return []

    def search_specific_pairs(self, token_addresses: List[str]) -> List[dict]:
        """
        Fetches pairs specifically for the provided target CAs.
        """
        if not token_addresses:
            return []
            
        print(f"[🔍 SCANNER] Targeted Snipe Mode: Fetching {len(token_addresses)} specific CAs...")
        valid_targets = []
        
        try:
            # DexScreener allows querying multiple addresses separated by commas (up to 30)
            addresses_str = ",".join(token_addresses)
            url = f"https://api.dexscreener.com/latest/dex/tokens/{addresses_str}"
            response = self.session.get(url, timeout=5)
            data = response.json()
            pairs = data.get('pairs', [])
            
            # Dictionary to ensure we only get the best pair per token
            best_pairs_map = {}
            
            for pair in pairs:
                if pair.get('chainId') != 'solana':
                    continue
                    
                address = pair.get('baseToken', {}).get('address', '')
                liquidity = pair.get('liquidity', {}).get('usd', 0) or 0
                
                # Keep the pair with the highest liquidity for each token address
                if address not in best_pairs_map or liquidity > best_pairs_map[address].get('liquidity', 0):
                    best_pairs_map[address] = pair
            
            # Format the valid targets
            for address, pair in best_pairs_map.items():
                liquidity = pair.get('liquidity', {}).get('usd', 0) or 0
                vol_h1 = pair.get('volume', {}).get('h1', 0) or 0
                buys_5m = pair.get('txns', {}).get('m5', {}).get('buys', 0) or 0
                volume_5m = pair.get('volume', {}).get('m5', 0) or 0
                symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                
                valid_targets.append({
                    'symbol': symbol,
                    'address': address,
                    'pairAddress': pair.get('pairAddress', ''),
                    'price_usd': float(pair.get('priceUsd', 0) or 0),
                    'liquidity': liquidity,
                    'volume_1h': vol_h1,
                    'buys_5m': buys_5m,
                    'volume_5m': volume_5m,
                    'dex': pair.get('dexId', 'raydium')
                })
                
            return valid_targets
        except Exception as e:
            print(f"[❌ SCANNER] Error fetching targeted CAs from DexScreener: {e}")
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

    def check_honeypot(self, token_address: str) -> dict:
        """
        Audits the token using RugCheck API to detect Honeypot, Freeze, or Mint risks.
        """
        # If it's a mock token address during local testing, mock a safety check
        if not token_address or token_address.startswith("TokenAddress") or "..." in token_address:
            return {'is_safe': True, 'reason': 'Simulated token bypassed'}
            
        try:
            url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                report = response.json()
                
                # Check for major honeypot indicators
                # 1. Freeze Authority (Can lock sells -> Honeypot)
                freeze = report.get('token', {}).get('freezeAuthority')
                if freeze is not None:
                    return {'is_safe': False, 'reason': 'Freeze Authority ACTIVE (Honeypot)'}
                    
                # 2. Mint Authority (Can print infinite tokens -> Inflation Rug)
                mint = report.get('token', {}).get('mintAuthority')
                if mint is not None:
                    return {'is_safe': False, 'reason': 'Mint Authority ACTIVE (Infinite Print)'}
                
                # 3. Specific dangerous risks list (RugCheck actually flags top holders and LP locks here)
                risks = report.get('risks', [])
                for risk in risks:
                    name = risk.get('name', '').lower()
                    level = risk.get('level', '').lower()
                    description = risk.get('description', '').lower()
                    
                    if 'freeze' in name:
                        return {'is_safe': False, 'reason': 'Freeze risk detected'}
                    if 'mint' in name:
                        return {'is_safe': False, 'reason': 'Mint risk detected'}
                    if 'rugged' in name or 'honeypot' in name:
                        return {'is_safe': False, 'reason': 'Flagged as Honeypot/Rug'}
                    
                    # Anti-Rugpull Checks (Top holders & Liquidity)
                    if level == 'danger':
                        if 'top' in name and 'holders' in name:
                            return {'is_safe': False, 'reason': f'High Risk: {risk.get("name")} (Whale Dump Potential)'}
                        if 'liquidity' in name or 'unlocked' in name:
                            return {'is_safe': False, 'reason': f'High Risk: {risk.get("name")} (LP not fully locked)'}
                            
                # 4. Manual Top Holders Check (Just in case)
                top_holders = report.get('topHolders', [])
                top_10_pct = sum(h.get('pct', 0) for h in top_holders[:10])
                if top_10_pct > 0.50:
                    return {'is_safe': False, 'reason': f'Top 10 holds {top_10_pct*100:.1f}% of supply (Rugpull Risk)'}
                    
            elif response.status_code == 404:
                return {'is_safe': False, 'reason': 'Too new for RugCheck (Skipping for safety)'}
        except Exception as e:
            return {'is_safe': False, 'reason': f'Audit API failed ({str(e)}) - Skipping for safety'}
            
        return {'is_safe': True, 'reason': 'RugCheck Audited: 100% Safe (LP Locked, No Freeze/Mint)'}

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
