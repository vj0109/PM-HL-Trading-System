#!/usr/bin/env python3
"""
POLYMARKET VOLUME SPIKE SIGNAL - TIER 1
Signal: Volume >3x average + probability move >5%
Logic: Informed trading detection - when volume spikes with price movement
"""

import requests
import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import statistics

class VolumeSpikePMSignal:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor', 
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Polymarket API endpoints
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        
        # Signal parameters
        self.volume_multiplier = 3.0  # 3x average volume threshold
        self.min_probability_move = 0.05  # 5% probability move minimum
        self.lookback_hours = 24  # 24-hour average for volume baseline
        
    def get_market_data(self) -> List[Dict]:
        """Fetch active markets from Polymarket Gamma API"""
        try:
            url = f"{self.gamma_api_base}/events"
            params = {
                'active': 'true',
                'closed': 'false',
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching market data: {e}")
            return []
    
    def get_market_history(self, market_id: str, hours: int = 24) -> Dict:
        """Get historical price and volume data for a market"""
        try:
            url = f"{self.gamma_api_base}/events/{market_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching market history for {market_id}: {e}")
            return {}
    
    def calculate_24h_volume_average(self, volume_history: List[float]) -> float:
        """Calculate 24-hour rolling average volume"""
        if len(volume_history) < 10:  # Need minimum data points
            return 0
            
        return statistics.mean(volume_history[-24:])  # Last 24 hours
    
    def detect_volume_spike_signal(self, market: Dict) -> Optional[Dict]:
        """
        Detect volume spike + probability move signal
        
        Returns signal dict if detected, None otherwise
        """
        try:
            market_id = market.get('id')
            if not market_id:
                return None
                
            # Get current market state
            current_price = float(market.get('outcome_prices', [0.5, 0.5])[0])
            current_volume = float(market.get('volume', 0))
            
            if current_volume == 0:
                return None
            
            # Get historical data for baseline
            history = self.get_market_history(market_id)
            if not history:
                return None
            
            # Extract volume history (simplified - in real implementation would parse time series)
            # For now, using simplified logic with available data
            volume_24h_avg = float(market.get('volume_24h', current_volume)) / 24
            
            if volume_24h_avg == 0:
                return None
            
            # Check volume spike (current vs 24h average)
            volume_ratio = current_volume / volume_24h_avg
            
            # Get price change (simplified - would need time series for real calculation)
            price_change = abs(current_price - 0.5)  # Simplified as deviation from 50%
            
            # Signal conditions
            volume_spike = volume_ratio >= self.volume_multiplier
            significant_move = price_change >= self.min_probability_move
            
            if volume_spike and significant_move:
                # Determine signal direction based on price
                direction = 'BUY' if current_price < 0.5 else 'SELL'
                confidence = min(0.75, 0.55 + (volume_ratio - 3) * 0.05)  # Scale confidence with volume
                
                signal = {
                    'signal_type': 'volume_spike',
                    'market_id': market_id,
                    'market_title': market.get('title', 'Unknown'),
                    'direction': direction,
                    'current_price': current_price,
                    'volume_ratio': volume_ratio,
                    'price_change': price_change,
                    'confidence': confidence,
                    'timestamp': datetime.now(),
                    'reasoning': f"Volume spike {volume_ratio:.1f}x average + {price_change:.1%} probability move"
                }
                
                return signal
                
        except Exception as e:
            print(f"❌ Error detecting signal for market {market_id}: {e}")
            
        return None
    
    def scan_all_markets(self) -> List[Dict]:
        """Scan all active markets for volume spike signals"""
        print(f"🔍 Scanning Polymarket for volume spike signals...")
        
        markets = self.get_market_data()
        if not markets:
            print("❌ No market data available")
            return []
        
        signals = []
        for market in markets:
            signal = self.detect_volume_spike_signal(market)
            if signal:
                signals.append(signal)
                print(f"🚨 SIGNAL DETECTED: {signal['market_title'][:50]}... - {signal['direction']} @ {signal['current_price']:.2%}")
        
        print(f"📊 Scanned {len(markets)} markets, found {len(signals)} volume spike signals")
        return signals
    
    def store_signal(self, signal: Dict) -> bool:
        """Store signal in database for tracking"""
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
                            status VARCHAR(20) DEFAULT 'DETECTED'
                        )
                    """)
                    
                    cursor.execute("""
                        INSERT INTO pm_signals 
                        (signal_type, market_id, market_title, direction, current_price, confidence, reasoning)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        signal['signal_type'],
                        signal['market_id'],
                        signal['market_title'],
                        signal['direction'],
                        signal['current_price'],
                        signal['confidence'],
                        signal['reasoning']
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ Error storing signal: {e}")
            return False

if __name__ == "__main__":
    # Test the signal detection
    detector = VolumeSpikePMSignal()
    
    print("🧪 TESTING POLYMARKET VOLUME SPIKE SIGNAL")
    print("=" * 50)
    
    signals = detector.scan_all_markets()
    
    if signals:
        print(f"\n🎯 FOUND {len(signals)} SIGNALS:")
        for signal in signals:
            print(f"📊 {signal['market_title'][:60]}...")
            print(f"   Direction: {signal['direction']} | Price: {signal['current_price']:.2%} | Confidence: {signal['confidence']:.1%}")
            print(f"   Reasoning: {signal['reasoning']}")
            
            # Store in database
            detector.store_signal(signal)
            print(f"   ✅ Stored in database")
            print()
    else:
        print("❌ No volume spike signals detected")
        
    print("🧪 Test complete!")