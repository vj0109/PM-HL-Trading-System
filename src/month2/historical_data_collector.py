#!/usr/bin/env python3
"""
Historical Data Collector - Accelerated Month 2 Start
Collect 500+ resolved markets with outcomes for ML training

This module collects resolved Polymarket contracts with final outcomes
for machine learning model training. Starting immediately in parallel
with daily predictions to accelerate development.
"""

import requests
import json
import psycopg2
import pandas as pd
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
import time
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../../logs/historical_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """Collect resolved Polymarket contracts for ML training"""
    
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
        
        # Rate limiting
        self.request_delay = 0.5  # 500ms between requests
        
        self.init_database()
        logger.info("Historical Data Collector initialized")
        
    def init_database(self):
        """Initialize database tables for historical market data"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Create resolved markets table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_resolved_markets (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) UNIQUE NOT NULL,
                    question TEXT NOT NULL,
                    category VARCHAR(100),
                    subcategory VARCHAR(100),
                    
                    -- Price features
                    final_price DECIMAL(5,4),
                    starting_price DECIMAL(5,4),
                    
                    -- Volume features  
                    total_volume DECIMAL(15,2),
                    volume_24h_before_resolution DECIMAL(15,2),
                    liquidity DECIMAL(15,2),
                    
                    -- Time features
                    created_at TIMESTAMP,
                    end_date TIMESTAMP,
                    resolved_at TIMESTAMP,
                    days_active INTEGER,
                    days_to_resolution_at_creation INTEGER,
                    
                    -- Outcome (target variable)
                    resolved_outcome INTEGER, -- 1 for YES, 0 for NO
                    winner VARCHAR(10), -- 'Yes' or 'No'
                    
                    -- Market characteristics
                    question_length INTEGER,
                    has_image BOOLEAN,
                    market_maker VARCHAR(100),
                    
                    -- Collection metadata
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_quality_score INTEGER DEFAULT 0 -- 0-100 quality score
                );
            ''')
            
            # Create feature engineering table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_engineered_features (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) NOT NULL,
                    
                    -- Engineered features (38 total)
                    price_movement DECIMAL(6,4), -- final_price - starting_price
                    price_volatility DECIMAL(6,4), -- calculated if price history available
                    volume_momentum DECIMAL(10,4), -- 24h volume / total volume
                    liquidity_ratio DECIMAL(6,4), -- liquidity / total volume
                    
                    -- Time features
                    market_duration_days INTEGER,
                    resolution_speed_days INTEGER,
                    created_month INTEGER,
                    created_day_of_week INTEGER,
                    
                    -- Text features
                    question_complexity DECIMAL(4,2), -- readability score
                    has_numbers BOOLEAN,
                    has_dates BOOLEAN,
                    question_sentiment DECIMAL(4,2), -- -1 to 1
                    
                    -- Category features (one-hot encoded)
                    category_politics BOOLEAN DEFAULT FALSE,
                    category_sports BOOLEAN DEFAULT FALSE,
                    category_crypto BOOLEAN DEFAULT FALSE,
                    category_economics BOOLEAN DEFAULT FALSE,
                    category_science BOOLEAN DEFAULT FALSE,
                    category_entertainment BOOLEAN DEFAULT FALSE,
                    category_other BOOLEAN DEFAULT FALSE,
                    
                    -- Market dynamics
                    early_adoption_score DECIMAL(4,2), -- volume in first 24h / total
                    late_surge_indicator BOOLEAN, -- high volume near resolution
                    
                    -- Base rates for category
                    category_base_rate DECIMAL(4,2), -- historical YES rate for category
                    
                    -- Feature engineering timestamp
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create collection progress table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_collection_progress (
                    id SERIAL PRIMARY KEY,
                    collection_batch VARCHAR(50),
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    markets_attempted INTEGER,
                    markets_collected INTEGER,
                    success_rate DECIMAL(5,2),
                    notes TEXT
                );
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("Historical data database initialized")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def get_resolved_events(self, limit: int = 200, offset: int = 0) -> List[Dict]:
        """Get resolved events from Gamma API"""
        try:
            url = f"{self.gamma_api}/events"
            params = {
                "closed": "true",
                "limit": limit,
                "offset": offset,
                "order": "endDate",
                "ascending": "false"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            events = response.json()
            logger.info(f"Retrieved {len(events)} resolved events (offset {offset})")
            
            time.sleep(self.request_delay)  # Rate limiting
            return events
            
        except Exception as e:
            logger.error(f"Error fetching resolved events: {e}")
            return []
    
    def extract_resolved_market_data(self, market: Dict, event: Dict) -> Optional[Dict]:
        """Extract comprehensive data from a resolved market"""
        try:
            # Check if market is actually resolved
            if not market.get('resolved', False):
                return None
                
            # Extract basic info
            market_id = market.get('condition_id') or market.get('conditionId')
            if not market_id:
                return None
            
            question = market.get('question', '')
            if not question:
                return None
            
            # Determine outcome
            winner = market.get('winner')
            if winner not in ['Yes', 'No']:
                logger.debug(f"Skipping market with unclear winner: {winner}")
                return None
            
            resolved_outcome = 1 if winner == 'Yes' else 0
            
            # Extract time information
            created_at = self.parse_timestamp(market.get('createdAt'))
            end_date = self.parse_timestamp(event.get('endDate') or market.get('endDate'))
            resolved_at = self.parse_timestamp(market.get('resolvedAt'))
            
            # Calculate time features
            days_active = 0
            days_to_resolution_at_creation = 0
            
            if created_at and resolved_at:
                days_active = (resolved_at - created_at).days
            
            if created_at and end_date:
                days_to_resolution_at_creation = (end_date - created_at).days
            
            return {
                'market_id': market_id,
                'question': question,
                'category': event.get('category', ''),
                'subcategory': event.get('subcategory', ''),
                
                # Price features
                'final_price': float(market.get('price', 0)),
                'starting_price': 0.5,  # Default assumption, could be improved
                
                # Volume features
                'total_volume': float(market.get('volume', 0)),
                'volume_24h_before_resolution': float(market.get('volume24hr', 0)),
                'liquidity': float(market.get('liquidityParameter', 0)),
                
                # Time features
                'created_at': created_at,
                'end_date': end_date,
                'resolved_at': resolved_at,
                'days_active': max(0, days_active),
                'days_to_resolution_at_creation': max(0, days_to_resolution_at_creation),
                
                # Outcome
                'resolved_outcome': resolved_outcome,
                'winner': winner,
                
                # Market characteristics
                'question_length': len(question),
                'has_image': bool(market.get('image')),
                'market_maker': market.get('marketMaker', '')
            }
            
        except Exception as e:
            logger.error(f"Error extracting market data: {e}")
            return None
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        
        try:
            # Handle different timestamp formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            return datetime.fromisoformat(timestamp_str)
        except:
            return None
    
    def store_resolved_markets(self, markets: List[Dict]) -> int:
        """Store resolved markets in database"""
        stored_count = 0
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            for market in markets:
                if not market:
                    continue
                    
                try:
                    cur.execute('''
                        INSERT INTO pm_resolved_markets (
                            market_id, question, category, subcategory,
                            final_price, starting_price, total_volume, 
                            volume_24h_before_resolution, liquidity,
                            created_at, end_date, resolved_at,
                            days_active, days_to_resolution_at_creation,
                            resolved_outcome, winner, question_length,
                            has_image, market_maker, data_quality_score
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                            %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (market_id) DO NOTHING
                        RETURNING id
                    ''', (
                        market['market_id'], market['question'], 
                        market['category'], market['subcategory'],
                        market['final_price'], market['starting_price'],
                        market['total_volume'], market['volume_24h_before_resolution'],
                        market['liquidity'], market['created_at'],
                        market['end_date'], market['resolved_at'],
                        market['days_active'], market['days_to_resolution_at_creation'],
                        market['resolved_outcome'], market['winner'],
                        market['question_length'], market['has_image'],
                        market['market_maker'], self.calculate_quality_score(market)
                    ))
                    
                    if cur.fetchone():
                        stored_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to store market {market.get('market_id', 'unknown')}: {e}")
                    continue
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"Stored {stored_count} resolved markets")
            return stored_count
            
        except Exception as e:
            logger.error(f"Database storage error: {e}")
            return 0
    
    def calculate_quality_score(self, market: Dict) -> int:
        """Calculate data quality score 0-100"""
        score = 0
        
        # Basic data completeness (40 points)
        if market.get('question'): score += 10
        if market.get('final_price') is not None: score += 10
        if market.get('total_volume', 0) > 0: score += 10
        if market.get('resolved_outcome') is not None: score += 10
        
        # Time data quality (30 points)
        if market.get('created_at'): score += 10
        if market.get('resolved_at'): score += 10
        if market.get('days_active', 0) > 0: score += 10
        
        # Market significance (30 points)
        volume = market.get('total_volume', 0)
        if volume > 1000: score += 10
        if volume > 10000: score += 10
        if market.get('days_active', 0) > 1: score += 10
        
        return min(score, 100)
    
    def collect_batch(self, batch_size: int = 200, max_batches: int = 5) -> Dict:
        """Collect a batch of resolved markets"""
        
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        logger.info(f"Starting collection batch: {batch_id}")
        
        total_attempted = 0
        total_collected = 0
        
        for batch_num in range(max_batches):
            offset = batch_num * batch_size
            logger.info(f"Collecting batch {batch_num + 1}/{max_batches} (offset {offset})")
            
            # Get resolved events
            events = self.get_resolved_events(limit=batch_size, offset=offset)
            
            if not events:
                logger.warning(f"No events returned for batch {batch_num + 1}")
                break
            
            # Extract markets from events
            batch_markets = []
            
            for event in events:
                markets = event.get('markets', [])
                
                for market in markets:
                    total_attempted += 1
                    
                    market_data = self.extract_resolved_market_data(market, event)
                    if market_data:
                        batch_markets.append(market_data)
            
            # Store batch
            stored_count = self.store_resolved_markets(batch_markets)
            total_collected += stored_count
            
            logger.info(f"Batch {batch_num + 1}: {stored_count} markets stored")
            
            # Rate limiting between batches
            time.sleep(1)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        success_rate = (total_collected / total_attempted * 100) if total_attempted > 0 else 0
        
        # Record collection progress
        self.record_collection_progress(
            batch_id, start_time, end_time, 
            total_attempted, total_collected, success_rate
        )
        
        logger.info(f"Collection complete: {total_collected}/{total_attempted} markets ({success_rate:.1f}%)")
        
        return {
            'batch_id': batch_id,
            'duration_seconds': duration,
            'markets_attempted': total_attempted,
            'markets_collected': total_collected,
            'success_rate': success_rate
        }
    
    def record_collection_progress(self, batch_id: str, start_time: datetime,
                                 end_time: datetime, attempted: int, 
                                 collected: int, success_rate: float):
        """Record collection progress in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO pm_collection_progress (
                    collection_batch, start_time, end_time,
                    markets_attempted, markets_collected, success_rate,
                    notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                batch_id, start_time, end_time,
                attempted, collected, success_rate,
                f"Automated collection - {collected} markets stored"
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record progress: {e}")
    
    def get_collection_stats(self) -> Dict:
        """Get current collection statistics"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Total markets
            cur.execute("SELECT COUNT(*) FROM pm_resolved_markets")
            total_markets = cur.fetchone()[0]
            
            # By category
            cur.execute('''
                SELECT category, COUNT(*) as count 
                FROM pm_resolved_markets 
                GROUP BY category 
                ORDER BY count DESC
            ''')
            category_breakdown = cur.fetchall()
            
            # Quality distribution
            cur.execute('''
                SELECT 
                    AVG(data_quality_score) as avg_quality,
                    MIN(data_quality_score) as min_quality,
                    MAX(data_quality_score) as max_quality
                FROM pm_resolved_markets
            ''')
            quality_stats = cur.fetchone()
            
            # Recent collection activity
            cur.execute('''
                SELECT COUNT(*) FROM pm_resolved_markets 
                WHERE collected_at >= CURRENT_DATE - INTERVAL '1 day'
            ''')
            recent_collections = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            return {
                'total_markets': total_markets,
                'category_breakdown': dict(category_breakdown),
                'avg_quality_score': float(quality_stats[0]) if quality_stats[0] else 0,
                'quality_range': (float(quality_stats[1]) if quality_stats[1] else 0, 
                                float(quality_stats[2]) if quality_stats[2] else 0),
                'recent_collections': recent_collections
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}

def main():
    """Main execution for historical data collection"""
    print("📊 HISTORICAL DATA COLLECTOR - ACCELERATED START")
    print("Collecting 500+ resolved markets for ML training...")
    
    collector = HistoricalDataCollector()
    
    # Initial collection stats
    initial_stats = collector.get_collection_stats()
    print(f"\nCurrent collection: {initial_stats.get('total_markets', 0)} markets")
    
    if initial_stats.get('total_markets', 0) < 500:
        print("🚀 Starting collection to reach 500+ markets target...")
        
        # Collect in batches until we have 500+ markets
        target_markets = 500
        current_count = initial_stats.get('total_markets', 0)
        
        while current_count < target_markets:
            needed = target_markets - current_count
            batches_needed = min(3, (needed // 100) + 1)  # ~100 markets per batch
            
            print(f"\nCollecting {batches_needed} batches (need {needed} more markets)...")
            
            result = collector.collect_batch(
                batch_size=200, 
                max_batches=batches_needed
            )
            
            print(f"✅ Batch completed: {result['markets_collected']} markets added")
            
            # Update count
            current_stats = collector.get_collection_stats()
            current_count = current_stats.get('total_markets', 0)
            
            print(f"📊 Progress: {current_count}/{target_markets} markets collected")
    
    # Final statistics
    final_stats = collector.get_collection_stats()
    print(f"\n🎉 COLLECTION COMPLETE!")
    print(f"Total Markets: {final_stats.get('total_markets', 0)}")
    print(f"Average Quality: {final_stats.get('avg_quality_score', 0):.1f}/100")
    print(f"Categories: {len(final_stats.get('category_breakdown', {}))}")
    
    for category, count in final_stats.get('category_breakdown', {}).items():
        print(f"  - {category}: {count} markets")

if __name__ == "__main__":
    main()