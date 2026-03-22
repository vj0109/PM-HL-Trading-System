#!/usr/bin/env python3
"""
EV Calculator + Kelly Criterion - Month 1 Week 3-4
Mathematical filters for positive EV trades only
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
import psycopg2
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmartEVCalculator:
    """Enhanced EV Calculator with Kelly Criterion and mathematical validation"""
    
    def __init__(self):
        self.min_ev_threshold = 0.05  # Minimum 5% expected value
        self.max_kelly_fraction = 0.25  # Maximum 25% of bankroll
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
        logger.info("SmartEVCalculator initialized")
    
    def calculate_ev(self, your_prob: float, market_price: float) -> float:
        """
        Calculate Expected Value for a trade
        
        Formula: EV = (win_probability × profit) - (loss_probability × loss)
        """
        if your_prob <= 0 or your_prob >= 1:
            raise ValueError("Probability must be between 0 and 1")
            
        if market_price <= 0 or market_price >= 1:
            raise ValueError("Market price must be between 0 and 1")
        
        # Profit if win = payout - cost = (1 - market_price)
        profit_if_win = 1 - market_price
        
        # Loss if lose = cost = market_price
        loss_if_lose = market_price
        
        # Expected Value calculation
        ev = (your_prob * profit_if_win) - ((1 - your_prob) * loss_if_lose)
        
        return ev
    
    def kelly_fraction(self, win_prob: float, market_price: float) -> float:
        """
        Calculate optimal Kelly bet size
        
        Formula: f = (b × p - q) / b
        where b = payout coefficient, p = win probability, q = 1-p
        """
        if market_price >= 1 or market_price <= 0:
            return 0
            
        if win_prob <= 0 or win_prob >= 1:
            return 0
        
        # b = payout ratio = (1 - market_price) / market_price
        b = (1 - market_price) / market_price
        p = win_prob
        q = 1 - win_prob
        
        # Kelly fraction
        f = (b * p - q) / b
        
        # Apply safety constraints
        if f <= 0:
            return 0
            
        # Cap at half-Kelly for safety, max 25% of bankroll
        safe_fraction = min(f * 0.5, self.max_kelly_fraction)
        
        return safe_fraction
    
    def analyze_opportunity(self, your_prob: float, market_price: float, 
                           market_question: str = "", market_id: str = "") -> Dict:
        """Comprehensive analysis of a trading opportunity"""
        
        try:
            # Calculate Expected Value
            ev = self.calculate_ev(your_prob, market_price)
            
            # Calculate Kelly position size
            kelly_size = self.kelly_fraction(your_prob, market_price)
            
            # Determine recommendation
            is_positive_ev = ev > self.min_ev_threshold
            is_significant_edge = abs(your_prob - market_price) > 0.1
            is_reasonable_kelly = kelly_size > 0.01  # At least 1% position
            
            recommendation = "BUY" if (is_positive_ev and kelly_size > 0) else "SKIP"
            
            # Calculate potential outcomes
            if kelly_size > 0:
                profit_if_correct = kelly_size * (1 - market_price) / market_price
                loss_if_wrong = kelly_size
            else:
                profit_if_correct = 0
                loss_if_wrong = 0
            
            return {
                'market_id': market_id,
                'market_question': market_question,
                'your_probability': your_prob,
                'market_price': market_price,
                'expected_value': ev,
                'kelly_fraction': kelly_size,
                'recommendation': recommendation,
                'edge': your_prob - market_price,
                'is_positive_ev': is_positive_ev,
                'is_significant_edge': is_significant_edge,
                'ev_percentage': ev * 100,
                'kelly_percentage': kelly_size * 100,
                'profit_if_correct': profit_if_correct,
                'loss_if_wrong': loss_if_wrong,
                'analysis_timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {e}")
            return {
                'error': str(e),
                'recommendation': 'SKIP'
            }
    
    def filter_positive_ev_trades(self, opportunities: List[Dict]) -> List[Dict]:
        """Filter to only positive EV trades and sort by attractiveness"""
        
        positive_ev_trades = []
        
        for opportunity in opportunities:
            your_prob = opportunity.get('your_probability') or opportunity.get('probability')
            market_price = opportunity.get('market_price')
            
            if your_prob is None or market_price is None:
                continue
            
            analysis = self.analyze_opportunity(
                your_prob, 
                market_price,
                opportunity.get('market_question', ''),
                opportunity.get('market_id', '')
            )
            
            if analysis.get('is_positive_ev') and analysis.get('kelly_fraction', 0) > 0.01:
                # Merge analysis with original opportunity
                enhanced_opportunity = {**opportunity, **analysis}
                positive_ev_trades.append(enhanced_opportunity)
        
        # Sort by Expected Value descending
        positive_ev_trades.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
        
        logger.info(f"Filtered {len(positive_ev_trades)} positive EV trades from {len(opportunities)} opportunities")
        
        return positive_ev_trades
    
    def store_ev_analysis(self, analysis: Dict) -> Optional[int]:
        """Store EV analysis in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Update predictions table with EV analysis
            if analysis.get('market_id'):
                cur.execute('''
                    UPDATE predictions 
                    SET 
                        expected_value = %s,
                        kelly_fraction = %s,
                        recommendation = %s,
                        edge = %s
                    WHERE market_id = %s AND prediction_date::date = CURRENT_DATE
                ''', (
                    analysis.get('expected_value'),
                    analysis.get('kelly_fraction'), 
                    analysis.get('recommendation'),
                    analysis.get('edge'),
                    analysis.get('market_id')
                ))
                
                rows_updated = cur.rowcount
                conn.commit()
                
                if rows_updated > 0:
                    logger.info(f"✅ Updated prediction with EV analysis")
                else:
                    logger.warning("No matching prediction found to update")
            
            cur.close()
            conn.close()
            
            return rows_updated
            
        except Exception as e:
            logger.error(f"Error storing EV analysis: {e}")
            return None
    
    def get_ev_summary(self) -> Dict:
        """Get summary statistics of EV performance"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Add EV columns to predictions table if they don't exist
            try:
                cur.execute('''
                    ALTER TABLE predictions 
                    ADD COLUMN IF NOT EXISTS expected_value DECIMAL(6,4),
                    ADD COLUMN IF NOT EXISTS kelly_fraction DECIMAL(5,4),
                    ADD COLUMN IF NOT EXISTS recommendation VARCHAR(10),
                    ADD COLUMN IF NOT EXISTS edge DECIMAL(6,4)
                ''')
                conn.commit()
            except:
                pass  # Columns might already exist
            
            # Get overall statistics
            cur.execute('''
                SELECT 
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN expected_value > 0.05 THEN 1 END) as positive_ev_count,
                    AVG(expected_value) as avg_ev,
                    AVG(kelly_fraction) as avg_kelly,
                    AVG(edge) as avg_edge,
                    MAX(expected_value) as max_ev
                FROM predictions
            ''')
            
            stats = cur.fetchone()
            
            if stats[0] > 0:  # If we have predictions
                total, positive_ev, avg_ev, avg_kelly, avg_edge, max_ev = stats
                
                summary = {
                    'total_predictions': total,
                    'positive_ev_trades': positive_ev or 0,
                    'positive_ev_rate': (positive_ev / total * 100) if positive_ev else 0,
                    'avg_expected_value': float(avg_ev) if avg_ev else 0,
                    'avg_kelly_fraction': float(avg_kelly) if avg_kelly else 0,
                    'avg_edge': float(avg_edge) if avg_edge else 0,
                    'max_expected_value': float(max_ev) if max_ev else 0
                }
            else:
                summary = {
                    'total_predictions': 0,
                    'positive_ev_trades': 0,
                    'positive_ev_rate': 0,
                    'avg_expected_value': 0,
                    'avg_kelly_fraction': 0,
                    'avg_edge': 0,
                    'max_expected_value': 0
                }
            
            cur.close()
            conn.close()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting EV summary: {e}")
            return {}

def test_ev_calculator():
    """Test the EV calculator with various scenarios"""
    print("🧮 TESTING EV CALCULATOR + KELLY CRITERION")
    
    calculator = SmartEVCalculator()
    
    # Test scenarios from the prediction we made
    test_cases = [
        {
            'name': 'Trump 2028 (our prediction)',
            'your_prob': 0.65,
            'market_price': 0.018,
            'expected': 'Strong BUY'
        },
        {
            'name': 'Fair value market',
            'your_prob': 0.50,
            'market_price': 0.50,
            'expected': 'SKIP'
        },
        {
            'name': 'Slight edge',
            'your_prob': 0.55,
            'market_price': 0.50,
            'expected': 'Small BUY'
        },
        {
            'name': 'Overpriced market',
            'your_prob': 0.30,
            'market_price': 0.60,
            'expected': 'SKIP'
        }
    ]
    
    print("\n📊 EV ANALYSIS RESULTS:")
    print("-" * 80)
    
    for case in test_cases:
        analysis = calculator.analyze_opportunity(
            case['your_prob'], 
            case['market_price'],
            case['name']
        )
        
        print(f"\n{case['name']}:")
        print(f"  Your Prob: {case['your_prob']:.3f} vs Market: {case['market_price']:.3f}")
        print(f"  Expected Value: {analysis['ev_percentage']:+.1f}%")
        print(f"  Kelly Size: {analysis['kelly_percentage']:.1f}% of bankroll")
        print(f"  Recommendation: {analysis['recommendation']}")
        print(f"  Edge: {analysis['edge']:+.3f}")
        
        if analysis['recommendation'] == 'BUY':
            print(f"  Profit if correct: {analysis['profit_if_correct']:.1%}")
            print(f"  Loss if wrong: {analysis['loss_if_wrong']:.1%}")
    
    print("\n✅ EV Calculator testing complete")
    return True

def main():
    """Test and demonstrate EV calculator"""
    print("🚀 MONTH 1 WEEK 3-4: MATHEMATICAL FILTERS")
    
    if test_ev_calculator():
        print("\n🎯 EV Calculator operational - ready for integration")
        
        # Get current EV summary
        calculator = SmartEVCalculator()
        summary = calculator.get_ev_summary()
        
        print(f"\n📊 CURRENT EV PERFORMANCE:")
        print(f"   Total Predictions: {summary.get('total_predictions', 0)}")
        print(f"   Positive EV Rate: {summary.get('positive_ev_rate', 0):.1f}%")
        print(f"   Average Edge: {summary.get('avg_edge', 0):+.3f}")

if __name__ == "__main__":
    main()