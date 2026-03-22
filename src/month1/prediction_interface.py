#!/usr/bin/env python3
"""
Prediction Interface - Month 1 Integration
Interactive system for daily probability assessments

This module provides a user-friendly interface for conducting daily
probability assessments and recording predictions.
"""

from polymarket_tracker import PolymarketTracker
from ev_calculator import EVCalculator
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionInterface:
    """Interactive interface for daily prediction workflow"""
    
    def __init__(self):
        self.tracker = PolymarketTracker()
        self.calculator = EVCalculator()
        
        logger.info("Prediction Interface initialized")
    
    def interactive_assessment(self, market: Dict) -> Optional[Dict]:
        """Interactive assessment for a single market"""
        print(f"\n🎯 ASSESSING MARKET:")
        print(f"Question: {market['question']}")
        print(f"Current Price: {market['price']:.1%}")
        print(f"Category: {market['category']} / {market['subcategory']}")
        print(f"24h Volume: ${market['volume_24h']:,.0f}")
        print(f"Days to Resolution: {market['days_to_resolution']}")
        print("-" * 60)
        
        # Get probability assessment
        while True:
            try:
                prob_input = input("Your probability estimate (0-100%): ").strip()
                
                if prob_input.lower() in ['skip', 's', '']:
                    print("⏭️ Skipping this market")
                    return None
                
                # Parse percentage
                if prob_input.endswith('%'):
                    prob_input = prob_input[:-1]
                
                your_prob = float(prob_input) / 100.0
                
                if not (0 < your_prob < 1):
                    print("❌ Probability must be between 0 and 100%")
                    continue
                    
                break
                
            except ValueError:
                print("❌ Invalid input. Enter a number between 0-100, or 'skip'")
                continue
        
        # Get reasoning
        reasoning = input("Reasoning (optional): ").strip()
        
        # Calculate EV and evaluate
        opportunity = self.calculator.evaluate_opportunity(
            market, your_prob, reasoning
        )
        
        if opportunity:
            print(f"\n✅ POSITIVE EV OPPORTUNITY!")
            print(f"Expected Value: {opportunity['expected_value']:+.1%}")
            print(f"Kelly Size: {opportunity['kelly_fraction']:.1%}")
            print(f"Edge: {opportunity['edge']:+.1%}")
            print(f"Direction: {opportunity['trade_direction']}")
        else:
            print(f"\n❌ Filtered out (negative EV or below threshold)")
            # Still create record for tracking
            opportunity = {
                'market_id': market['market_id'],
                'question': market['question'],
                'market_price': market['price'],
                'your_probability': your_prob,
                'expected_value': self.calculator.calculate_ev(your_prob, market['price']),
                'kelly_fraction': 0,
                'reasoning': reasoning,
                'filtered_out': True
            }
        
        return opportunity
    
    def batch_assessment_mode(self, markets: List[Dict]) -> List[Dict]:
        """Quick batch assessment mode"""
        print(f"\n🚀 BATCH ASSESSMENT MODE")
        print(f"Assessing {len(markets)} markets quickly...")
        
        opportunities = []
        
        for i, market in enumerate(markets, 1):
            print(f"\n[{i}/{len(markets)}] {market['question'][:60]}...")
            print(f"Price: {market['price']:.1%} | Volume: ${market['volume_24h']:,.0f}")
            
            # Quick probability input
            while True:
                try:
                    prob_input = input(f"Your % (or 's' to skip): ").strip()
                    
                    if prob_input.lower() in ['skip', 's', '']:
                        break
                    
                    if prob_input.endswith('%'):
                        prob_input = prob_input[:-1]
                    
                    your_prob = float(prob_input) / 100.0
                    
                    if 0 < your_prob < 1:
                        opp = self.calculator.evaluate_opportunity(
                            market, your_prob, "Batch assessment"
                        )
                        if opp:
                            opportunities.append(opp)
                            print(f"✅ EV: {opp['expected_value']:+.1%}")
                        else:
                            print("❌ Filtered")
                        break
                    else:
                        print("Invalid range")
                        
                except ValueError:
                    print("Invalid input")
                    continue
        
        return opportunities
    
    def save_predictions(self, opportunities: List[Dict]) -> int:
        """Save all predictions to database"""
        saved_count = 0
        
        for opp in opportunities:
            if not opp.get('filtered_out', False):
                success = self.tracker.record_prediction(
                    market_id=opp['market_id'],
                    market_question=opp['question'],
                    market_price=opp['market_price'],
                    your_probability=opp['your_probability'],
                    expected_value=opp.get('expected_value'),
                    reasoning=opp.get('reasoning', '')
                )
                if success:
                    saved_count += 1
        
        return saved_count
    
    def daily_workflow(self, mode: str = 'interactive') -> Dict:
        """Complete daily assessment workflow"""
        print("🌅 STARTING DAILY ASSESSMENT WORKFLOW")
        print("=" * 50)
        
        # Get markets
        markets = self.tracker.daily_assessment_workflow()
        
        if not markets:
            print("❌ No markets available")
            return {'success': False}
        
        # Choose assessment mode
        if mode == 'batch':
            opportunities = self.batch_assessment_mode(markets)
        else:
            opportunities = []
            for market in markets:
                opp = self.interactive_assessment(market)
                if opp and not opp.get('filtered_out', False):
                    opportunities.append(opp)
        
        if not opportunities:
            print("\n📊 No positive EV opportunities found today")
            return {'success': True, 'opportunities': 0}
        
        # Show summary
        print(f"\n📊 DAILY SUMMARY:")
        print(f"Markets Assessed: {len(markets)}")
        print(f"Positive EV Opportunities: {len(opportunities)}")
        
        # Generate report
        report = self.calculator.generate_report(opportunities)
        print(report)
        
        # Portfolio allocation
        allocation = self.calculator.portfolio_allocation(opportunities)
        print(f"\n💰 PORTFOLIO ALLOCATION:")
        print(f"Total Allocation: {allocation['total_allocation']:.1%}")
        print(f"Number of Positions: {allocation['number_of_positions']}")
        
        # Save predictions
        saved_count = self.save_predictions(opportunities)
        print(f"\n💾 Saved {saved_count} predictions to database")
        
        # Show statistics
        stats = self.tracker.get_prediction_stats()
        print(f"\n📈 RUNNING STATISTICS:")
        print(f"Total Predictions: {stats.get('total_predictions', 0)}")
        print(f"Current Accuracy: {stats.get('accuracy', 0):.1%}")
        
        return {
            'success': True,
            'opportunities': len(opportunities),
            'saved_predictions': saved_count,
            'stats': stats,
            'allocation': allocation
        }
    
    def show_help(self):
        """Show help information"""
        help_text = """
🆘 PREDICTION INTERFACE HELP

DAILY WORKFLOW COMMANDS:
  python prediction_interface.py daily          - Run full interactive assessment
  python prediction_interface.py batch          - Run quick batch assessment  
  python prediction_interface.py stats          - Show current statistics
  
DURING ASSESSMENT:
  - Enter probability as number (e.g., "65" for 65%)
  - Type 'skip' or 's' to skip a market
  - Leave reasoning blank if no specific rationale
  
TIPS:
  - Focus on markets where you have genuine insight
  - Consider base rates before making assessments
  - Track your reasoning to improve over time
  - Aim for markets with substantial volume (>$1000)
"""
        print(help_text)

def main():
    """Main function for daily use"""
    import sys
    
    interface = PredictionInterface()
    
    if len(sys.argv) < 2:
        print("🤖 POLYMARKET PREDICTION INTERFACE - MONTH 1")
        print("Usage: python prediction_interface.py [daily|batch|stats|help]")
        interface.show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'daily':
        result = interface.daily_workflow(mode='interactive')
        print(f"\n✅ Workflow completed: {result}")
        
    elif command == 'batch':
        result = interface.daily_workflow(mode='batch')
        print(f"\n✅ Batch assessment completed: {result}")
        
    elif command == 'stats':
        stats = interface.tracker.get_prediction_stats()
        print(f"\n📊 CURRENT STATISTICS:")
        for key, value in stats.items():
            if key == 'accuracy':
                print(f"{key.title()}: {value:.1%}")
            else:
                print(f"{key.title().replace('_', ' ')}: {value}")
                
    elif command == 'help':
        interface.show_help()
        
    else:
        print(f"❌ Unknown command: {command}")
        interface.show_help()

if __name__ == "__main__":
    main()