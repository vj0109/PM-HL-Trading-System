#!/usr/bin/env python3
"""
POLYMARKET VOLUME SPIKE BACKTESTING - OFFICIAL CLIENT
Using the official py-clob-client with correct API methods
Following Claude's methodology with proper Polymarket APIs
"""

import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import statistics

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import TradeParams

class PMVolumeSpikeOfficialBacktester:
    def __init__(self):
        # Official Polymarket CLOB client
        self.client = ClobClient("https://clob.polymarket.com")  # Level 0 (no auth)
        
        # Test connection
        try:
            ok = self.client.get_ok()
            time_resp = self.client.get_server_time()
            print(f"✅ Connected to Polymarket CLOB API - Status: {ok}, Time: {time_resp}")
        except Exception as e:
            print(f"❌ Failed to connect to CLOB API: {e}")
            
        # Test parameters (Claude's specifications)
        self.test_params = {
            'volume_multipliers': [2, 3, 5, 10],  # Claude's: 2x, 3x, 5x, 10x
            'min_price_moves': [0.03, 0.05, 0.08, 0.10],  # Claude's: 3%, 5%, 8%, 10%
            'holding_periods': ['6h', '12h', '24h', '48h', '7d'],
            'min_liquidity': [25000, 50000, 100000]  # Claude's: $25K, $50K, $100K
        }
    
    def get_active_markets(self) -> List[Dict]:
        """
        Get active markets using official client
        """
        print("🔍 Fetching active markets from official CLOB API...")
        
        try:
            # Get all markets - API returns dict with 'data' key
            response = self.client.get_markets()
            
            if isinstance(response, dict) and 'data' in response:
                markets = response['data']
            else:
                markets = response
            
            print(f"📊 Raw response type: {type(response)}")
            print(f"📊 Markets found: {len(markets) if isinstance(markets, list) else 'Not a list'}")
            
            # Filter for markets we can analyze
            # Look for markets that have historical data (can be closed but with trades)
            analyzable_markets = []
            active_count = 0
            closed_count = 0
            
            for market in markets:
                if isinstance(market, dict):
                    is_active = market.get('active', False)
                    is_closed = market.get('closed', True)
                    
                    if is_active:
                        active_count += 1
                    if is_closed:
                        closed_count += 1
                    
                    # For backtesting, we want markets with historical data
                    # Include both active and recently closed markets
                    if market.get('enable_order_book', False) or len(market.get('tokens', [])) > 0:
                        analyzable_markets.append(market)
            
            print(f"📊 Found {len(markets)} total markets:")
            print(f"   Active: {active_count}, Closed: {closed_count}")
            print(f"   Analyzable (with data): {len(analyzable_markets)}")
            return analyzable_markets[:10]  # Return first 10 for testing
            
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_market_trades(self, condition_id: str, limit: int = 1000) -> List[Dict]:
        """
        Get trade history for a market using official client
        """
        print(f"📈 Fetching trades for market {condition_id[:10]}...")
        
        try:
            # Use TradeParams to get market trades
            trade_params = TradeParams(
                market=condition_id,
                # Can add other filters here
            )
            
            trades = self.client.get_trades(trade_params)
            print(f"   📊 Found {len(trades)} trades")
            return trades
            
        except Exception as e:
            print(f"   ❌ Error fetching trades: {e}")
            return []
    
    def get_market_live_activity(self, condition_id: str) -> List[Dict]:
        """
        Get live market activity using official client
        """
        try:
            activity = self.client.get_market_trades_events(condition_id)
            return activity if activity else []
        except Exception as e:
            print(f"   ❌ Error fetching live activity: {e}")
            return []
    
    def aggregate_hourly_volume_bars(self, trades: List[Dict]) -> Dict[str, float]:
        """
        Aggregate trades into hourly volume bars (Claude's Step 3)
        """
        hourly_volumes = defaultdict(float)
        
        for trade in trades:
            try:
                # Parse timestamp from trade
                timestamp = trade.get('timestamp') or trade.get('created_at')
                if not timestamp:
                    continue
                
                # Convert to datetime
                if isinstance(timestamp, str):
                    # Handle various timestamp formats
                    try:
                        if 'T' in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(float(timestamp))
                    except:
                        continue
                elif isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                else:
                    continue
                
                # Round to hour
                hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                
                # Add volume
                volume = float(trade.get('size', 0) or trade.get('volume', 0) or 0)
                hourly_volumes[hour_key] += volume
                
            except Exception as e:
                continue
        
        return dict(hourly_volumes)
    
    def get_market_prices_from_trades(self, trades: List[Dict]) -> Dict[str, float]:
        """
        Extract price history from trades
        """
        prices = {}
        
        for trade in trades:
            try:
                timestamp = trade.get('timestamp') or trade.get('created_at')
                price = float(trade.get('price', 0))
                
                if timestamp and price > 0:
                    if isinstance(timestamp, str):
                        if 'T' in timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(float(timestamp))
                    else:
                        dt = datetime.fromtimestamp(timestamp)
                    
                    prices[dt.isoformat()] = price
                    
            except:
                continue
        
        return prices
    
    def detect_volume_spikes_claude(self, volume_bars: Dict[str, float], 
                                   volume_multiplier: float = 3.0, 
                                   window_hours: int = 24) -> List[Dict]:
        """
        Detect volume spikes exactly as Claude specified
        """
        spikes = []
        timestamps = sorted(volume_bars.keys())
        
        for i, timestamp in enumerate(timestamps):
            current_volume = volume_bars[timestamp]
            
            # Calculate rolling average for window
            window_start = max(0, i - window_hours)
            window_volumes = [volume_bars[ts] for ts in timestamps[window_start:i]]
            
            if len(window_volumes) < window_hours // 2:
                continue
            
            avg_volume = statistics.mean(window_volumes)
            
            if avg_volume > 0 and current_volume >= volume_multiplier * avg_volume:
                spikes.append({
                    'timestamp': timestamp,
                    'volume': current_volume,
                    'avg_volume': avg_volume,
                    'ratio': current_volume / avg_volume
                })
        
        return spikes
    
    def detect_probability_moves_claude(self, prices: Dict[str, float], 
                                       min_move: float = 0.05) -> List[Dict]:
        """
        Detect probability moves exactly as Claude specified
        """
        moves = []
        timestamps = sorted(prices.keys())
        
        for i in range(1, len(timestamps)):
            prev_price = prices[timestamps[i-1]]
            curr_price = prices[timestamps[i]]
            
            if prev_price > 0:
                price_change = abs(curr_price - prev_price)
                
                if price_change >= min_move:  # Claude's: >5 percentage points
                    direction = 'UP' if curr_price > prev_price else 'DOWN'
                    moves.append({
                        'timestamp': timestamps[i],
                        'prev_price': prev_price,
                        'curr_price': curr_price,
                        'change': price_change,
                        'direction': direction
                    })
        
        return moves
    
    def find_spike_move_combinations_claude(self, spikes: List[Dict], moves: List[Dict]) -> List[Dict]:
        """
        Find volume spikes that coincide with probability moves (Claude's method)
        """
        combinations = []
        
        for spike in spikes:
            spike_time = datetime.fromisoformat(spike['timestamp'])
            
            for move in moves:
                move_time = datetime.fromisoformat(move['timestamp'])
                
                # Claude's condition: spike accompanies probability move
                time_diff = abs((move_time - spike_time).total_seconds() / 3600)
                
                if time_diff <= 2:  # Within 2 hours
                    combinations.append({
                        'timestamp': spike['timestamp'],
                        'volume_ratio': spike['ratio'],
                        'price_change': move['change'],
                        'direction': move['direction'],
                        'entry_price': move['curr_price'],
                        'volume': spike['volume'],
                        'reasoning': f"Volume {spike['ratio']:.1f}x + {move['change']:.1%} move {move['direction']}"
                    })
        
        return combinations
    
    def test_single_market_claude_method(self, market: Dict) -> Optional[Dict]:
        """
        Test Claude's complete methodology on one market
        """
        condition_id = market.get('condition_id') or market.get('id')
        if not condition_id:
            return None
        
        market_question = market.get('question', 'Unknown')[:60]
        print(f"\n🎯 Testing Claude method: {market_question}...")
        
        # Step 1: Get trade activity (Claude's /activity endpoint)
        trades = self.get_market_trades(condition_id)
        
        if len(trades) < 10:
            print(f"   ⚠️ Insufficient trade data ({len(trades)} trades)")
            return None
        
        # Step 2: Aggregate hourly volume bars (Claude's method)
        volume_bars = self.aggregate_hourly_volume_bars(trades)
        
        if len(volume_bars) < 12:
            print(f"   ⚠️ Insufficient volume history ({len(volume_bars)} hours)")
            return None
        
        # Step 3: Get price history from trades
        prices = self.get_market_prices_from_trades(trades)
        
        if len(prices) < 10:
            print(f"   ⚠️ Insufficient price history ({len(prices)} points)")
            return None
        
        # Step 4: Detect volume spikes (Claude's parameters)
        spikes = self.detect_volume_spikes_claude(volume_bars, volume_multiplier=3.0)
        
        # Step 5: Detect probability moves (Claude's >5% threshold)  
        moves = self.detect_probability_moves_claude(prices, min_move=0.05)
        
        # Step 6: Find combinations (Claude's coincident detection)
        combinations = self.find_spike_move_combinations_claude(spikes, moves)
        
        print(f"   📊 Found {len(spikes)} spikes, {len(moves)} moves, {len(combinations)} combinations")
        
        if combinations:
            print(f"   ✅ SUCCESS: {len(combinations)} volume spike + probability move signals")
            return {
                'market_id': condition_id,
                'market_question': market_question,
                'spikes': len(spikes),
                'moves': len(moves),
                'combinations': combinations
            }
        else:
            print(f"   ❌ No spike+move combinations found")
            return None

