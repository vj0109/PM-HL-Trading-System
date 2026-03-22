#!/usr/bin/env python3
"""
SIGNAL 31: CORRELATED MARKET ARBITRAGE - CLAUDE'S METHODOLOGY
Multi-outcome event arbitrage detection following Claude's exact specification

Hypothesis: When multi-outcome event probabilities don't sum to ~$1.00, there's arbitrage
Core Logic: Sum all YES prices across outcomes in single events
- If sum > $1.05: Sell all outcomes (lock in profit)  
- If sum < $0.95: Buy all outcomes
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

class ClaudeMultiOutcomeArbitrage:
    def __init__(self):
        self.gamma_host = "https://gamma-api.polymarket.com"
        self.clob_host = "https://clob.polymarket.com"
        
        # API credentials
        self.api_key = "019d1560-55b8-7931-94d7-57187ba3a860"
        self.api_secret = "foJLgU2ulRSjryEfBuQFajltV3v0JbiX7s2jcgygS5c="
        self.api_passphrase = "ee1aebe2ac25aa0baada650ad70fc3098a17dd9193f92382dba0d6e128cd3109"
        
        # Claude's specified parameters to test
        self.arbitrage_thresholds = [0.02, 0.03, 0.05, 0.08, 0.10]  # Deviation from $1.00
        self.liquidity_minimums = [5000, 10000, 25000]  # Per-market minimums
        
        # Initialize CLOB client for authenticated requests
        try:
            self.clob_client = ClobClient(
                host=self.clob_host,
                key=self.api_key,
                secret=self.api_secret,
                passphrase=self.api_passphrase,
                chain_id=POLYGON
            )
            print("✅ CLOB client initialized successfully")
        except Exception as e:
            print(f"❌ CLOB client initialization failed: {e}")
            self.clob_client = None
    
    def get_multi_outcome_events(self, closed=True, limit=100):
        """
        Get events with multiple markets for arbitrage analysis
        Following Claude's API workflow: GET /events?closed=true
        """
        print(f"🔍 Getting {'closed' if closed else 'active'} multi-outcome events...")
        
        try:
            response = requests.get(
                f"{self.gamma_host}/events",
                params={
                    "closed": str(closed).lower(),
                    "limit": limit,
                    "order": "volume",
                    "ascending": "false"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                events = response.json()
                
                # Filter for events with multiple markets (2+ outcomes)
                multi_outcome_events = []
                for event in events:
                    markets = event.get('markets', [])
                    if len(markets) >= 2:  # Multi-outcome event
                        event_data = {
                            'event_id': event.get('id'),
                            'slug': event.get('slug', ''),
                            'title': event.get('title', ''),
                            'category': event.get('category', ''),
                            'closed': event.get('closed', False),
                            'end_date': event.get('end_date_iso'),
                            'markets': []
                        }
                        
                        # Extract market data for probability summation
                        for market in markets:
                            market_data = {
                                'condition_id': market.get('condition_id') or market.get('conditionId'),
                                'question': market.get('question', ''),
                                'token_id': market.get('id'),
                                'current_price': market.get('price', 0),  # YES price
                                'volume': market.get('volume', 0),
                                'liquidity': market.get('liquidity', 0),
                                'closed': market.get('closed', False)
                            }
                            
                            if market_data['condition_id']:
                                event_data['markets'].append(market_data)
                        
                        if len(event_data['markets']) >= 2:
                            multi_outcome_events.append(event_data)
                
                print(f"✅ Found {len(multi_outcome_events)} multi-outcome events")
                return multi_outcome_events
                
            else:
                print(f"❌ Failed to get events: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting events: {e}")
            return []
    
    def get_price_history_for_tokens(self, token_ids: List[str], event_slug: str):
        """
        Get historical price data for all tokens in an event
        Following Claude's workflow: GET /prices-history for all tokens
        """
        print(f"📊 Getting price history for {len(token_ids)} tokens in {event_slug}...")
        
        price_histories = {}
        
        for token_id in token_ids:
            try:
                response = requests.get(
                    f"{self.clob_host}/prices-history",
                    params={
                        "market": token_id,
                        "interval": "max",
                        "fidelity": "720"  # 12-hour fidelity
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    history = data.get('history', [])
                    
                    if history:
                        price_histories[token_id] = history
                        print(f"   ✅ {token_id}: {len(history)} price points")
                    else:
                        print(f"   ⚠️ {token_id}: No price history")
                else:
                    print(f"   ❌ {token_id}: HTTP {response.status_code}")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ {token_id}: Error - {e}")
        
        return price_histories
    
    def calculate_arbitrage_opportunities(self, event_data: Dict, price_histories: Dict, threshold: float):
        """
        Calculate arbitrage opportunities using Claude's probability summation method
        
        Core Logic:
        - At each timestamp, sum YES prices across all outcomes
        - If sum > 1.0 + threshold: Arbitrage (sell all outcomes)
        - If sum < 1.0 - threshold: Arbitrage (buy all outcomes)
        """
        arbitrage_opportunities = []
        markets = event_data['markets']
        
        # Build synchronized timestamp data
        all_timestamps = set()
        for token_id in price_histories:
            for price_point in price_histories[token_id]:
                all_timestamps.add(price_point['t'])
        
        sorted_timestamps = sorted(all_timestamps)
        print(f"   📅 Analyzing {len(sorted_timestamps)} timestamps for arbitrage...")
        
        for timestamp in sorted_timestamps:
            # Get prices at this timestamp for all markets
            prices_at_timestamp = {}
            total_sum = 0
            valid_markets = 0
            
            for market in markets:
                token_id = market['condition_id']
                if token_id in price_histories:
                    # Find closest price to timestamp
                    closest_price = self.get_price_at_timestamp(price_histories[token_id], timestamp)
                    if closest_price is not None:
                        prices_at_timestamp[token_id] = closest_price
                        total_sum += closest_price
                        valid_markets += 1
            
            # Claude's arbitrage logic: check if sum deviates from 1.00
            if valid_markets >= 2:  # Need at least 2 outcomes
                upper_threshold = 1.0 + threshold
                lower_threshold = 1.0 - threshold
                
                if total_sum > upper_threshold:
                    # Arbitrage: Sell all outcomes
                    arbitrage_opportunities.append({
                        'timestamp': timestamp,
                        'type': 'SELL_ALL',
                        'total_sum': total_sum,
                        'threshold': threshold,
                        'edge': total_sum - 1.0,
                        'markets_count': valid_markets,
                        'prices': prices_at_timestamp,
                        'event': event_data['slug']
                    })
                    
                elif total_sum < lower_threshold:
                    # Arbitrage: Buy all outcomes
                    arbitrage_opportunities.append({
                        'timestamp': timestamp,
                        'type': 'BUY_ALL', 
                        'total_sum': total_sum,
                        'threshold': threshold,
                        'edge': 1.0 - total_sum,
                        'markets_count': valid_markets,
                        'prices': prices_at_timestamp,
                        'event': event_data['slug']
                    })
        
        return arbitrage_opportunities
    
    def get_price_at_timestamp(self, price_history: List[Dict], target_timestamp: int):
        """Get price closest to target timestamp"""
        if not price_history:
            return None
            
        # Find closest timestamp
        closest_price = None
        min_diff = float('inf')
        
        for price_point in price_history:
            diff = abs(price_point['t'] - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_price = price_point.get('p', 0)
        
        return closest_price
    
    def simulate_arbitrage_performance(self, opportunities: List[Dict], event_data: Dict):
        """
        Simulate P&L tracking to resolution as Claude specified
        """
        if not opportunities:
            return None
        
        # Calculate performance metrics
        total_opportunities = len(opportunities)
        total_edge = sum(opp['edge'] for opp in opportunities)
        avg_edge = total_edge / total_opportunities if total_opportunities > 0 else 0
        
        # Simulate execution assuming we can trade at midpoint
        simulated_pnl = 0
        for opp in opportunities:
            # Simple simulation: edge * $100 position size
            trade_pnl = opp['edge'] * 100  # $100 per trade
            simulated_pnl += trade_pnl
        
        return {
            'event': event_data['slug'],
            'total_opportunities': total_opportunities,
            'avg_edge_per_opportunity': avg_edge,
            'total_edge_available': total_edge,
            'simulated_pnl': simulated_pnl,
            'opportunities_per_day': total_opportunities,  # Rough estimate
            'category': event_data.get('category', 'unknown')
        }
    
    def run_claude_arbitrage_backtest(self):
        """
        Main function implementing Claude's complete methodology
        """
        print("🔬 SIGNAL 31: CLAUDE'S MULTI-OUTCOME ARBITRAGE BACKTEST")
        print("🎯 Goal: Find probability summation arbitrage in multi-outcome events")
        print("📋 Method: Sum YES prices across outcomes, detect deviations from $1.00")
        print("=" * 80)
        
        # Step 1: Get multi-outcome events (closed for backtesting)
        events = self.get_multi_outcome_events(closed=True, limit=50)
        
        if not events:
            print("❌ No multi-outcome events available for backtesting")
            return []
        
        all_results = []
        
        # Step 2: Test each arbitrage threshold (Claude's parameter testing)
        for threshold in self.arbitrage_thresholds:
            print(f"\n🧪 TESTING ARBITRAGE THRESHOLD: {threshold:.1%}")
            print("-" * 50)
            
            threshold_results = []
            
            for i, event_data in enumerate(events[:10]):  # Test first 10 events
                print(f"\n📊 Event {i+1}/10: {event_data['title'][:50]}...")
                print(f"   Markets: {len(event_data['markets'])}")
                
                # Get token IDs for price history
                token_ids = [market['condition_id'] for market in event_data['markets']]
                
                # Get price history for all tokens
                price_histories = self.get_price_history_for_tokens(token_ids, event_data['slug'])
                
                if price_histories:
                    # Calculate arbitrage opportunities
                    opportunities = self.calculate_arbitrage_opportunities(
                        event_data, price_histories, threshold
                    )
                    
                    if opportunities:
                        print(f"   🎯 Found {len(opportunities)} arbitrage opportunities!")
                        
                        # Simulate performance
                        performance = self.simulate_arbitrage_performance(opportunities, event_data)
                        if performance:
                            performance['threshold'] = threshold
                            threshold_results.append(performance)
                            
                            print(f"   💰 Simulated P&L: ${performance['simulated_pnl']:.2f}")
                            print(f"   📈 Avg Edge: {performance['avg_edge_per_opportunity']:.1%}")
                    else:
                        print(f"   ✅ No arbitrage found (efficient pricing)")
                else:
                    print(f"   ⚠️ No price history available")
            
            all_results.extend(threshold_results)
        
        # Analyze results across thresholds
        self.analyze_threshold_performance(all_results)
        
        return all_results
    
    def analyze_threshold_performance(self, results: List[Dict]):
        """Analyze performance across different arbitrage thresholds"""
        if not results:
            print("\n❌ No arbitrage opportunities found across all thresholds")
            return
        
        print(f"\n📊 THRESHOLD PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        # Group by threshold
        threshold_groups = {}
        for result in results:
            threshold = result['threshold']
            if threshold not in threshold_groups:
                threshold_groups[threshold] = []
            threshold_groups[threshold].append(result)
        
        # Analyze each threshold
        for threshold in sorted(threshold_groups.keys()):
            group = threshold_groups[threshold]
            total_opportunities = sum(r['total_opportunities'] for r in group)
            total_pnl = sum(r['simulated_pnl'] for r in group)
            avg_edge = sum(r['avg_edge_per_opportunity'] for r in group) / len(group)
            
            print(f"\n🎯 THRESHOLD {threshold:.1%}:")
            print(f"   Events with arbitrage: {len(group)}")
            print(f"   Total opportunities: {total_opportunities}")
            print(f"   Total simulated P&L: ${total_pnl:.2f}")
            print(f"   Average edge: {avg_edge:.1%}")
            print(f"   Opportunities per event: {total_opportunities/len(group):.1f}")
        
        # Find best threshold
        best_threshold = max(threshold_groups.keys(), 
                           key=lambda t: sum(r['simulated_pnl'] for r in threshold_groups[t]))
        
        print(f"\n🏆 BEST THRESHOLD: {best_threshold:.1%}")
        print(f"   Total P&L: ${sum(r['simulated_pnl'] for r in threshold_groups[best_threshold]):.2f}")
    
    def save_results(self, results: List[Dict]):
        """Save arbitrage backtest results"""
        if results:
            output_file = '/home/vj/PM-HL-Trading-System/data/signal31_claude_arbitrage_results.json'
            
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'signal_type': 'claude_multi_outcome_arbitrage',
                'methodology': 'probability_summation_across_outcomes',
                'thresholds_tested': self.arbitrage_thresholds,
                'results_count': len(results),
                'results': results,
                'summary': {
                    'total_events_with_arbitrage': len(set(r['event'] for r in results)),
                    'total_opportunities': sum(r['total_opportunities'] for r in results),
                    'total_simulated_pnl': sum(r['simulated_pnl'] for r in results),
                    'avg_edge_across_all': sum(r['avg_edge_per_opportunity'] for r in results) / len(results) if results else 0
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\n💾 Results saved to: signal31_claude_arbitrage_results.json")

def main():
    """Run Claude's multi-outcome arbitrage detection"""
    detector = ClaudeMultiOutcomeArbitrage()
    results = detector.run_claude_arbitrage_backtest()
    detector.save_results(results)
    
    if results:
        print(f"\n🎉 CLAUDE'S ARBITRAGE BACKTEST COMPLETE!")
        print(f"   Total events analyzed: {len(set(r['event'] for r in results))}")
        print(f"   Total arbitrage opportunities: {sum(r['total_opportunities'] for r in results)}")
        print(f"   Total simulated profit: ${sum(r['simulated_pnl'] for r in results):.2f}")
    else:
        print(f"\n✅ BACKTEST COMPLETE: Markets appear efficiently priced")
        print(f"   No multi-outcome arbitrage opportunities found")

if __name__ == "__main__":
    main()