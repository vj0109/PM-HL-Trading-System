#!/usr/bin/env python3
"""
API DATA EXPLORER
Investigate actual Polymarket API data structure to understand why signals aren't firing
"""

import requests
import json
from typing import Dict, List

class APIDataExplorer:
    def __init__(self):
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        self.clob_api_base = 'https://clob.polymarket.com'
    
    def explore_gamma_api_structure(self):
        """Explore Gamma API data structure"""
        print("🔍 EXPLORING GAMMA API DATA STRUCTURE")
        print("=" * 50)
        
        try:
            # Get a few active markets
            url = f"{self.gamma_api_base}/events"
            params = {'active': 'true', 'limit': 5}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            markets = response.json()
            print(f"📊 Found {len(markets)} markets to analyze")
            
            if markets:
                print("\n🎯 SAMPLE MARKET DATA STRUCTURE:")
                sample = markets[0]
                
                print(f"Market ID: {sample.get('id', 'N/A')}")
                print(f"Title: {sample.get('title', 'N/A')}")
                print(f"Active: {sample.get('active', 'N/A')}")
                print(f"Closed: {sample.get('closed', 'N/A')}")
                
                print(f"\n💰 PRICE DATA:")
                print(f"outcome_prices: {sample.get('outcome_prices', 'N/A')}")
                print(f"outcome_tokens: {sample.get('outcome_tokens', 'N/A')}")
                
                print(f"\n📊 VOLUME DATA:")
                print(f"volume: {sample.get('volume', 'N/A')}")
                print(f"volume_24h: {sample.get('volume_24h', 'N/A')}")
                
                print(f"\n📅 TIME DATA:")
                print(f"end_date_iso: {sample.get('end_date_iso', 'N/A')}")
                print(f"start_date_iso: {sample.get('start_date_iso', 'N/A')}")
                
                print(f"\n🏷️ ALL AVAILABLE FIELDS:")
                for key in sorted(sample.keys()):
                    print(f"   {key}: {type(sample[key]).__name__}")
                
                # Show full JSON for first market (truncated)
                print(f"\n📋 FULL MARKET JSON (first market):")
                print(json.dumps(sample, indent=2)[:1500] + "...")
                
            return markets
            
        except Exception as e:
            print(f"❌ Error exploring Gamma API: {e}")
            return []
    
    def explore_clob_api_structure(self):
        """Explore CLOB API data structure"""
        print("\n🔍 EXPLORING CLOB API DATA STRUCTURE")
        print("=" * 50)
        
        try:
            # Try to get market data from CLOB API
            url = f"{self.clob_api_base}/markets"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            markets = response.json()
            
            if isinstance(markets, list) and markets:
                print(f"📊 Found {len(markets)} markets in CLOB API")
                sample = markets[0]
                
                print(f"\n🎯 SAMPLE CLOB MARKET DATA:")
                print(f"Market ID: {sample.get('condition_id', 'N/A')}")
                print(f"Question: {sample.get('question', 'N/A')}")
                print(f"Active: {sample.get('active', 'N/A')}")
                
                print(f"\n🏷️ CLOB AVAILABLE FIELDS:")
                for key in sorted(sample.keys()):
                    print(f"   {key}: {type(sample[key]).__name__}")
                    
            else:
                print(f"📊 CLOB API response: {type(markets)}")
                if isinstance(markets, dict):
                    print(f"Response keys: {list(markets.keys())}")
                
        except Exception as e:
            print(f"❌ Error exploring CLOB API: {e}")
    
    def analyze_price_patterns(self, markets: List[Dict]):
        """Analyze actual price patterns in market data"""
        print(f"\n📊 ANALYZING PRICE PATTERNS")
        print("=" * 50)
        
        price_samples = []
        
        for i, market in enumerate(markets[:20]):  # Analyze first 20
            try:
                outcome_prices = market.get('outcome_prices')
                if outcome_prices:
                    print(f"\nMarket {i+1}: {market.get('title', 'Unknown')[:40]}...")
                    print(f"   Raw outcome_prices: {outcome_prices}")
                    print(f"   Type: {type(outcome_prices)}")
                    
                    if isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
                        yes_price = float(outcome_prices[0])
                        no_price = float(outcome_prices[1])
                        print(f"   YES price: {yes_price:.3f} ({yes_price:.1%})")
                        print(f"   NO price: {no_price:.3f} ({no_price:.1%})")
                        print(f"   Sum: {yes_price + no_price:.3f}")
                        print(f"   Deviation from 50%: {abs(yes_price - 0.5):.1%}")
                        
                        price_samples.append({
                            'market': market.get('title', 'Unknown')[:30],
                            'yes_price': yes_price,
                            'no_price': no_price,
                            'deviation': abs(yes_price - 0.5)
                        })
                        
            except Exception as e:
                print(f"   ❌ Error parsing market {i+1}: {e}")
        
        if price_samples:
            print(f"\n🎯 PRICE ANALYSIS SUMMARY:")
            deviations = [p['deviation'] for p in price_samples]
            print(f"   Markets analyzed: {len(price_samples)}")
            print(f"   Max deviation: {max(deviations):.1%}")
            print(f"   Min deviation: {min(deviations):.1%}")
            print(f"   Average deviation: {sum(deviations)/len(deviations):.1%}")
            print(f"   Markets > 5% deviation: {sum(1 for d in deviations if d > 0.05)}")
            print(f"   Markets > 10% deviation: {sum(1 for d in deviations if d > 0.10)}")
            print(f"   Markets > 20% deviation: {sum(1 for d in deviations if d > 0.20)}")
            
            # Show most interesting markets
            interesting = sorted(price_samples, key=lambda x: x['deviation'], reverse=True)[:5]
            print(f"\n🎯 MOST INTERESTING MARKETS (highest deviation):")
            for market in interesting:
                print(f"   {market['market']}: {market['yes_price']:.1%} (dev: {market['deviation']:.1%})")
    
    def test_different_endpoints(self):
        """Test different API endpoints to find better data"""
        print(f"\n🔧 TESTING DIFFERENT API ENDPOINTS")
        print("=" * 50)
        
        # Test various Gamma API endpoints
        endpoints_to_try = [
            '/events?active=true&limit=10',
            '/events?closed=false&limit=10',  
            '/events?limit=10',
            '/markets?limit=10',
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.gamma_api_base}{endpoint}"
                print(f"\n🔍 Testing: {endpoint}")
                
                response = requests.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response type: {type(data)}")
                    if isinstance(data, list):
                        print(f"   Items count: {len(data)}")
                        if data:
                            print(f"   First item keys: {list(data[0].keys())[:10]}")
                    elif isinstance(data, dict):
                        print(f"   Dict keys: {list(data.keys())}")
                else:
                    print(f"   ❌ Failed")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")

def main():
    """Run API data exploration"""
    explorer = APIDataExplorer()
    
    print("🚀 POLYMARKET API DATA EXPLORATION")
    print("📊 Understanding why signals aren't firing")
    print("=" * 60)
    
    # Explore Gamma API
    markets = explorer.explore_gamma_api_structure()
    
    # Explore CLOB API
    explorer.explore_clob_api_structure()
    
    # Analyze price patterns
    if markets:
        explorer.analyze_price_patterns(markets)
    
    # Test different endpoints
    explorer.test_different_endpoints()
    
    print(f"\n🧪 API exploration complete!")

if __name__ == "__main__":
    main()