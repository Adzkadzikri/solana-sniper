# solana_sniper/social_tracker.py
import random
from .config import REQUIRED_SOCIAL_HYPE

class SocialSentimentTracker:
    def __init__(self):
        pass

    def evaluate_hype(self, target: dict) -> dict:
        """
        Audits the real-time transaction count and volume in the last 5 minutes 
        to identify whale activity and strong buying momentum.
        """
        symbol = target['symbol']
        buys_5m = target.get('buys_5m', 0)
        vol_5m = target.get('volume_5m', 0)
        
        print(f"[🐦 SOCIAL] Analyzing real-time Solana on-chain momentum for ${symbol}...")
        
        # Dynamic momentum scoring:
        # - Each buy transaction in 5m gives +2 points (up to 60 points)
        # - Each $100 of 5m volume gives +5 points (up to 40 points)
        txn_score = min(buys_5m * 2, 60)
        vol_score = min((vol_5m / 100) * 5, 40)
        
        hype_score = int(txn_score + vol_score)
        
        # Whales: HIGH if volume in 5 mins is over $1,500 OR buy txns > 20
        whale_activity = "HIGH" if (vol_5m >= 1500 or buys_5m >= 20) else "LOW"
        
        print(f"   => Real Trade Score: {hype_score}/100 | 5M Buys: {buys_5m} | 5M Volume: ${vol_5m:.2f} | Whales: {whale_activity}")
        
        # Approved if hype score passes threshold
        is_approved = hype_score >= REQUIRED_SOCIAL_HYPE or whale_activity == "HIGH"
        
        return {
            'hype_score': hype_score,
            'whale_activity': whale_activity,
            'is_approved': is_approved
        }
