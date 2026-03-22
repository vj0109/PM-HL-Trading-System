#!/usr/bin/env python3
"""
SIGNAL 31: CORRELATED MARKET ARBITRAGE - OPTIMIZED VERSION
Fast implementation focusing on high-probability correlation patterns
"""

import requests
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple

class OptimizedCorrelatedArbitrage:
    def __init__(self):
        self.gamma_host = "https://gamma-api.polymarket.com"
        
    def get_active_markets(self, limit=50):
        """Get active markets - limited sample for testing"""
        print("🔍 Getting active markets (optimized sample)...")
        
        try:
            response = requests.get(
                f"{self.gamma_host}/events",
                params={
                    "closed": "false",
                    "limit": limit,
                    "order": "volume",
                    "ascending": "false"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                events = response.json()
                
                all_markets = []
                for event in events:
                    markets = event.get('markets', [])
                    for market in markets:
                        if not market.get('closed', True):
                            market_data = {
                                'condition_id': market.get('condition_id') or market.get('conditionId'),
                                'question': market.get('question', ''),
                                'event_title': event.get('title', ''),
                                'volume': market.get('volume', 0),
                                'probability': market.get('price', 0),
                                'event_slug': event.get('slug', ''),
                                'category': event.get('category', '')
                            }
                            
                            if market_data['condition_id'] and market_data['question']:
                                all_markets.append(market_data)
                
                print(f"✅ Retrieved {len(all_markets)} active markets")
                return all_markets
                
            else:
                print(f"❌ Failed to get markets: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting markets: {e}")
            return []
    
    def find_same_event_arbitrage(self, markets: List[Dict]) -> List[Dict]:
        """
        Find arbitrage within same events (much more efficient)
        """
        print(f"🔍 Finding same-event arbitrage opportunities...")
        
        # Group markets by event
        events = {}
        for market in markets:
            event_key = market['event_slug']
            if event_key not in events:
                events[event_key] = []
            events[event_key].append(market)
        
        opportunities = []
        
        for event_slug, event_markets in events.items():
            if len(event_markets) < 2:
                continue
                
            print(f"   Analyzing event: {event_slug} ({len(event_markets)} markets)")
            
            # Look for obvious inverse pairs within same event
            for i, market1 in enumerate(event_markets):
                for j, market2 in enumerate(event_markets[i+1:], i+1):
                    
                    q1 = market1['question'].lower()
                    q2 = market2['question'].lower()
                    
                    # Check for inverse patterns
                    inverse_found = False
                    pattern_type = ""
                    
                    # Trump vs Biden
                    if ('trump' in q1 and 'biden' in q2) or ('biden' in q1 and 'trump' in q2):
                        if ('win' in q1 and 'win' in q2) or ('elect' in q1 and 'elect' in q2):
                            inverse_found = True
                            pattern_type = "candidate_inverse"
                    
                    # Above vs Below
                    elif ('above' in q1 and 'below' in q2) or ('below' in q1 and 'above' in q2):
                        inverse_found = True
                        pattern_type = "threshold_inverse"
                    
                    # More than vs Less than
                    elif ('more than' in q1 and 'less than' in q2) or ('less than' in q1 and 'more than' in q2):
                        inverse_found = True
                        pattern_type = "quantity_inverse"
                    
                    # Yes vs No (same base question)
                    elif q1.replace(' yes', '').replace(' no', '') == q2.replace(' yes', '').replace(' no', ''):
                        if (' yes' in q1 and ' no' in q2) or (' no' in q1 and ' yes' in q2):
                            inverse_found = True
                            pattern_type = "yes_no_inverse"
                    
                    if inverse_found:
                        prob1 = float(market1.get('probability', 0))
                        prob2 = float(market2.get('probability', 0))
                        
                        # For inverse correlation: prob1 + prob2 should ≈ 1.0
                        actual_sum = prob1 + prob2
                        divergence = abs(actual_sum - 1.0)
                        
                        if divergence > 0.05:  # 5% threshold
                            if actual_sum > 1.05:
                                signal = "SELL_BOTH"
                                edge = actual_sum - 1.0
                            elif actual_sum < 0.95:
                                signal = "BUY_BOTH"
                                edge = 1.0 - actual_sum
                            else:
                                continue
                            
                            opportunity = {
                                'market1': market1,
                                'market2': market2,
                                'pattern_type': pattern_type,
                                'prob1': prob1,
                                'prob2': prob2,
                                'actual_sum': actual_sum,
                                'divergence': divergence,
                                'signal': signal,
                                'edge': edge,
                                'confidence': min(edge * 10, 1.0)
                            }
                            
                            opportunities.append(opportunity)
        
        return opportunities
    
    def find_direct_correlations_fast(self, markets: List[Dict]) -> List[Dict]:
        """
        Fast direct correlation detection using keyword similarity
        """
        print(f"🔍 Finding direct correlations (fast method)...")
        
        opportunities = []
        
        # Group by similar keywords
        keyword_groups = {}
        for market in markets:
            question = market['question'].lower()
            
            # Extract key entities
            entities = []
            if 'trump' in question:
                entities.append('trump')
            if 'biden' in question:
                entities.append('biden')
            if 'bitcoin' in question or 'btc' in question:
                entities.append('bitcoin')
            if 'ethereum' in question or 'eth' in question:
                entities.append('ethereum')
            
            for entity in entities:
                if entity not in keyword_groups:
                    keyword_groups[entity] = []
                keyword_groups[entity].append(market)
        
        # Find price discrepancies within entity groups
        for entity, entity_markets in keyword_groups.items():
            if len(entity_markets) < 2:
                continue
                
            print(f"   Analyzing {entity} markets: {len(entity_markets)}")
            
            for i, market1 in enumerate(entity_markets):
                for j, market2 in enumerate(entity_markets[i+1:], i+1):
                    
                    prob1 = float(market1.get('probability', 0))
                    prob2 = float(market2.get('probability', 0))
                    
                    # Look for similar questions with different prices
                    divergence = abs(prob1 - prob2)
                    
                    if divergence > 0.15:  # 15% price difference
                        if prob1 > prob2:
                            signal = "SELL_HIGH_BUY_LOW"
                            high_market, low_market = market1, market2
                        else:
                            signal = "SELL_HIGH_BUY_LOW"
                            high_market, low_market = market2, market1
                        
                        opportunity = {
                            'high_market': high_market,
                            'low_market': low_market,
                            'pattern_type': f"{entity}_price_divergence",
                            'high_prob': max(prob1, prob2),
                            'low_prob': min(prob1, prob2),
                            'divergence': divergence,
                            'signal': signal,
                            'edge': divergence / 2,  # Rough edge estimate
                            'confidence': min(divergence * 5, 1.0)
                        }
                        
                        opportunities.append(opportunity)
        
        return opportunities
    
    def run_optimized_arbitrage_detection(self):
        """
        Main optimized arbitrage detection
        """
        print("🔬 SIGNAL 31: OPTIMIZED CORRELATED MARKET ARBITRAGE")
        print("🎯 Goal: Fast detection of high-probability arbitrage opportunities")
        print("📋 Strategy: Focus on same-event correlations and entity groupings")
        print("=" * 75)
        
        # Get smaller sample for speed
        markets = self.get_active_markets(limit=50)
        
        if not markets:
            print("❌ No markets available")
            return []
        
        # Find arbitrage opportunities
        print(f"\n📊 ANALYZING {len(markets)} MARKETS FOR ARBITRAGE")
        print("-" * 50)
        
        inverse_opportunities = self.find_same_event_arbitrage(markets)
        direct_opportunities = self.find_direct_correlations_fast(markets)
        
        all_opportunities = inverse_opportunities + direct_opportunities
        
        # Sort by edge
        all_opportunities.sort(key=lambda x: x['edge'], reverse=True)
        
        print(f"\n🎉 ARBITRAGE DETECTION COMPLETE")
        print("=" * 40)
        print(f"📊 Markets analyzed: {len(markets)}")
        print(f"🔄 Inverse opportunities: {len(inverse_opportunities)}")
        print(f"🔗 Direct opportunities: {len(direct_opportunities)}")
        print(f"🎯 Total opportunities: {len(all_opportunities)}")
        
        if all_opportunities:
            print(f"\n💰 TOP ARBITRAGE OPPORTUNITIES:")
            for i, opp in enumerate(all_opportunities[:10]):
                edge = opp['edge']
                confidence = opp['confidence']
                signal = opp['signal']
                pattern = opp['pattern_type']
                
                print(f"\n{i+1}. {signal} | Edge: {edge:.1%} | Confidence: {confidence:.1%}")
                print(f"   Pattern: {pattern}")
                
                if 'market1' in opp:  # Inverse correlation
                    print(f"   Market 1: {opp['market1']['question'][:60]}... ({opp['prob1']:.1%})")
                    print(f"   Market 2: {opp['market2']['question'][:60]}... ({opp['prob2']:.1%})")
                    print(f"   Sum: {opp['actual_sum']:.1%} (should be ~100%)")
                else:  # Direct correlation
                    print(f"   High: {opp['high_market']['question'][:60]}... ({opp['high_prob']:.1%})")
                    print(f"   Low:  {opp['low_market']['question'][:60]}... ({opp['low_prob']:.1%})")
        
        return all_opportunities

def main():
    """Run optimized arbitrage detection"""
    detector = OptimizedCorrelatedArbitrage()
    opportunities = detector.run_optimized_arbitrage_detection()
    
    if opportunities:
        # Save results
        output_file = '/home/vj/PM-HL-Trading-System/data/signal31_arbitrage_optimized.json'
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'signal_type': 'correlated_market_arbitrage_optimized',
            'opportunities_count': len(opportunities),
            'opportunities': opportunities
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Results saved to: signal31_arbitrage_optimized.json")
        
        total_edge = sum(opp['edge'] for opp in opportunities)
        print(f"\n📊 SUMMARY:")
        print(f"   Total opportunities: {len(opportunities)}")
        print(f"   Total edge available: {total_edge:.1%}")
        print(f"   Best opportunity: {opportunities[0]['edge']:.1%}")

if __name__ == "__main__":
    main()