#!/usr/bin/env python3
"""
Resolved Markets Collector - Working Implementation
Collect resolved Polymarket contracts using correct API parameters

Using discovered approach: closed=true&active=false
Resolution outcomes available in outcomePrices field
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
        logging.FileHandler('logs/resolved_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ResolvedMarketsCollector:
    """Collect resolved Polymarket contracts using working API approach"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.gamma_api = "https://gamma-api.polymarket.com"
        
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
        logger.info("Resolved Markets Collector initialized")
        
    def init_database(self):
        """Initialize database tables for resolved market data"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Create resolved markets table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pm_resolved_markets_final (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) UNIQUE NOT NULL,
                    condition_id VARCHAR(100),
                    question TEXT NOT NULL,
                    slug VARCHAR(200),
                    category VARCHAR(100),
                    subcategory VARCHAR(100),
                    
                    -- Market metadata
                    description TEXT,
                    resolution_source TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP,
                    closed_time TIMESTAMP,
                    
                    -- Outcomes and resolution
                    outcomes JSONB,
                    outcome_prices JSONB,
                    resolved_outcome INTEGER, -- 0 or 1 for binary markets
                    winning_outcome TEXT, -- 'Yes' or 'No'
                    
                    -- Volume and liquidity
                    total_volume DECIMAL(15,2),
                    volume_24h DECIMAL(15,2),
                    volume_1w DECIMAL(15,2),
                    volume_1m DECIMAL(15,2),
                    liquidity DECIMAL(15,2),
                    open_interest DECIMAL(15,2),
                    
                    -- Market characteristics
                    question_length INTEGER,
                    has_image BOOLEAN,
                    market_maker_address VARCHAR(100),
                    clob_token_ids JSONB,
                    
                    -- Trading data
                    best_bid DECIMAL(8,6),
                    best_ask DECIMAL(8,6),
                    last_trade_price DECIMAL(8,6),
                    spread DECIMAL(8,6),
                    
                    -- Fees and risk
                    maker_base_fee INTEGER,
                    taker_base_fee INTEGER,
                    neg_risk BOOLEAN DEFAULT FALSE,
                    
                    -- Collection metadata
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_quality_score INTEGER DEFAULT 0,
                    
                    -- Tags and categorization
                    tags JSONB,
                    
                    -- Price change indicators
                    one_day_price_change DECIMAL(8,6),
                    one_hour_price_change DECIMAL(8,6),
                    one_week_price_change DECIMAL(8,6),
                    one_month_price_change DECIMAL(8,6),
                    one_year_price_change DECIMAL(8,6)
                );
            ''')
            
            # Create index for fast lookups
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_pm_resolved_markets_condition_id 
                ON pm_resolved_markets_final(condition_id)
            ''')
            
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_pm_resolved_markets_category 
                ON pm_resolved_markets_final(category)
            ''')
            
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_pm_resolved_markets_resolved_outcome 
                ON pm_resolved_markets_final(resolved_outcome)
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("Resolved markets database initialized")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def get_resolved_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get resolved markets using correct API parameters"""
        try:
            url = f"{self.gamma_api}/markets"
            params = {
                "closed": "true",
                "active": "false",  # Key parameters discovered
                "limit": limit,
                "offset": offset,
                "order": "endDate",
                "ascending": "false"  # Most recent first
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            markets = response.json()
            logger.info(f"Retrieved {len(markets)} resolved markets (offset {offset})")
            
            time.sleep(self.request_delay)  # Rate limiting
            return markets
            
        except Exception as e:
            logger.error(f"Error fetching resolved markets: {e}")
            return []
    
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
    
    def determine_resolution_outcome(self, market: Dict) -> Tuple[Optional[int], Optional[str]]:
        """Determine resolution outcome from outcomePrices"""
        try:
            outcome_prices_raw = market.get('outcomePrices', [])
            outcomes_raw = market.get('outcomes', [])
            
            if not outcome_prices_raw or not outcomes_raw:
                return None, None
            
            # Parse JSON strings if needed
            if isinstance(outcome_prices_raw, str):
                outcome_prices = json.loads(outcome_prices_raw)
            else:
                outcome_prices = outcome_prices_raw
                
            if isinstance(outcomes_raw, str):
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
            
            if not outcome_prices or not outcomes:
                return None, None
            
            # Convert prices to floats
            prices = [float(price) for price in outcome_prices]
            
            # Find the winning outcome (price closest to 1.0)
            if len(prices) == 2:  # Binary market
                if prices[0] > 0.99:  # First outcome won (Yes)
                    return 1, outcomes[0] if len(outcomes) > 0 else "Yes"
                elif prices[1] > 0.99:  # Second outcome won (No)
                    return 0, outcomes[1] if len(outcomes) > 1 else "No"
                elif prices[0] < 0.01:  # First outcome lost
                    return 0, outcomes[1] if len(outcomes) > 1 else "No"
                elif prices[1] < 0.01:  # Second outcome lost  
                    return 1, outcomes[0] if len(outcomes) > 0 else "Yes"
            
            # For multi-outcome markets, find highest price
            if len(prices) > 2:
                max_price_idx = prices.index(max(prices))
                if prices[max_price_idx] > 0.9:  # Clear winner
                    return max_price_idx, outcomes[max_price_idx] if len(outcomes) > max_price_idx else f"Outcome_{max_price_idx}"
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error determining resolution: {e}")
            return None, None
    
    def extract_resolved_market_data(self, market: Dict) -> Optional[Dict]:
        """Extract comprehensive data from a resolved market"""
        try:
            # Basic validation
            market_id = market.get('id')
            condition_id = market.get('conditionId')
            question = market.get('question')
            
            if not market_id or not question:
                return None
            
            # Check if actually resolved
            outcome_prices = market.get('outcomePrices', [])
            if not outcome_prices:
                return None
            
            # Determine resolution outcome
            resolved_outcome, winning_outcome = self.determine_resolution_outcome(market)
            if resolved_outcome is None:
                logger.debug(f"Could not determine outcome for market: {question[:50]}...")
                return None
            
            # Parse timestamps
            start_date = self.parse_timestamp(market.get('startDate'))
            end_date = self.parse_timestamp(market.get('endDate'))
            created_at = self.parse_timestamp(market.get('createdAt'))
            closed_time = self.parse_timestamp(market.get('closedTime'))
            
            # Extract numeric values safely
            def safe_float(value, default=0.0):
                try:
                    return float(value) if value is not None else default
                except:
                    return default
            
            def safe_int(value, default=0):
                try:
                    return int(value) if value is not None else default
                except:
                    return default
            
            return {
                'market_id': market_id,
                'condition_id': condition_id,
                'question': question,
                'slug': market.get('slug'),
                'category': market.get('category'),
                'subcategory': market.get('subcategory'),
                
                # Market metadata
                'description': market.get('description'),
                'resolution_source': market.get('resolutionSource'),
                'start_date': start_date,
                'end_date': end_date,
                'created_at': created_at,
                'closed_time': closed_time,
                
                # Outcomes and resolution
                'outcomes': json.dumps(market.get('outcomes', [])),
                'outcome_prices': json.dumps(outcome_prices),
                'resolved_outcome': resolved_outcome,
                'winning_outcome': winning_outcome,
                
                # Volume and liquidity
                'total_volume': safe_float(market.get('volume')),
                'volume_24h': safe_float(market.get('volume24hr')),
                'volume_1w': safe_float(market.get('volume1wk')),
                'volume_1m': safe_float(market.get('volume1mo')),
                'liquidity': safe_float(market.get('liquidity')),
                'open_interest': safe_float(market.get('openInterest')),
                
                # Market characteristics
                'question_length': len(question),
                'has_image': bool(market.get('image')),
                'market_maker_address': market.get('marketMakerAddress'),
                'clob_token_ids': json.dumps(market.get('clobTokenIds', [])),
                
                # Trading data
                'best_bid': safe_float(market.get('bestBid')),
                'best_ask': safe_float(market.get('bestAsk')),
                'last_trade_price': safe_float(market.get('lastTradePrice')),
                'spread': safe_float(market.get('spread')),
                
                # Fees and risk
                'maker_base_fee': safe_int(market.get('makerBaseFee')),
                'taker_base_fee': safe_int(market.get('takerBaseFee')),
                'neg_risk': bool(market.get('negRisk', False)),
                
                # Tags
                'tags': json.dumps(market.get('tags', [])),
                
                # Price changes
                'one_day_price_change': safe_float(market.get('oneDayPriceChange')),
                'one_hour_price_change': safe_float(market.get('oneHourPriceChange')),
                'one_week_price_change': safe_float(market.get('oneWeekPriceChange')),
                'one_month_price_change': safe_float(market.get('oneMonthPriceChange')),
                'one_year_price_change': safe_float(market.get('oneYearPriceChange'))
            }
            
        except Exception as e:
            logger.error(f"Error extracting market data: {e}")
            return None
    
    def calculate_quality_score(self, market_data: Dict) -> int:
        """Calculate data quality score 0-100"""
        score = 0
        
        # Basic data completeness (40 points)
        if market_data.get('question'): score += 10
        if market_data.get('resolved_outcome') is not None: score += 20
        if market_data.get('category'): score += 10
        
        # Volume and liquidity (30 points)
        volume = market_data.get('total_volume', 0)
        if volume > 1000: score += 10
        if volume > 10000: score += 10
        if market_data.get('liquidity', 0) > 0: score += 10
        
        # Time data (20 points)
        if market_data.get('start_date'): score += 5
        if market_data.get('end_date'): score += 5
        if market_data.get('created_at'): score += 5
        if market_data.get('closed_time'): score += 5
        
        # Trading activity (10 points)
        if market_data.get('last_trade_price', 0) > 0: score += 5
        if market_data.get('open_interest', 0) > 0: score += 5
        
        return min(score, 100)
    
    def store_resolved_markets(self, markets_data: List[Dict]) -> int:
        """Store resolved markets in database"""
        stored_count = 0
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            for market_data in markets_data:
                if not market_data:
                    continue
                
                # Calculate quality score
                market_data['data_quality_score'] = self.calculate_quality_score(market_data)
                
                try:
                    # Use ON CONFLICT to handle duplicates
                    cur.execute('''
                        INSERT INTO pm_resolved_markets_final (
                            market_id, condition_id, question, slug, category, subcategory,
                            description, resolution_source, start_date, end_date, created_at, closed_time,
                            outcomes, outcome_prices, resolved_outcome, winning_outcome,
                            total_volume, volume_24h, volume_1w, volume_1m, liquidity, open_interest,
                            question_length, has_image, market_maker_address, clob_token_ids,
                            best_bid, best_ask, last_trade_price, spread,
                            maker_base_fee, taker_base_fee, neg_risk, tags,
                            one_day_price_change, one_hour_price_change, one_week_price_change,
                            one_month_price_change, one_year_price_change, data_quality_score
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (market_id) DO NOTHING
                        RETURNING id
                    ''', (
                        market_data['market_id'], market_data['condition_id'], market_data['question'],
                        market_data['slug'], market_data['category'], market_data['subcategory'],
                        market_data['description'], market_data['resolution_source'],
                        market_data['start_date'], market_data['end_date'], market_data['created_at'],
                        market_data['closed_time'], market_data['outcomes'], market_data['outcome_prices'],
                        market_data['resolved_outcome'], market_data['winning_outcome'],
                        market_data['total_volume'], market_data['volume_24h'], market_data['volume_1w'],
                        market_data['volume_1m'], market_data['liquidity'], market_data['open_interest'],
                        market_data['question_length'], market_data['has_image'],
                        market_data['market_maker_address'], market_data['clob_token_ids'],
                        market_data['best_bid'], market_data['best_ask'], market_data['last_trade_price'],
                        market_data['spread'], market_data['maker_base_fee'], market_data['taker_base_fee'],
                        market_data['neg_risk'], market_data['tags'], market_data['one_day_price_change'],
                        market_data['one_hour_price_change'], market_data['one_week_price_change'],
                        market_data['one_month_price_change'], market_data['one_year_price_change'],
                        market_data['data_quality_score']
                    ))
                    
                    if cur.fetchone():
                        stored_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to store market {market_data.get('market_id', 'unknown')}: {e}")
                    continue
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"Stored {stored_count} resolved markets")
            return stored_count
            
        except Exception as e:
            logger.error(f"Database storage error: {e}")
            return 0
    
    def collect_batch(self, batch_size: int = 100, max_batches: int = 10) -> Dict:
        """Collect a batch of resolved markets"""
        
        batch_id = f"resolved_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        logger.info(f"Starting resolved markets collection: {batch_id}")
        
        total_attempted = 0
        total_collected = 0
        total_resolved = 0
        
        for batch_num in range(max_batches):
            offset = batch_num * batch_size
            logger.info(f"Collecting batch {batch_num + 1}/{max_batches} (offset {offset})")
            
            # Get resolved markets
            markets = self.get_resolved_markets(limit=batch_size, offset=offset)
            
            if not markets:
                logger.warning(f"No markets returned for batch {batch_num + 1}")
                break
            
            # Extract and validate market data
            batch_resolved_data = []
            
            for market in markets:
                total_attempted += 1
                
                market_data = self.extract_resolved_market_data(market)
                if market_data:
                    batch_resolved_data.append(market_data)
                    total_resolved += 1
            
            # Store batch
            stored_count = self.store_resolved_markets(batch_resolved_data)
            total_collected += stored_count
            
            logger.info(f"Batch {batch_num + 1}: {total_resolved} extracted, {stored_count} stored")
            
            # Rate limiting between batches
            time.sleep(1)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'batch_id': batch_id,
            'duration_seconds': duration,
            'markets_attempted': total_attempted,
            'markets_resolved': total_resolved,
            'markets_stored': total_collected,
            'resolution_rate': (total_resolved / total_attempted * 100) if total_attempted > 0 else 0,
            'storage_rate': (total_collected / total_resolved * 100) if total_resolved > 0 else 0
        }
        
        logger.info(f"Collection complete: {total_collected}/{total_resolved}/{total_attempted} stored/resolved/attempted")
        
        return result
    
    def get_collection_stats(self) -> Dict:
        """Get current collection statistics"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Total markets
            cur.execute("SELECT COUNT(*) FROM pm_resolved_markets_final")
            total_markets = cur.fetchone()[0]
            
            # By resolution outcome
            cur.execute('''
                SELECT resolved_outcome, COUNT(*) as count 
                FROM pm_resolved_markets_final 
                GROUP BY resolved_outcome 
                ORDER BY resolved_outcome
            ''')
            outcome_breakdown = cur.fetchall()
            
            # By category
            cur.execute('''
                SELECT category, COUNT(*) as count 
                FROM pm_resolved_markets_final 
                GROUP BY category 
                ORDER BY count DESC
                LIMIT 10
            ''')
            category_breakdown = cur.fetchall()
            
            # Quality distribution
            cur.execute('''
                SELECT 
                    AVG(data_quality_score) as avg_quality,
                    MIN(data_quality_score) as min_quality,
                    MAX(data_quality_score) as max_quality
                FROM pm_resolved_markets_final
            ''')
            quality_stats = cur.fetchone()
            
            # Volume statistics
            cur.execute('''
                SELECT 
                    SUM(total_volume) as total_volume,
                    AVG(total_volume) as avg_volume,
                    MAX(total_volume) as max_volume
                FROM pm_resolved_markets_final
                WHERE total_volume > 0
            ''')
            volume_stats = cur.fetchone()
            
            cur.close()
            conn.close()
            
            return {
                'total_markets': total_markets,
                'outcome_breakdown': dict(outcome_breakdown),
                'category_breakdown': dict(category_breakdown),
                'avg_quality_score': float(quality_stats[0]) if quality_stats[0] else 0,
                'quality_range': (float(quality_stats[1]) if quality_stats[1] else 0, 
                                float(quality_stats[2]) if quality_stats[2] else 0),
                'total_volume': float(volume_stats[0]) if volume_stats[0] else 0,
                'avg_volume': float(volume_stats[1]) if volume_stats[1] else 0,
                'max_volume': float(volume_stats[2]) if volume_stats[2] else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}

def main():
    """Main execution for resolved markets collection"""
    print("📊 RESOLVED MARKETS COLLECTOR - WORKING IMPLEMENTATION")
    print("Using discovered API approach: closed=true&active=false")
    
    collector = ResolvedMarketsCollector()
    
    # Initial collection stats
    initial_stats = collector.get_collection_stats()
    print(f"\nCurrent collection: {initial_stats.get('total_markets', 0)} resolved markets")
    
    if initial_stats.get('total_markets', 0) < 500:
        print("🚀 Starting collection to reach 500+ resolved markets target...")
        
        # Collect in batches until we have 500+ markets
        target_markets = 500
        current_count = initial_stats.get('total_markets', 0)
        
        while current_count < target_markets:
            needed = target_markets - current_count
            batches_needed = min(5, (needed // 80) + 1)  # ~80 resolved per batch
            
            print(f"\nCollecting {batches_needed} batches (need {needed} more resolved markets)...")
            
            result = collector.collect_batch(
                batch_size=100, 
                max_batches=batches_needed
            )
            
            print(f"✅ Batch completed:")
            print(f"   Attempted: {result['markets_attempted']}")
            print(f"   Resolved: {result['markets_resolved']} ({result['resolution_rate']:.1f}%)")
            print(f"   Stored: {result['markets_stored']} ({result['storage_rate']:.1f}%)")
            
            # Update count
            current_stats = collector.get_collection_stats()
            current_count = current_stats.get('total_markets', 0)
            
            print(f"📊 Progress: {current_count}/{target_markets} resolved markets collected")
            
            if current_count >= target_markets:
                break
    
    # Final statistics
    final_stats = collector.get_collection_stats()
    print(f"\n🎉 COLLECTION COMPLETE!")
    print(f"Total Resolved Markets: {final_stats.get('total_markets', 0)}")
    print(f"Resolution Outcomes: {final_stats.get('outcome_breakdown', {})}")
    print(f"Average Quality: {final_stats.get('avg_quality_score', 0):.1f}/100")
    print(f"Total Volume: ${final_stats.get('total_volume', 0):,.0f}")
    
    print(f"\nTop Categories:")
    for category, count in list(final_stats.get('category_breakdown', {}).items())[:5]:
        print(f"  - {category}: {count} markets")
    
    print(f"\n✅ Ready for ML model training!")

if __name__ == "__main__":
    main()