#!/usr/bin/env python3
"""
POLYMARKET VOLUME SPIKE BACKTESTING - CLAUDE'S METHODOLOGY
Following Claude's exact approach: trade-level data → volume bars → spike detection → forward testing
"""

import requests
import time
import psycopg2
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import statistics
from collections import defaultdict

class PMVolumeSpikeClaudeBacktester:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Polymarket APIs (Claude's specified endpoints)
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        self.clob_api_base = 'https://clob.polymarket.com'
        
        # Test parameters (Claude's specifications)
        self.test_params = {
            'volume_multipliers': [2, 3, 5, 10],  # Claude's: 2x, 3x, 5x, 10x
            'min_price_moves': [0.03, 0.05, 0.08, 0.10],  # Claude's: 3%, 5%, 8%, 10%
            'holding_periods': ['6h', '12h', '24h', '48h', '7d', 'resolution'],  # Claude's periods
            'volume_windows': ['24h', '48h', '7d'],  # Claude's averaging windows
            'min_liquidity': [25000, 50000, 100000]  # Claude's: $25K, $50K, $100K
        }
    
    def get_liquid_resolved_markets(self, limit: int = 200) -> List[Dict]:
        """
        GET /events?closed=true&order=volume&ascending=false&limit=200
        Claude's Step 1: Get most liquid resolved markets
        """
        print(f"🔍 Fetching {limit} most liquid resolved markets (Claude's method)...")
        
        try:
            url = f"{self.gamma_api_base}/events"
            params = {
                'closed': 'true',
                'order': 'volume',
                'ascending': 'false',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            markets = response.json()
            print(f"📊 Found {len(markets)} liquid resolved markets")
            
            return markets
            
        except Exception as e:
            print(f"❌ Error fetching liquid markets: {e}")
            return []
    
    def get_trade_activity(self, condition_id: str) -> List[Dict]:
        """
        GET /activity?market={conditionId}&type=TRADE with pagination
        Claude's Step 2: Get all trades for market
        """
        print(f"📈 Fetching trade activity for market {condition_id[:10]}...")
        
        try:
            all_trades = []
            cursor = None
            
            while True:
                url = f"{self.gamma_api_base}/activity"
                params = {
                    'market': condition_id,
                    'type': 'TRADE',
                    'limit': 1000
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                response = requests.get(url, params=params, timeout=15)
                if response.status_code != 200:
                    print(f"   ⚠️ No trade data available for {condition_id}")
                    break
                
                data = response.json()
                
                if isinstance(data, list):
                    trades = data
                    next_cursor = None
                elif isinstance(data, dict):
                    trades = data.get('data', [])
                    next_cursor = data.get('next_cursor')
                else:
                    break
                
                if not trades:
                    break
                    
                all_trades.extend(trades)
                
                if not next_cursor:
                    break
                    
                cursor = next_cursor
                
                # Limit to avoid infinite loops
                if len(all_trades) > 10000:
                    break
            
            print(f"   📊 Found {len(all_trades)} trades")
            return all_trades
            
        except Exception as e:
            print(f"   ❌ Error fetching trades: {e}")
            return []
    
    def aggregate_hourly_volume_bars(self, trades: List[Dict]) -> Dict[str, float]:
        """
        Claude's Step 3: Aggregate trades into hourly volume bars
        """
        hourly_volumes = defaultdict(float)
        
        for trade in trades:
            try:
                # Parse timestamp
                timestamp = trade.get('timestamp')
                if not timestamp:
                    continue
                    
                # Parse to datetime and round to hour
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    
                hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
                
                # Add volume
                volume = float(trade.get('volume', 0) or trade.get('size', 0) or 0)
                hourly_volumes[hour_key] += volume
                
            except Exception as e:
                continue
        
        return dict(hourly_volumes)
    
    def get_price_history(self, condition_id: str) -> Dict[str, float]:
        """
        GET /prices-history for price at each timestamp
        Claude's Step 4: Get historical prices
        """
        print(f"💰 Fetching price history for {condition_id[:10]}...")
        
        try:
            # Try multiple endpoints for price history
            endpoints = [
                f"/prices-history?market={condition_id}",
                f"/markets/{condition_id}/history", 
                f"/events/{condition_id}/prices"
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.gamma_api_base}{endpoint}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Parse price data into timestamp -> price mapping
                        prices = {}
                        
                        if isinstance(data, list):
                            for item in data:
                                timestamp = item.get('timestamp') or item.get('time')
                                price = item.get('price') or item.get('yes_price')
                                if timestamp and price:
                                    prices[timestamp] = float(price)
                        
                        if prices:
                            print(f"   📊 Found {len(prices)} price points")
                            return prices
                            
                except:
                    continue
            
            print(f"   ⚠️ No price history available")
            return {}
            
        except Exception as e:
            print(f"   ❌ Error fetching price history: {e}")
            return {}
    
    def detect_volume_spikes(self, volume_bars: Dict[str, float], volume_multiplier: float = 3.0, window_hours: int = 24) -> List[Dict]:
        """
        Claude's Step 5: Detect volume spikes (volume > X * rolling average)
        """
        spikes = []
        
        # Sort timestamps
        timestamps = sorted(volume_bars.keys())
        
        for i, timestamp in enumerate(timestamps):
            current_volume = volume_bars[timestamp]
            
            # Calculate rolling average for window
            window_start = max(0, i - window_hours)
            window_volumes = [volume_bars[ts] for ts in timestamps[window_start:i]]
            
            if len(window_volumes) < window_hours // 2:  # Need enough history
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
    
    def detect_price_moves(self, prices: Dict[str, float], min_move: float = 0.05) -> List[Dict]:
        """
        Detect significant price movements (>X% in short timeframe)
        """
        moves = []
        
        timestamps = sorted(prices.keys())
        
        for i in range(1, len(timestamps)):
            prev_price = prices[timestamps[i-1]]
            curr_price = prices[timestamps[i]]
            
            if prev_price > 0:
                price_change = abs(curr_price - prev_price) / prev_price
                
                if price_change >= min_move:
                    direction = 'UP' if curr_price > prev_price else 'DOWN'
                    moves.append({
                        'timestamp': timestamps[i],
                        'prev_price': prev_price,
                        'curr_price': curr_price,
                        'change': price_change,
                        'direction': direction
                    })
        
        return moves
    
    def find_spike_move_combinations(self, spikes: List[Dict], moves: List[Dict], time_tolerance_hours: int = 2) -> List[Dict]:
        """
        Claude's Method: Find volume spikes that coincide with price moves
        """
        combinations = []
        
        for spike in spikes:
            spike_time = datetime.fromisoformat(spike['timestamp'])
            
            for move in moves:
                move_time = datetime.fromisoformat(move['timestamp'])
                
                # Check if spike and move occurred within time tolerance
                time_diff = abs((move_time - spike_time).total_seconds() / 3600)
                
                if time_diff <= time_tolerance_hours:
                    combinations.append({
                        'timestamp': spike['timestamp'],
                        'volume_ratio': spike['ratio'],
                        'price_change': move['change'],
                        'direction': move['direction'],
                        'entry_price': move['curr_price'],
                        'volume': spike['volume']
                    })
        
        return combinations
    
    def simulate_forward_performance(self, signal: Dict, prices: Dict[str, float], holding_periods: List[str]) -> Dict:
        """
        Claude's Step 6: Track performance over various holding periods
        """
        entry_time = datetime.fromisoformat(signal['timestamp'])
        entry_price = signal['entry_price']
        direction = signal['direction']
        
        performance = {}
        
        for period in holding_periods:
            if period == 'resolution':
                # Find final resolution price
                final_timestamps = sorted([ts for ts in prices.keys() 
                                         if datetime.fromisoformat(ts) > entry_time])
                if final_timestamps:
                    exit_price = prices[final_timestamps[-1]]
                    period_key = 'resolution'
                else:
                    continue
            else:
                # Calculate exit time
                hours = {'6h': 6, '12h': 12, '24h': 24, '48h': 48, '7d': 168}[period]
                exit_time = entry_time + timedelta(hours=hours)
                
                # Find closest price to exit time
                exit_price = None
                min_diff = float('inf')
                
                for ts in prices.keys():
                    ts_time = datetime.fromisoformat(ts)
                    if ts_time >= entry_time:
                        diff = abs((ts_time - exit_time).total_seconds())
                        if diff < min_diff:
                            min_diff = diff
                            exit_price = prices[ts]
                
                if exit_price is None:
                    continue
                    
                period_key = period
            
            # Calculate performance
            if direction == 'UP':
                # Bought expecting price to go up
                profit = exit_price - entry_price
            else:
                # Bought expecting price to go down (short or NO position)
                profit = entry_price - exit_price
            
            performance[period_key] = {
                'exit_price': exit_price,
                'profit': profit,
                'return_pct': profit / entry_price if entry_price > 0 else 0
            }
        
        return performance
    
    def backtest_single_market(self, market: Dict) -> Optional[Dict]:
        """
        Claude's complete workflow for one market
        """
        condition_id = market.get('conditionId') or market.get('condition_id')
        if not condition_id:
            return None
        
        market_title = market.get('title', 'Unknown')
        print(f"\n🎯 Testing: {market_title[:60]}...")
        
        # Step 1: Get trade activity
        trades = self.get_trade_activity(condition_id)
        if len(trades) < 10:  # Need sufficient trade history
            print(f"   ⚠️ Insufficient trades ({len(trades)})")
            return None
        
        # Step 2: Aggregate hourly volume bars
        volume_bars = self.aggregate_hourly_volume_bars(trades)
        if len(volume_bars) < 24:  # Need at least 24 hours of data
            print(f"   ⚠️ Insufficient volume history ({len(volume_bars)} hours)")
            return None
        
        # Step 3: Get price history
        prices = self.get_price_history(condition_id)
        if len(prices) < 10:
            print(f"   ⚠️ No price history available")
            return None
        
        # Step 4: Detect volume spikes
        spikes = self.detect_volume_spikes(volume_bars, volume_multiplier=3.0)
        
        # Step 5: Detect price moves
        moves = self.detect_price_moves(prices, min_move=0.05)
        
        # Step 6: Find combinations
        combinations = self.find_spike_move_combinations(spikes, moves)
        
        if not combinations:
            print(f"   ❌ No volume spike + price move combinations found")
            return None
        
        print(f"   ✅ Found {len(combinations)} spike+move combinations")
        
        # Step 7: Simulate forward performance
        results = []
        for combo in combinations:
            performance = self.simulate_forward_performance(
                combo, prices, ['6h', '12h', '24h', '48h', 'resolution']
            )
            
            if performance:
                results.append({
                    'signal': combo,
                    'performance': performance
                })
        
        return {
            'market_id': condition_id,
            'market_title': market_title,
            'total_spikes': len(spikes),
            'total_moves': len(moves),
            'combinations': len(combinations),
            'results': results
        }

def main():
    """Run Claude's Volume Spike backtesting methodology"""
    backtester = PMVolumeSpikeClaudeBacktester()
    
    print("🚀 POLYMARKET VOLUME SPIKE BACKTESTING - CLAUDE'S METHOD")
    print("📊 Following Claude's exact methodology:")
    print("   1. Get liquid resolved markets")
    print("   2. Fetch trade-level data (/activity)")  
    print("   3. Aggregate hourly volume bars")
    print("   4. Get price history (/prices-history)")
    print("   5. Detect spikes + moves")
    print("   6. Simulate forward performance")
    print("=" * 80)
    
    # Step 1: Get liquid resolved markets
    markets = backtester.get_liquid_resolved_markets(limit=50)  # Start small
    
    if not markets:
        print("❌ No market data available")
        return
    
    # Test on subset first
    print(f"\n🧪 Testing on {min(10, len(markets))} markets...")
    
    all_results = []
    
    for i, market in enumerate(markets[:10]):  # Test first 10
        try:
            result = backtester.backtest_single_market(market)
            if result:
                all_results.append(result)
                
        except Exception as e:
            print(f"   ❌ Error testing market: {e}")
            continue
    
    # Analyze results
    print(f"\n📊 CLAUDE METHOD RESULTS:")
    print("=" * 50)
    
    total_combinations = sum(r['combinations'] for r in all_results)
    successful_tests = len([r for r in all_results if r['combinations'] > 0])
    
    print(f"Markets tested: {len(all_results)}")
    print(f"Markets with signals: {successful_tests}")
    print(f"Total spike+move combinations: {total_combinations}")
    
    if total_combinations > 0:
        print(f"\n✅ SUCCESS: Claude's method found {total_combinations} signals")
        print(f"🚀 Ready for full-scale backtesting with parameter optimization")
    else:
        print(f"❌ No signals found - need to investigate API endpoints")
        print(f"🔧 May need to test different API endpoints or adjust parameters")

if __name__ == "__main__":
    main()