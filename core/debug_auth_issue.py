#!/usr/bin/env python3
"""
DEBUG POLYMARKET AUTHENTICATION ISSUE
Try different approaches to understand the authentication problem
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
import requests

def test_different_auth_approaches():
    """Try various authentication approaches"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
    
    print("🔍 DEBUGGING POLYMARKET AUTHENTICATION")
    print("=" * 50)
    
    # Test 1: Check what endpoints work without auth
    print("\n🧪 Test 1: Endpoints that work without authentication")
    try:
        client = ClobClient(host="https://clob.polymarket.com")
        
        # These should work without auth
        ok = client.get_ok()
        time_resp = client.get_server_time()
        markets = client.get_markets()
        
        print(f"✅ get_ok(): {ok}")
        print(f"✅ get_server_time(): {time_resp}")
        print(f"✅ get_markets(): {len(markets.get('data', [])) if isinstance(markets, dict) else 'Failed'}")
        
        # Test a specific market's order book
        if isinstance(markets, dict) and 'data' in markets:
            sample_market = markets['data'][0]
            condition_id = sample_market['condition_id']
            
            try:
                order_book = client.get_order_book(condition_id)
                print(f"✅ get_order_book(): Available")
            except Exception as e:
                print(f"❌ get_order_book(): {e}")
                
            try:
                midpoint = client.get_midpoint(condition_id)
                print(f"✅ get_midpoint(): {midpoint}")
            except Exception as e:
                print(f"❌ get_midpoint(): {e}")
        
    except Exception as e:
        print(f"❌ Basic client failed: {e}")
    
    # Test 2: Check authentication methods
    print(f"\n🧪 Test 2: Different credential configurations")
    
    configs_to_test = [
        {"api_key": api_key, "api_secret": api_secret, "api_passphrase": api_passphrase},
        {"api_key": api_key, "api_secret": api_secret, "api_passphrase": ""},
        {"api_key": api_key, "api_secret": "", "api_passphrase": api_passphrase},
    ]
    
    for i, config in enumerate(configs_to_test):
        print(f"\nConfig {i+1}: key={bool(config['api_key'])}, secret={bool(config['api_secret'])}, pass={bool(config['api_passphrase'])}")
        try:
            creds = ApiCreds(**config)
            client = ClobClient(host="https://clob.polymarket.com", creds=creds)
            
            # Try to get API keys (this might work if authenticated)
            try:
                api_keys = client.get_api_keys()
                print(f"✅ get_api_keys(): {api_keys}")
            except Exception as e:
                print(f"❌ get_api_keys(): {e}")
                
        except Exception as e:
            print(f"❌ Client creation failed: {e}")
    
    # Test 3: Check credential validation
    print(f"\n🧪 Test 3: Credential validation")
    try:
        creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        )
        
        # Check if there's a credential validation endpoint
        client = ClobClient(host="https://clob.polymarket.com", creds=creds)
        
        try:
            # This might tell us if credentials are valid
            result = client.get_ok()  # Try with auth
            print(f"✅ Authenticated get_ok(): {result}")
        except Exception as e:
            print(f"❌ Authenticated get_ok(): {e}")
            
    except Exception as e:
        print(f"❌ Credential validation failed: {e}")

def test_manual_http_requests():
    """Try manual HTTP requests to understand the API better"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    
    print(f"\n🔧 TESTING MANUAL HTTP REQUESTS")
    print("=" * 40)
    
    base_url = "https://clob.polymarket.com"
    
    # Test different header configurations
    headers_configs = [
        {"Authorization": f"Bearer {api_key}"},
        {"X-API-Key": api_key},
        {"CLOB-API-KEY": api_key},
        {}  # No auth headers
    ]
    
    for i, headers in enumerate(headers_configs):
        print(f"\n🧪 HTTP Test {i+1}: {list(headers.keys()) if headers else 'No auth'}")
        
        try:
            # Test the trades endpoint directly
            response = requests.get(f"{base_url}/trades", headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: Got {len(data) if isinstance(data, list) else 'data'}")
            else:
                print(f"❌ Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

def main():
    """Run authentication debugging"""
    print("🔍 POLYMARKET AUTHENTICATION DEBUGGING")
    print("🎯 Goal: Understand why trade data access is failing")
    print("=" * 60)
    
    test_different_auth_approaches()
    test_manual_http_requests()
    
    print(f"\n📊 SUMMARY:")
    print("- API credentials provided but trade endpoint still returns auth error")
    print("- May need account activation, different permissions, or endpoint approach")
    print("- Need to investigate Polymarket documentation for proper setup")

if __name__ == "__main__":
    main()