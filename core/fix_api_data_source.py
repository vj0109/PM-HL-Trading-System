#!/usr/bin/env python3
"""
FIX API DATA SOURCE
Find the correct API endpoint that has price data for signals
"""

import requests
import json
from typing import Dict, List

class APIDataSourceFixer:
    def __init__(self):
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        self.clob_api_base = 'https://clob.polymarket.com'
    
    def explore_markets_endpoint(self):
        """Explore the /markets endpoint which seems to have different data"""
        print("🔍 EXPLORING /markets ENDPOINT")
        print("=" * 40)
        
        try:
            url = f"{self.gamma_api_base}/markets"
            params = {'limit': 10}
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            markets = response.json()
            print(f"📊 Found {len(markets)} markets")
            
            if markets:
                sample = markets[0]
                print(f"\n🎯 SAMPLE /markets DATA:")
                print(f"Market ID: {sample.get('id', 'N/A')}")
                print(f"Question: {sample.get('question', 'N/A')}")
                print(f"Slug: {sample.get('slug', 'N/A')}")
                
                print(f"\n💰 PRICE-RELATED FIELDS:")
                price_fields = ['price', 'prices', 'outcome_prices', 'last_price', 'bid', 'ask', 'mid_price']
                for field in price_fields:
                    if field in sample:
                        print(f"   {field}: {sample[field]}")
                
                print(f"\n📊 VOLUME-RELATED FIELDS:")
                volume_fields = ['volume', 'volume24hr', 'volume_24h', 'liquidity', 'openInterest']
                for field in volume_fields:
                    if field in sample:
                        print(f"   {field}: {sample[field]}")
                
                print(f"\n🏷️ ALL AVAILABLE FIELDS:")
                for key in sorted(sample.keys()):
                    print(f"   {key}: {type(sample[key]).__name__} = {str(sample[key])[:50]}")
                    
                print(f"\n📋 FULL MARKET JSON:")
                print(json.dumps(sample, indent=2))
                
            return markets
            
        except Exception as e:
            print(f"❌ Error exploring /markets: {e}")
            return []
    
    def explore_clob_markets_detailed(self):
        """Explore CLOB API markets endpoint in detail"""
        print(f"\n🔍 EXPLORING CLOB /markets DETAILED")
        print("=" * 40)
        
        try:
            url = f"{self.clob_api_base}/markets"
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and data['data']:
                markets = data['data']
                print(f"📊 Found {len(markets)} markets in CLOB")
                
                sample = markets[0]
                print(f"\n🎯 SAMPLE CLOB MARKET:")
                print(f"Condition ID: {sample.get('condition_id', 'N/A')}")
                print(f"Question: {sample.get('question', 'N/A')}")
                
                print(f"\n💰 PRICE DATA IN CLOB:")
                for key in sample.keys():
                    if 'price' in key.lower() or 'bid' in key.lower() or 'ask' in key.lower():
                        print(f"   {key}: {sample[key]}")
                
                print(f"\n📊 VOLUME DATA IN CLOB:")
                for key in sample.keys():
                    if 'volume' in key.lower() or 'liquidity' in key.lower():
                        print(f"   {key}: {sample[key]}")
                
                print(f"\n🏷️ ALL CLOB FIELDS:")
                for key in sorted(sample.keys()):
                    print(f"   {key}: {type(sample[key]).__name__}")
                
                return markets
                
        except Exception as e:
            print(f"❌ Error exploring CLOB markets: {e}")
            return []
    
    def find_price_data_endpoint(self):
        """Try to find an endpoint that actually has real-time price data"""
        print(f"\n🎯 SEARCHING FOR LIVE PRICE DATA")
        print("=" * 40)
        
        # Try different endpoint combinations
        endpoints_to_try = [
            ('gamma', '/markets?active=true'),
            ('gamma', '/markets?closed=false'), 
            ('gamma', '/events?active=true&includeMarkets=true'),
            ('clob', '/markets'),
            ('clob', '/book'),
            ('clob', '/prices'),
            ('clob', '/midpoint'),
        ]
        
        for api_type, endpoint in endpoints_to_try:
            try:
                base_url = self.gamma_api_base if api_type == 'gamma' else self.clob_api_base
                url = f"{base_url}{endpoint}"
                
                print(f"\n🔍 Testing {api_type.upper()}: {endpoint}")
                
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Look for price-like data
                    if isinstance(data, list) and data:
                        sample = data[0]
                        price_indicators = []
                        for key, value in sample.items():
                            if any(price_word in key.lower() for price_word in ['price', 'bid', 'ask', 'mid']):
                                if isinstance(value, (int, float)) and 0 < value < 1:
                                    price_indicators.append(f"{key}={value}")
                        
                        if price_indicators:
                            print(f"   ✅ Found price data: {', '.join(price_indicators[:3])}")
                        else:
                            print(f"   ❌ No valid price data")
                    
                    elif isinstance(data, dict):
                        if 'data' in data and data['data']:
                            print(f"   📊 Found {len(data['data'])} items in data field")
                        else:
                            print(f"   📊 Dict with keys: {list(data.keys())}")
                else:
                    print(f"   ❌ Status {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    def test_specific_market_prices(self):
        """Test getting prices for specific markets"""
        print(f"\n🎯 TESTING SPECIFIC MARKET PRICES")
        print("=" * 40)
        
        try:
            # First get a market ID from /markets
            markets_url = f"{self.gamma_api_base}/markets"
            response = requests.get(markets_url, params={'limit': 3}, timeout=10)
            
            if response.status_code == 200:
                markets = response.json()
                
                if markets:
                    for market in markets[:3]:
                        market_id = market.get('id')
                        condition_id = market.get('conditionId')
                        
                        print(f"\n🎯 Market: {market.get('question', 'Unknown')[:50]}...")
                        print(f"   Market ID: {market_id}")
                        print(f"   Condition ID: {condition_id}")
                        
                        # Try to get price data for this specific market
                        price_endpoints = [
                            f"/markets/{market_id}",
                            f"/markets/{condition_id}",
                        ]
                        
                        for endpoint in price_endpoints:
                            try:
                                url = f"{self.gamma_api_base}{endpoint}"
                                resp = requests.get(url, timeout=5)
                                
                                if resp.status_code == 200:
                                    data = resp.json()
                                    print(f"   ✅ {endpoint}: Found data")
                                    
                                    # Look for price data
                                    for key, value in data.items():
                                        if 'price' in key.lower():
                                            print(f"      {key}: {value}")
                                else:
                                    print(f"   ❌ {endpoint}: Status {resp.status_code}")
                                    
                            except:
                                print(f"   ❌ {endpoint}: Error")
                
        except Exception as e:
            print(f"❌ Error testing specific markets: {e}")

def main():
    """Run API data source investigation"""
    fixer = APIDataSourceFixer()
    
    print("🚀 FINDING CORRECT POLYMARKET PRICE DATA SOURCE")
    print("📊 The /events endpoint doesn't have prices - need to find the right one")
    print("=" * 70)
    
    # Explore /markets endpoint
    gamma_markets = fixer.explore_markets_endpoint()
    
    # Explore CLOB markets
    clob_markets = fixer.explore_clob_markets_detailed()
    
    # Search for live price data
    fixer.find_price_data_endpoint()
    
    # Test specific market prices
    fixer.test_specific_market_prices()
    
    print(f"\n🧪 API data source investigation complete!")

if __name__ == "__main__":
    main()