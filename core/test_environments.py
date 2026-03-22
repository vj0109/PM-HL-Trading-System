#!/usr/bin/env python3
"""
TEST DIFFERENT POLYMARKET ENVIRONMENTS
Check if credentials work on different environments (testnet vs mainnet)
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
import requests

def test_different_environments():
    """Test credentials on different possible environments"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
    
    print("🌐 TESTING DIFFERENT POLYMARKET ENVIRONMENTS")
    print("=" * 55)
    
    # Different possible environments
    environments = [
        {"name": "Production CLOB", "url": "https://clob.polymarket.com"},
        {"name": "Staging CLOB", "url": "https://staging-clob.polymarket.com"},
        {"name": "Testnet CLOB", "url": "https://testnet-clob.polymarket.com"},
        {"name": "API v1", "url": "https://api.polymarket.com"},
        {"name": "Data API", "url": "https://data-api.polymarket.com"},
        {"name": "Gamma API", "url": "https://gamma-api.polymarket.com"},
    ]
    
    for env in environments:
        print(f"\n🧪 Testing: {env['name']}")
        print(f"🔗 URL: {env['url']}")
        
        try:
            # Test basic connection first
            response = requests.get(f"{env['url']}/time", timeout=5)
            if response.status_code == 200:
                print("✅ Basic connection works")
                
                # Test with credentials
                try:
                    creds = ApiCreds(
                        api_key=api_key,
                        api_secret=api_secret,
                        api_passphrase=api_passphrase
                    )
                    
                    client = ClobClient(host=env['url'], creds=creds)
                    
                    # Test authenticated endpoint
                    try:
                        api_keys = client.get_api_keys()
                        print("🎉 AUTHENTICATION SUCCESS!")
                        print(f"✅ API Keys: {api_keys}")
                        
                        # If this works, test trade data
                        try:
                            markets = client.get_markets()
                            if isinstance(markets, dict) and 'data' in markets:
                                condition_id = markets['data'][0]['condition_id']
                                trades = client.get_trades({"market": condition_id})
                                print(f"🎉 TRADE DATA SUCCESS: {len(trades)} trades")
                                return env['name'], env['url']
                        except Exception as e:
                            print(f"⚠️ Trade data failed: {e}")
                            
                    except Exception as e:
                        print(f"❌ Auth failed: {e}")
                        
                except Exception as e:
                    print(f"❌ Client creation failed: {e}")
                    
            else:
                print(f"❌ Connection failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Environment unreachable: {e}")
    
    return None, None

def test_api_key_validation():
    """Check if the API key format/length is correct"""
    
    api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
    api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
    api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
    
    print(f"\n🔍 API CREDENTIAL ANALYSIS")
    print("=" * 30)
    
    print(f"API Key format: {api_key}")
    print(f"  - Length: {len(api_key)}")
    print(f"  - Format: UUID-like with dashes")
    print(f"  - Valid UUID format: {api_key.count('-') == 4}")
    
    print(f"\nAPI Secret format: {api_secret}")
    print(f"  - Length: {len(api_secret)}")
    print(f"  - Ends with =: {api_secret.endswith('=')}")
    print(f"  - Base64-like: {all(c.isalnum() or c in '+/=' for c in api_secret)}")
    
    print(f"\nPassphrase format: {api_passphrase}")
    print(f"  - Length: {len(api_passphrase)}")
    print(f"  - Hex-like: {all(c in '0123456789abcdef' for c in api_passphrase)}")
    
    # Check if these look like valid credentials
    valid_format = (
        len(api_key) == 36 and  # UUID length
        api_key.count('-') == 4 and  # UUID dashes
        len(api_secret) >= 40 and  # Reasonable secret length
        api_secret.endswith('=') and  # Base64 padding
        len(api_passphrase) == 64 and  # Hex string length
        all(c in '0123456789abcdef' for c in api_passphrase)  # Hex format
    )
    
    print(f"\n📊 Credential format analysis:")
    print(f"✅ All formats look valid: {valid_format}")

def main():
    """Test environments and analyze credentials"""
    print("🔍 POLYMARKET ENVIRONMENT & CREDENTIAL TESTING")
    print("🎯 Goal: Find working environment for provided credentials")
    print("=" * 65)
    
    # Test API key format
    test_api_key_validation()
    
    # Test different environments
    working_env, working_url = test_different_environments()
    
    if working_env:
        print(f"\n🎉 SUCCESS!")
        print(f"✅ Working environment: {working_env}")
        print(f"🔗 Working URL: {working_url}")
    else:
        print(f"\n❌ NO WORKING ENVIRONMENT FOUND")
        print("Possible issues:")
        print("- API key may be invalid or expired")
        print("- Account may need activation")
        print("- Credentials may be for a different service")
        print("- API may require additional setup steps")

if __name__ == "__main__":
    main()