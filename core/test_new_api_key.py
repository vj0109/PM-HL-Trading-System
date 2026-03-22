#!/usr/bin/env python3
"""
TEST NEW POLYMARKET API KEY
Test if the new API key works for historical trade data access
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, TradeParams

def test_new_api_key():
    """Test the new API key with existing secret and passphrase"""
    
    # New API key provided by VJ
    api_key = "019d1560-55b8-7931-94d7-57187ba3a860"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
    
    print("🔑 TESTING NEW POLYMARKET API KEY")
    print("=" * 45)
    print(f"🆔 New API Key: {api_key}")
    
    try:
        # Create credentials with new API key
        creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        )
        
        client = ClobClient(
            host="https://clob.polymarket.com",
            creds=creds
        )
        
        print("✅ Credentials created successfully")
        
        # Test basic connection
        ok = client.get_ok()
        time_resp = client.get_server_time()
        print(f"✅ Connection: {ok}, Server Time: {time_resp}")
        
        # Test API key validation endpoint
        try:
            api_keys = client.get_api_keys()
            print(f"🎉 API KEY AUTHENTICATION SUCCESS!")
            print(f"✅ API Keys response: {api_keys}")
        except Exception as e:
            print(f"❌ API key authentication failed: {e}")
            return False
        
        # Test market access
        markets = client.get_markets()
        if isinstance(markets, dict) and 'data' in markets:
            markets_data = markets['data']
            print(f"✅ Markets access: {len(markets_data)} markets available")
            
            # THE CRITICAL TEST: Historical trade data access
            if markets_data:
                test_market = markets_data[0]
                condition_id = test_market['condition_id']
                question = test_market.get('question', 'Unknown')
                
                print(f"\n🧪 TESTING HISTORICAL TRADE DATA ACCESS")
                print(f"📊 Test Market: {question[:60]}...")
                print(f"🆔 Condition ID: {condition_id}")
                
                try:
                    # This is what was failing before
                    trade_params = TradeParams(market=condition_id)
                    trades = client.get_trades(trade_params)
                    
                    print(f"🎉 HISTORICAL TRADE ACCESS SUCCESS!")
                    print(f"✅ Retrieved {len(trades)} trades")
                    
                    if trades:
                        sample_trade = trades[0]
                        print(f"📈 Sample trade fields: {list(sample_trade.keys())}")
                        
                        # Check for Claude's required data fields
                        has_price = 'price' in sample_trade or 'execution_price' in sample_trade
                        has_volume = 'size' in sample_trade or 'volume' in sample_trade or 'amount' in sample_trade
                        has_timestamp = 'timestamp' in sample_trade or 'created_at' in sample_trade
                        
                        print(f"📊 Claude's requirements check:")
                        print(f"   ✅ Price data: {has_price}")
                        print(f"   ✅ Volume data: {has_volume}")
                        print(f"   ✅ Timestamp data: {has_timestamp}")
                        
                        if has_price and has_volume and has_timestamp:
                            print(f"\n🚀 READY FOR CLAUDE'S METHODOLOGY!")
                            print(f"✅ All required data fields available")
                            return True
                        else:
                            print(f"\n⚠️ Missing required data fields")
                            return False
                    else:
                        print(f"⚠️ No trades found for this market")
                        return False
                        
                except Exception as trade_error:
                    print(f"❌ Historical trade access failed: {trade_error}")
                    return False
            else:
                print("❌ No markets found")
                return False
        else:
            print("❌ Market access failed")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def main():
    """Test the new API key"""
    print("🔑 NEW POLYMARKET API KEY TEST")
    print("🎯 Goal: Check if new key enables historical trade data access")
    print("🔬 Required for: Claude's volume spike methodology")
    print("=" * 65)
    
    success = test_new_api_key()
    
    if success:
        print(f"\n🎉 SUCCESS!")
        print(f"✅ New API key works for historical trade data")
        print(f"🚀 Ready to implement Claude's volume spike methodology")
        print(f"📋 Next step: Await instructions on implementing Claude's 7-step process")
    else:
        print(f"\n❌ AUTHENTICATION STILL FAILED")
        print(f"🔧 New API key does not resolve the historical data access issue")

if __name__ == "__main__":
    main()