#!/usr/bin/env python3
"""
DEBUG TRADES DATA
Check what condition_ids are actually available in the trades endpoint
"""

import requests
from collections import Counter

def debug_trades_data():
    """Check what markets actually have trades in the API"""
    
    print("🔍 DEBUGGING TRADES DATA")
    print("=" * 30)
    
    try:
        # Get recent trades
        response = requests.get("https://data-api.polymarket.com/trades", params={"limit": 100}, timeout=15)
        
        if response.status_code == 200:
            trades = response.json()
            print(f"✅ Got {len(trades)} recent trades")
            
            if trades:
                # Analyze condition_ids in trades
                condition_ids = [trade.get('conditionId') for trade in trades if trade.get('conditionId')]
                condition_counts = Counter(condition_ids)
                
                print(f"\n📊 Condition IDs in recent trades:")
                for condition_id, count in condition_counts.most_common(10):
                    print(f"   {condition_id[:20]}... : {count} trades")
                
                # Show sample trade structure
                sample_trade = trades[0]
                print(f"\n📈 Sample trade structure:")
                for key, value in sample_trade.items():
                    print(f"   {key}: {value}")
                
                return list(condition_counts.keys())
                
        else:
            print(f"❌ Failed to get trades: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return []

def test_with_active_condition_ids():
    """Test Claude's methodology with condition_ids that actually have trades"""
    
    print(f"\n🧪 TESTING WITH ACTIVE CONDITION IDS")
    print("=" * 40)
    
    # Get condition_ids with recent trades
    active_condition_ids = debug_trades_data()
    
    if not active_condition_ids:
        print("❌ No active condition_ids found")
        return
    
    # Test with first few active condition_ids
    from claude_volume_spike_methodology import ClaudeVolumeSpikePM
    
    claude_system = ClaudeVolumeSpikePM()
    
    for i, condition_id in enumerate(active_condition_ids[:3]):
        print(f"\n🔬 TESTING CONDITION ID {i+1}: {condition_id}")
        
        # Manually create market data for testing
        fake_market = {
            'condition_id': condition_id,
            'question': f'Test Market {i+1}',
            'volume': 5000,
            'closed': False,
            'resolved': False
        }
        
        try:
            # Run steps 2-7
            trades = claude_system.step2_fetch_trade_data(condition_id, limit=500)
            print(f"📊 Trades found: {len(trades)}")
            
            if trades:
                hourly_bars = claude_system.step3_aggregate_hourly_volume_bars(trades)
                print(f"📈 Hourly bars: {len(hourly_bars)}")
                
                if not hourly_bars.empty:
                    price_history = claude_system.step4_extract_price_history(hourly_bars)
                    volume_spikes = claude_system.step5_detect_volume_spikes(hourly_bars)
                    prob_moves = claude_system.step6_detect_probability_moves(price_history)
                    signals = claude_system.step7_find_spike_move_combinations(volume_spikes, prob_moves)
                    
                    print(f"🎯 RESULTS:")
                    print(f"   Volume spikes: {len(volume_spikes)}")
                    print(f"   Probability moves: {len(prob_moves)}")
                    print(f"   Signal combinations: {len(signals)}")
                    
                    if signals:
                        print(f"🎉 SIGNALS FOUND! Claude's methodology working!")
                        return True
                    
        except Exception as e:
            print(f"❌ Error testing {condition_id}: {e}")
            continue
    
    return False

def main():
    """Debug and test trades data"""
    print("🔍 POLYMARKET TRADES DATA DEBUGGING")
    print("🎯 Goal: Find condition_ids with actual trade data")
    print("=" * 55)
    
    success = test_with_active_condition_ids()
    
    if success:
        print(f"\n✅ SUCCESS!")
        print(f"🎯 Claude's methodology works with active markets")
    else:
        print(f"\n❌ NEED MORE INVESTIGATION")
        print(f"🔧 May need different data source or parameters")

if __name__ == "__main__":
    main()