#!/usr/bin/env python3
"""
SIGNAL 31: CORRELATED MARKET ARBITRAGE
Find related Polymarket outcomes with price discrepancies for arbitrage opportunities

Logic: Markets with correlated outcomes should have consistent probabilities
Example: "Trump wins" vs "Biden loses" should be inverse correlation
When prices diverge from expected correlation, arbitrage opportunity exists
"""

import requests
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple
import difflib

class CorrelatedMarketArbitrage:
    def __init__(self):
        self.gamma_host = "https://gamma-api.polymarket.com"
        self.clob_host = "https://clob.polymarket.com"
        
        # Correlation patterns to detect
        self.inverse_patterns = [
            # Presidential election patterns
            (r"(?i)trump.*win", r"(?i)biden.*win"),
            (r"(?i)biden.*win", r"(?i)trump.*win"),
            (r"(?i)republican.*win", r"(?i)democrat.*win"),
            (r"(?i)democrat.*win", r"(?i)republican.*win"),
            
            # Binary outcome patterns
            (r"(?i)above", r"(?i)below"),
            (r"(?i)more than", r"(?i)less than"),
            (r"(?i)higher than", r"(?i)lower than"),
            (r"(?i)increase", r"(?i)decrease"),
            (r"(?i)yes", r"(?i)no"),
        ]
        
        # Direct correlation patterns (same outcome, different wording)
        self.direct_patterns = [
            # Same event, different phrasing
            (r"(?i)(\w+)\s+win", r"(?i)(\w+)\s+victory"),
            (r"(?i)(\w+)\s+elected", r"(?i)(\w+)\s+win"),
            (r"(?i)price\s+above\s+(\$?\d+)", r"(?i)reach\s+(\$?\d+)"),
        ]
    
    def get_active_markets(self, limit=100):
        """Get current active markets from Gamma API"""
        print("🔍 Getting active markets for correlation analysis...")
        
        try:
            response = requests.get(
                f"{self.gamma_host}/events",
                params={
                    "closed": "false",  # Active markets only
                    "limit": limit,
                    "order": "volume",
                    "ascending": "false"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                events = response.json()
                
                # Extract all markets from events
                all_markets = []
                for event in events:
                    markets = event.get('markets', [])
                    for market in markets:
                        if not market.get('closed', True):  # Only active markets
                            market_data = {
                                'condition_id': market.get('condition_id') or market.get('conditionId'),
                                'question': market.get('question', ''),
                                'event_title': event.get('title', ''),
                                'volume': market.get('volume', 0),
                                'probability': market.get('price', 0),  # Current probability
                                'market_slug': market.get('market_slug', ''),
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
    
    def find_inverse_correlations(self, markets: List[Dict]) -> List[Tuple[Dict, Dict, str]]:
        """
        Find pairs of markets that should be inversely correlated
        Returns: [(market1, market2, pattern_type), ...]
        """
        print(f"\n🔍 Finding inverse correlation pairs...")
        
        inverse_pairs = []
        total_comparisons = len(markets) * (len(markets) - 1) // 2
        comparisons_done = 0
        
        for i, market1 in enumerate(markets):
            for j, market2 in enumerate(markets[i+1:], i+1):
                comparisons_done += 1
                
                # Progress update
                if comparisons_done % 1000 == 0:
                    print(f"   Progress: {comparisons_done}/{total_comparisons} comparisons ({comparisons_done/total_comparisons*100:.1f}%)")
                # Skip if same market
                if market1['condition_id'] == market2['condition_id']:
                    continue
                
                # Skip if different events (for now - could expand later)
                if market1['event_slug'] != market2['event_slug']:
                    continue
                
                question1 = market1['question'].lower()
                question2 = market2['question'].lower()
                
                # Check each inverse pattern
                for pattern1, pattern2 in self.inverse_patterns:
                    if (re.search(pattern1, question1) and re.search(pattern2, question2)) or \
                       (re.search(pattern2, question1) and re.search(pattern1, question2)):
                        
                        inverse_pairs.append((market1, market2, f"inverse: {pattern1} <-> {pattern2}"))
                        break
        
        print(f"✅ Found {len(inverse_pairs)} inverse correlation pairs")
        return inverse_pairs
    
    def find_direct_correlations(self, markets: List[Dict]) -> List[Tuple[Dict, Dict, str]]:
        """
        Find pairs of markets that should be directly correlated (same outcome)
        """
        print(f"\n🔍 Finding direct correlation pairs...")
        
        direct_pairs = []
        
        for i, market1 in enumerate(markets):
            for j, market2 in enumerate(markets[i+1:], i+1):
                # Skip if same market
                if market1['condition_id'] == market2['condition_id']:
                    continue
                
                question1 = market1['question'].lower()
                question2 = market2['question'].lower()
                
                # Check similarity score first (quick filter)
                similarity = difflib.SequenceMatcher(None, question1, question2).ratio()
                
                if similarity > 0.7:  # 70% similar text
                    direct_pairs.append((market1, market2, f"text_similarity: {similarity:.2f}"))
                    continue
                
                # Check direct patterns
                for pattern1, pattern2 in self.direct_patterns:
                    match1 = re.search(pattern1, question1)
                    match2 = re.search(pattern2, question2)
                    
                    if match1 and match2:
                        # If patterns have groups, check if they match
                        if match1.groups() and match2.groups():
                            if match1.groups() == match2.groups():
                                direct_pairs.append((market1, market2, f"direct: {pattern1} = {pattern2}"))
                        else:
                            direct_pairs.append((market1, market2, f"direct: {pattern1} = {pattern2}"))
        
        print(f"✅ Found {len(direct_pairs)} direct correlation pairs")
        return direct_pairs
    
    def calculate_arbitrage_opportunity(self, market1: Dict, market2: Dict, correlation_type: str) -> Dict:
        """
        Calculate arbitrage opportunity for a correlated pair
        """
        prob1 = float(market1.get('probability', 0))
        prob2 = float(market2.get('probability', 0))
        
        if correlation_type.startswith('inverse'):
            # For inverse correlation: prob1 + prob2 should ≈ 1.0
            expected_sum = 1.0
            actual_sum = prob1 + prob2
            divergence = abs(actual_sum - expected_sum)
            
            # Arbitrage signal strength
            if actual_sum > 1.05:  # Both overpriced
                signal = "SELL_BOTH"
                edge = actual_sum - 1.0
            elif actual_sum < 0.95:  # Both underpriced  
                signal = "BUY_BOTH"
                edge = 1.0 - actual_sum
            else:
                signal = "NO_ARBITRAGE"
                edge = 0.0
                
        else:  # Direct correlation
            # For direct correlation: prob1 ≈ prob2
            divergence = abs(prob1 - prob2)
            
            if divergence > 0.1:  # 10% divergence threshold
                if prob1 > prob2:
                    signal = "SELL_MARKET1_BUY_MARKET2"
                else:
                    signal = "SELL_MARKET2_BUY_MARKET1"
                edge = divergence
            else:
                signal = "NO_ARBITRAGE"
                edge = 0.0
        
        return {
            'market1': market1,
            'market2': market2,
            'correlation_type': correlation_type,
            'prob1': prob1,
            'prob2': prob2,
            'divergence': divergence,
            'signal': signal,
            'edge': edge,
            'confidence': min(edge * 10, 1.0)  # Convert edge to confidence score
        }
    
    def detect_arbitrage_opportunities(self):
        """
        Main function to detect correlated market arbitrage opportunities
        """
        print("🔬 SIGNAL 31: CORRELATED MARKET ARBITRAGE")
        print("🎯 Goal: Find price discrepancies between correlated markets")
        print("📋 Logic: Inverse correlations should sum to ~1.0, direct correlations should match")
        print("=" * 80)
        
        # Get active markets
        markets = self.get_active_markets(limit=100)
        
        if not markets:
            print("❌ No markets available for analysis")
            return []
        
        # Find correlation pairs
        inverse_pairs = self.find_inverse_correlations(markets)
        direct_pairs = self.find_direct_correlations(markets)
        
        # Calculate arbitrage opportunities
        all_opportunities = []
        
        print(f"\n📊 ANALYZING INVERSE CORRELATIONS")
        print("-" * 40)
        for market1, market2, pattern in inverse_pairs:
            opportunity = self.calculate_arbitrage_opportunity(market1, market2, pattern)
            if opportunity['signal'] != 'NO_ARBITRAGE':
                all_opportunities.append(opportunity)
                
                print(f"🎯 ARBITRAGE FOUND!")
                print(f"   Market 1: {market1['question'][:60]}... ({opportunity['prob1']:.1%})")
                print(f"   Market 2: {market2['question'][:60]}... ({opportunity['prob2']:.1%})")
                print(f"   Pattern: {pattern}")
                print(f"   Signal: {opportunity['signal']}")
                print(f"   Edge: {opportunity['edge']:.1%}")
                print(f"   Confidence: {opportunity['confidence']:.1%}")
        
        print(f"\n📊 ANALYZING DIRECT CORRELATIONS")
        print("-" * 40)
        for market1, market2, pattern in direct_pairs:
            opportunity = self.calculate_arbitrage_opportunity(market1, market2, pattern)
            if opportunity['signal'] != 'NO_ARBITRAGE':
                all_opportunities.append(opportunity)
                
                print(f"🎯 ARBITRAGE FOUND!")
                print(f"   Market 1: {market1['question'][:60]}... ({opportunity['prob1']:.1%})")
                print(f"   Market 2: {market2['question'][:60]}... ({opportunity['prob2']:.1%})")
                print(f"   Pattern: {pattern}")
                print(f"   Signal: {opportunity['signal']}")
                print(f"   Edge: {opportunity['edge']:.1%}")
                print(f"   Confidence: {opportunity['confidence']:.1%}")
        
        # Sort by edge/confidence
        all_opportunities.sort(key=lambda x: x['edge'], reverse=True)
        
        print(f"\n🎉 ARBITRAGE DETECTION COMPLETE")
        print("=" * 40)
        print(f"📊 Total markets analyzed: {len(markets)}")
        print(f"🔗 Inverse pairs found: {len(inverse_pairs)}")
        print(f"🔗 Direct pairs found: {len(direct_pairs)}")
        print(f"🎯 Arbitrage opportunities: {len(all_opportunities)}")
        
        if all_opportunities:
            print(f"\n💰 TOP 5 ARBITRAGE OPPORTUNITIES:")
            for i, opp in enumerate(all_opportunities[:5]):
                print(f"   {i+1}. {opp['signal']} | Edge: {opp['edge']:.1%} | Confidence: {opp['confidence']:.1%}")
                print(f"      {opp['market1']['question'][:50]}...")
                print(f"      vs {opp['market2']['question'][:50]}...")
        
        return all_opportunities
    
    def save_results(self, opportunities: List[Dict]):
        """Save arbitrage opportunities to file"""
        if opportunities:
            output_file = '/home/vj/PM-HL-Trading-System/data/signal31_arbitrage_opportunities.json'
            
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'signal_type': 'correlated_market_arbitrage',
                'opportunities_count': len(opportunities),
                'opportunities': opportunities
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\n💾 Results saved to: signal31_arbitrage_opportunities.json")

def main():
    """Run correlated market arbitrage detection"""
    detector = CorrelatedMarketArbitrage()
    opportunities = detector.detect_arbitrage_opportunities()
    detector.save_results(opportunities)
    
    if opportunities:
        total_edge = sum(opp['edge'] for opp in opportunities)
        avg_confidence = sum(opp['confidence'] for opp in opportunities) / len(opportunities)
        
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"   Total opportunities: {len(opportunities)}")
        print(f"   Total edge available: {total_edge:.1%}")
        print(f"   Average confidence: {avg_confidence:.1%}")
        print(f"   Best opportunity: {opportunities[0]['edge']:.1%} edge")

if __name__ == "__main__":
    main()