#!/usr/bin/env python3
"""
Forward Testing Tracker - Alternative to Historical Data
Real-time prediction tracking and outcome monitoring

Since Polymarket API doesn't provide historical resolution data,
this system tracks our predictions and monitors for resolutions
to build our own training dataset.
"""

import requests
import json
import psycopg2
import pandas as pd
from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import time
# import schedule  # Optional - can use cron instead

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../../logs/forward_testing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ForwardTestingTracker:
    """Track predictions and monitor for market resolutions"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.clob_api = "https://clob.polymarket.com"
        
        # Database configuration
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
        self.init_database()
        logger.info("Forward Testing Tracker initialized")
        
    def init_database(self):
        """Initialize database tables for forward testing"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Add resolution tracking columns to existing predictions table
            cur.execute('''
                ALTER TABLE pm_predictions 
                ADD COLUMN IF NOT EXISTS resolution_checked_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS resolution_method VARCHAR(50),
                ADD COLUMN IF NOT EXISTS final_price DECIMAL(5,4),
                ADD COLUMN IF NOT EXISTS market_status VARCHAR(20),
                ADD COLUMN IF NOT EXISTS resolution_confidence DECIMAL(3,2),
                ADD COLUMN IF NOT EXISTS days_tracked INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_price_update TIMESTAMP,
                ADD COLUMN IF NOT EXISTS price_history JSONB
            ''')
            
            # Create forward test performance table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_forward_test_performance (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    total_predictions INTEGER,
                    resolved_predictions INTEGER,
                    correct_predictions INTEGER,
                    accuracy DECIMAL(5,4),
                    avg_expected_value DECIMAL(6,4),
                    avg_actual_return DECIMAL(6,4),
                    edge_validation DECIMAL(6,4), -- actual_return - expected_return
                    confidence_interval_lower DECIMAL(5,4),
                    confidence_interval_upper DECIMAL(5,4),
                    sample_size_adequate BOOLEAN,
                    notes TEXT
                );
            ''')
            
            # Create market monitoring table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_market_monitoring (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) UNIQUE NOT NULL,
                    question TEXT NOT NULL,
                    prediction_id INTEGER REFERENCES pm_predictions(id),
                    start_monitoring_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Market state tracking
                    current_price DECIMAL(5,4),
                    price_changes INTEGER DEFAULT 0,
                    volume_24h DECIMAL(15,2),
                    days_to_resolution INTEGER,
                    
                    -- Resolution detection
                    resolution_detected BOOLEAN DEFAULT FALSE,
                    resolution_date TIMESTAMP,
                    resolved_outcome INTEGER, -- 1=YES, 0=NO
                    resolution_source VARCHAR(50),
                    
                    -- Monitoring metadata
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    check_frequency_hours INTEGER DEFAULT 12,
                    monitoring_active BOOLEAN DEFAULT TRUE
                );
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("Forward testing database initialized")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def start_monitoring_prediction(self, prediction_id: int) -> bool:
        """Start monitoring a prediction for resolution"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get prediction details
            cur.execute('''
                SELECT market_id, market_question FROM pm_predictions 
                WHERE id = %s
            ''', (prediction_id,))
            
            result = cur.fetchone()
            if not result:
                logger.error(f"Prediction {prediction_id} not found")
                return False
            
            market_id, question = result
            
            # Get current market data
            market_data = self.get_current_market_data(market_id)
            if not market_data:
                logger.warning(f"Could not get market data for {market_id}")
                return False
            
            # Insert monitoring record
            cur.execute('''
                INSERT INTO pm_market_monitoring (
                    market_id, question, prediction_id, current_price,
                    volume_24h, days_to_resolution
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (market_id) DO UPDATE SET
                    prediction_id = EXCLUDED.prediction_id,
                    last_checked = CURRENT_TIMESTAMP
            ''', (
                market_id, question, prediction_id,
                market_data.get('price', 0),
                market_data.get('volume_24h', 0),
                market_data.get('days_to_resolution', 0)
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"Started monitoring prediction {prediction_id} for market {market_id[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return False
    
    def get_current_market_data(self, market_id: str) -> Optional[Dict]:
        """Get current market data by scanning events"""
        try:
            # Search through active events for this market
            response = requests.get(f"{self.gamma_api}/events", params={
                "active": "true",
                "limit": 100
            }, timeout=30)
            
            if response.status_code != 200:
                return None
            
            events = response.json()
            
            for event in events:
                markets = event.get('markets', [])
                for market in markets:
                    if market.get('condition_id') == market_id or market.get('conditionId') == market_id:
                        # Calculate days to resolution
                        end_date_str = event.get('endDate') or market.get('endDate')
                        days_to_resolution = 0
                        
                        if end_date_str:
                            try:
                                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                now = datetime.now(timezone.utc)
                                days_to_resolution = (end_date - now).days
                            except:
                                pass
                        
                        return {
                            'price': float(market.get('price', 0)),
                            'volume_24h': float(market.get('volume24hr', 0)),
                            'active': market.get('active', False),
                            'closed': market.get('closed', False),
                            'winner': market.get('winner'),
                            'days_to_resolution': max(0, days_to_resolution)
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    def check_for_resolutions(self) -> Dict:
        """Check all monitored markets for resolutions"""
        logger.info("🔍 Checking for market resolutions...")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get all active monitoring records
            cur.execute('''
                SELECT market_id, prediction_id, question, days_to_resolution
                FROM pm_market_monitoring 
                WHERE monitoring_active = TRUE 
                AND resolution_detected = FALSE
                ORDER BY days_to_resolution ASC
            ''')
            
            monitoring_records = cur.fetchall()
            logger.info(f"Checking {len(monitoring_records)} monitored markets")
            
            resolutions_found = 0
            price_updates = 0
            
            for market_id, pred_id, question, days_remaining in monitoring_records:
                # Get current market state
                current_data = self.get_current_market_data(market_id)
                
                if current_data:
                    # Update market monitoring record
                    cur.execute('''
                        UPDATE pm_market_monitoring 
                        SET current_price = %s, volume_24h = %s, 
                            days_to_resolution = %s, last_checked = CURRENT_TIMESTAMP,
                            price_changes = price_changes + 1
                        WHERE market_id = %s
                    ''', (
                        current_data['price'], current_data['volume_24h'],
                        current_data['days_to_resolution'], market_id
                    ))
                    price_updates += 1
                    
                    # Check for resolution
                    if self.is_market_resolved(current_data):
                        resolution_outcome = self.determine_outcome(current_data)
                        
                        if resolution_outcome is not None:
                            # Mark as resolved
                            cur.execute('''
                                UPDATE pm_market_monitoring 
                                SET resolution_detected = TRUE,
                                    resolution_date = CURRENT_TIMESTAMP,
                                    resolved_outcome = %s,
                                    resolution_source = 'api_detection',
                                    monitoring_active = FALSE
                                WHERE market_id = %s
                            ''', (resolution_outcome, market_id))
                            
                            # Update prediction record
                            cur.execute('''
                                UPDATE pm_predictions 
                                SET actual_outcome = %s,
                                    correct_prediction = (
                                        CASE WHEN your_probability > 0.5 AND %s = TRUE THEN TRUE
                                             WHEN your_probability < 0.5 AND %s = FALSE THEN TRUE  
                                             ELSE FALSE END
                                    ),
                                    resolution_date = CURRENT_TIMESTAMP,
                                    final_price = %s,
                                    resolution_checked_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            ''', (
                                resolution_outcome, resolution_outcome, resolution_outcome,
                                current_data['price'], pred_id
                            ))
                            
                            resolutions_found += 1
                            logger.info(f"✅ RESOLUTION DETECTED: {question[:60]}... = {resolution_outcome}")
                
                # Rate limiting
                time.sleep(0.2)
            
            conn.commit()
            cur.close()
            conn.close()
            
            result = {
                'markets_checked': len(monitoring_records),
                'price_updates': price_updates,
                'resolutions_found': resolutions_found,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Resolution check complete: {resolutions_found} new resolutions from {len(monitoring_records)} markets")
            return result
            
        except Exception as e:
            logger.error(f"Error checking resolutions: {e}")
            return {'error': str(e)}
    
    def is_market_resolved(self, market_data: Dict) -> bool:
        """Determine if a market is resolved based on available data"""
        # Check for explicit winner
        if market_data.get('winner') in ['Yes', 'No']:
            return True
        
        # Check if market is closed and not active
        if market_data.get('closed') and not market_data.get('active'):
            return True
        
        # Check if past resolution date (days_to_resolution <= 0)
        if market_data.get('days_to_resolution', 1) <= 0:
            return True
        
        return False
    
    def determine_outcome(self, market_data: Dict) -> Optional[int]:
        """Determine market outcome (1 for YES, 0 for NO)"""
        # Explicit winner
        winner = market_data.get('winner')
        if winner == 'Yes':
            return 1
        elif winner == 'No':
            return 0
        
        # Fallback: use final price if market is clearly resolved
        if self.is_market_resolved(market_data):
            final_price = market_data.get('price', 0.5)
            
            # If price is very close to 0 or 1, assume resolved
            if final_price >= 0.95:
                return 1
            elif final_price <= 0.05:
                return 0
        
        return None  # Cannot determine outcome
    
    def get_forward_test_performance(self) -> Dict:
        """Calculate current forward test performance metrics"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get resolved predictions
            cur.execute('''
                SELECT 
                    your_probability, 
                    market_price, 
                    expected_value,
                    actual_outcome,
                    correct_prediction,
                    (CASE WHEN your_probability > 0.5 AND actual_outcome = 1 
                          THEN (1 - market_price)
                          WHEN your_probability < 0.5 AND actual_outcome = 0  
                          THEN market_price
                          ELSE -market_price END) as actual_return
                FROM pm_predictions 
                WHERE actual_outcome IS NOT NULL
            ''')
            
            results = cur.fetchall()
            
            if not results:
                return {'error': 'No resolved predictions yet'}
            
            # Calculate metrics
            total_predictions = len(results)
            correct_predictions = sum(1 for r in results if r[4])  # correct_prediction
            accuracy = correct_predictions / total_predictions
            
            expected_values = [r[2] for r in results if r[2] is not None]
            actual_returns = [r[5] for r in results if r[5] is not None]
            
            avg_expected_value = sum(expected_values) / len(expected_values) if expected_values else 0
            avg_actual_return = sum(actual_returns) / len(actual_returns) if actual_returns else 0
            
            edge_validation = avg_actual_return - avg_expected_value
            
            # Bootstrap confidence interval for accuracy
            if total_predictions >= 10:
                import numpy as np
                accuracies = []
                for _ in range(1000):
                    sample = np.random.choice(results, size=len(results), replace=True)
                    sample_accuracy = sum(1 for r in sample if r[4]) / len(sample)
                    accuracies.append(sample_accuracy)
                
                ci_lower = np.percentile(accuracies, 2.5)
                ci_upper = np.percentile(accuracies, 97.5)
            else:
                ci_lower = ci_upper = accuracy
            
            cur.close()
            conn.close()
            
            return {
                'total_predictions': total_predictions,
                'correct_predictions': correct_predictions,
                'accuracy': accuracy,
                'avg_expected_value': avg_expected_value,
                'avg_actual_return': avg_actual_return,
                'edge_validation': edge_validation,
                'confidence_interval': (ci_lower, ci_upper),
                'sample_size_adequate': total_predictions >= 30,
                'statistical_significance': ci_lower > 0.5 and total_predictions >= 30
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            return {'error': str(e)}
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        perf = self.get_forward_test_performance()
        
        if 'error' in perf:
            return f"Performance Report: {perf['error']}"
        
        report = []
        report.append("=" * 60)
        report.append("FORWARD TESTING PERFORMANCE REPORT")
        report.append("=" * 60)
        
        report.append(f"\n📊 PREDICTION METRICS:")
        report.append(f"Total Predictions: {perf['total_predictions']}")
        report.append(f"Resolved: {perf['correct_predictions']}")
        report.append(f"Accuracy: {perf['accuracy']:.1%}")
        
        if perf['total_predictions'] >= 10:
            ci = perf['confidence_interval']
            report.append(f"95% Confidence Interval: [{ci[0]:.1%}, {ci[1]:.1%}]")
        
        report.append(f"\n💰 FINANCIAL PERFORMANCE:")
        report.append(f"Average Expected Value: {perf['avg_expected_value']:+.1%}")
        report.append(f"Average Actual Return: {perf['avg_actual_return']:+.1%}")
        report.append(f"Edge Validation: {perf['edge_validation']:+.1%}")
        
        report.append(f"\n🎯 STATISTICAL VALIDATION:")
        report.append(f"Sample Size Adequate: {'✅' if perf['sample_size_adequate'] else '❌'}")
        report.append(f"Statistically Significant: {'✅' if perf.get('statistical_significance') else '❌'}")
        
        if perf['sample_size_adequate'] and perf.get('statistical_significance'):
            report.append(f"\n🎉 EDGE CONFIRMED: System demonstrates statistically significant positive edge!")
        elif perf['total_predictions'] >= 10:
            report.append(f"\n⏳ PROMISING: Need more data for statistical significance")
        else:
            report.append(f"\n🚀 EARLY STAGE: Continue collecting resolution data")
        
        return "\n".join(report)
    
    def auto_monitor_all_predictions(self):
        """Automatically start monitoring for all unmonitored predictions"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Find predictions not yet being monitored
            cur.execute('''
                SELECT p.id FROM pm_predictions p
                LEFT JOIN pm_market_monitoring m ON p.id = m.prediction_id
                WHERE m.prediction_id IS NULL 
                AND p.actual_outcome IS NULL
            ''')
            
            unmonitored = cur.fetchall()
            
            cur.close()
            conn.close()
            
            for (pred_id,) in unmonitored:
                self.start_monitoring_prediction(pred_id)
                time.sleep(0.1)  # Rate limiting
                
            logger.info(f"Started monitoring {len(unmonitored)} new predictions")
            
        except Exception as e:
            logger.error(f"Error auto-monitoring: {e}")

def scheduled_resolution_check():
    """Scheduled function to check for resolutions"""
    tracker = ForwardTestingTracker()
    tracker.auto_monitor_all_predictions()
    result = tracker.check_for_resolutions()
    
    if result.get('resolutions_found', 0) > 0:
        report = tracker.generate_performance_report()
        logger.info(f"Updated performance report:\n{report}")

def main():
    """Main execution for forward testing tracker"""
    print("🔮 FORWARD TESTING TRACKER - REAL-TIME RESOLUTION MONITORING")
    print("Building our own training dataset through prediction tracking...")
    
    tracker = ForwardTestingTracker()
    
    # Auto-monitor all existing predictions
    tracker.auto_monitor_all_predictions()
    
    # Check for resolutions
    result = tracker.check_for_resolutions()
    print(f"\n📊 Resolution Check Result: {result}")
    
    # Show current performance
    report = tracker.generate_performance_report()
    print(f"\n{report}")
    
    print("\n⏰ For continuous monitoring, add to cron:")
    print("0 */12 * * * cd /home/vj/PM-HL-Trading-System/src/month2 && python3 forward_testing_tracker.py")
    print("\n💡 This will check for resolutions every 12 hours")

if __name__ == "__main__":
    main()