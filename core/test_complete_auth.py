#!/usr/bin/env python3
"""
TEST COMPLETE POLYMARKET AUTHENTICATION
Using all three credentials: API Key + Secret + Passphrase
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, TradeParams

def test_complete_authentication():
    """Test with all three credentials"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
    
    print("🔑 TESTING COMPLETE POLYMARKET AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Create credentials with all three components
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
        
        # Test market access
        markets = client.get_markets()
        if isinstance(markets, dict) and 'data' in markets:
            markets_data = markets['data']
            print(f"✅ Markets access: {len(markets_data)} markets available")
            
            # Test historical trade data access (the key test!)
            if markets_data:
                test_market = markets_data[0]
                condition_id = test_market['condition_id']
                question = test_market.get('question', 'Unknown')
                
                print(f"\n🧪 Testing historical trade access...")
                print(f"📊 Market: {question[:60]}...")
                print(f"🆔 Condition ID: {condition_id}")
                
                try:
                    # This is what failed before - test if it works now
                    trade_params = TradeParams(market=condition_id)
                    trades = client.get_trades(trade_params)
                    
                    print(f"🎉 SUCCESS! Got {len(trades)} historical trades!")
                    
                    if trades:
                        sample_trade = trades[0]
                        print(f"📈 Sample trade fields: {list(sample_trade.keys())}")
                        
                        # Show key trade data
                        price = sample_trade.get('price', sample_trade.get('execution_price'))
                        size = sample_trade.get('size', sample_trade.get('volume', sample_trade.get('amount')))
                        timestamp = sample_trade.get('timestamp', sample_trade.get('created_at'))
                        side = sample_trade.get('side', sample_trade.get('type'))
                        
                        print(f"💰 Sample: Price: {price}, Size: {size}, Side: {side}, Time: {timestamp}")
                        
                        return True, trades, sample_trade
                    
                except Exception as trade_error:
                    print(f"❌ Trade data access failed: {trade_error}")
                    return False, None, None
            else:
                print("❌ No markets found")
                return False, None, None
        else:
            print("❌ Market access failed")
            return False, None, None
            
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False, None, None

def test_claude_volume_spike_data():
    """Test accessing data needed for Claude's volume spike methodology"""
    
    print(f"\n🚀 TESTING CLAUDE'S VOLUME SPIKE DATA ACCESS")
    print("=" * 60)
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
    
    try:
        creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        )
        
        client = ClobClient(
            host="https://clob.polymarket.com",
            creds=creds
        )
        
        # Get resolved markets for backtesting
        markets = client.get_markets()
        if isinstance(markets, dict) and 'data' in markets:
            markets_data = markets['data']
            
            # Look for closed/resolved markets
            closed_markets = [m for m in markets_data if m.get('closed', False)]
            active_markets = [m for m in markets_data if not m.get('closed', True)]
            
            print(f"📊 Total markets: {len(markets_data)}")
            print(f"📊 Closed markets: {len(closed_markets)} (for backtesting)")
            print(f"📊 Active markets: {len(active_markets)} (for live signals)")
            
            # Test trade data on a few markets
            test_markets = (closed_markets[:2] if closed_markets else []) + (active_markets[:1] if active_markets else [])
            
            successful_data = 0
            
            for i, market in enumerate(test_markets):
                condition_id = market['condition_id']
                question = market.get('question', 'Unknown')
                is_closed = market.get('closed', False)
                
                print(f"\n🧪 Test {i+1}: {'CLOSED' if is_closed else 'ACTIVE'}")
                print(f"📊 {question[:50]}...")
                
                try:
                    trade_params = TradeParams(market=condition_id)
                    trades = client.get_trades(trade_params)
                    
                    if trades:
                        print(f"✅ {len(trades)} trades available")
                        
                        # Analyze trade data structure for Claude's methodology
                        sample = trades[0]
                        has_price = 'price' in sample or 'execution_price' in sample
                        has_size = 'size' in sample or 'volume' in sample or 'amount' in sample
                        has_timestamp = 'timestamp' in sample or 'created_at' in sample
                        has_side = 'side' in sample or 'type' in sample
                        
                        print(f"   📈 Has price: {has_price}")
                        print(f"   📊 Has volume: {has_size}")
                        print(f"   ⏰ Has timestamp: {has_timestamp}")
                        print(f"   📍 Has side: {has_side}")
                        
                        if has_price and has_size and has_timestamp:
                            successful_data += 1
                            print(f"   ✅ SUITABLE for Claude's methodology!")
                        else:
                            print(f"   ⚠️ Missing required fields")
                    else:
                        print(f"   ❌ No trades found")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            if successful_data > 0:
                print(f"\n🎉 SUCCESS: {successful_data}/{len(test_markets)} markets have complete trade data")
                print(f"✅ Ready to implement Claude's volume spike methodology!")
                return True
            else:
                print(f"\n❌ No markets have complete trade data")
                return False
                
    except Exception as e:
        print(f"❌ Claude methodology test failed: {e}")
        return False

def main():
    """Run complete authentication test"""
    print("🔑 POLYMARKET COMPLETE AUTHENTICATION TEST")
    print("🎯 Goal: Access historical trade data for Claude's volume spike methodology")
    print("=" * 70)
    
    # Test basic authentication and trade access
    success, trades, sample_trade = test_complete_authentication()
    
    if success:
        print(f"\n🎉 AUTHENTICATION SUCCESSFUL!")
        print(f"✅ Historical trade data access confirmed")
        
        # Test Claude's specific data requirements
        claude_ready = test_claude_volume_spike_data()
        
        if claude_ready:
            print(f"\n🚀 READY TO IMPLEMENT CLAUDE'S METHODOLOGY")
            print(f"📊 All required data fields available")
            print(f"🎯 Can proceed with volume spike backtesting")
        
    else:
        print(f"\n❌ Authentication still failed")
        print(f"🔧 May need different approach or additional setup")

if __name__ == "__main__":
    main()