#!/usr/bin/env python3
"""
TEST POLYMARKET FULL AUTHENTICATION
Using API Key + Secret to access historical trade data
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, TradeParams

def test_authentication():
    """Test different authentication combinations"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    
    print("🔑 TESTING POLYMARKET AUTHENTICATION")
    print("=" * 50)
    
    # Test 1: API Key + Secret (no passphrase)
    print("🧪 Test 1: API Key + Secret")
    try:
        creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=""  # Empty passphrase
        )
        
        client = ClobClient(
            host="https://clob.polymarket.com",
            creds=creds
        )
        
        # Test connection
        ok = client.get_ok()
        time_resp = client.get_server_time()
        print(f"   ✅ Connection: {ok}, Time: {time_resp}")
        
        # Test trade data access
        print("   🔍 Testing trade data access...")
        
        # Get a sample market ID
        markets = client.get_markets()
        if isinstance(markets, dict) and 'data' in markets:
            sample_market = markets['data'][0]
            condition_id = sample_market['condition_id']
            
            print(f"   📊 Testing with market: {condition_id[:10]}...")
            
            # Try to get trades
            trade_params = TradeParams(market=condition_id)
            trades = client.get_trades(trade_params)
            
            print(f"   ✅ SUCCESS: Got {len(trades)} trades with authentication!")
            
            # Show sample trade data
            if trades:
                sample_trade = trades[0]
                print(f"   📈 Sample trade: {list(sample_trade.keys())}")
                
            return True
            
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        
    # Test 2: Try different passphrase values
    for passphrase in ["", "polymarket", "clob", "api"]:
        print(f"\n🧪 Test 2: With passphrase '{passphrase}'")
        try:
            creds = ApiCreds(
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=passphrase
            )
            
            client = ClobClient(
                host="https://clob.polymarket.com", 
                creds=creds
            )
            
            # Quick test
            markets = client.get_markets()
            if isinstance(markets, dict) and 'data' in markets:
                condition_id = markets['data'][0]['condition_id']
                trade_params = TradeParams(market=condition_id)
                trades = client.get_trades(trade_params)
                
                print(f"   ✅ SUCCESS with passphrase '{passphrase}': {len(trades)} trades")
                return True
                
        except Exception as e:
            print(f"   ❌ Failed with passphrase '{passphrase}': {e}")
    
    return False

def test_claude_methodology_authenticated():
    """If authentication works, test Claude's methodology"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5" 
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    
    try:
        # Use successful authentication
        creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=""
        )
        
        client = ClobClient(
            host="https://clob.polymarket.com",
            creds=creds
        )
        
        print(f"\n🚀 TESTING CLAUDE'S METHODOLOGY WITH AUTHENTICATION")
        print("=" * 60)
        
        # Get markets
        markets = client.get_markets()
        if isinstance(markets, dict) and 'data' in markets:
            markets_data = markets['data']
            
            # Test on first 3 markets with closed status
            tested_markets = 0
            successful_trades = 0
            
            for market in markets_data[:10]:
                if tested_markets >= 3:
                    break
                    
                condition_id = market['condition_id']
                question = market.get('question', 'Unknown')[:60]
                
                print(f"\n🎯 Testing: {question}...")
                
                try:
                    # Get authenticated trade data
                    trade_params = TradeParams(market=condition_id)
                    trades = client.get_trades(trade_params)
                    
                    if trades:
                        print(f"   ✅ Got {len(trades)} trades!")
                        successful_trades += 1
                        
                        # Show sample trade structure
                        if len(trades) > 0:
                            sample = trades[0]
                            print(f"   📊 Trade fields: {list(sample.keys())}")
                            
                            # Look for price and volume data
                            price = sample.get('price', sample.get('execution_price', 'N/A'))
                            size = sample.get('size', sample.get('volume', sample.get('amount', 'N/A')))
                            timestamp = sample.get('timestamp', sample.get('created_at', 'N/A'))
                            
                            print(f"   💰 Sample: Price: {price}, Size: {size}, Time: {timestamp}")
                    else:
                        print(f"   ⚠️ No trades found")
                        
                except Exception as e:
                    print(f"   ❌ Error getting trades: {e}")
                
                tested_markets += 1
            
            print(f"\n📊 AUTHENTICATION TEST RESULTS:")
            print(f"   Markets tested: {tested_markets}")
            print(f"   Markets with trade data: {successful_trades}")
            
            if successful_trades > 0:
                print(f"\n✅ AUTHENTICATION SUCCESS!")
                print(f"🚀 Ready to implement Claude's full methodology with historical trade data!")
            else:
                print(f"\n❌ No trade data accessible")
                
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")

def main():
    """Run authentication tests"""
    print("🔑 POLYMARKET API AUTHENTICATION TEST")
    print("📊 Testing API Key + Secret combination")
    print("🎯 Goal: Access historical trade data for Claude's methodology")
    print("=" * 70)
    
    # Test basic authentication
    auth_success = test_authentication()
    
    if auth_success:
        # If basic auth works, test Claude's methodology
        test_claude_methodology_authenticated()
    else:
        print(f"\n❌ Authentication failed with current credentials")
        print("🔧 May need additional credentials (passphrase) or different auth method")

if __name__ == "__main__":
    main()