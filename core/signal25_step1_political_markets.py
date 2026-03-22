#!/usr/bin/env python3
"""
SIGNAL 25 - STEP 1: POLITICAL MARKETS DISCOVERY
Using official Polymarket GitHub py-clob-client endpoints
Find resolved political markets for polling divergence analysis
"""

from py_clob_client.client import ClobClient
import requests
import json
from datetime import datetime

class PoliticalMarketsDiscovery:
    def __init__(self):
        # Using official py-clob-client endpoints
        self.clob_host = "https://clob.polymarket.com"
        self.gamma_host = "https://gamma-api.polymarket.com"
        
        # Initialize CLOB client (no auth needed for market discovery)
        self.client = ClobClient(host=self.clob_host)
    
    def get_all_clob_markets(self, limit=1000):
        """
        Get markets from CLOB API using official client
        Following official py-clob-client methods
        """
        print("🔍 Step 1a: Getting markets from CLOB API (Official Client)")
        print("-" * 55)
        
        try:
            # Using official get_markets() method
            markets_response = self.client.get_markets()
            
            if isinstance(markets_response, dict) and 'data' in markets_response:
                markets = markets_response['data']
                print(f"✅ Retrieved {len(markets)} markets from CLOB API")
                
                # Show sample market structure
                if markets:
                    sample = markets[0]
                    print(f"📊 Sample market fields: {list(sample.keys())}")
                
                return markets
            else:
                print(f"❌ Unexpected CLOB markets format: {type(markets_response)}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting CLOB markets: {e}")
            return []
    
    def get_gamma_events_comprehensive(self, limit=500):
        """
        Get comprehensive events from Gamma API, focusing on resolved events
        Following Claude's guidance but expanding search scope
        """
        print(f"\n🔍 Step 1b: Getting comprehensive events from Gamma API")
        print("-" * 60)
        
        try:
            # First, let's discover what tag IDs exist for politics
            # Get more events, specifically include closed ones
            response = requests.get(
                f"{self.gamma_host}/events",
                params={
                    "limit": limit,
                    "closed": "true"  # Focus on resolved events for backtesting
                },
                timeout=15
            )
            
            if response.status_code == 200:
                events = response.json()
                print(f"✅ Gamma events endpoint accessible")
                
                if events and len(events) > 0:
                    sample_event = events[0]
                    print(f"📊 Sample event fields: {list(sample_event.keys())}")
                    
                    # Look for tag-related fields
                    tag_fields = [k for k in sample_event.keys() if 'tag' in k.lower()]
                    category_fields = [k for k in sample_event.keys() if any(word in k.lower() for word in ['category', 'type', 'genre', 'group'])]
                    
                    print(f"🏷️ Tag-related fields: {tag_fields}")
                    print(f"📂 Category-related fields: {category_fields}")
                    
                    return events
                else:
                    print("⚠️ No events found in sample")
                    return []
            else:
                print(f"❌ Gamma events API failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting Gamma events: {e}")
            return []
    
    def find_political_markets_method1(self, events):
        """
        Method 1: Find political markets by keywords in titles/descriptions
        """
        print(f"\n🔍 Step 1c: Finding political markets (Method 1: Keywords)")
        print("-" * 60)
        
        political_keywords = [
            'election', 'president', 'biden', 'trump', 'democrat', 'republican',
            'senate', 'congress', 'house', 'governor', 'primary', 'vote', 'voting',
            'politics', 'political', 'campaign', 'nominee', 'nomination',
            # 2024 election specific
            '2024', 'harris', 'kamala', 'desantis', 'vivek', 'ramaswamy', 
            'haley', 'nikki', 'christie', 'pence', 'newsom',
            # General political terms
            'white house', 'oval office', 'presidency', 'vice president',
            'electoral', 'swing state', 'battleground', 'caucus', 'ballot'
        ]
        
        political_events = []
        
        for event in events:
            title = event.get('title', '').lower()
            description = event.get('description', '').lower()
            
            # Check if any political keywords appear
            is_political = any(keyword in title or keyword in description for keyword in political_keywords)
            
            if is_political:
                political_events.append(event)
        
        print(f"✅ Found {len(political_events)} political events via keywords")
        
        # Extract markets from political events
        political_markets = []
        for event in political_events:
            markets = event.get('markets', [])
            for market in markets:
                # Add event context to market
                market['event_title'] = event.get('title', '')
                market['event_description'] = event.get('description', '')
                market['is_political'] = True
                political_markets.append(market)
        
        print(f"📊 Extracted {len(political_markets)} political markets")
        
        return political_markets
    
    def find_political_markets_method2(self, events):
        """
        Method 2: Find political markets by checking for tags/categories
        """
        print(f"\n🔍 Step 1d: Finding political markets (Method 2: Tags)")
        print("-" * 55)
        
        # Analyze tag structure in events
        all_tags = []
        tag_types = set()
        
        for event in events[:20]:  # Sample first 20 events
            # Look for various tag field names
            for field_name, field_value in event.items():
                if 'tag' in field_name.lower():
                    tag_types.add(field_name)
                    if isinstance(field_value, list):
                        for tag in field_value:
                            if isinstance(tag, dict):
                                # Tag is a dict, extract name or id
                                tag_name = tag.get('name', tag.get('id', str(tag)))
                                all_tags.append(tag_name)
                            else:
                                all_tags.append(str(tag))
                    elif field_value:
                        all_tags.append(str(field_value))
        
        print(f"🏷️ Tag field types found: {list(tag_types)}")
        
        # Count tag occurrences
        from collections import Counter
        tag_counts = Counter(all_tags)
        
        print(f"📊 Most common tags:")
        for tag, count in tag_counts.most_common(10):
            print(f"   {tag}: {count}")
        
        # Look for political tags
        potential_political_tags = [tag for tag, count in tag_counts.items() 
                                   if any(word in str(tag).lower() for word in ['politi', 'elect', 'govern'])]
        
        print(f"🗳️ Potential political tags: {potential_political_tags}")
        
        return potential_political_tags
    
    def filter_resolved_markets(self, political_markets):
        """
        Filter for resolved/closed political markets suitable for backtesting
        """
        print(f"\n🔍 Step 1e: Filtering for resolved political markets")
        print("-" * 50)
        
        resolved_markets = []
        
        for market in political_markets:
            is_closed = market.get('closed', False)
            is_resolved = market.get('resolved', False)
            has_condition_id = market.get('condition_id') or market.get('conditionId')
            
            if is_closed and has_condition_id:
                resolved_markets.append({
                    'condition_id': has_condition_id,
                    'question': market.get('question', market.get('event_title', 'Unknown')),
                    'closed': is_closed,
                    'resolved': is_resolved,
                    'volume': market.get('volume', 0),
                    'event_title': market.get('event_title', ''),
                    'is_political': True
                })
        
        print(f"✅ Found {len(resolved_markets)} resolved political markets")
        
        # Sort by volume for liquidity
        resolved_markets.sort(key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
        
        # Show top 10 by volume
        print(f"\n📊 Top 10 resolved political markets by volume:")
        for i, market in enumerate(resolved_markets[:10]):
            volume = market.get('volume', 0)
            try:
                volume_float = float(volume) if volume else 0
                volume_str = f"${volume_float:,.0f}"
            except (ValueError, TypeError):
                volume_str = f"${volume}"
            question = market['question'][:60]
            print(f"   {i+1}. {question}... ({volume_str} volume)")
        
        return resolved_markets
    
    def run_political_markets_discovery(self):
        """
        Execute complete political markets discovery process
        """
        print("🔬 SIGNAL 25 - STEP 1: POLITICAL MARKETS DISCOVERY")
        print("🎯 Goal: Find resolved political markets for polling divergence analysis")
        print("📋 Using: Official Polymarket py-clob-client endpoints")
        print("=" * 75)
        
        # Step 1a: Get all markets from CLOB
        clob_markets = self.get_all_clob_markets()
        
        # Step 1b: Get events from Gamma (to find political categorization)
        gamma_events = self.get_gamma_events_comprehensive(limit=500)
        
        if not gamma_events:
            print("❌ Cannot proceed without Gamma events data")
            return []
        
        # Step 1c: Find political markets by keywords
        political_markets_keywords = self.find_political_markets_method1(gamma_events)
        
        # Step 1d: Find political markets by tags
        political_tags = self.find_political_markets_method2(gamma_events)
        
        # Step 1e: Filter for resolved markets
        resolved_political_markets = self.filter_resolved_markets(political_markets_keywords)
        
        print(f"\n🎉 STEP 1 COMPLETE - POLITICAL MARKETS DISCOVERY")
        print("=" * 55)
        print(f"✅ Total resolved political markets found: {len(resolved_political_markets)}")
        print(f"📊 Ready for Step 2: Price history collection")
        
        return resolved_political_markets

def main():
    """Run political markets discovery"""
    discovery = PoliticalMarketsDiscovery()
    political_markets = discovery.run_political_markets_discovery()
    
    # Save results for next step
    if political_markets:
        with open('/home/vj/PM-HL-Trading-System/data/political_markets_resolved.json', 'w') as f:
            json.dump(political_markets, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: data/political_markets_resolved.json")
        print(f"🚀 Ready for Signal 25 Step 2: Price history collection")
    else:
        print(f"\n⚠️ No political markets found - check data sources")

if __name__ == "__main__":
    main()