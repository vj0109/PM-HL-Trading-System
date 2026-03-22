#!/usr/bin/env python3
"""
TEST POLYMARKET DATA API FOR CLAUDE'S METHODOLOGY
Test the Data API endpoints that Claude specified for volume spike detection
"""

import requests
import json
from datetime import datetime, timedelta

def test_data_api_endpoints():
    """Test Claude's specified Data API endpoints"""
    
    base_url = "https://data-api.polymarket.com"
    
    print("🔍 TESTING POLYMARKET DATA API FOR CLAUDE'S METHODOLOGY")
    print("=" * 60)
    print(f"🌐 Base URL: {base_url}")
    print(f"🔓 Authentication: Not required (public API)")
    
    # Test 1: Activity endpoint (trade data)
    print(f"\n🧪 Test 1: /activity endpoint (Claude's trade data source)")
    try:
        response = requests.get(f"{base_url}/activity", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Activity endpoint accessible")
            
            if isinstance(data, list) and data:
                print(f"📊 Sample activity data: {len(data)} records")
                sample = data[0]
                print(f"📈 Sample fields: {list(sample.keys())}")
                
                # Check for required fields
                has_market = 'market' in sample or 'condition_id' in sample
                has_volume = 'volume' in sample or 'size' in sample or 'amount' in sample
                has_price = 'price' in sample or 'execution_price' in sample
                has_timestamp = 'timestamp' in sample or 'created_at' in sample
                
                print(f"   🎯 Claude's requirements:")
                print(f"   📊 Market ID: {has_market}")
                print(f"   💰 Volume: {has_volume}")
                print(f"   💲 Price: {has_price}")
                print(f"   ⏰ Timestamp: {has_timestamp}")
                
            else:
                print(f"⚠️ No activity data or unexpected format")
                
        else:
            print(f"❌ Failed: {response.status_code} - {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Activity endpoint error: {e}")
    
    # Test 2: Price history endpoint
    print(f"\n🧪 Test 2: /prices-history endpoint (Claude's price data source)")
    try:
        # Try with and without parameters
        response = requests.get(f"{base_url}/prices-history", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Price history endpoint accessible")
            print(f"📊 Data type: {type(data)}, Length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
            
            if data:
                sample = data[0] if isinstance(data, list) else data
                print(f"📈 Sample price data: {sample}")
                
        elif response.status_code == 400:
            print(f"⚠️ Bad request - may need parameters")
            # Try with sample parameters
            test_params = {"market": "test", "interval": "1h"}
            response2 = requests.get(f"{base_url}/prices-history", params=test_params, timeout=10)
            print(f"With params status: {response2.status_code}")
            
        else:
            print(f"❌ Failed: {response.status_code} - {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Price history endpoint error: {e}")
    
    # Test 3: General endpoint discovery
    print(f"\n🧪 Test 3: Endpoint discovery")
    test_endpoints = [
        "/trades",
        "/markets",
        "/events",
        "/volume",
        "/positions",
        "/history"
    ]
    
    working_endpoints = []
    for endpoint in test_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                working_endpoints.append(endpoint)
                print(f"✅ {endpoint}: Available")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    print(f"\n📊 Working endpoints: {working_endpoints}")
    
    return working_endpoints

def test_with_market_data():
    """Test Data API with actual market data from Gamma API"""
    
    print(f"\n🔬 TESTING DATA API WITH REAL MARKET DATA")
    print("=" * 45)
    
    # Get markets from Gamma API first
    try:
        gamma_response = requests.get("https://gamma-api.polymarket.com/markets?limit=5", timeout=10)
        
        if gamma_response.status_code == 200:
            markets = gamma_response.json()
            
            if markets and len(markets) > 0:
                sample_market = markets[0]
                condition_id = sample_market.get('condition_id')
                question = sample_market.get('question', 'Unknown')
                
                print(f"📊 Testing with market: {question[:50]}...")
                print(f"🆔 Condition ID: {condition_id}")
                
                # Test Data API endpoints with this market
                data_base = "https://data-api.polymarket.com"
                
                # Test activity for this market
                try:
                    params = {"market": condition_id}
                    activity_response = requests.get(f"{data_base}/activity", params=params, timeout=10)
                    print(f"Activity for market: Status {activity_response.status_code}")
                    
                    if activity_response.status_code == 200:
                        activity_data = activity_response.json()
                        print(f"✅ Market activity: {len(activity_data) if isinstance(activity_data, list) else 'Available'}")
                        
                        if isinstance(activity_data, list) and activity_data:
                            sample_trade = activity_data[0]
                            print(f"📈 Sample trade: {sample_trade}")
                            return True
                            
                except Exception as e:
                    print(f"❌ Market activity test failed: {e}")
                    
        else:
            print(f"❌ Could not get markets from Gamma API: {gamma_response.status_code}")
            
    except Exception as e:
        print(f"❌ Market data test failed: {e}")
    
    return False

def main():
    """Test Polymarket Data API for Claude's methodology"""
    print("🔍 POLYMARKET DATA API TESTING FOR CLAUDE'S VOLUME SPIKE METHODOLOGY")
    print("🎯 Goal: Verify access to trade data and price history as Claude specified")
    print("📋 Claude's requirements: /activity endpoint + /prices-history endpoint")
    print("=" * 80)
    
    # Test basic endpoints
    working_endpoints = test_data_api_endpoints()
    
    # Test with real market data
    market_success = test_with_market_data()
    
    print(f"\n📊 SUMMARY:")
    print(f"   Working endpoints: {len(working_endpoints)}")
    print(f"   Market data access: {'✅' if market_success else '❌'}")
    
    if working_endpoints or market_success:
        print(f"\n🎉 DATA API ACCESS SUCCESSFUL!")
        print(f"✅ Can proceed with testing Claude's methodology")
        print(f"📋 Next: Implement Claude's 7-step volume spike detection")
    else:
        print(f"\n❌ DATA API ACCESS FAILED")
        print(f"🔧 Need to investigate alternative data sources")

if __name__ == "__main__":
    main()