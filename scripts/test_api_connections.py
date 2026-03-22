#!/usr/bin/env python3
"""Test real API connections"""

import requests
import json

print('🧪 TESTING REAL API CONNECTIONS:')
print('=' * 50)

# Test Hyperliquid API
print('📊 HYPERLIQUID API:')
try:
    response = requests.post(
        'https://api.hyperliquid.xyz/info',
        json={'type': 'allMids'},
        timeout=5
    )
    
    if response.status_code == 200:
        prices = response.json()
        print(f'✅ Connected - Got {len(prices)} prices')
        print(f'   BTC: ${float(prices.get("BTC", 0)):,.2f}')
        print(f'   ETH: ${float(prices.get("ETH", 0)):,.2f}')  
        print(f'   SOL: ${float(prices.get("SOL", 0)):,.2f}')
    else:
        print(f'❌ Failed - Status: {response.status_code}')
        
except Exception as e:
    print(f'❌ Error: {e}')

print()

# Test Polymarket API  
print('🎲 POLYMARKET API:')
try:
    # Test with a known active market
    response = requests.get('https://gamma-api.polymarket.com/markets?limit=1&active=true', timeout=5)
    
    if response.status_code == 200:
        markets = response.json()
        if markets:
            market = markets[0]
            print(f'✅ Connected - Sample market:')
            print(f'   ID: {market.get("id", "Unknown")}')
            print(f'   Question: {market.get("question", "Unknown")[:50]}...')
            print(f'   Active: {market.get("active", False)}')
            prices = market.get('outcomePrices', [])
            if prices:
                print(f'   YES: ${float(prices[0]):.3f}, NO: ${float(prices[1]):.3f}')
        else:
            print('⚠️  Connected but no markets returned')
    else:
        print(f'❌ Failed - Status: {response.status_code}')
        
except Exception as e:
    print(f'❌ Error: {e}')

print()

print('🎯 OUR TRADING SYSTEM VERIFICATION:')
print('=' * 50)

# Check if our trading system uses these APIs
import simple_hl_trader
import simple_whale_trader

hl_trader = simple_hl_trader.SimpleHLTrader()
whale_trader = simple_whale_trader.SimpleWhaleTrader()

print('📊 HL Trader API test:')
try:
    info = hl_trader.get_hl_info()
    if info:
        print(f'✅ HL API working - Got {len(info)} assets')
    else:
        print('❌ HL API not responding')
except:
    print('❌ HL API error')

print()

print('🎲 Whale Trader API test:')  
try:
    # Test with a sample market ID
    prices = whale_trader.get_market_prices('1467763')  # Sample ID
    if prices:
        print(f'✅ PM API working - Sample prices: YES={prices.get("yes_price", 0):.3f}, NO={prices.get("no_price", 0):.3f}')
    else:
        print('⚠️  PM API connected but no prices for sample market')
except Exception as e:
    print(f'❌ PM API error: {e}')