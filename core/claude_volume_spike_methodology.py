#!/usr/bin/env python3
"""
CLAUDE'S VOLUME SPIKE METHODOLOGY - POLYMARKET IMPLEMENTATION
Following Claude's exact 7-step process for volume spike detection and backtesting
Using Data API /trades endpoint (confirmed working)
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import json
import time

class ClaudeVolumeSpikePM:
    def __init__(self):
        self.data_api_base = "https://data-api.polymarket.com"
        self.gamma_api_base = "https://gamma-api.polymarket.com"
        
        # Claude's parameters
        self.volume_spike_threshold = 3.0  # >3x average volume
        self.price_move_threshold = 0.05   # >5 percentage point move
        self.time_window_hours = 2         # Within 2 hours
        self.lookback_days = 7             # Average volume over 7 days
    
    def step1_get_liquid_resolved_markets(self, limit=50):
        """
        Step 1: Get liquid resolved markets for backtesting
        Claude: "Get liquid resolved markets from the Data API"
        """
        print("🔍 STEP 1: Getting liquid resolved markets...")
        
        try:
            # Get closed markets from Gamma API
            # For testing: Use active markets first, then closed ones
            response = requests.get(
                f"{self.gamma_api_base}/events", 
                params={
                    "closed": "false",  # Active markets for testing
                    "order": "volume",
                    "ascending": "false", 
                    "limit": limit
                },
                timeout=15
            )
            
            if response.status_code == 200:
                events = response.json()
                
                resolved_markets = []
                for event in events:
                    markets = event.get('markets', [])
                    for market in markets:
                        # For testing, use active markets 
                        if not market.get('closed', True):
                            # Use both market and event level data
                            condition_id = market.get('condition_id') or market.get('conditionId')
                            question = market.get('question') or event.get('title', 'Unknown')
                            
                            if condition_id:  # Only add if we have a condition_id
                                resolved_markets.append({
                                    'condition_id': condition_id,
                                    'question': question,
                                    'volume': market.get('volume', 0),
                                    'closed': market.get('closed', False),
                                    'resolved': market.get('resolved', False)
                                })
                
                # Filter for liquid markets (volume > $1000)
                liquid_markets = []
                for m in resolved_markets:
                    try:
                        volume = float(m['volume']) if m['volume'] else 0
                        if volume > 1000:
                            liquid_markets.append(m)
                    except (ValueError, TypeError):
                        continue
                
                print(f"✅ Found {len(resolved_markets)} resolved markets")
                print(f"📊 Liquid markets (>$1000 volume): {len(liquid_markets)}")
                
                return liquid_markets[:limit]
                
            else:
                print(f"❌ Failed to get markets: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting markets: {e}")
            return []
    
    def step2_fetch_trade_data(self, condition_id, limit=1000):
        """
        Step 2: Fetch trade-level data for a specific market
        Claude: "Fetch trade-level data from the Data API (/activity)"
        Using /trades which we confirmed works
        """
        print(f"📊 STEP 2: Fetching trade data for {condition_id[:10]}...")
        
        try:
            # Get all recent trades (Data API doesn't filter by market in params, 
            # but returns trades we can filter)
            response = requests.get(
                f"{self.data_api_base}/trades",
                params={"limit": limit},
                timeout=15
            )
            
            if response.status_code == 200:
                all_trades = response.json()
                
                # Filter trades for this specific market
                market_trades = [
                    trade for trade in all_trades 
                    if trade.get('conditionId') == condition_id
                ]
                
                print(f"✅ Got {len(market_trades)} trades for this market")
                
                return market_trades
                
            else:
                print(f"❌ Failed to get trades: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching trades: {e}")
            return []
    
    def step3_aggregate_hourly_volume_bars(self, trades):
        """
        Step 3: Aggregate trade data into hourly volume bars
        Claude: "Aggregate hourly volume bars"
        """
        print("📈 STEP 3: Aggregating hourly volume bars...")
        
        if not trades:
            return pd.DataFrame()
        
        # Convert trades to DataFrame
        df = pd.DataFrame(trades)
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df['hour'] = df['datetime'].dt.floor('h')
        
        # Aggregate by hour
        hourly_bars = df.groupby('hour').agg({
            'size': 'sum',  # Total volume
            'price': ['first', 'last', 'min', 'max'],  # OHLC prices
            'conditionId': 'count'  # Number of trades
        }).round(6)
        
        # Flatten column names
        hourly_bars.columns = ['volume', 'open', 'close', 'low', 'high', 'trade_count']
        hourly_bars.reset_index(inplace=True)
        
        print(f"✅ Created {len(hourly_bars)} hourly bars")
        
        return hourly_bars
    
    def step4_extract_price_history(self, hourly_bars):
        """
        Step 4: Extract price history from aggregated data
        Claude: "Get price history (/prices-history)"
        """
        print("💰 STEP 4: Extracting price history...")
        
        if hourly_bars.empty:
            return pd.DataFrame()
        
        # Create price history with probability calculations
        price_history = hourly_bars[['hour', 'open', 'close', 'low', 'high', 'volume']].copy()
        
        # Calculate price movements
        price_history['price_change'] = price_history['close'] - price_history['open']
        price_history['price_change_pct'] = (price_history['close'] - price_history['open'])
        
        # For prediction markets, price represents probability (0.0 to 1.0)
        # Price change of 0.05 = 5 percentage point move
        price_history['probability_move'] = abs(price_history['price_change_pct'])
        
        print(f"✅ Extracted price history for {len(price_history)} periods")
        
        return price_history
    
    def step5_detect_volume_spikes(self, hourly_bars, lookback_periods=168):  # 7 days = 168 hours
        """
        Step 5: Detect volume spikes (>3x average volume)
        Claude: "Detect spikes + moves"
        """
        print("🚨 STEP 5: Detecting volume spikes...")
        
        if hourly_bars.empty or len(hourly_bars) < lookback_periods:
            print(f"⚠️ Insufficient data for volume spike detection")
            return pd.DataFrame()
        
        df = hourly_bars.copy()
        
        # Calculate rolling average volume
        df['avg_volume'] = df['volume'].rolling(window=lookback_periods, min_periods=1).mean()
        
        # Detect volume spikes
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        df['is_volume_spike'] = df['volume_ratio'] > self.volume_spike_threshold
        
        # Filter to only volume spikes
        volume_spikes = df[df['is_volume_spike']].copy()
        
        print(f"✅ Found {len(volume_spikes)} volume spikes (>{self.volume_spike_threshold}x average)")
        
        return volume_spikes
    
    def step6_detect_probability_moves(self, price_history):
        """
        Step 6: Detect significant probability moves (>5 percentage points)
        Claude: "Detect probability moves (>5%)"
        """
        print("📊 STEP 6: Detecting probability moves...")
        
        if price_history.empty:
            return pd.DataFrame()
        
        df = price_history.copy()
        
        # Detect significant probability moves
        df['is_prob_move'] = df['probability_move'] > self.price_move_threshold
        
        # Filter to only significant moves
        prob_moves = df[df['is_prob_move']].copy()
        
        print(f"✅ Found {len(prob_moves)} significant probability moves (>{self.price_move_threshold*100}pp)")
        
        return prob_moves
    
    def step7_find_spike_move_combinations(self, volume_spikes, prob_moves):
        """
        Step 7: Find volume spike + probability move combinations within 2 hours
        Claude: "Find spike+move combinations occurring within 2 hours"
        """
        print("🎯 STEP 7: Finding spike+move combinations...")
        
        if volume_spikes.empty or prob_moves.empty:
            print("⚠️ No spikes or moves found")
            return []
        
        signals = []
        time_window = timedelta(hours=self.time_window_hours)
        
        for _, spike in volume_spikes.iterrows():
            spike_time = spike['hour']
            
            # Look for probability moves within time window
            for _, move in prob_moves.iterrows():
                move_time = move['hour']
                time_diff = abs(spike_time - move_time)
                
                if time_diff <= time_window:
                    # Found a spike+move combination
                    signal = {
                        'signal_time': spike_time,
                        'volume_spike': {
                            'hour': spike_time,
                            'volume': spike['volume'],
                            'avg_volume': spike['avg_volume'],
                            'volume_ratio': spike['volume_ratio']
                        },
                        'probability_move': {
                            'hour': move_time,
                            'price_change': move['price_change_pct'],
                            'probability_move': move['probability_move'],
                            'direction': 'UP' if move['price_change_pct'] > 0 else 'DOWN'
                        },
                        'time_between': time_diff,
                        'signal_strength': spike['volume_ratio'] * move['probability_move']
                    }
                    signals.append(signal)
        
        print(f"✅ Found {len(signals)} volume spike + probability move combinations")
        
        return signals
    
    def run_claude_methodology(self, market_limit=10):
        """
        Execute Claude's complete 7-step methodology
        """
        print("🚀 EXECUTING CLAUDE'S VOLUME SPIKE METHODOLOGY")
        print("=" * 60)
        print("📋 Claude's 7 Steps:")
        print("   1. Get liquid resolved markets")
        print("   2. Fetch trade-level data")
        print("   3. Aggregate hourly volume bars") 
        print("   4. Extract price history")
        print("   5. Detect volume spikes (>3x)")
        print("   6. Detect probability moves (>5%)")
        print("   7. Find spike+move combinations")
        print("=" * 60)
        
        # Step 1: Get markets
        markets = self.step1_get_liquid_resolved_markets(limit=market_limit)
        
        if not markets:
            print("❌ No markets found, cannot continue")
            return {}
        
        all_results = {}
        successful_analyses = 0
        
        # Analyze each market
        for i, market in enumerate(markets[:5]):  # Limit to 5 for testing
            condition_id = market['condition_id']
            question = market['question']
            
            print(f"\n📊 ANALYZING MARKET {i+1}/{len(markets[:5])}")
            print(f"❓ {question[:80]}...")
            print(f"🆔 Condition ID: {condition_id}")
            print("-" * 50)
            
            try:
                # Steps 2-7 for this market
                trades = self.step2_fetch_trade_data(condition_id, limit=1000)
                
                if not trades:
                    print("⚠️ No trades found for this market")
                    continue
                
                hourly_bars = self.step3_aggregate_hourly_volume_bars(trades)
                price_history = self.step4_extract_price_history(hourly_bars)
                volume_spikes = self.step5_detect_volume_spikes(hourly_bars)
                prob_moves = self.step6_detect_probability_moves(price_history)
                signals = self.step7_find_spike_move_combinations(volume_spikes, prob_moves)
                
                # Store results
                all_results[condition_id] = {
                    'market_info': market,
                    'trades_count': len(trades),
                    'hourly_bars_count': len(hourly_bars),
                    'volume_spikes_count': len(volume_spikes),
                    'prob_moves_count': len(prob_moves),
                    'signals_count': len(signals),
                    'signals': signals
                }
                
                if signals:
                    successful_analyses += 1
                    print(f"🎯 SIGNALS FOUND: {len(signals)} for this market")
                else:
                    print(f"📊 No signals found for this market")
                
            except Exception as e:
                print(f"❌ Error analyzing market: {e}")
                continue
        
        # Summary
        print(f"\n🎉 CLAUDE METHODOLOGY COMPLETE")
        print("=" * 40)
        print(f"📊 Markets analyzed: {len(all_results)}")
        print(f"🎯 Markets with signals: {successful_analyses}")
        
        total_signals = sum(result['signals_count'] for result in all_results.values())
        print(f"🚨 Total signals found: {total_signals}")
        
        if total_signals > 0:
            print(f"\n✅ CLAUDE'S METHODOLOGY SUCCESSFUL!")
            print(f"🎯 Ready for backtesting and validation")
        else:
            print(f"\n⚠️ No signals found in test markets")
            print(f"🔧 May need parameter adjustment or more data")
        
        return all_results

def main():
    """Run Claude's volume spike methodology"""
    print("🔬 CLAUDE'S VOLUME SPIKE METHODOLOGY - POLYMARKET")
    print("🎯 Goal: Detect informed trading through volume spikes + price moves")
    print("📊 Data Source: Polymarket Data API /trades endpoint")
    print("=" * 70)
    
    # Initialize and run Claude's methodology
    claude_system = ClaudeVolumeSpikePM()
    results = claude_system.run_claude_methodology(market_limit=10)
    
    print(f"\n📋 Results summary:")
    for condition_id, result in results.items():
        market_title = result['market_info']['question'][:50]
        signals_count = result['signals_count']
        print(f"   {condition_id[:10]}... | {market_title}... | {signals_count} signals")

if __name__ == "__main__":
    main()