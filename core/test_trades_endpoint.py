#!/usr/bin/env python3
"""
TEST POLYMARKET DATA API /trades ENDPOINT
Test if /trades provides the historical trade data needed for Claude's methodology
"""

import requests
import json
from datetime import datetime, timedelta

def test_trades_endpoint_basic():
    """Test basic /trades endpoint access"""
    
    base_url = "https://data-api.polymarket.com"
    
    print("🔍 TESTING /trades ENDPOINT FOR CLAUDE'S METHODOLOGY")
    print("=" * 55)
    
    # Test 1: Basic /trades endpoint
    print("🧪 Test 1: Basic /trades endpoint (no parameters)")
    try:
        response = requests.get(f"{base_url}/trades", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Got {len(data) if isinstance(data, list) else 'data'}")
            
            if isinstance(data, list) and data:
                sample_trade = data[0]
                print(f"📈 Sample trade fields: {list(sample_trade.keys())}")
                print(f"📊 Sample trade: {sample_trade}")
                
                # Check Claude's required fields
                has_market_id = any(field in sample_trade for field in ['market', 'condition_id', 'token_id'])
                has_price = any(field in sample_trade for field in ['price', 'execution_price'])
                has_volume = any(field in sample_trade for field in ['volume', 'size', 'amount'])
                has_timestamp = any(field in sample_trade for field in ['timestamp', 'created_at', 'block_time'])
                
                print(f"\n🎯 Claude's Requirements Check:")
                print(f"   📊 Market identifier: {has_market_id}")
                print(f"   💰 Price data: {has_price}")
                print(f"   📈 Volume data: {has_volume}")
                print(f"   ⏰ Timestamp: {has_timestamp}")
                
                claude_ready = has_market_id and has_price and has_volume and has_timestamp
                print(f"   🎉 Ready for Claude methodology: {claude_ready}")
                
                return data, claude_ready
                
            else:
                print("⚠️ No trade data or unexpected format")
                
        elif response.status_code == 400:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"⚠️ Bad request: {error_data}")
            return None, False
            
        else:
            print(f"❌ Failed: {response.status_code} - {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Trades endpoint error: {e}")
    
    return None, False

def test_trades_with_parameters():
    """Test /trades endpoint with different parameters"""
    
    base_url = "https://data-api.polymarket.com"
    
    print(f"\n🧪 Test 2: /trades with different parameters")
    
    # Get a real market ID from Gamma API first
    market_id = None
    try:
        gamma_response = requests.get("https://gamma-api.polymarket.com/markets?limit=1", timeout=5)
        if gamma_response.status_code == 200:
            markets = gamma_response.json()
            if markets and len(markets) > 0:
                market_id = markets[0].get('condition_id')
                question = markets[0].get('question', 'Unknown')
                print(f"📊 Using market: {question[:50]}...")
                print(f"🆔 Market ID: {market_id}")
    except:
        print("⚠️ Could not get market ID from Gamma API")
    
    # Test different parameter combinations
    param_sets = [
        {},  # No parameters (already tested above)
        {"limit": 10},
        {"market": market_id} if market_id else {"market": "test"},
        {"token_id": market_id} if market_id else {"token_id": "test"},
        {"condition_id": market_id} if market_id else {"condition_id": "test"},
        {"limit": 5, "market": market_id} if market_id else {"limit": 5},
    ]
    
    successful_params = []
    
    for i, params in enumerate(param_sets):
        print(f"\n   🔬 Parameter set {i+1}: {params}")
        try:
            response = requests.get(f"{base_url}/trades", params=params, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS: {len(data) if isinstance(data, list) else 'Got data'}")
                successful_params.append(params)
                
                if isinstance(data, list) and data:
                    sample = data[0]
                    # Look for market/condition identifiers
                    market_fields = [k for k in sample.keys() if 'market' in k.lower() or 'condition' in k.lower() or 'token' in k.lower()]
                    print(f"   📊 Market fields found: {market_fields}")
                    
            elif response.status_code == 400:
                error_msg = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:100]
                print(f"   ❌ Bad request: {error_msg}")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return successful_params

