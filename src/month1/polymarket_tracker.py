#!/usr/bin/env python3
"""
Polymarket Tracker - Month 1, Week 1
Market Discovery and Tracking System

This module implements the core market discovery and probability tracking
system for the ML-based Polymarket strategy.
"""

import requests
import json
import psycopg2
import pandas as pd
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/polymarket_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PolymarketTracker:
    """Main class for discovering and tracking Polymarket opportunities"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        # API endpoints
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.clob_api = "https://clob.polymarket.com"
        
        # Database configuration
        self.db_config = db_config or {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
        # Initialize database
        self.init_database()
        
        logger.info("PolymarketTracker initialized successfully")
        
    def init_database(self):
        """Initialize database tables for prediction tracking"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Create predictions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_predictions (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) NOT NULL,
                    market_question TEXT NOT NULL,
                    market_price DECIMAL(5,4) NOT NULL,
                    your_probability DECIMAL(5,4) NOT NULL,
                    expected_value DECIMAL(6,4),
                    reasoning TEXT,
                    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolution_date TIMESTAMP,
                    actual_outcome BOOLEAN,
                    correct_prediction BOOLEAN,
                    category VARCHAR(100),
                    subcategory VARCHAR(100),
                    volume_24h DECIMAL(15,2),
                    days_to_resolution INTEGER
                );
            ''')
            
            # Create market features table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_market_features (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) NOT NULL,
                    volume_24h DECIMAL(15,2),
                    total_volume DECIMAL(15,2),
                    liquidity DECIMAL(15,2),
                    days_to_resolution INTEGER,
                    category VARCHAR(100),
                    subcategory VARCHAR(100),
                    question_length INTEGER,
                    has_image BOOLEAN,
                    created_at TIMESTAMP,
                    feature_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create performance tracking table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_performance_tracking (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    total_predictions INTEGER,
                    correct_predictions INTEGER,
                    accuracy DECIMAL(5,4),
                    positive_ev_trades INTEGER,
                    avg_expected_value DECIMAL(6,4),
                    notes TEXT
                );
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def get_active_markets(self, limit: int = 20) -> List[Dict]:
        """Get highest volume active markets from Gamma API"""
        try:
            url = f"{self.gamma_api}/events"
            params = {
                "limit": limit,
                "order": "volume24hr", 
                "ascending": "false",
                "active": "true"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            events = response.json()
            markets = []
            
            for event in events:
                event_markets = event.get('markets', [])
                for market in event_markets:
                    if market.get('active', False):
                        market_data = self.extract_market_features(market, event)
                        markets.append(market_data)
            
            logger.info(f"Retrieved {len(markets)} active markets")
            return markets[:limit]  # Ensure we don't exceed limit
            
        except Exception as e:
            logger.error(f"Error fetching active markets: {e}")
            return []
    
    def extract_market_features(self, market: Dict, event: Dict) -> Dict:
        """Extract relevant features from market data"""
        try:
            # Calculate days to resolution
            end_date_str = event.get('endDate') or market.get('endDate')
            days_to_resolution = 0
            
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    days_to_resolution = (end_date - now).days
                except:
                    days_to_resolution = 0
            
            return {
                "market_id": market.get("condition_id") or market.get("conditionId"),
                "question": market.get("question", ""),
                "price": float(market.get("price", 0)),
                "volume_24h": float(market.get("volume24hr", 0)),
                "total_volume": float(market.get("volume", 0)),
                "liquidity": float(market.get("liquidityParameter", 0)),
                "category": event.get("category", ""),
                "subcategory": event.get("subcategory", ""),
                "days_to_resolution": max(0, days_to_resolution),
                "question_length": len(market.get("question", "")),
                "has_image": bool(market.get("image")),
                "created_at": market.get("createdAt"),
                "active": market.get("active", False),
                "resolved": market.get("resolved", False)
            }
            
        except Exception as e:
            logger.error(f"Error extracting market features: {e}")
            return {}
    
    def calculate_days_remaining(self, market_data: Dict) -> int:
        """Calculate days remaining until market resolution"""
        return market_data.get('days_to_resolution', 0)
    
    def store_market_features(self, markets: List[Dict]):
        """Store market features in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            for market in markets:
                if not market.get('market_id'):
                    continue
                    
                cur.execute('''
                    INSERT INTO pm_market_features (
                        market_id, volume_24h, total_volume, liquidity,
                        days_to_resolution, category, subcategory,
                        question_length, has_image, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (
                    market['market_id'],
                    market['volume_24h'],
                    market['total_volume'],
                    market['liquidity'],
                    market['days_to_resolution'],
                    market['category'],
                    market['subcategory'],
                    market['question_length'],
                    market['has_image'],
                    market['created_at']
                ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"Stored features for {len(markets)} markets")
            
        except Exception as e:
            logger.error(f"Error storing market features: {e}")
    
    def display_markets_for_assessment(self, markets: List[Dict]) -> List[Dict]:
        """Display markets in a format suitable for manual probability assessment"""
        print("\n" + "="*80)
        print("DAILY MARKET ASSESSMENT - PROBABILITY TRACKING")
        print("="*80)
        
        assessment_markets = []
        
        for i, market in enumerate(markets[:10], 1):  # Limit to 10 for manual assessment
            if not market.get('market_id'):
                continue
                
            print(f"\nMARKET {i}:")
            print(f"Question: {market['question']}")
            print(f"Current Price: {market['price']:.1%}")
            print(f"24h Volume: ${market['volume_24h']:,.0f}")
            print(f"Category: {market['category']} / {market['subcategory']}")
            print(f"Days to Resolution: {market['days_to_resolution']}")
            print(f"Market ID: {market['market_id']}")
            print("-" * 60)
            
            assessment_markets.append(market)
        
        return assessment_markets
    
    def record_prediction(self, market_id: str, market_question: str, 
                         market_price: float, your_probability: float,
                         reasoning: str = "", expected_value: float = None) -> bool:
        """Record a probability prediction in the database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO pm_predictions (
                    market_id, market_question, market_price, your_probability,
                    expected_value, reasoning
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                market_id, market_question, market_price, your_probability,
                expected_value, reasoning
            ))
            
            prediction_id = cur.fetchone()[0]
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"Recorded prediction {prediction_id} for market {market_id[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error recording prediction: {e}")
            return False
    
    def get_prediction_stats(self) -> Dict:
        """Get current prediction statistics"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Total predictions
            cur.execute("SELECT COUNT(*) FROM pm_predictions")
            total_predictions = cur.fetchone()[0]
            
            # Resolved predictions
            cur.execute("SELECT COUNT(*) FROM pm_predictions WHERE actual_outcome IS NOT NULL")
            resolved_predictions = cur.fetchone()[0]
            
            # Accuracy on resolved predictions
            cur.execute('''
                SELECT COUNT(*) FROM pm_predictions 
                WHERE actual_outcome IS NOT NULL AND correct_prediction = true
            ''')
            correct_predictions = cur.fetchone()[0]
            
            accuracy = correct_predictions / resolved_predictions if resolved_predictions > 0 else 0
            
            # Recent predictions (last 7 days)
            cur.execute('''
                SELECT COUNT(*) FROM pm_predictions 
                WHERE prediction_date >= CURRENT_DATE - INTERVAL '7 days'
            ''')
            recent_predictions = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            return {
                'total_predictions': total_predictions,
                'resolved_predictions': resolved_predictions,
                'correct_predictions': correct_predictions,
                'accuracy': accuracy,
                'recent_predictions': recent_predictions
            }
            
        except Exception as e:
            logger.error(f"Error getting prediction stats: {e}")
            return {}
    
    def daily_assessment_workflow(self):
        """Execute the daily market assessment workflow"""
        logger.info("Starting daily assessment workflow")
        
        try:
            # 1. Get active markets
            markets = self.get_active_markets(limit=15)
            
            if not markets:
                logger.warning("No markets retrieved, ending workflow")
                return
            
            # 2. Store market features
            self.store_market_features(markets)
            
            # 3. Display markets for assessment
            assessment_markets = self.display_markets_for_assessment(markets)
            
            # 4. Show current statistics
            stats = self.get_prediction_stats()
            print(f"\n📊 CURRENT STATISTICS:")
            print(f"Total Predictions: {stats.get('total_predictions', 0)}")
            print(f"Resolved: {stats.get('resolved_predictions', 0)}")
            print(f"Accuracy: {stats.get('accuracy', 0):.1%}")
            print(f"Recent (7d): {stats.get('recent_predictions', 0)}")
            
            print(f"\n✅ Daily workflow completed successfully")
            print(f"Retrieved and stored {len(markets)} markets")
            print(f"Ready for manual probability assessment")
            
            return assessment_markets
            
        except Exception as e:
            logger.error(f"Error in daily workflow: {e}")
            return None

def main():
    """Main function for testing the tracker"""
    tracker = PolymarketTracker()
    
    print("🚀 POLYMARKET TRACKER - MONTH 1 WEEK 1")
    print("Testing market discovery and tracking system...")
    
    # Run daily assessment workflow
    markets = tracker.daily_assessment_workflow()
    
    if markets:
        print(f"\n✅ SUCCESS: {len(markets)} markets ready for assessment")
        print("\nNext steps:")
        print("1. Manually assess probability for each market")
        print("2. Record predictions using tracker.record_prediction()")
        print("3. Track accuracy over time")
    else:
        print("\n❌ FAILED: Could not retrieve markets")

if __name__ == "__main__":
    main()