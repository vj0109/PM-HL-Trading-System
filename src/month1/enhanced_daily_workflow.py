#!/usr/bin/env python3
"""
Enhanced Daily Assessment with EV Filtering - Month 1 Week 3-4
Integration of mathematical filters with daily workflow
"""

import psycopg2
from simple_tracker import SimplePolymarketTracker
from smart_ev_calculator import SmartEVCalculator
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedDailyWorkflow:
    """Enhanced daily workflow with mathematical EV filtering"""
    
    def __init__(self):
        self.tracker = SimplePolymarketTracker()
        self.ev_calculator = SmartEVCalculator()
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
        logger.info("Enhanced Daily Workflow initialized")
    
    def enhanced_assessment(self, market):
        """Enhanced assessment with EV analysis"""
        print(f"\n📊 ENHANCED MARKET ASSESSMENT")
        print(f"Question: {market['question']}")
        print(f"Current Market Price: {market['current_price']:.3f} ({market['current_price']*100:.1f}%)")
        print(f"Volume 24h: ${market['volume_24h']:,.0f}")
        print(f"Days to Resolution: {market['days_to_resolution']}")
        print(f"Category: {market['category'] or 'General'}")
        
        # Get probability assessment
        while True:
            try:
                user_input = input(f"\nYour probability (0.00-1.00, 'skip', or 'quit'): ").strip()
                if user_input.lower() in ['skip', 's', 'quit', 'q']:
                    return None
                    
                probability = float(user_input)
                if 0 <= probability <= 1:
                    break
                else:
                    print("❌ Please enter a value between 0.00 and 1.00")
            except ValueError:
                print("❌ Please enter a valid decimal number (or 'skip'/'quit')")
        
        # Calculate EV analysis IMMEDIATELY
        ev_analysis = self.ev_calculator.analyze_opportunity(
            probability,
            market['current_price'],
            market['question'],
            market['market_id']
        )
        
        # Show EV analysis to user
        print(f"\n🧮 MATHEMATICAL ANALYSIS:")
        print(f"   Expected Value: {ev_analysis['ev_percentage']:+.1f}%")
        print(f"   Kelly Position: {ev_analysis['kelly_percentage']:.1f}% of bankroll")
        print(f"   Edge: {ev_analysis['edge']:+.3f}")
        print(f"   Recommendation: {ev_analysis['recommendation']}")
        
        if ev_analysis['recommendation'] == 'BUY':
            print(f"   ✅ POSITIVE EV TRADE!")
            print(f"   Profit if correct: {ev_analysis['profit_if_correct']:.1%}")
            print(f"   Risk if wrong: {ev_analysis['loss_if_wrong']:.1%}")
        else:
            print(f"   ❌ Below EV threshold - filtered out")
            
        # Get reasoning
        print(f"\n💭 Brief reasoning for {probability:.3f} probability:")
        reasoning = input("Reasoning: ").strip()
        
        return {
            'probability': probability,
            'reasoning': reasoning or "No reasoning provided",
            'ev_analysis': ev_analysis
        }
    
    def store_enhanced_prediction(self, market, assessment):
        """Store prediction with full EV analysis"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            ev_analysis = assessment['ev_analysis']
            
            cur.execute('''
                INSERT INTO predictions (
                    market_id, market_question, market_price, 
                    your_probability, reasoning, prediction_date,
                    expected_value, kelly_fraction, recommendation, edge
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                market['market_id'],
                market['question'],
                market['current_price'],
                assessment['probability'],
                assessment['reasoning'],
                datetime.now(),
                ev_analysis.get('expected_value'),
                ev_analysis.get('kelly_fraction'),
                ev_analysis.get('recommendation'),
                ev_analysis.get('edge')
            ))
            
            prediction_id = cur.fetchone()[0]
            
            # Store market features
            cur.execute('''
                INSERT INTO market_features (
                    market_id, volume_24h, days_to_resolution, 
                    category, market_cap
                ) VALUES (%s, %s, %s, %s, %s)
            ''', (
                market['market_id'],
                market['volume_24h'],
                market['days_to_resolution'],
                market['category'],
                market['market_cap']
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"✅ Stored enhanced prediction {prediction_id}")
            return prediction_id
            
        except Exception as e:
            logger.error(f"Error storing enhanced prediction: {e}")
            return None
    
    def enhanced_daily_workflow(self):
        """Main enhanced daily workflow (Month 1 Week 3-4)"""
        print("📅 ENHANCED DAILY WORKFLOW - WITH EV FILTERING")
        print("=" * 60)
        
        # Get opportunities
        markets = self.tracker.get_active_markets(limit=15)
        
        # Filter to suitable markets (same as before)
        suitable_markets = []
        for market in markets:
            if (market['volume_24h'] > 100 and 
                market['days_to_resolution'] > 1 and 
                market['days_to_resolution'] < 1000 and
                market['question'] and 
                len(market['question']) > 10):
                suitable_markets.append(market)
        
        if not suitable_markets:
            print("❌ No suitable markets found today")
            return
        
        print(f"\n🎯 Found {len(suitable_markets)} markets to assess...")
        print("🧮 Enhanced with EV calculation and Kelly position sizing")
        print("(Type 'skip' to skip a market, 'quit' to exit)")
        
        predictions_made = 0
        positive_ev_trades = 0
        total_ev = 0
        
        for i, market in enumerate(suitable_markets[:10], 1):  # Limit to 10 for testing
            print(f"\n--- Market {i}/{min(10, len(suitable_markets))} ---")
            
            assessment = self.enhanced_assessment(market)
            
            if assessment is None:
                print("⏭️  Skipping this market")
                continue
            
            # Store enhanced prediction
            prediction_id = self.store_enhanced_prediction(market, assessment)
            
            if prediction_id:
                predictions_made += 1
                ev_analysis = assessment['ev_analysis']
                total_ev += ev_analysis.get('expected_value', 0)
                
                if ev_analysis.get('recommendation') == 'BUY':
                    positive_ev_trades += 1
                    print(f"\n✅ POSITIVE EV TRADE RECORDED!")
                else:
                    print(f"\n📝 ASSESSMENT RECORDED (below EV threshold)")
            
            # Ask to continue
            if i < min(10, len(suitable_markets)):
                cont = input(f"\nContinue to next market? (y/n/quit): ").strip().lower()
                if cont in ['n', 'no', 'quit', 'q']:
                    break
        
        # Show enhanced summary
        print(f"\n🎉 ENHANCED DAILY ASSESSMENT COMPLETE!")
        print(f"📊 Predictions made: {predictions_made}")
        print(f"✅ Positive EV trades: {positive_ev_trades}")
        print(f"🔍 EV Filter effectiveness: {((predictions_made - positive_ev_trades) / predictions_made * 100):.1f}% of trades filtered out" if predictions_made > 0 else "No trades to filter")
        print(f"📈 Average EV: {(total_ev / predictions_made * 100):+.1f}%" if predictions_made > 0 else "+0.0%")
        
        return self.show_enhanced_summary()
    
    def show_enhanced_summary(self):
        """Show enhanced summary with EV statistics"""
        try:
            summary = self.ev_calculator.get_ev_summary()
            
            print(f"\n📊 CUMULATIVE EV PERFORMANCE:")
            print(f"   Total Predictions: {summary.get('total_predictions', 0)}")
            print(f"   Positive EV Trades: {summary.get('positive_ev_trades', 0)}")
            print(f"   Positive EV Rate: {summary.get('positive_ev_rate', 0):.1f}%")
            print(f"   Average Expected Value: {summary.get('avg_expected_value', 0)*100:+.1f}%")
            print(f"   Average Edge: {summary.get('avg_edge', 0):+.3f}")
            print(f"   Max EV Found: {summary.get('max_expected_value', 0)*100:+.1f}%")
            
            # Calculate filter effectiveness
            total_preds = summary.get('total_predictions', 0)
            positive_ev = summary.get('positive_ev_trades', 0)
            
            if total_preds > 0:
                filter_effectiveness = ((total_preds - positive_ev) / total_preds * 100)
                print(f"\n🔍 MATHEMATICAL FILTER PERFORMANCE:")
                print(f"   Filter effectiveness: {filter_effectiveness:.1f}% of bad trades removed")
                print(f"   Quality improvement: {(positive_ev / total_preds * 100):.1f}% of trades are positive EV")
                
                if filter_effectiveness >= 70:
                    print(f"   ✅ MONTH 1 WEEK 3-4 TARGET MET: >70% filtering achieved!")
                else:
                    print(f"   🎯 Target: 70-80% filtering (currently {filter_effectiveness:.1f}%)")
            
            return total_preds
            
        except Exception as e:
            logger.error(f"Error getting enhanced summary: {e}")
            return 0

def main():
    """Run enhanced daily workflow"""
    workflow = EnhancedDailyWorkflow()
    workflow.enhanced_daily_workflow()

if __name__ == "__main__":
    main()