def test_trade_data_structure():
    """Analyze the structure of trade data for Claude's methodology"""
    
    base_url = "https://data-api.polymarket.com"
    
    print(f"\n🔬 Test 3: Analyzing trade data structure for Claude's methodology")
    
    try:
        # Get trade data with limit
        response = requests.get(f"{base_url}/trades", params={"limit": 5}, timeout=10)
        
        if response.status_code == 200:
            trades = response.json()
            
            if isinstance(trades, list) and trades:
                print(f"📊 Analyzing {len(trades)} trades...")
                
                # Analyze first trade in detail
                sample_trade = trades[0]
                print(f"\n📈 Sample Trade Analysis:")
                print(f"Raw data: {json.dumps(sample_trade, indent=2)}")
                
                # Claude's methodology requirements:
                # 1. Market identifier (to group trades by market)
                # 2. Price (to track price movements)  
                # 3. Volume/Size (to detect volume spikes)
                # 4. Timestamp (to create hourly bars)
                # 5. Side/Type (for market analysis)
                
                print(f"\n🎯 Claude's Methodology Field Mapping:")
                
                for field, value in sample_trade.items():
                    field_type = type(value).__name__
                    print(f"   {field}: {value} ({field_type})")
                
                # Check if we can derive required data
                print(f"\n✅ Claude Methodology Readiness Assessment:")
                
                # Look for market identification
                market_fields = [k for k in sample_trade.keys() if any(identifier in k.lower() for identifier in ['market', 'condition', 'token', 'asset'])]
                print(f"   📊 Market ID fields: {market_fields}")
                
                # Look for price data
                price_fields = [k for k in sample_trade.keys() if any(identifier in k.lower() for identifier in ['price', 'rate', 'value'])]
                print(f"   💰 Price fields: {price_fields}")
                
                # Look for volume data
                volume_fields = [k for k in sample_trade.keys() if any(identifier in k.lower() for identifier in ['volume', 'size', 'amount', 'quantity'])]
                print(f"   📈 Volume fields: {volume_fields}")
                
                # Look for time data
                time_fields = [k for k in sample_trade.keys() if any(identifier in k.lower() for identifier in ['time', 'date', 'created', 'block'])]
                print(f"   ⏰ Time fields: {time_fields}")
                
                # Look for side/type data
                side_fields = [k for k in sample_trade.keys() if any(identifier in k.lower() for identifier in ['side', 'type', 'direction'])]
                print(f"   📍 Side fields: {side_fields}")
                
                # Assessment
                has_required_fields = bool(market_fields and price_fields and volume_fields and time_fields)
                print(f"\n🎉 CLAUDE METHODOLOGY COMPATIBLE: {has_required_fields}")
                
                return has_required_fields, sample_trade
                
        else:
            print(f"❌ Could not get trade data for analysis: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Trade data analysis failed: {e}")
    
    return False, None

def main():
    """Test /trades endpoint for Claude's volume spike methodology"""
    print("🔍 POLYMARKET /trades ENDPOINT TESTING")
    print("🎯 Goal: Verify if /trades provides data needed for Claude's methodology")
    print("📋 Claude needs: Market ID, Price, Volume, Timestamp for volume spike detection")
    print("=" * 80)
    
    # Test 1: Basic endpoint access
    trades_data, basic_ready = test_trades_endpoint_basic()
    
    # Test 2: Parameter exploration
    working_params = test_trades_with_parameters()
    
    # Test 3: Data structure analysis
    claude_compatible, sample_trade = test_trade_data_structure()
    
    print(f"\n📊 FINAL ASSESSMENT:")
    print(f"   Basic endpoint access: {'✅' if trades_data else '❌'}")
    print(f"   Working parameter sets: {len(working_params) if working_params else 0}")
    print(f"   Claude methodology compatible: {'✅' if claude_compatible else '❌'}")
    
    if claude_compatible:
        print(f"\n🎉 SUCCESS!")
        print(f"✅ /trades endpoint provides data needed for Claude's methodology")
        print(f"🚀 Ready to proceed with Claude's 7-step volume spike detection")
        print(f"📋 Next: Await instructions to implement Claude's methodology")
    else:
        print(f"\n❌ DATA INCOMPATIBLE")
        print(f"🔧 /trades endpoint missing required fields for Claude's methodology")
        print(f"🎯 Need alternative data source approach")

if __name__ == "__main__":
    main()