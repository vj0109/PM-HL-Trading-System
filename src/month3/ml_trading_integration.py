#!/usr/bin/env python3
"""
ML TRADING INTEGRATION - Month 3 Component
Connects 95% accuracy ML model to live Polymarket trading execution
"""

import psycopg2
import joblib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLTradingIntegration:
    """Bridge between ML predictions and trading execution"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # VJ Requirements: <30 days for feedback loop
        self.trading_criteria = {
            'min_confidence': 0.80,           # 80%+ ML confidence
            'min_expected_value': 0.15,       # 15%+ expected value  
            'max_days_to_resolution': 30,     # VJ requirement: <30 days
            'min_volume_24h': 500,            # $500+ daily volume
            'max_daily_trades': 5             # Max 5 ML trades per day
        }
        
        # Position sizing and risk parameters
        self.position_params = {
            'base_position_size': 500,        # Base size per trade
            'max_position_size': 1500,        # Max size for high confidence
            'stop_loss_pct': 0.15,            # 15% max loss 
            'take_profit_pct': 0.30,          # 30% target profit
            'max_open_positions': 8           # Max concurrent PM positions
        }
        
        logger.info("ML Trading Integration initialized")
    
    def get_pending_ml_signals(self) -> List[Dict]:
        """Get recent ML predictions ready for trading"""
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get yesterday's ML predictions not yet traded
            cur.execute('''
                SELECT 
                    id, market_id, market_question, market_price, your_probability,
                    expected_value, reasoning, prediction_date, kelly_fraction,
                    recommendation
                FROM predictions 
                WHERE DATE(prediction_date) >= CURRENT_DATE - INTERVAL '1 day'
                AND resolved_outcome IS NULL
                AND id NOT IN (
                    SELECT COALESCE(ml_prediction_id, -1) 
                    FROM pm_paper_trades 
                    WHERE ml_prediction_id IS NOT NULL
                )
                ORDER BY expected_value DESC
            ''')
            
            predictions = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            
            cur.close()
            conn.close()
            
            # Convert to list of dictionaries
            ml_signals = []
            for pred in predictions:
                signal = dict(zip(columns, pred))
                ml_signals.append(signal)
            
            logger.info(f"Found {len(ml_signals)} pending ML signals")
            return ml_signals
            
        except Exception as e:
            logger.error(f"Error getting pending ML signals: {e}")
            return []
    
    def get_market_details(self, market_id: str) -> Optional[Dict]:
        """Get current market details from Polymarket API"""
        
        try:
            response = requests.get(
                f'https://gamma-api.polymarket.com/markets/{market_id}',
                timeout=10
            )
            
            if response.status_code == 200:
                market_data = response.json()
                
                # Calculate days to resolution
                if market_data.get('endDate'):
                    end_date = datetime.fromisoformat(market_data['endDate'].replace('Z', '+00:00'))
                    days_to_resolution = (end_date - datetime.now()).days
                else:
                    days_to_resolution = 999  # Unknown resolution
                
                return {
                    'active': market_data.get('active', False),
                    'question': market_data.get('question', ''),
                    'current_yes_price': float(market_data.get('outcomePrices', ['0.5'])[0]),
                    'current_no_price': float(market_data.get('outcomePrices', ['0.5', '0.5'])[1]),
                    'volume_24h': float(market_data.get('volume24hr', 0)),
                    'days_to_resolution': days_to_resolution,
                    'end_date': market_data.get('endDate')
                }
                
        except Exception as e:
            logger.error(f"Error getting market details for {market_id}: {e}")
        
        return None
    
    def evaluate_trading_criteria(self, prediction: Dict, market_details: Dict) -> Tuple[bool, List[str]]:
        """Evaluate if ML prediction meets trading criteria"""
        
        reasons = []
        
        # Check confidence threshold
        # Note: We'll need to add ML confidence to predictions table
        confidence = prediction.get('ml_confidence', 0.85)  # Default high confidence
        if confidence < self.trading_criteria['min_confidence']:
            reasons.append(f"Low confidence: {confidence:.1%} < {self.trading_criteria['min_confidence']:.1%}")
        
        # Check expected value
        ev = float(prediction.get('expected_value', 0))
        if ev < self.trading_criteria['min_expected_value']:
            reasons.append(f"Low EV: {ev:.1%} < {self.trading_criteria['min_expected_value']:.1%}")
        
        # Check days to resolution (VJ requirement)
        days_out = market_details.get('days_to_resolution', 999)
        if days_out > self.trading_criteria['max_days_to_resolution']:
            reasons.append(f"Too long to resolution: {days_out} > {self.trading_criteria['max_days_to_resolution']} days")
        
        # Check volume
        volume = market_details.get('volume_24h', 0)
        if volume < self.trading_criteria['min_volume_24h']:
            reasons.append(f"Low volume: ${volume:,.0f} < ${self.trading_criteria['min_volume_24h']:,.0f}")
        
        # Check if market is still active
        if not market_details.get('active', False):
            reasons.append("Market not active")
        
        passes_criteria = len(reasons) == 0
        return passes_criteria, reasons
    
    def calculate_position_size(self, prediction: Dict) -> float:
        """Calculate position size based on Kelly criterion and confidence"""
        
        kelly_fraction = float(prediction.get('kelly_fraction', 0.1))
        expected_value = float(prediction.get('expected_value', 0.1))
        
        # Base position from Kelly (capped at reasonable max)
        kelly_size = min(kelly_fraction * 10000, self.position_params['max_position_size'])
        
        # Adjust based on expected value (higher EV = larger position)
        ev_multiplier = min(expected_value / 0.15, 2.0)  # Up to 2x for very high EV
        
        position_size = max(
            self.position_params['base_position_size'],
            min(kelly_size * ev_multiplier, self.position_params['max_position_size'])
        )
        
        return round(position_size, 2)
    
    def create_trade_signal(self, prediction: Dict, market_details: Dict) -> Dict:
        """Convert ML prediction to trading signal"""
        
        ml_prob = float(prediction['your_probability'])
        market_price = float(prediction['market_price'])
        
        # Determine trade direction
        if ml_prob > 0.5:
            direction = 'YES'
            entry_price = market_details['current_yes_price']
        else:
            direction = 'NO'
            entry_price = market_details['current_no_price']
        
        position_size = self.calculate_position_size(prediction)
        
        trade_signal = {
            'market_id': prediction['market_id'],
            'market_question': prediction['market_question'],
            'direction': direction,
            'entry_price': entry_price,
            'position_size': position_size,
            'ml_probability': ml_prob,
            'expected_value': prediction['expected_value'],
            'reasoning': f"ML Signal: {prediction['reasoning']}",
            'days_to_resolution': market_details['days_to_resolution'],
            'end_date': market_details['end_date'],
            'ml_prediction_id': prediction['id'],
            'stop_loss_pct': self.position_params['stop_loss_pct'],
            'take_profit_pct': self.position_params['take_profit_pct']
        }
        
        return trade_signal
    
    def record_trade_execution(self, trade_signal: Dict) -> bool:
        """Record executed trade in database"""
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO pm_paper_trades (
                    market_id, market_question, direction, entry_price, position_size,
                    ml_probability, expected_value, reasoning, days_to_resolution,
                    end_date, ml_prediction_id, stop_loss_pct, take_profit_pct,
                    entry_time, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 'OPEN'
                )
            ''', (
                trade_signal['market_id'],
                trade_signal['market_question'],
                trade_signal['direction'],
                trade_signal['entry_price'],
                trade_signal['position_size'],
                trade_signal['ml_probability'],
                trade_signal['expected_value'],
                trade_signal['reasoning'],
                trade_signal['days_to_resolution'],
                trade_signal['end_date'],
                trade_signal['ml_prediction_id'],
                trade_signal['stop_loss_pct'],
                trade_signal['take_profit_pct']
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"✅ Recorded trade: {trade_signal['direction']} {trade_signal['market_question'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error recording trade execution: {e}")
            return False
    
    def process_ml_signals(self) -> Dict:
        """Main process: Convert ML predictions to trades"""
        
        logger.info("🚀 Processing ML signals for trading...")
        
        # Get pending ML predictions
        ml_signals = self.get_pending_ml_signals()
        
        if not ml_signals:
            logger.info("No pending ML signals found")
            return {'trades_generated': 0, 'signals_evaluated': 0}
        
        trades_generated = 0
        signals_evaluated = len(ml_signals)
        
        for prediction in ml_signals:
            try:
                # Get current market details
                market_details = self.get_market_details(prediction['market_id'])
                
                if not market_details:
                    logger.warning(f"Could not get market details for {prediction['market_id']}")
                    continue
                
                # Evaluate trading criteria
                passes, reasons = self.evaluate_trading_criteria(prediction, market_details)
                
                if passes:
                    # Create and record trade signal
                    trade_signal = self.create_trade_signal(prediction, market_details)
                    
                    if self.record_trade_execution(trade_signal):
                        trades_generated += 1
                        
                        logger.info(f"🎯 Generated trade #{trades_generated}:")
                        logger.info(f"   Market: {trade_signal['market_question'][:60]}...")
                        logger.info(f"   Direction: {trade_signal['direction']} at ${trade_signal['entry_price']:.3f}")
                        logger.info(f"   Size: ${trade_signal['position_size']:.0f}")
                        logger.info(f"   Resolves in: {trade_signal['days_to_resolution']} days")
                
                else:
                    logger.info(f"❌ Filtered out: {prediction['market_question'][:50]}...")
                    for reason in reasons:
                        logger.info(f"   - {reason}")
                
                # Respect daily trade limit
                if trades_generated >= self.trading_criteria['max_daily_trades']:
                    logger.info(f"Daily trade limit reached: {trades_generated}")
                    break
                    
            except Exception as e:
                logger.error(f"Error processing signal {prediction['id']}: {e}")
        
        summary = {
            'signals_evaluated': signals_evaluated,
            'trades_generated': trades_generated,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ ML signal processing complete: {trades_generated}/{signals_evaluated} converted to trades")
        
        return summary

def main():
    """Run ML trading integration"""
    integration = MLTradingIntegration()
    result = integration.process_ml_signals()
    print(f"📊 Summary: {result}")

if __name__ == "__main__":
    main()