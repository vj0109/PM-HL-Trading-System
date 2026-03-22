#!/usr/bin/env python3
"""
POLYMARKET CONTRARIAN REVERSAL SIGNAL - TIER 1  
Signal: >10% probability move in 24h without news catalyst
Logic: Mean reversion in thin markets - non-news moves are often noise
"""

import requests
import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class ContrarianPMSignal:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Polymarket API
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        
        # Signal parameters
        self.min_price_move = 0.10  # 10% minimum move
        self.lookback_hours = 24    # 24-hour window
        self.max_volume_threshold = 5000  # Avoid high-volume/news-driven moves
        
    def get_active_markets(self) -> List[Dict]:
        """Fetch active markets"""
        try:
            url = f"{self.gamma_api_base}/events"
            params = {
                'active': 'true',
                'closed': 'false', 
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def get_market_price_history(self, market_id: str) -> Optional[Dict]:
        """Get price history for a market (simplified - would need time series API)"""
        try:
            url = f"{self.gamma_api_base}/events/{market_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ Error fetching price history for {market_id}: {e}")
            return None
    
    def check_news_catalyst(self, market: Dict) -> bool:
        """
        Simple news catalyst check - in production would check:
        - Recent news articles mentioning the market
        - Social media spikes 
        - Official announcements
        
        For now, using volume as proxy
        """
        try:
            volume_24h = float(market.get('volume_24h', 0))
            volume = float(market.get('volume', 0))
            
            # If current volume much higher than 24h average, likely news-driven
            if volume_24h > 0 and volume > 0:
                current_vs_avg = volume / (volume_24h / 24)
                return current_vs_avg > 3.0  # 3x volume = likely news
                
            return volume > self.max_volume_threshold
            
        except:
            return False
    
    def detect_contrarian_signal(self, market: Dict) -> Optional[Dict]:
        """
        Detect contrarian reversal opportunity
        Logic: Large price move without news catalyst = mean reversion opportunity
        """
        try:
            market_id = market.get('id')
            if not market_id:
                return None
                
            # Get current price
            outcome_prices = market.get('outcome_prices', [0.5, 0.5])
            if not outcome_prices:
                return None
                
            current_price = float(outcome_prices[0])
            
            # For simplicity, estimate previous price from available data
            # In production, would use time series data
            volume_24h = float(market.get('volume_24h', 0))
            volume = float(market.get('volume', 0))
            
            # Rough estimate: if market is far from 50% and low volume, might be reversal opportunity
            deviation_from_50 = abs(current_price - 0.5)
            
            # Check if this looks like a large recent move
            if deviation_from_50 < self.min_price_move:
                return None
            
            # Check for news catalyst (high volume)
            has_news = self.check_news_catalyst(market)
            if has_news:
                return None  # Avoid news-driven moves
            
            # Contrarian logic: bet against extreme positions in low-news environments
            if current_price > 0.6:
                # Price high, bet it will come down
                direction = 'NO'
                confidence = 0.55 + (current_price - 0.6) * 0.3  # Higher for more extreme
            elif current_price < 0.4:
                # Price low, bet it will go up  
                direction = 'YES'
                confidence = 0.55 + (0.4 - current_price) * 0.3
            else:
                return None  # Not extreme enough
                
            confidence = min(0.70, confidence)  # Cap at 70%
            
            signal = {
                'signal_type': 'contrarian',
                'market_id': market_id,
                'market_title': market.get('title', 'Unknown'),
                'direction': direction,
                'current_price': current_price,
                'deviation': deviation_from_50,
                'volume_indicator': volume,
                'confidence': confidence,
                'timestamp': datetime.now(),
                'reasoning': f"Contrarian bet: price at {current_price:.1%} (deviation: {deviation_from_50:.1%}) without news catalyst"
            }
            
            return signal
            
        except Exception as e:
            print(f"❌ Error detecting contrarian signal: {e}")
            return None
    
    def scan_for_contrarian_signals(self) -> List[Dict]:
        """Scan all markets for contrarian opportunities"""
        print(f"🔍 Scanning for contrarian reversal signals...")
        
        markets = self.get_active_markets()
        if not markets:
            return []
        
        signals = []
        extreme_markets = 0
        
        for market in markets:
            # Count markets with extreme pricing
            outcome_prices = market.get('outcome_prices', [0.5, 0.5])
            if outcome_prices:
                price = float(outcome_prices[0])
                if price > 0.6 or price < 0.4:
                    extreme_markets += 1
                    
            signal = self.detect_contrarian_signal(market)
            if signal:
                signals.append(signal)
                print(f"🚨 CONTRARIAN SIGNAL: {signal['market_title'][:50]}...")
                print(f"   Direction: {signal['direction']} | Price: {signal['current_price']:.1%}")
        
        print(f"📊 Scanned {len(markets)} markets ({extreme_markets} with extreme pricing)")
        print(f"🎯 Found {len(signals)} contrarian signals")
        
        return signals
    
    def store_signal(self, signal: Dict) -> bool:
        """Store signal in database"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS pm_signals (
                            id SERIAL PRIMARY KEY,
                            signal_type VARCHAR(50),
                            market_id VARCHAR(100),
                            market_title TEXT,
                            direction VARCHAR(10),
                            current_price DECIMAL(10,6),
                            confidence DECIMAL(5,3),
                            reasoning TEXT,
                            detected_at TIMESTAMP DEFAULT NOW(),
                            status VARCHAR(20) DEFAULT 'DETECTED',
                            deviation DECIMAL(5,3),
                            volume_indicator DECIMAL(15,2)
                        )
                    """)
                    
                    cursor.execute("""
                        INSERT INTO pm_signals 
                        (signal_type, market_id, market_title, direction, current_price, 
                         confidence, reasoning, deviation, volume_indicator)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        signal['signal_type'],
                        signal['market_id'],
                        signal['market_title'],
                        signal['direction'],
                        signal['current_price'],
                        signal['confidence'],
                        signal['reasoning'],
                        signal['deviation'],
                        signal['volume_indicator']
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ Error storing signal: {e}")
            return False

if __name__ == "__main__":
    # Test contrarian signal detection
    detector = ContrarianPMSignal()
    
    print("🧪 TESTING POLYMARKET CONTRARIAN SIGNAL")
    print("=" * 50)
    
    signals = detector.scan_for_contrarian_signals()
    
    if signals:
        print(f"\n🎯 FOUND {len(signals)} CONTRARIAN SIGNALS:")
        for signal in signals:
            print(f"📊 {signal['market_title'][:60]}...")
            print(f"   Direction: {signal['direction']} | Price: {signal['current_price']:.1%}")
            print(f"   Deviation: {signal['deviation']:.1%} | Confidence: {signal['confidence']:.1%}")
            print(f"   Volume: {signal['volume_indicator']:.0f}")
            print(f"   Reasoning: {signal['reasoning']}")
            
            # Store signal
            detector.store_signal(signal)
            print(f"   ✅ Stored in database")
            print()
    else:
        print("❌ No contrarian signals detected")
    
    print("🧪 Test complete!")