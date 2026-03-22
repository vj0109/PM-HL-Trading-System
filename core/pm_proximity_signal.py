#!/usr/bin/env python3
"""
POLYMARKET RESOLUTION PROXIMITY SIGNAL - TIER 1
Signal: Markets at ~50% with <48h to resolution
Logic: Mathematical 2:1 odds when time is short and market uncertain
"""

import requests
import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import dateutil.parser

class ProximityPMSignal:
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
        self.max_hours_to_resolution = 48  # 48 hours maximum
        self.min_hours_to_resolution = 2   # 2 hours minimum (avoid manipulation)
        self.price_range_min = 0.35        # 35% minimum
        self.price_range_max = 0.65        # 65% maximum (around 50%)
        
    def get_active_markets(self) -> List[Dict]:
        """Fetch active markets approaching resolution"""
        try:
            url = f"{self.gamma_api_base}/events"
            params = {
                'active': 'true',
                'closed': 'false',
                'limit': 200
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def parse_resolution_time(self, market: Dict) -> Optional[datetime]:
        """Extract resolution time from market data"""
        try:
            # Try different possible fields for resolution time
            end_date_iso = market.get('end_date_iso')
            if end_date_iso:
                return dateutil.parser.parse(end_date_iso)
                
            # Fallback to other date fields
            for field in ['end_date', 'resolve_date', 'resolution_date']:
                if market.get(field):
                    return dateutil.parser.parse(market[field])
                    
            return None
            
        except Exception as e:
            print(f"❌ Error parsing resolution time: {e}")
            return None
    
    def calculate_time_to_resolution(self, resolution_time: datetime) -> float:
        """Calculate hours until resolution"""
        now = datetime.now(resolution_time.tzinfo) if resolution_time.tzinfo else datetime.utcnow()
        time_diff = resolution_time - now
        return time_diff.total_seconds() / 3600  # Convert to hours
    
    def detect_proximity_signal(self, market: Dict) -> Optional[Dict]:
        """
        Detect resolution proximity signal
        Logic: Market near 50% with <48h but >2h to resolution = 2:1 odds opportunity
        """
        try:
            market_id = market.get('id')
            if not market_id:
                return None
            
            # Get current price (YES outcome)
            outcome_prices = market.get('outcome_prices', [0.5, 0.5])
            if not outcome_prices:
                return None
                
            current_price = float(outcome_prices[0])
            
            # Check if price is in target range (around 50%)
            if not (self.price_range_min <= current_price <= self.price_range_max):
                return None
            
            # Get resolution time
            resolution_time = self.parse_resolution_time(market)
            if not resolution_time:
                return None
            
            # Calculate time to resolution
            hours_to_resolution = self.calculate_time_to_resolution(resolution_time)
            
            # Check time window
            if not (self.min_hours_to_resolution <= hours_to_resolution <= self.max_hours_to_resolution):
                return None
            
            # Determine signal direction (contrarian to avoid late money)
            # If price > 50%, bet NO (market may be overconfident)
            # If price < 50%, bet YES (market may be underconfident)
            if current_price > 0.5:
                direction = 'NO'
                edge_estimate = current_price - 0.5  # How far from 50%
            else:
                direction = 'YES' 
                edge_estimate = 0.5 - current_price
            
            # Calculate confidence based on time pressure and price deviation
            time_factor = 1 - (hours_to_resolution / self.max_hours_to_resolution)  # Closer = higher
            price_factor = edge_estimate * 2  # Further from 50% = less confident
            confidence = 0.55 + (time_factor * 0.15) - (price_factor * 0.10)
            confidence = max(0.50, min(0.75, confidence))  # Clamp between 50-75%
            
            signal = {
                'signal_type': 'proximity',
                'market_id': market_id,
                'market_title': market.get('title', 'Unknown'),
                'direction': direction,
                'current_price': current_price,
                'hours_to_resolution': hours_to_resolution,
                'resolution_time': resolution_time,
                'confidence': confidence,
                'timestamp': datetime.now(),
                'reasoning': f"Market at {current_price:.1%} with {hours_to_resolution:.1f}h to resolution - 2:1 odds opportunity"
            }
            
            return signal
            
        except Exception as e:
            print(f"❌ Error detecting proximity signal: {e}")
            return None
    
    def scan_for_proximity_signals(self) -> List[Dict]:
        """Scan all markets for proximity signals"""
        print(f"🔍 Scanning for resolution proximity signals...")
        
        markets = self.get_active_markets()
        if not markets:
            return []
        
        signals = []
        markets_with_resolution = 0
        
        for market in markets:
            # Check if market has resolution data
            if self.parse_resolution_time(market):
                markets_with_resolution += 1
                
            signal = self.detect_proximity_signal(market)
            if signal:
                signals.append(signal)
                print(f"🚨 PROXIMITY SIGNAL: {signal['market_title'][:50]}...")
                print(f"   Direction: {signal['direction']} | Price: {signal['current_price']:.1%} | Time: {signal['hours_to_resolution']:.1f}h")
        
        print(f"📊 Scanned {len(markets)} markets ({markets_with_resolution} with resolution data)")
        print(f"🎯 Found {len(signals)} proximity signals")
        
        return signals
    
    def store_signal(self, signal: Dict) -> bool:
        """Store signal in database"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Ensure table exists
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
                            hours_to_resolution DECIMAL(8,2),
                            resolution_time TIMESTAMP
                        )
                    """)
                    
                    cursor.execute("""
                        INSERT INTO pm_signals 
                        (signal_type, market_id, market_title, direction, current_price, 
                         confidence, reasoning, hours_to_resolution, resolution_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        signal['signal_type'],
                        signal['market_id'], 
                        signal['market_title'],
                        signal['direction'],
                        signal['current_price'],
                        signal['confidence'],
                        signal['reasoning'],
                        signal['hours_to_resolution'],
                        signal['resolution_time']
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ Error storing signal: {e}")
            return False

if __name__ == "__main__":
    # Test proximity signal detection
    detector = ProximityPMSignal()
    
    print("🧪 TESTING POLYMARKET PROXIMITY SIGNAL")
    print("=" * 50)
    
    signals = detector.scan_for_proximity_signals()
    
    if signals:
        print(f"\n🎯 FOUND {len(signals)} PROXIMITY SIGNALS:")
        for signal in signals:
            print(f"📊 {signal['market_title'][:60]}...")
            print(f"   Direction: {signal['direction']} | Price: {signal['current_price']:.1%}")
            print(f"   Time to resolution: {signal['hours_to_resolution']:.1f} hours")
            print(f"   Confidence: {signal['confidence']:.1%}")
            print(f"   Reasoning: {signal['reasoning']}")
            
            # Store signal
            detector.store_signal(signal)
            print(f"   ✅ Stored in database")
            print()
    else:
        print("❌ No proximity signals detected")
    
    print("🧪 Test complete!")