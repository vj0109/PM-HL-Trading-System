#!/usr/bin/env python3
"""
SIGNAL 25 - STEP 2 COMPLETE: FULL PRICE HISTORY COLLECTION
Collect price history for all 84 political markets using validated endpoint
Following Claude's specification: /prices-history?market={id}&interval=max&fidelity=720
"""

import requests
import json
from datetime import datetime
import time
import pandas as pd

class CompletePriceHistoryCollector:
    def __init__(self):
        self.clob_host = "https://clob.polymarket.com"
        
    def load_political_markets(self):
        """Load all 84 political markets from Step 1"""
        print("📂 Loading all 84 political markets from Step 1...")
        
        try:
            with open('/home/vj/PM-HL-Trading-System/data/political_markets_resolved.json', 'r') as f:
                markets = json.load(f)
            
            print(f"✅ Loaded {len(markets)} political markets")
            return markets
            
        except Exception as e:
            print(f"❌ Error loading markets: {e}")
            return []
    
    def get_price_history_for_market(self, condition_id, market_info):
        """
        Get price history for a single market using validated endpoint
        """
        try:
            # Using Claude's validated endpoint
            url = f"{self.clob_host}/prices-history"
            params = {
                "market": condition_id,
                "interval": "max",
                "fidelity": 720  # 12-hour minimum fidelity for resolved markets
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'history' in data and data['history']:
                    history = data['history']
                    
                    return {
                        'success': True,
                        'condition_id': condition_id,
                        'market_info': market_info,
                        'price_history': history,
                        'data_points': len(history),
                        'collected_at': datetime.now().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'condition_id': condition_id,
                        'error': 'No price history found',
                        'response_data': data
                    }
            else:
                return {
                    'success': False,
                    'condition_id': condition_id,
                    'error': f'HTTP {response.status_code}',
                    'response_text': response.text[:200]
                }
                
        except Exception as e:
            return {
                'success': False,
                'condition_id': condition_id,
                'error': str(e)
            }
    
    def analyze_price_data_structure(self, successful_results):
        """
        Analyze the structure of collected price data
        """
        print(f"\n📊 ANALYZING PRICE DATA STRUCTURE")
        print("=" * 40)
        
        if not successful_results:
            print("❌ No successful results to analyze")
            return {}
        
        # Analyze first successful result
        sample = successful_results[0]
        sample_history = sample['price_history']
        
        if sample_history:
            sample_point = sample_history[0]
            print(f"📈 Sample price data point structure:")
            print(f"   Type: {type(sample_point)}")
            
            if isinstance(sample_point, dict):
                print(f"   Fields: {list(sample_point.keys())}")
                for key, value in sample_point.items():
                    print(f"     {key}: {value} ({type(value).__name__})")
            else:
                print(f"   Value: {sample_point}")
        
        # Statistics across all markets
        data_points = [len(r['price_history']) for r in successful_results]
        
        print(f"\n📊 Dataset Statistics:")
        print(f"   Markets with data: {len(successful_results)}")
        print(f"   Total price points: {sum(data_points):,}")
        print(f"   Average points per market: {sum(data_points) / len(data_points):.1f}")
        print(f"   Min points: {min(data_points)}")
        print(f"   Max points: {max(data_points)}")
        
        # Date range analysis if timestamps available
        if sample_history and isinstance(sample_history[0], dict):
            timestamp_fields = [k for k in sample_history[0].keys() if 'time' in k.lower() or 'date' in k.lower()]
            if timestamp_fields:
                print(f"   Timestamp fields found: {timestamp_fields}")
        
        return {
            'total_markets': len(successful_results),
            'total_price_points': sum(data_points),
            'avg_points_per_market': sum(data_points) / len(data_points),
            'min_points': min(data_points),
            'max_points': max(data_points),
            'sample_structure': sample_point if sample_history else None
        }
    
    def collect_all_price_histories(self):
        """
        Collect price history for all 84 political markets
        """
        print("🔬 SIGNAL 25 - STEP 2 COMPLETE: FULL PRICE HISTORY COLLECTION")
        print("🎯 Goal: Collect price data for all 84 political markets")
        print("📋 Using: Validated Claude endpoint with 12-hour fidelity")
        print("=" * 75)
        
        # Load markets
        markets = self.load_political_markets()
        
        if not markets:
            print("❌ No markets to process")
            return {}
        
        print(f"\n📊 COLLECTING PRICE HISTORY FOR ALL {len(markets)} MARKETS")
        print("=" * 60)
        
        successful_results = []
        failed_results = []
        
        for i, market in enumerate(markets):
            condition_id = market['condition_id']
            question = market['question']
            volume = market.get('volume', 0)
            
            print(f"\n📊 Market {i+1}/{len(markets)}")
            print(f"❓ {question[:80]}...")
            print(f"🆔 {condition_id}")
            print(f"💰 Volume: ${volume:,.0f}" if isinstance(volume, (int, float)) else f"💰 Volume: {volume}")
            
            # Collect price history
            result = self.get_price_history_for_market(condition_id, market)
            
            if result['success']:
                data_points = result['data_points']
                successful_results.append(result)
                print(f"   ✅ SUCCESS: {data_points:,} price data points collected")
            else:
                failed_results.append(result)
                error = result['error']
                print(f"   ❌ FAILED: {error}")
            
            # Rate limiting - don't overwhelm API
            if i < len(markets) - 1:  # Don't sleep after last request
                time.sleep(0.5)  # 500ms between requests
            
            # Progress update every 10 markets
            if (i + 1) % 10 == 0:
                success_rate = len(successful_results) / (i + 1) * 100
                print(f"\n   📊 Progress: {i+1}/{len(markets)} completed ({success_rate:.1f}% success rate)")
        
        # Final results
        print(f"\n🎉 PRICE HISTORY COLLECTION COMPLETE")
        print("=" * 45)
        print(f"✅ Successful: {len(successful_results)}/{len(markets)} markets ({len(successful_results)/len(markets)*100:.1f}%)")
        print(f"❌ Failed: {len(failed_results)} markets")
        
        if failed_results:
            print(f"\n❌ Failed Markets:")
            for i, failed in enumerate(failed_results[:5]):  # Show first 5 failures
                print(f"   {i+1}. {failed['condition_id'][:10]}... - {failed['error']}")
            if len(failed_results) > 5:
                print(f"   ... and {len(failed_results) - 5} more")
        
        # Analyze successful data
        if successful_results:
            analysis = self.analyze_price_data_structure(successful_results)
            
            # Save complete dataset
            output_data = {
                'metadata': {
                    'collected_at': datetime.now().isoformat(),
                    'total_markets_attempted': len(markets),
                    'successful_markets': len(successful_results),
                    'failed_markets': len(failed_results),
                    'success_rate_percent': len(successful_results)/len(markets)*100,
                    'endpoint_used': f"{self.clob_host}/prices-history",
                    'parameters': {
                        'interval': 'max',
                        'fidelity': 720
                    }
                },
                'analysis': analysis,
                'successful_results': successful_results,
                'failed_results': failed_results
            }
            
            # Save to file
            output_file = '/home/vj/PM-HL-Trading-System/data/complete_price_history_dataset.json'
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\n💾 Complete dataset saved to: complete_price_history_dataset.json")
            print(f"📊 Dataset contains {analysis['total_price_points']:,} total price points")
            print(f"🚀 Ready for Signal 25 Step 3: Polling data sources")
            
            return output_data
        else:
            print(f"\n❌ No successful price data collected")
            return {}

def main():
    """Run complete price history collection"""
    collector = CompletePriceHistoryCollector()
    results = collector.collect_all_price_histories()
    
    if results and results.get('successful_results'):
        success_count = len(results['successful_results'])
        total_points = results['analysis']['total_price_points']
        
        print(f"\n🎉 COLLECTION SUMMARY:")
        print(f"   ✅ Markets: {success_count}/84")
        print(f"   📊 Price Points: {total_points:,}")
        print(f"   📈 Average per Market: {total_points/success_count:.1f}")
        print(f"   🎯 Ready for backtesting!")
    else:
        print(f"\n⚠️ Collection incomplete or failed")

if __name__ == "__main__":
    main()