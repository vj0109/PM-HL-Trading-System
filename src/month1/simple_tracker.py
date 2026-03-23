#!/usr/bin/env python3
"""
Simple Market Tracker - Month 1 Week 1-2
Simplified version following exact strategy specifications
"""

import requests
import json
import psycopg2
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplePolymarketTracker:
    """Simplified tracker matching ML strategy specifications exactly"""
    
    def __init__(self):
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
    def get_active_markets(self, limit=20):
        """Get highest volume active markets with <30 day filter"""
        try:
            # Get more events to ensure we find enough short-term markets
            response = requests.get(f"{self.gamma_api}/events", params={
                "limit": min(limit * 3, 100),  # Get more events to filter from
                "order": "volume24hr", 
                "ascending": "false",
                "active": "true",
                "closed": "false"
            })
            response.raise_for_status()
            
            events = response.json()
            markets = []
            now = datetime.now(timezone.utc)
            
            for event in events:
                event_markets = event.get('markets', [])
                for market in event_markets:
                    if market.get('active', False):
                        # Calculate days to resolution first
                        end_date_str = market.get('endDate')
                        if end_date_str:
                            try:
                                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                days_out = (end_date - now).days
                                
                                # VJ requirement: Only markets resolving in 1-30 days
                                if 1 <= days_out <= 30:
                                    market_data = self.extract_market_features(market)
                                    if market_data:
                                        markets.append(market_data)
                            except Exception:
                                continue
            
            # Sort by volume descending and return top results
            markets.sort(key=lambda x: x['volume_24h'], reverse=True)
            return markets[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def extract_market_features(self, market):
        """Extract relevant features for prediction"""
        try:
            # Parse outcome prices if they're strings
            outcome_prices = market.get('outcomePrices', [])
            if isinstance(outcome_prices, str):
                outcome_prices = json.loads(outcome_prices)
            
            # Get current price (use first outcome price)
            current_price = 0.5  # Default
            if outcome_prices and len(outcome_prices) > 0:
                try:
                    current_price = float(outcome_prices[0])
                except:
                    current_price = 0.5
                    
            # Calculate days to resolution
            end_date_str = market.get('endDate')
            days_to_resolution = 30  # Default
            
            if end_date_str:
                try:
                    if end_date_str.endswith('Z'):
                        end_date_str = end_date_str[:-1] + '+00:00'
                    end_date = datetime.fromisoformat(end_date_str)
                    now = datetime.now(timezone.utc)
                    days_to_resolution = max(1, (end_date - now).days)
                except:
                    days_to_resolution = 30
            
            return {
                "current_price": current_price,
                "volume_24h": float(market.get("volume24hr", 0)),
                "days_to_resolution": days_to_resolution,
                "category": market.get("category", ""),
                "market_cap": float(market.get("liquidityParameter", 0)),
                "market_id": market.get("conditionId", ""),
                "question": market.get("question", ""),
                "total_volume": float(market.get("volume", 0))
            }
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

def test_system():
    """Test the simple tracker system"""
    print("🧪 TESTING SIMPLE MARKET DISCOVERY")
    
    tracker = SimplePolymarketTracker()
    markets = tracker.get_active_markets(limit=5)
    
    print(f"Retrieved {len(markets)} markets")
    
    if markets:
        print("\n📊 SAMPLE MARKETS:")
        for i, market in enumerate(markets[:3], 1):
            print(f"\n{i}. {market['question'][:60]}...")
            print(f"   Price: {market['current_price']:.3f}")
            print(f"   Volume 24h: ${market['volume_24h']:,.0f}")
            print(f"   Days to resolution: {market['days_to_resolution']}")
            print(f"   Category: {market['category'] or 'None'}")
        
        print("\n✅ Simple market discovery working")
        return True
    else:
        print("❌ No markets retrieved")
        return False

if __name__ == "__main__":
    test_system()