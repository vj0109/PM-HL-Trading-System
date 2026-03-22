#!/usr/bin/env python3
"""
Expected Value Calculator - Month 1, Week 2
Mathematical Filters and Position Sizing

This module implements the Expected Value calculation and Kelly Criterion
for filtering profitable trading opportunities.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EVCalculator:
    """Expected Value calculator with Kelly Criterion position sizing"""
    
    def __init__(self, min_ev_threshold: float = 0.05, max_kelly_fraction: float = 0.25):
        self.min_ev_threshold = min_ev_threshold  # Minimum 5% expected value
        self.max_kelly_fraction = max_kelly_fraction  # Max 25% of bankroll (half-Kelly)
        
        logger.info(f"EVCalculator initialized - Min EV: {min_ev_threshold:.1%}, Max Kelly: {max_kelly_fraction:.1%}")
        
    def calculate_ev(self, your_prob: float, market_price: float) -> float:
        """
        Calculate Expected Value for a binary prediction market trade
        
        Formula: EV = (win_probability × profit) - (loss_probability × loss)
        
        Args:
            your_prob: Your estimated probability (0.0 to 1.0)
            market_price: Current market price (0.0 to 1.0)
            
        Returns:
            Expected value as decimal (e.g., 0.15 = 15% expected return)
        """
        if not (0 < your_prob < 1):
            raise ValueError(f"Probability must be between 0 and 1, got {your_prob}")
        if not (0 < market_price < 1):
            raise ValueError(f"Market price must be between 0 and 1, got {market_price}")
        
        # If we buy YES at market_price:
        # - Win: get (1 - market_price) profit if outcome is YES
        # - Lose: lose market_price if outcome is NO
        
        profit_if_win = 1 - market_price
        loss_if_lose = market_price
        win_probability = your_prob
        lose_probability = 1 - your_prob
        
        ev = (win_probability * profit_if_win) - (lose_probability * loss_if_lose)
        
        return ev
    
    def kelly_fraction(self, win_prob: float, market_price: float) -> float:
        """
        Calculate optimal Kelly bet size for binary outcome
        
        Kelly formula for binary bet: f = (bp - q) / b
        where:
        - b = payout coefficient = (1 - market_price) / market_price
        - p = win probability
        - q = 1 - p = lose probability
        
        Args:
            win_prob: Probability of winning (0.0 to 1.0)
            market_price: Market price (0.0 to 1.0)
            
        Returns:
            Optimal fraction of bankroll to bet (0.0 to max_kelly_fraction)
        """
        if not (0 < win_prob < 1):
            return 0.0
        if not (0 < market_price < 1):
            return 0.0
            
        # Calculate payout coefficient
        b = (1 - market_price) / market_price
        
        # Kelly fraction
        f = (win_prob * (b + 1) - 1) / b
        
        # Apply safety limits
        if f <= 0:
            return 0.0
        
        # Cap at half-Kelly for safety
        return min(f * 0.5, self.max_kelly_fraction)
    
    def evaluate_opportunity(self, market_data: Dict, your_prob: float, 
                           reasoning: str = "") -> Optional[Dict]:
        """
        Comprehensive evaluation of a trading opportunity
        
        Args:
            market_data: Market information dictionary
            your_prob: Your probability assessment
            reasoning: Text explaining your assessment
            
        Returns:
            Opportunity dict if positive EV, None if filtered out
        """
        try:
            market_price = market_data.get('price', 0)
            market_id = market_data.get('market_id', '')
            question = market_data.get('question', '')
            
            if not market_price or not market_id:
                logger.warning("Missing required market data")
                return None
            
            # Calculate Expected Value
            ev = self.calculate_ev(your_prob, market_price)
            
            # Filter by minimum EV threshold
            if ev < self.min_ev_threshold:
                logger.debug(f"Filtered out: EV {ev:.1%} below threshold {self.min_ev_threshold:.1%}")
                return None
            
            # Calculate Kelly position size
            kelly_size = self.kelly_fraction(your_prob, market_price)
            
            # Filter by minimum position size
            if kelly_size < 0.01:  # Minimum 1% position
                logger.debug(f"Filtered out: Kelly size {kelly_size:.1%} too small")
                return None
            
            # Calculate additional metrics
            edge = your_prob - market_price
            profit_potential = (1 - market_price) if your_prob > market_price else market_price
            risk_amount = market_price if your_prob > market_price else (1 - market_price)
            
            opportunity = {
                'market_id': market_id,
                'question': question[:100] + "..." if len(question) > 100 else question,
                'market_price': market_price,
                'your_probability': your_prob,
                'expected_value': ev,
                'kelly_fraction': kelly_size,
                'recommended_size': kelly_size,
                'edge': edge,
                'profit_potential': profit_potential,
                'risk_amount': risk_amount,
                'reasoning': reasoning,
                'evaluation_time': datetime.now().isoformat(),
                'trade_direction': 'BUY_YES' if your_prob > market_price else 'BUY_NO'
            }
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error evaluating opportunity: {e}")
            return None
    
    def filter_positive_ev(self, opportunities: List[Dict]) -> List[Dict]:
        """
        Filter and rank opportunities by Expected Value
        
        Args:
            opportunities: List of opportunity dictionaries
            
        Returns:
            Sorted list of positive EV opportunities
        """
        positive_ev_trades = []
        
        for opp in opportunities:
            if opp and opp.get('expected_value', 0) > 0:
                positive_ev_trades.append(opp)
        
        # Sort by Expected Value descending
        positive_ev_trades.sort(key=lambda x: x['expected_value'], reverse=True)
        
        logger.info(f"Filtered to {len(positive_ev_trades)} positive EV opportunities from {len(opportunities)} total")
        
        return positive_ev_trades
    
    def portfolio_allocation(self, opportunities: List[Dict], 
                           total_bankroll: float = 10000) -> Dict:
        """
        Calculate optimal portfolio allocation across multiple opportunities
        
        Args:
            opportunities: List of positive EV opportunities
            total_bankroll: Total available capital
            
        Returns:
            Portfolio allocation recommendations
        """
        if not opportunities:
            return {'total_allocation': 0, 'positions': []}
        
        total_kelly = sum(opp['kelly_fraction'] for opp in opportunities)
        
        # Scale down if total allocation exceeds 100%
        scale_factor = min(1.0, 1.0 / total_kelly) if total_kelly > 1.0 else 1.0
        
        positions = []
        total_allocation = 0
        
        for opp in opportunities:
            scaled_kelly = opp['kelly_fraction'] * scale_factor
            dollar_allocation = scaled_kelly * total_bankroll
            
            position = {
                'market_id': opp['market_id'],
                'question': opp['question'],
                'kelly_fraction': scaled_kelly,
                'dollar_allocation': dollar_allocation,
                'expected_value': opp['expected_value'],
                'trade_direction': opp['trade_direction']
            }
            
            positions.append(position)
            total_allocation += scaled_kelly
        
        return {
            'total_allocation': total_allocation,
            'total_dollar_amount': total_allocation * total_bankroll,
            'number_of_positions': len(positions),
            'positions': positions,
            'scale_factor_applied': scale_factor
        }
    
    def risk_metrics(self, opportunities: List[Dict]) -> Dict:
        """Calculate portfolio risk metrics"""
        if not opportunities:
            return {}
        
        evs = [opp['expected_value'] for opp in opportunities]
        kelly_sizes = [opp['kelly_fraction'] for opp in opportunities]
        edges = [opp['edge'] for opp in opportunities]
        
        return {
            'avg_expected_value': np.mean(evs),
            'median_expected_value': np.median(evs),
            'min_expected_value': min(evs),
            'max_expected_value': max(evs),
            'avg_kelly_size': np.mean(kelly_sizes),
            'total_kelly_allocation': sum(kelly_sizes),
            'avg_edge': np.mean(edges),
            'num_opportunities': len(opportunities)
        }
    
    def generate_report(self, opportunities: List[Dict]) -> str:
        """Generate a formatted report of opportunities"""
        if not opportunities:
            return "No positive EV opportunities found."
        
        report = []
        report.append("=" * 80)
        report.append("POSITIVE EXPECTED VALUE OPPORTUNITIES")
        report.append("=" * 80)
        
        # Summary statistics
        risk_stats = self.risk_metrics(opportunities)
        report.append(f"\nSUMMARY:")
        report.append(f"Number of Opportunities: {risk_stats['num_opportunities']}")
        report.append(f"Average Expected Value: {risk_stats['avg_expected_value']:.1%}")
        report.append(f"Total Kelly Allocation: {risk_stats['total_kelly_allocation']:.1%}")
        report.append(f"Average Edge: {risk_stats['avg_edge']:.1%}")
        
        report.append(f"\nTOP OPPORTUNITIES:")
        report.append("-" * 80)
        
        for i, opp in enumerate(opportunities[:10], 1):  # Top 10
            report.append(f"\n{i}. {opp['question']}")
            report.append(f"   Market Price: {opp['market_price']:.1%} | Your Prob: {opp['your_probability']:.1%} | Edge: {opp['edge']:+.1%}")
            report.append(f"   Expected Value: {opp['expected_value']:+.1%} | Kelly Size: {opp['kelly_fraction']:.1%}")
            report.append(f"   Direction: {opp['trade_direction']} | Reasoning: {opp['reasoning'][:60]}...")
        
        return "\n".join(report)

def main():
    """Test the EV Calculator"""
    print("🧮 EXPECTED VALUE CALCULATOR - MONTH 1 WEEK 2")
    print("Testing mathematical filters and position sizing...")
    
    calculator = EVCalculator()
    
    # Test cases
    test_opportunities = [
        {
            'market_id': 'test_1',
            'question': 'Will Bitcoin reach $100k by end of 2024?',
            'price': 0.30  # Market says 30%
        },
        {
            'market_id': 'test_2', 
            'question': 'Will it rain tomorrow in NYC?',
            'price': 0.65  # Market says 65%
        },
        {
            'market_id': 'test_3',
            'question': 'Will the next coin flip be heads?',
            'price': 0.45  # Market says 45%
        }
    ]
    
    # Test probabilities (your assessments)
    your_assessments = [0.55, 0.40, 0.50]  # 55%, 40%, 50%
    
    print("\nEvaluating test opportunities...")
    
    evaluated_opportunities = []
    for i, (market, your_prob) in enumerate(zip(test_opportunities, your_assessments)):
        opp = calculator.evaluate_opportunity(
            market, 
            your_prob, 
            reasoning=f"Test assessment {i+1}"
        )
        if opp:
            evaluated_opportunities.append(opp)
    
    # Generate report
    if evaluated_opportunities:
        report = calculator.generate_report(evaluated_opportunities)
        print(report)
        
        # Portfolio allocation
        allocation = calculator.portfolio_allocation(evaluated_opportunities)
        print(f"\n💰 PORTFOLIO ALLOCATION:")
        print(f"Total Allocation: {allocation['total_allocation']:.1%}")
        print(f"Dollar Amount: ${allocation['total_dollar_amount']:,.0f}")
    else:
        print("\n❌ No positive EV opportunities found")

if __name__ == "__main__":
    main()