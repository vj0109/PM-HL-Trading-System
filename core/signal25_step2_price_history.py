#!/usr/bin/env python3
"""
SIGNAL 25 - STEP 2: PRICE HISTORY COLLECTION
Using Official Polymarket API endpoints to collect historical price data
Following Claude's guidance: GET /prices-history?market={tokenID}&interval=max&fidelity=720
"""

from py_clob_client.client import ClobClient
import requests
import json
from datetime import datetime, timedelta
import time

class PriceHistoryCollector:
    def __init__(self):
        # Using official endpoints
        self.clob_host = "https://clob.polymarket.com"
        self.gamma_host = "https://gamma-api.polymarket.com"
        
        # Initialize client
        self.client = ClobClient(host=self.clob_host)
    
    def load_political_markets(self):
        """Load the political markets from Step 1"""
        print("📂 Loading political markets from Step 1...")
        
        try:
            with open('/home/vj/PM-HL-Trading-System/data/political_markets_resolved.json', 'r') as f:
                markets = json.load(f)
            
            print(f"✅ Loaded {len(markets)} political markets")
            return markets
            
        except Exception as e:
            print(f"❌ Error loading markets: {e}")
            return []
    
    def test_price_history_endpoints(self, condition_id):
        """
        Test different possible price history endpoints
        Following Claude's specification but checking what actually exists
        """
        print(f"🧪 Testing price history endpoints for {condition_id[:10]}...")
        
        endpoints_to_test = [
            # Claude's specified endpoint
            f"/prices-history?market={condition_id}&interval=max&fidelity=720",
            
            # Alternative patterns from official docs
            f"/prices?market={condition_id}",
            f"/price?market={condition_id}",
            f"/midpoint?market={condition_id}",
            
            # Try with token ID instead
            f"/prices-history?token={condition_id}&interval=max&fidelity=720",
            f"/prices?token={condition_id}",
            
            # Try different host
            f"/markets/{condition_id}/prices",
            f"/markets/{condition_id}/price-history",
        ]
        
        working_endpoints = []
        
        for endpoint in endpoints_to_test:
            try:
                # Test on CLOB host
                url = f"{self.clob_host}{endpoint}"
                response = requests.get(url, timeout=10)
                
                print(f"   CLOB {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    working_endpoints.append({
                        'endpoint': endpoint,
                        'host': 'clob',
                        'response_type': type(data).__name__,
                        'data_length': len(data) if isinstance(data, (list, dict)) else 'N/A'
                    })
                    
                    # Show sample data structure
                    if isinstance(data, list) and data:
                        sample = data[0]
                        print(f"      Sample: {list(sample.keys()) if isinstance(sample, dict) else str(sample)[:100]}")
                    elif isinstance(data, dict):
                        print(f"      Keys: {list(data.keys())}")
                        
            except Exception as e:
                print(f"   CLOB {endpoint}: Error - {e}")
        
        # Also test Gamma API for price history
        gamma_endpoints = [
            f"/markets/{condition_id}/prices",
            f"/events/{condition_id}/prices",
        ]
        
        for endpoint in gamma_endpoints:
            try:
                url = f"{self.gamma_host}{endpoint}"
                response = requests.get(url, timeout=10)
                
                print(f"   Gamma {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    working_endpoints.append({
                        'endpoint': endpoint,
                        'host': 'gamma',
                        'response_type': type(data).__name__,
                        'data_length': len(data) if isinstance(data, (list, dict)) else 'N/A'
                    })
                    
            except Exception as e:
                print(f"   Gamma {endpoint}: Error - {e}")
        
        return working_endpoints
    
    def test_official_client_price_methods(self, condition_id):
        """
        Test official py-clob-client methods for price data
        """
        print(f"\n🧪 Testing official client price methods...")
        
        methods_to_test = [
            ('get_midpoint', lambda: self.client.get_midpoint(condition_id)),
            ('get_last_trade_price', lambda: self.client.get_last_trade_price(condition_id)),
            ('get_market', lambda: self.client.get_market(condition_id)),
        ]
        
        working_methods = []
        
        for method_name, method_func in methods_to_test:
            try:
                print(f"   Testing {method_name}...")
                result = method_func()
                
                print(f"   ✅ {method_name}: Success")
                print(f"      Type: {type(result).__name__}")
                
                if isinstance(result, dict):
                    print(f"      Keys: {list(result.keys())}")
                elif isinstance(result, list) and result:
                    print(f"      Sample: {result[0] if len(str(result[0])) < 100 else str(result[0])[:100]}")
                else:
                    print(f"      Value: {str(result)[:100]}")
                
                working_methods.append(method_name)
                
            except Exception as e:
                print(f"   ❌ {method_name}: {e}")
        
        return working_methods
    
    def collect_price_data_sample(self, markets_sample=5):
        """
        Collect price data for a sample of markets to test approach
        """
        print(f"\n📊 STEP 2: COLLECTING PRICE DATA SAMPLE")
        print("=" * 50)
        
        markets = self.load_political_markets()
        
        if not markets:
            print("❌ No markets to process")
            return {}
        
        # Test with top markets by volume
        test_markets = markets[:markets_sample]
        results = {}
        
        for i, market in enumerate(test_markets):
            condition_id = market['condition_id']
            question = market['question']
            
            print(f"\n📊 Testing Market {i+1}/{len(test_markets)}")
            print(f"❓ {question[:60]}...")
            print(f"🆔 Condition ID: {condition_id}")
            print("-" * 60)
            
            # Test HTTP endpoints
            working_endpoints = self.test_price_history_endpoints(condition_id)
            
            # Test official client methods  
            working_methods = self.test_official_client_price_methods(condition_id)
            
            results[condition_id] = {
                'market_info': market,
                'working_endpoints': working_endpoints,
                'working_methods': working_methods
            }
            
            # Don't overwhelm APIs
            time.sleep(1)
        
        return results
    
    def analyze_price_data_structure(self, results):
        """
        Analyze the structure of price data to determine best approach
        """
        print(f"\n🔍 ANALYZING PRICE DATA STRUCTURE")
        print("=" * 40)
        
        all_working_endpoints = []
        all_working_methods = []
        
        for condition_id, result in results.items():
            all_working_endpoints.extend(result['working_endpoints'])
            all_working_methods.extend(result['working_methods'])
        
        # Count successful endpoints
        from collections import Counter
        endpoint_counts = Counter([ep['endpoint'] for ep in all_working_endpoints])
        method_counts = Counter(all_working_methods)
        
        print(f"📊 Working Endpoints (success count):")
        for endpoint, count in endpoint_counts.most_common():
            print(f"   {endpoint}: {count}/{len(results)} markets")
        
        print(f"\n📊 Working Client Methods (success count):")
        for method, count in method_counts.most_common():
            print(f"   {method}: {count}/{len(results)} markets")
        
        # Recommend best approach
        if endpoint_counts:
            best_endpoint = endpoint_counts.most_common(1)[0]
            print(f"\n✅ RECOMMENDED ENDPOINT: {best_endpoint[0]} ({best_endpoint[1]} successes)")
        
        if method_counts:
            best_method = method_counts.most_common(1)[0]
            print(f"✅ RECOMMENDED CLIENT METHOD: {best_method[0]} ({best_method[1]} successes)")
        
        return {
            'endpoint_counts': endpoint_counts,
            'method_counts': method_counts,
            'best_endpoint': endpoint_counts.most_common(1)[0] if endpoint_counts else None,
            'best_method': method_counts.most_common(1)[0] if method_counts else None
        }
    
    def run_price_history_collection(self):
        """
        Execute price history collection test
        """
        print("🔬 SIGNAL 25 - STEP 2: PRICE HISTORY COLLECTION")
        print("🎯 Goal: Find working endpoint for historical price data")
        print("📋 Testing: Claude's /prices-history + official client methods")
        print("=" * 70)
        
        # Collect sample data
        results = self.collect_price_data_sample(markets_sample=5)
        
        if not results:
            print("❌ No results to analyze")
            return None
        
        # Analyze structure
        analysis = self.analyze_price_data_structure(results)
        
        print(f"\n🎉 STEP 2 COMPLETE - PRICE DATA COLLECTION TEST")
        print("=" * 55)
        
        if analysis['best_endpoint'] or analysis['best_method']:
            print(f"✅ Found working approach for price data collection")
            print(f"🚀 Ready for Step 3: Polling data source setup")
        else:
            print(f"⚠️ No reliable price data endpoints found")
            print(f"🔧 May need alternative approach or further investigation")
        
        return analysis

def main():
    """Run price history collection test"""
    collector = PriceHistoryCollector()
    analysis = collector.run_price_history_collection()
    
    # Save results
    if analysis:
        with open('/home/vj/PM-HL-Trading-System/data/price_history_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n💾 Analysis saved to: data/price_history_analysis.json")

if __name__ == "__main__":
    main()