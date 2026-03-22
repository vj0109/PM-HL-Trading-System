#!/usr/bin/env python3
"""
Daily Assessment Workflow - Month 1 Week 1-2 Core Deliverable
Manual probability assessment and tracking system
"""

import psycopg2
from simple_tracker import SimplePolymarketTracker
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailyAssessment:
    """Core daily probability assessment workflow"""
    
    def __init__(self):
        self.tracker = SimplePolymarketTracker()
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
    def get_todays_opportunities(self, limit=10):
        """Pull 10-15 highest volume active markets"""
        print("🔍 Discovering today's market opportunities...")
        
        markets = self.tracker.get_active_markets(limit=limit)
        
        # Filter to good opportunities (looser criteria for Month 1)
        good_markets = []
        for market in markets:
            if (market['volume_24h'] > 100 and  # Lower volume threshold 
                market['days_to_resolution'] > 1 and 
                market['days_to_resolution'] < 1000 and  # Allow longer term
                market['question'] and 
                len(market['question']) > 10):  # Basic quality filter
                good_markets.append(market)
        
        print(f"Found {len(good_markets)} suitable markets for assessment")
        return good_markets[:limit]
    
    def assess_probability(self, market):
        """Manual probability assessment (core Month 1 activity)"""
        print(f"\n📊 MARKET ASSESSMENT")
        print(f"Question: {market['question']}")
        print(f"Current Market Price: {market['current_price']:.3f}")
        print(f"Volume 24h: ${market['volume_24h']:,.0f}")
        print(f"Days to Resolution: {market['days_to_resolution']}")
        print(f"Category: {market['category'] or 'General'}")
        
        print(f"\n🤔 What's your probability assessment for YES outcome?")
        print(f"Market price: {market['current_price']:.3f} ({market['current_price']*100:.1f}%)")
        
        while True:
            try:
                user_input = input("Your probability (0.00-1.00): ").strip()
                if user_input.lower() in ['skip', 's', 'quit', 'q']:
                    return None
                    
                probability = float(user_input)
                if 0 <= probability <= 1:
                    break
                else:
                    print("❌ Please enter a value between 0.00 and 1.00")
            except ValueError:
                print("❌ Please enter a valid decimal number (or 'skip')")
        
        # Get reasoning
        print(f"\n💭 Brief reasoning for {probability:.3f} probability:")
        reasoning = input("Reasoning: ").strip()
        
        return {
            'probability': probability,
            'reasoning': reasoning or "No reasoning provided"
        }
    
    def store_prediction(self, market, assessment):
        """Store prediction in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO predictions (
                    market_id, market_question, market_price, 
                    your_probability, reasoning, prediction_date
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                market['market_id'],
                market['question'],
                market['current_price'],
                assessment['probability'],
                assessment['reasoning'],
                datetime.now()
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
            
            logger.info(f"✅ Stored prediction {prediction_id}")
            return prediction_id
            
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
            return None
    
    def daily_workflow(self):
        """Main daily assessment workflow (Month 1 core deliverable)"""
        print("📅 DAILY PROBABILITY ASSESSMENT WORKFLOW")
        print("=" * 50)
        
        # Get opportunities
        markets = self.get_todays_opportunities(limit=10)
        
        if not markets:
            print("❌ No suitable markets found today")
            return
        
        print(f"\n🎯 Assessing {len(markets)} markets today...")
        print("(Type 'skip' to skip a market, 'quit' to exit)")
        
        predictions_made = 0
        
        for i, market in enumerate(markets, 1):
            print(f"\n--- Market {i}/{len(markets)} ---")
            
            assessment = self.assess_probability(market)
            
            if assessment is None:
                print("⏭️  Skipping this market")
                continue
            
            # Store prediction
            prediction_id = self.store_prediction(market, assessment)
            
            if prediction_id:
                predictions_made += 1
                
                # Show assessment summary
                market_price = market['current_price']
                your_prob = assessment['probability']
                edge = your_prob - market_price
                
                print(f"\n📝 ASSESSMENT RECORDED:")
                print(f"   Market: {market_price:.3f} vs Your: {your_prob:.3f}")
                print(f"   Edge: {edge:+.3f} ({'Positive' if edge > 0 else 'Negative'} EV)")
                print(f"   Reasoning: {assessment['reasoning'][:50]}...")
            
            # Ask to continue
            if i < len(markets):
                cont = input(f"\nContinue to next market? (y/n/quit): ").strip().lower()
                if cont in ['n', 'no', 'quit', 'q']:
                    break
        
        print(f"\n✅ Daily assessment complete!")
        print(f"📊 Predictions made: {predictions_made}")
        
        return self.show_daily_summary()
    
    def show_daily_summary(self):
        """Show today's prediction summary"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Today's predictions
            cur.execute('''
                SELECT COUNT(*), AVG(your_probability), AVG(market_price)
                FROM predictions 
                WHERE DATE(prediction_date) = CURRENT_DATE
            ''')
            
            today_stats = cur.fetchone()
            count, avg_prob, avg_market = today_stats
            
            if count > 0:
                print(f"\n📊 TODAY'S SUMMARY:")
                print(f"   Predictions: {count}")
                print(f"   Avg Your Probability: {avg_prob:.3f}")
                print(f"   Avg Market Price: {avg_market:.3f}")
                print(f"   Overall Edge: {avg_prob - avg_market:+.3f}")
            
            # Total predictions to date
            cur.execute('SELECT COUNT(*) FROM predictions')
            total_predictions = cur.fetchone()[0]
            print(f"\n🎯 PROGRESS: {total_predictions} total predictions tracked")
            
            cur.close()
            conn.close()
            
            return total_predictions
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return 0

def main():
    """Run daily assessment"""
    assessment = DailyAssessment()
    assessment.daily_workflow()

if __name__ == "__main__":
    main()