#!/usr/bin/env python3
"""
FIXED POLYMARKET API - Using Correct Endpoints
Following VJ's API reference requirements for <30 day markets
"""

import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PolymarketAPIFixed:
    """Fixed Polymarket API using correct endpoints from documentation"""
    
    def __init__(self):
        # Updated API endpoints per VJ's documentation links
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.clob_api = "https://clob.polymarket.com"
        
    def get_simplified_markets(self, limit=100, active_only=True) -> List[Dict]:
        """Get markets using simplified markets endpoint"""
        
        try:
            # Use simplified markets endpoint
            params = {
                'limit': limit,
                'archived': 'false'
            }
            
            if active_only:
                params['active'] = 'true'
            
            response = requests.get(
                f"{self.gamma_api}/simplified-markets", 
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Simplified markets API error: {response.status_code}")
                return []
                
            markets_data = response.json()
            logger.info(f"Retrieved {len(markets_data)} markets from simplified API")
            
            return markets_data
            
        except Exception as e:
            logger.error(f"Error getting simplified markets: {e}")
            return []
    
    def get_markets_by_date_range(self, days_ahead=30) -> List[Dict]:
        """Get markets resolving within specified days using markets endpoint"""
        
        try:
            # Get current time and future cutoff
            now = datetime.now(timezone.utc)
            cutoff_date = now + timedelta(days=days_ahead)
            
            # Use markets endpoint with date filtering
            params = {
                'limit': 100,
                'archived': 'false',
                'active': 'true',
                'order': 'volume24hr',
                'order_direction': 'desc'
            }
            
            response = requests.get(
                f"{self.gamma_api}/markets",
                params=params, 
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Markets API error: {response.status_code}")
                return []
            
            all_markets = response.json()
            
            # Filter by resolution date
            filtered_markets = []
            for market in all_markets:
                end_date_str = market.get('endDate')
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        days_to_resolution = (end_date - now).days
                        
                        if 1 <= days_to_resolution <= days_ahead:
                            market['days_to_resolution'] = days_to_resolution
                            filtered_markets.append(market)
                            
                    except (ValueError, TypeError):
                        continue
            
            logger.info(f"Found {len(filtered_markets)} markets resolving within {days_ahead} days")
            return filtered_markets
            
        except Exception as e:
            logger.error(f"Error getting markets by date range: {e}")
            return []
    
    def get_events_with_markets(self, limit=50) -> List[Dict]:
        """Get events and their markets using events endpoint"""
        
        try:
            params = {
                'limit': limit,
                'archived': 'false',
                'order': 'volume24hr',
                'order_direction': 'desc'
            }
            
            response = requests.get(
                f"{self.gamma_api}/events",
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Events API error: {response.status_code}")
                return []
            
            events = response.json()
            all_markets = []
            
            now = datetime.now(timezone.utc)
            
            for event in events:
                event_markets = event.get('markets', [])
                for market in event_markets:
                    if market.get('active', False):
                        # Add event context
                        market['event_title'] = event.get('title', '')
                        market['event_id'] = event.get('id', '')
                        
                        # Calculate days to resolution
                        end_date_str = market.get('endDate')
                        if end_date_str:
                            try:
                                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                market['days_to_resolution'] = (end_date - now).days
                            except (ValueError, TypeError):
                                market['days_to_resolution'] = 999
                        else:
                            market['days_to_resolution'] = 999
                        
                        all_markets.append(market)
            
            logger.info(f"Retrieved {len(all_markets)} markets from events API")
            return all_markets
            
        except Exception as e:
            logger.error(f"Error getting events with markets: {e}")
            return []
    
    def extract_market_data(self, market: Dict) -> Optional[Dict]:
        """Extract standardized market data from any API response"""
        
        try:
            # Get basic market info
            market_id = market.get('conditionId') or market.get('condition_id') or market.get('id', '')
            question = market.get('question', '')
            
            if not market_id or not question:
                return None
            
            # Get pricing info
            outcome_prices = market.get('outcomePrices', ['0.5', '0.5'])
            if isinstance(outcome_prices, str):
                outcome_prices = json.loads(outcome_prices)
            
            current_price = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5
            
            # Get volume info  
            volume_24h = float(market.get('volume24hr', 0))
            total_volume = float(market.get('volume', 0))
            
            # Get resolution timing
            days_to_resolution = market.get('days_to_resolution', 999)
            if days_to_resolution == 999:
                end_date_str = market.get('endDate')
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        days_to_resolution = (end_date - now).days
                    except (ValueError, TypeError):
                        days_to_resolution = 999
            
            # Get category info
            category = (market.get('category', '') or 
                       market.get('event_title', '') or
                       market.get('tags', [''])[0] if market.get('tags') else '')
            
            return {
                'market_id': market_id,
                'question': question,
                'current_price': current_price,
                'volume_24h': volume_24h,
                'total_volume': total_volume,
                'days_to_resolution': max(0, days_to_resolution),
                'category': category,
                'market_cap': float(market.get('liquidityParameter', 0)),
                'active': market.get('active', True),
                'end_date': market.get('endDate', '')
            }
            
        except Exception as e:
            logger.error(f"Error extracting market data: {e}")
            return None
    
    def find_short_term_markets(self, max_days=30, min_volume=100) -> List[Dict]:
        """Find markets resolving within max_days with sufficient volume"""
        
        logger.info(f"🔍 Searching for markets resolving within {max_days} days...")
        
        # Try multiple API approaches to find short-term markets
        all_markets = []
        
        # Approach 1: Markets endpoint with date filtering
        markets_api = self.get_markets_by_date_range(max_days)
        all_markets.extend(markets_api)
        
        # Approach 2: Events endpoint
        events_markets = self.get_events_with_markets(100)
        for market in events_markets:
            if market.get('days_to_resolution', 999) <= max_days:
                all_markets.append(market)
        
        # Approach 3: Simplified markets endpoint 
        simple_markets = self.get_simplified_markets(200)
        now = datetime.now(timezone.utc)
        
        for market in simple_markets:
            end_date_str = market.get('endDate')
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    days_out = (end_date - now).days
                    if 1 <= days_out <= max_days:
                        market['days_to_resolution'] = days_out
                        all_markets.append(market)
                except (ValueError, TypeError):
                    continue
        
        # Remove duplicates and extract standardized data
        unique_markets = {}
        processed_markets = []
        
        for market in all_markets:
            market_data = self.extract_market_data(market)
            if market_data:
                market_id = market_data['market_id']
                
                # Skip duplicates
                if market_id in unique_markets:
                    continue
                unique_markets[market_id] = True
                
                # Apply volume filter
                if market_data['volume_24h'] >= min_volume:
                    processed_markets.append(market_data)
        
        # Sort by volume descending
        processed_markets.sort(key=lambda x: x['volume_24h'], reverse=True)
        
        logger.info(f"✅ Found {len(processed_markets)} unique short-term markets with volume ≥${min_volume}")
        
        return processed_markets

def main():
    """Test the fixed API"""
    api = PolymarketAPIFixed()
    
    print("🔍 TESTING FIXED POLYMARKET API:")
    print("=" * 50)
    
    # Find short-term markets
    short_markets = api.find_short_term_markets(max_days=30, min_volume=50)
    
    print(f"📊 MARKETS RESOLVING ≤30 DAYS: {len(short_markets)}")
    print()
    
    for i, market in enumerate(short_markets[:10]):
        print(f"{i+1:2d}. {market['question'][:70]}...")
        print(f"    Days: {market['days_to_resolution']:3d} | Volume: ${market['volume_24h']:8,.0f} | Price: ${market['current_price']:.3f}")
        print(f"    ID: {market['market_id'][:20]}...")
        print()
    
    if len(short_markets) > 10:
        print(f"... and {len(short_markets) - 10} more markets")
    
    return short_markets

if __name__ == "__main__":
    main()