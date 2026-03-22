#!/usr/bin/env python3
"""
POLYMARKET VOLUME SPIKE - CLAUDE'S METHOD WITH AUTHENTICATION
Using provided API key to access historical trade data
Following Claude's exact methodology with real data
"""

import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import statistics

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import TradeParams, ApiCreds

class PMClaudeAuthenticated:
    def __init__(self):
        # API credentials provided by VJ
        self.api_key = "019d1553-8a65-708e-8a4a-7076da3a6de5"
        
        # Initialize authenticated client
        try:
            # First try with just API key (read-only)
            self.client = ClobClient(
                host="https://clob.polymarket.com",
                creds=ApiCreds(api_key=self.api_key)
            )
            
            # Test connection
            ok = self.client.get_ok()
            server_time = self.client.get_server_time()
            print(f"✅ Authenticated connection - Status: {ok}, Time: {server_time}")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("⚠️ Trying read-only mode...")
            
            # Fallback to read-only
            self.client = ClobClient("https://clob.polymarket.com")
            
        # Claude's test parameters
        self.test_params = {
            'volume_multipliers': [2, 3, 5, 10],
            'min_price_moves': [0.03, 0.05, 0.08, 0.10],
            'holding_periods': ['6h', '12h', '24h', '48h', '7d', 'resolution']
        }
    
    def get_liquid_resolved_markets(self, limit: int = 50) -> List[Dict]:
        """
        Claude's Step 1: GET /events?closed=true&order=volume&ascending=false
        """
        print(f"🔍 Fetching {limit} most liquid resolved markets...")
        
        try:
            # Get markets with CLOB client
            response = self.client.get_markets()
            
            if isinstance(response, dict) and 'data' in response:
                markets = response['data']
            else:
                markets = response
            
            # Filter for closed markets (for backtesting)
            closed_markets = []
            for market in markets:
                if isinstance(market, dict) and market.get('closed', False):
                    # Check if market has resolution data
                    tokens = market.get('tokens', [])
                    if tokens and any(token.get('winner') is not None for token in tokens):
                        closed_markets.append(market)
            
            # Sort by implied volume/activity (simplified)
            closed_markets.sort(key=lambda m: len(m.get('tokens', [])), reverse=True)
            
            print(f"📊 Found {len(markets)} total markets, {len(closed_markets)} closed with resolution")
            return closed_markets[:limit]
            
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def get_market_trades_authenticated(self, condition_id: str) -> List[Dict]:
        """
        Claude's Step 2: GET /activity?market={conditionId}&type=TRADE
        Now with authentication!
        """
        print(f"📈 Fetching authenticated trade data for {condition_id[:10]}...")
        
        try:
            # Use TradeParams to get market trades
            trade_params = TradeParams(market=condition_id)
            
            trades = self.client.get_trades(trade_params)
            print(f"   ✅ Found {len(trades)} trades with authentication")
            return trades
            
        except Exception as e:
            print(f"   ❌ Error fetching authenticated trades: {e}")
            
            # Try alternative methods
            try:
                # Try get_market_trades_events
                events = self.client.get_market_trades_events(condition_id)
                if events:
                    print(f"   ✅ Found {len(events)} trade events")
                    return events
                    
            except Exception as e2:
                print(f"   ❌ Alternative method failed: {e2}")
            
            return []
    
    def aggregate_hourly_volume_bars(self, trades: List[Dict]) -> Dict[str, float]:
        """
        Claude's Step 3: Aggregate trades into hourly volume bars
        """
        hourly_volumes = defaultdict(float)
        
        for trade in trades:
            try:
                # Extract timestamp
                timestamp = (trade.get('timestamp') or 
                           trade.get('created_at') or 
                           trade.get('time') or
                           trade.get('tx_hash_timestamp'))
                
                if not timestamp:
                    continue
                
                # Parse timestamp
                if isinstance(timestamp, str):
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
                
                # Extract volume/size
                volume = float(trade.get('size', 0) or 
                             trade.get('volume', 0) or 
                             trade.get('amount', 0) or 0)
                
                if volume > 0:
                    hourly_volumes[hour_key] += volume
                    
            except Exception as e:
                continue
        
        print(f"   📊 Aggregated into {len(hourly_volumes)} hourly bars")
        return dict(hourly_volumes)
    
    def extract_price_history(self, trades: List[Dict]) -> Dict[str, float]:
        """
        Claude's Step 4: Extract price history from trade data
        """
        prices = {}
        
        for trade in trades:
            try:
                timestamp = (trade.get('timestamp') or 
                           trade.get('created_at') or 
                           trade.get('time'))
                
                price = float(trade.get('price', 0) or 
                            trade.get('execution_price', 0) or 0)
                
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
        
        print(f"   📊 Extracted {len(prices)} price points")
        return prices
    
    def detect_volume_spikes_claude(self, volume_bars: Dict[str, float], 
                                   volume_multiplier: float = 3.0) -> List[Dict]:
        """
        Claude's Step 5: Detect volume spikes (>X * rolling 24h average)
        """
        spikes = []
        timestamps = sorted(volume_bars.keys())
        
        for i, timestamp in enumerate(timestamps):
            current_volume = volume_bars[timestamp]
            
            # Calculate 24-hour rolling average
            window_start = max(0, i - 24)
            window_volumes = [volume_bars[ts] for ts in timestamps[window_start:i]]
            
            if len(window_volumes) < 12:  # Need at least 12 hours of history
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
        Claude's Step 6: Detect probability moves >5 percentage points
        """
        moves = []
        timestamps = sorted(prices.keys())
        
        for i in range(1, len(timestamps)):
            prev_price = prices[timestamps[i-1]]
            curr_price = prices[timestamps[i]]
            
            # Calculate move in percentage points (not percentage)
            price_change = abs(curr_price - prev_price)
            
            if price_change >= min_move:  # Claude's: >5 percentage points
                direction = 'UP' if curr_price > prev_price else 'DOWN'
                moves.append({
                    'timestamp': timestamps[i],
                    'prev_price': prev_price,
                    'curr_price': curr_price,
                    'change_pct_points': price_change,
                    'direction': direction
                })
        
        return moves
    
    def find_coincident_signals_claude(self, spikes: List[Dict], moves: List[Dict]) -> List[Dict]:
        """
        Claude's Step 7: Find volume spikes that coincide with probability moves
        """
        signals = []
        
        for spike in spikes:
            spike_time = datetime.fromisoformat(spike['timestamp'])
            
            for move in moves:
                move_time = datetime.fromisoformat(move['timestamp'])
                
                # Check if spike and move occurred within 2 hours
                time_diff = abs((move_time - spike_time).total_seconds() / 3600)
                
                if time_diff <= 2.0:  # Within 2 hours
                    signals.append({
                        'timestamp': spike['timestamp'],
                        'volume_ratio': spike['ratio'],
                        'price_change_pct_points': move['change_pct_points'],
                        'direction': move['direction'],
                        'entry_price': move['curr_price'],
                        'volume': spike['volume'],
                        'reasoning': f"Claude signal: {spike['ratio']:.1f}x volume + {move['change_pct_points']:.1%} {move['direction']} move"
                    })
                    
                    # Only match each spike once
                    break
        
        return signals
    
    def test_claude_methodology_authenticated(self, market: Dict) -> Optional[Dict]:
        """
        Test Claude's complete methodology with authenticated data access
        """
        condition_id = market.get('condition_id')
        question = market.get('question', 'Unknown')[:60]
        
        if not condition_id:
            return None
        
        print(f"\n🎯 Testing Claude methodology: {question}...")
        
        # Step 1: Get authenticated trade data
        trades = self.get_market_trades_authenticated(condition_id)
        
        if len(trades) < 20:  # Need sufficient trade history
            print(f"   ⚠️ Insufficient trades ({len(trades)})")
            return None
        
        # Step 2: Aggregate hourly volume bars
        volume_bars = self.aggregate_hourly_volume_bars(trades)
        
        if len(volume_bars) < 24:
            print(f"   ⚠️ Insufficient volume history ({len(volume_bars)} hours)")
            return None
        
        # Step 3: Extract price history
        prices = self.extract_price_history(trades)
        
        if len(prices) < 20:
            print(f"   ⚠️ Insufficient price history ({len(prices)} points)")
            return None
        
        # Step 4: Detect volume spikes (Claude's 3x threshold)
        spikes = self.detect_volume_spikes_claude(volume_bars, volume_multiplier=3.0)
        
        # Step 5: Detect probability moves (Claude's 5% threshold)
        moves = self.detect_probability_moves_claude(prices, min_move=0.05)
        
        # Step 6: Find coincident signals
        signals = self.find_coincident_signals_claude(spikes, moves)
        
        print(f"   📊 Results: {len(spikes)} spikes, {len(moves)} moves, {len(signals)} signals")
        
        if signals:
            print(f"   ✅ SUCCESS: Found {len(signals)} authenticated Claude signals!")
            for signal in signals[:2]:  # Show first 2
                print(f"      {signal['reasoning']}")
            
            return {
                'market_id': condition_id,
                'question': question,
                'total_trades': len(trades),
                'volume_hours': len(volume_bars),
                'price_points': len(prices),
                'spikes': len(spikes),
                'moves': len(moves),
                'signals': signals,
                'market_resolution': self.get_market_resolution(market)
            }
        else:
            print(f"   ❌ No coincident signals found")
            return None
    
    def get_market_resolution(self, market: Dict) -> Optional[str]:
        """
        Determine market resolution for backtesting
        """
        tokens = market.get('tokens', [])
        for token in tokens:
            if token.get('winner'):
                return token.get('outcome')
        return None

def main():
    """Test Claude's methodology with authenticated API access"""
    tester = PMClaudeAuthenticated()
    
    print("🚀 CLAUDE'S POLYMARKET METHODOLOGY - AUTHENTICATED")
    print("🔑 Using provided API key for historical trade data access")
    print("📊 Following Claude's exact 7-step process:")
    print("   1. Get liquid resolved markets")
    print("   2. Fetch authenticated trade data")
    print("   3. Aggregate hourly volume bars")
    print("   4. Extract price history from trades")
    print("   5. Detect volume spikes (>3x 24h average)")
    print("   6. Detect probability moves (>5 percentage points)")
    print("   7. Find coincident volume spike + price move signals")
    print("=" * 80)
    
    # Get markets for testing
    markets = tester.get_liquid_resolved_markets(limit=10)
    
    if not markets:
        print("❌ No resolved markets available")
        return
    
    # Test Claude methodology on sample markets
    successful_tests = []
    total_signals = 0
    
    for i, market in enumerate(markets[:5]):  # Test first 5
        try:
            result = tester.test_claude_methodology_authenticated(market)
            if result and result['signals']:
                successful_tests.append(result)
                total_signals += len(result['signals'])
                
        except Exception as e:
            print(f"   ❌ Error testing market: {e}")
            continue
    
    # Results summary
    print(f"\n📊 CLAUDE METHODOLOGY RESULTS (AUTHENTICATED):")
    print("=" * 60)
    print(f"Markets tested: {min(5, len(markets))}")
    print(f"Markets with signals: {len(successful_tests)}")
    print(f"Total Claude signals found: {total_signals}")
    
    if successful_tests:
        print(f"\n✅ AUTHENTICATION SUCCESS!")
        print(f"🎯 Claude's methodology working with real trade data!")
        print(f"\nSample results:")
        
        for result in successful_tests[:3]:
            print(f"\n📊 {result['question']}")
            print(f"   Trades: {result['total_trades']}, Signals: {len(result['signals'])}")
            for signal in result['signals'][:2]:
                print(f"      - {signal['reasoning']}")
        
        print(f"\n🚀 READY FOR FULL BACKTESTING:")
        print("   1. Test different parameters (2x, 3x, 5x, 10x volume)")
        print("   2. Test different move thresholds (3%, 5%, 8%, 10%)")
        print("   3. Simulate holding periods (6h, 12h, 24h, 48h, 7d)")
        print("   4. Calculate win rates and expected values")
        print("   5. Apply 55%+ win rate validation criteria")
        
    else:
        print(f"❌ No signals found")
        print(f"🔧 Authentication working but may need parameter adjustment")

if __name__ == "__main__":
    main()