def main():
    """Test Claude's Volume Spike methodology with official Polymarket client"""
    backtester = PMVolumeSpikeOfficialBacktester()
    
    print("🚀 POLYMARKET VOLUME SPIKE - CLAUDE'S METHOD + OFFICIAL CLIENT")
    print("📊 Using official py-clob-client with correct API endpoints")
    print("🔗 Following Claude's exact methodology:")
    print("   1. Get active markets from CLOB API")
    print("   2. Fetch trade data via get_trades()")
    print("   3. Aggregate hourly volume bars")
    print("   4. Extract price history from trades") 
    print("   5. Detect volume spikes (>3x average)")
    print("   6. Detect probability moves (>5%)")
    print("   7. Find spike+move combinations")
    print("=" * 80)
    
    # Get active markets
    markets = backtester.get_active_markets()
    
    if not markets:
        print("❌ No active markets found")
        return
    
    # Test on sample markets
    print(f"\n🧪 Testing Claude's method on {min(5, len(markets))} active markets...")
    
    successful_tests = []
    total_combinations = 0
    
    for i, market in enumerate(markets[:5]):
        try:
            result = backtester.test_single_market_claude_method(market)
            if result:
                successful_tests.append(result)
                total_combinations += len(result['combinations'])
                
        except Exception as e:
            print(f"   ❌ Error testing market: {e}")
            continue
    
    # Results
    print(f"\n📊 CLAUDE METHOD RESULTS WITH OFFICIAL CLIENT:")
    print("=" * 60)
    print(f"Markets tested: {min(5, len(markets))}")
    print(f"Markets with signals: {len(successful_tests)}")
    print(f"Total spike+move combinations: {total_combinations}")
    
    if successful_tests:
        print(f"\n✅ SUCCESS: Found {total_combinations} volume spike + probability move signals!")
        print(f"🎯 Sample signals:")
        for result in successful_tests[:3]:
            print(f"   📊 {result['market_question']}")
            for combo in result['combinations'][:2]:
                print(f"      {combo['reasoning']}")
        
        print(f"\n🚀 READY FOR FULL BACKTESTING:")
        print("   1. Run on larger market sample") 
        print("   2. Test different parameters (2x, 3x, 5x, 10x volume)")
        print("   3. Test different move thresholds (3%, 5%, 8%, 10%)")
        print("   4. Simulate forward performance with holding periods")
        print("   5. Apply 55%+ win rate validation criteria")
        
    else:
        print(f"❌ No signals detected with current parameters")
        print(f"🔧 Try adjusting parameters:")
        print("   - Lower volume multiplier (2x instead of 3x)")
        print("   - Lower move threshold (3% instead of 5%)")
        print("   - Different time windows")

if __name__ == "__main__":
    main()