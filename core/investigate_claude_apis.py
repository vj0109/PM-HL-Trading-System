#!/usr/bin/env python3
"""
INVESTIGATE CLAUDE'S SPECIFIED API ENDPOINTS
Test each endpoint Claude mentioned to see what's actually available
"""

import requests
import json
from typing import Dict, List

class PolymarketAPIInvestigator:
    def __init__(self):
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        self.clob_api_base = 'https://clob.polymarket.com'
    
    def test_events_endpoint(self):
        """Test Claude's: GET /events?closed=true&order=volume&ascending=false&limit=200"""
        print("🔍 TESTING CLAUDE'S EVENTS ENDPOINT")
        print("=" * 50)
        
        try:
            url = f"{self.gamma_api_base}/events"
            params = {
                'closed': 'true',
                'order': 'volume',
                'ascending': 'false', 
                'limit': 10
            }
            
            print(f"📊 Testing: {url}")
            print(f"   Params: {params}")
            
            response = requests.get(url, params=params, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response type: {type(data)}")
                
                if isinstance(data, list) and data:
                    sample = data[0]
                    print(f"   Sample fields: {list(sample.keys())[:10]}")
                    
                    # Check for conditionId field
                    condition_id = sample.get('conditionId') or sample.get('condition_id')
                    print(f"   Has conditionId: {condition_id is not None}")
                    if condition_id:
                        print(f"   Sample conditionId: {condition_id[:20]}...")
                        
                    return data[:3]  # Return first 3 for testing
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        return []
    
    def test_activity_endpoint(self, condition_id: str):
        """Test Claude's: GET /activity?market={conditionId}&type=TRADE"""
        print(f"\n🔍 TESTING CLAUDE'S ACTIVITY ENDPOINT")
        print("=" * 50)
        
        endpoints_to_try = [
            f"/activity?market={condition_id}&type=TRADE",
            f"/activity?market={condition_id}",
            f"/trades?market={condition_id}",
            f"/markets/{condition_id}/activity",
            f"/markets/{condition_id}/trades"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.gamma_api_base}{endpoint}"
                print(f"📊 Testing: {endpoint}")
                
                response = requests.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response type: {type(data)}")
                    
                    if isinstance(data, list) and data:
                        print(f"   Items: {len(data)}")
                        sample = data[0]
                        print(f"   Sample fields: {list(sample.keys())}")
                        print(f"   ✅ FOUND WORKING ACTIVITY ENDPOINT!")
                        return data[:5]
                        
                    elif isinstance(data, dict):
                        print(f"   Dict keys: {list(data.keys())}")
                        if 'data' in data:
                            print(f"   Data items: {len(data.get('data', []))}")
                            
                elif response.status_code == 404:
                    print(f"   ❌ Not found")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
        
        return []
    
    def test_prices_history_endpoint(self, condition_id: str):
        """Test Claude's: GET /prices-history"""
        print(f"\n🔍 TESTING CLAUDE'S PRICES-HISTORY ENDPOINT")
        print("=" * 50)
        
        endpoints_to_try = [
            f"/prices-history?market={condition_id}",
            f"/prices-history/{condition_id}",
            f"/markets/{condition_id}/prices-history",
            f"/markets/{condition_id}/history",
            f"/events/{condition_id}/prices",
            f"/history/prices?market={condition_id}"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.gamma_api_base}{endpoint}"
                print(f"📊 Testing: {endpoint}")
                
                response = requests.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response type: {type(data)}")
                    
                    if isinstance(data, list) and data:
                        print(f"   Items: {len(data)}")
                        sample = data[0]
                        print(f"   Sample fields: {list(sample.keys())}")
                        print(f"   ✅ FOUND WORKING PRICES ENDPOINT!")
                        return data[:5]
                        
                    elif isinstance(data, dict):
                        print(f"   Dict keys: {list(data.keys())}")
                        
                elif response.status_code == 404:
                    print(f"   ❌ Not found")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
        
        return []
    
    def test_clob_api_endpoints(self, condition_id: str):
        """Test CLOB API for trading data"""
        print(f"\n🔍 TESTING CLOB API ENDPOINTS")
        print("=" * 50)
        
        endpoints_to_try = [
            f"/activity?market={condition_id}",
            f"/trades?market={condition_id}",
            f"/book?token_id={condition_id}",
            f"/midpoint?market={condition_id}",
            f"/markets/{condition_id}"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.clob_api_base}{endpoint}"
                print(f"📊 Testing CLOB: {endpoint}")
                
                response = requests.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response type: {type(data)}")
                    
                    if isinstance(data, list) and data:
                        print(f"   Items: {len(data)}")
                        sample = data[0]
                        print(f"   Sample fields: {list(sample.keys())}")
                        print(f"   ✅ FOUND WORKING CLOB ENDPOINT!")
                        return data[:3]
                        
                    elif isinstance(data, dict):
                        print(f"   Dict keys: {list(data.keys())}")
                        
                elif response.status_code in [400, 422]:
                    print(f"   ⚠️ Bad request - may need different parameters")
                elif response.status_code == 404:
                    print(f"   ❌ Not found")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
        
        return []
    
    def explore_alternative_data_sources(self):
        """Look for alternative endpoints that might have the data we need"""
        print(f"\n🔍 EXPLORING ALTERNATIVE DATA SOURCES")
        print("=" * 50)
        
        # Try to find any endpoint with historical trade/price data
        endpoints_to_try = [
            "/markets/history",
            "/trades",
            "/history",
            "/data",
            "/analytics",
            "/volume",
            "/liquidity"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.gamma_api_base}{endpoint}"
                print(f"📊 Testing: {endpoint}")
                
                response = requests.get(url, timeout=10)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response type: {type(data)}")
                    print(f"   ✅ FOUND DATA at {endpoint}!")
                    
                    if isinstance(data, list) and data:
                        sample = data[0]
                        print(f"   Sample fields: {list(sample.keys())}")
                    elif isinstance(data, dict):
                        print(f"   Dict keys: {list(data.keys())}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")

def main():
    """Test all of Claude's specified API endpoints"""
    investigator = PolymarketAPIInvestigator()
    
    print("🚀 INVESTIGATING CLAUDE'S POLYMARKET API ENDPOINTS")
    print("📊 Testing each endpoint Claude specified in his methodology")
    print("=" * 80)
    
    # Step 1: Test events endpoint
    markets = investigator.test_events_endpoint()
    
    if markets:
        sample_market = markets[0]
        condition_id = (sample_market.get('conditionId') or 
                       sample_market.get('condition_id') or 
                       sample_market.get('id'))
        
        if condition_id:
            print(f"\n🎯 Testing with sample conditionId: {condition_id}")
            
            # Step 2: Test activity endpoint  
            trades = investigator.test_activity_endpoint(condition_id)
            
            # Step 3: Test prices-history endpoint
            prices = investigator.test_prices_history_endpoint(condition_id)
            
            # Step 4: Test CLOB API
            clob_data = investigator.test_clob_api_endpoints(condition_id)
            
    # Step 5: Explore alternatives
    investigator.explore_alternative_data_sources()
    
    print(f"\n📊 INVESTIGATION COMPLETE!")
    print("=" * 50)
    print("Next steps:")
    print("1. Use working endpoints found above")
    print("2. If no historical data available, start forward testing")
    print("3. Consider alternative data sources or manual collection")

if __name__ == "__main__":
    main()