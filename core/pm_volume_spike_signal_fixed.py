#!/usr/bin/env python3
"""
POLYMARKET VOLUME SPIKE SIGNAL - FIXED VERSION
Uses correct API endpoint with actual price data
"""

import requests
import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import statistics

class VolumeSpikePMSignalFixed:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor', 
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Polymarket API endpoints
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        
        # Signal parameters (more realistic after analysis)
        self.volume_multiplier = 1.5  # Reduced from 3.0
        self.min_probability_move = 0.02  # Reduced from 0.05 (2%)
        self.min_volume = 1000  # Minimum volume to consider
        
    def get_active_markets_with_prices(self) -> List[Dict]:
        """Fetch active markets with actual price data"""
        try:
            url = f"{self.gamma_api_base}/markets"
            params = {
                'closed': 'false',
                'active': 'true',
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            markets = response.json()
            
            # Filter for markets with actual price data
            valid_markets = []
            for market in markets:
                outcome_prices = market.get('outcomePrices', '["0", "0"]')
                
                try:
                    import json
                    prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                    
                    if len(prices) >= 2:
                        yes_price = float(prices[0])
                        no_price = float(prices[1])
                        
                        # Valid market if prices are not both 0 and sum close to 1
                        if yes_price > 0 and no_price > 0 and 0.8 <= (yes_price + no_price) <= 1.2:
                            valid_markets.append(market)
                            
                except:
                    # Also try lastTradePrice as alternative
                    last_price = market.get('lastTradePrice', 0)
                    if last_price and float(last_price) > 0:
                        valid_markets.append(market)
            
            print(f"📊 Found {len(markets)} total markets, {len(valid_markets)} with valid prices")
            return valid_markets
            
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def detect_volume_spike_signal(self, market: Dict) -> Optional[Dict]:
        """
        Detect volume spike + probability move signal with corrected data
        """
        try:
            market_id = market.get('id')
            if not market_id:
                return None
            
            # Get price data
            outcome_prices = market.get('outcomePrices', '["0", "0"]')
            last_trade_price = market.get('lastTradePrice', 0)
            
            current_price = None
            
            # Try to parse outcome prices first
            try:
                import json
                prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                if len(prices) >= 2:
                    yes_price = float(prices[0])
                    if 0 < yes_price < 1:
                        current_price = yes_price
            except:
                pass
            
            # Fallback to last trade price
            if current_price is None and last_trade_price:
                last_price = float(last_trade_price)
                if 0 < last_price < 1:
                    current_price = last_price
            
            if current_price is None:
                return None
            
            # Get volume data
            volume = float(market.get('volumeNum', 0) or market.get('volume', 0) or 0)
            volume_24h = float(market.get('volume24hr', 0) or 0)
            
            if volume < self.min_volume:
                return None
            
            # Calculate volume ratio
            if volume_24h > 0:
                volume_ratio = volume / volume_24h
            else:
                # If no 24h data, use current volume as indicator
                volume_ratio = 2.0  # Assume moderate activity
            
            # Check volume spike
            volume_spike = volume_ratio >= self.volume_multiplier
            
            # Check price movement (deviation from 50%)
            price_deviation = abs(current_price - 0.5)
            significant_move = price_deviation >= self.min_probability_move
            
            if volume_spike and significant_move:
                # Determine signal direction
                direction = 'YES' if current_price < 0.5 else 'NO'
                confidence = min(0.75, 0.55 + (volume_ratio - 1.5) * 0.05 + price_deviation * 0.5)
                
                signal = {
                    'signal_type': 'volume_spike_fixed',
                    'market_id': market_id,
                    'market_title': market.get('question', 'Unknown'),
                    'direction': direction,
                    'current_price': current_price,
                    'volume_ratio': volume_ratio,
                    'price_deviation': price_deviation,
                    'volume': volume,
                    'confidence': confidence,
                    'timestamp': datetime.now(),
                    'reasoning': f"Volume {volume_ratio:.1f}x + {price_deviation:.1%} deviation + ${volume:,.0f} volume"
                }
                
                return signal
                
        except Exception as e:
            print(f"❌ Error detecting signal for market {market_id}: {e}")
            
        return None
    
    def scan_all_markets(self) -> List[Dict]:
        """Scan all active markets for volume spike signals"""
        print(f"🔍 Scanning Polymarket for volume spike signals (FIXED VERSION)...")
        
        markets = self.get_active_markets_with_prices()
        if not markets:
            print("❌ No market data available")
            return []
        
        signals = []
        markets_analyzed = 0
        
        for market in markets:
            markets_analyzed += 1
            signal = self.detect_volume_spike_signal(market)
            if signal:
                signals.append(signal)
                print(f"🚨 SIGNAL DETECTED: {signal['market_title'][:50]}... - {signal['direction']} @ {signal['current_price']:.2%}")
                print(f"   Volume: ${signal['volume']:,.0f} ({signal['volume_ratio']:.1f}x) | Deviation: {signal['price_deviation']:.1%}")
        
        print(f"📊 Analyzed {markets_analyzed} markets with prices, found {len(signals)} volume spike signals")
        return signals
    
    def store_signal(self, signal: Dict) -> bool:
        """Store signal in database"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS pm_signals_fixed (
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
                            volume_ratio DECIMAL(8,2),
                            price_deviation DECIMAL(5,3),
                            volume_amount DECIMAL(15,2)
                        )
                    """)
                    
                    cursor.execute("""
                        INSERT INTO pm_signals_fixed 
                        (signal_type, market_id, market_title, direction, current_price, 
                         confidence, reasoning, volume_ratio, price_deviation, volume_amount)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        signal['signal_type'],
                        signal['market_id'],
                        signal['market_title'],
                        signal['direction'],
                        signal['current_price'],
                        signal['confidence'],
                        signal['reasoning'],
                        signal['volume_ratio'],
                        signal['price_deviation'],
                        signal['volume']
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ Error storing signal: {e}")
            return False

if __name__ == "__main__":
    # Test the FIXED signal detection
    detector = VolumeSpikePMSignalFixed()
    
    print("🧪 TESTING POLYMARKET VOLUME SPIKE SIGNAL (FIXED)")
    print("=" * 60)
    
    signals = detector.scan_all_markets()
    
    if signals:
        print(f"\n🎯 FOUND {len(signals)} SIGNALS:")
        for signal in signals:
            print(f"📊 {signal['market_title'][:60]}...")
            print(f"   Direction: {signal['direction']} | Price: {signal['current_price']:.1%} | Confidence: {signal['confidence']:.1%}")
            print(f"   Volume: ${signal['volume']:,.0f} | Ratio: {signal['volume_ratio']:.1f}x | Deviation: {signal['price_deviation']:.1%}")
            print(f"   Reasoning: {signal['reasoning']}")
            
            # Store in database
            detector.store_signal(signal)
            print(f"   ✅ Stored in database")
            print()
    else:
        print("❌ No volume spike signals detected")
        print("🔧 Consider adjusting parameters:")
        print(f"   - Volume multiplier: {detector.volume_multiplier}x (try 1.2x)")
        print(f"   - Price deviation: {detector.min_probability_move:.1%} (try 1%)")
        print(f"   - Min volume: ${detector.min_volume:,} (try $500)")
        
    print("🧪 Fixed signal test complete!")