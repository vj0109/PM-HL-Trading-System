#!/usr/bin/env python3
"""
POLYMARKET PARAMETER TUNER
Test different parameter combinations to find optimal settings
Similar to HL approach where we tuned MACD parameters
"""

import requests
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import itertools

class PMParameterTuner:
    def __init__(self):
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        
    def fetch_sample_markets(self, limit: int = 100) -> List[Dict]:
        """Fetch sample markets to analyze current parameter ranges"""
        try:
            # Get active markets
            url = f"{self.gamma_api_base}/events"
            params = {
                'active': 'true',
                'closed': 'false',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def analyze_volume_distributions(self, markets: List[Dict]):
        """Analyze volume patterns to understand parameter ranges"""
        print(f"📊 ANALYZING VOLUME DISTRIBUTIONS")
        print("=" * 40)
        
        volume_ratios = []
        price_deviations = []
        
        for market in markets:
            try:
                volume = float(market.get('volume', 0))
                volume_24h = float(market.get('volume_24h', 0))
                
                if volume > 0 and volume_24h > 0:
                    volume_avg_24h = volume_24h / 24
                    volume_ratio = volume / volume_avg_24h if volume_avg_24h > 0 else 0
                    
                    if volume_ratio > 0:
                        volume_ratios.append(volume_ratio)
                
                # Price deviation from 50%
                outcome_prices = market.get('outcome_prices', [0.5, 0.5])
                if outcome_prices:
                    price = float(outcome_prices[0])
                    deviation = abs(price - 0.5)
                    price_deviations.append(deviation)
                    
            except:
                continue
        
        if volume_ratios:
            print(f"🔍 VOLUME RATIO ANALYSIS:")
            print(f"   Samples analyzed: {len(volume_ratios)}")
            print(f"   Min ratio: {min(volume_ratios):.2f}x")
            print(f"   Max ratio: {max(volume_ratios):.2f}x")
            print(f"   Average ratio: {sum(volume_ratios)/len(volume_ratios):.2f}x")
            print(f"   Ratios > 2x: {sum(1 for r in volume_ratios if r > 2.0)}")
            print(f"   Ratios > 3x: {sum(1 for r in volume_ratios if r > 3.0)}")
            print(f"   Ratios > 1.5x: {sum(1 for r in volume_ratios if r > 1.5)}")
        
        if price_deviations:
            print(f"\n🎯 PRICE DEVIATION ANALYSIS:")
            print(f"   Samples analyzed: {len(price_deviations)}")
            print(f"   Max deviation: {max(price_deviations):.1%}")
            print(f"   Average deviation: {sum(price_deviations)/len(price_deviations):.1%}")
            print(f"   Deviations > 5%: {sum(1 for d in price_deviations if d > 0.05)}")
            print(f"   Deviations > 3%: {sum(1 for d in price_deviations if d > 0.03)}")
            print(f"   Deviations > 10%: {sum(1 for d in price_deviations if d > 0.10)}")
        
        return volume_ratios, price_deviations
    
    def test_parameter_combinations(self, markets: List[Dict]):
        """Test different parameter combinations to find signal frequency"""
        print(f"\n🧪 TESTING PARAMETER COMBINATIONS")
        print("=" * 40)
        
        # Parameter ranges to test (much more relaxed)
        volume_thresholds = [1.2, 1.5, 2.0, 2.5, 3.0]
        price_thresholds = [0.01, 0.02, 0.03, 0.05, 0.08]
        
        results = []
        
        for vol_thresh in volume_thresholds:
            for price_thresh in price_thresholds:
                signals_detected = 0
                
                for market in markets:
                    try:
                        volume = float(market.get('volume', 0))
                        volume_24h = float(market.get('volume_24h', 0))
                        
                        if volume > 0 and volume_24h > 0:
                            volume_avg_24h = volume_24h / 24
                            volume_ratio = volume / volume_avg_24h if volume_avg_24h > 0 else 0
                            
                            # Price deviation
                            outcome_prices = market.get('outcome_prices', [0.5, 0.5])
                            if outcome_prices:
                                price = float(outcome_prices[0])
                                deviation = abs(price - 0.5)
                                
                                # Test signal conditions
                                if volume_ratio >= vol_thresh and deviation >= price_thresh:
                                    signals_detected += 1
                                    
                    except:
                        continue
                
                results.append({
                    'volume_threshold': vol_thresh,
                    'price_threshold': price_thresh,
                    'signals_detected': signals_detected,
                    'signal_rate': signals_detected / len(markets) if markets else 0
                })
        
        # Sort by signal detection rate
        results.sort(key=lambda x: x['signals_detected'], reverse=True)
        
        print(f"\n📊 TOP PARAMETER COMBINATIONS:")
        print(f"{'Vol Thresh':<12} {'Price Thresh':<14} {'Signals':<10} {'Rate':<8}")
        print("-" * 50)
        
        for result in results[:10]:
            print(f"{result['volume_threshold']:<12.1f} {result['price_threshold']:<14.1%} {result['signals_detected']:<10} {result['signal_rate']:<8.1%}")
        
        return results
    
    def recommend_parameters(self, results: List[Dict]):
        """Recommend parameter settings based on analysis"""
        print(f"\n🎯 PARAMETER RECOMMENDATIONS:")
        print("=" * 40)
        
        # Find parameters that give reasonable signal frequency (5-20% of markets)
        good_params = [r for r in results if 0.05 <= r['signal_rate'] <= 0.20]
        
        if good_params:
            best = good_params[0]
            print(f"✅ RECOMMENDED PARAMETERS:")
            print(f"   Volume threshold: {best['volume_threshold']:.1f}x")
            print(f"   Price threshold: {best['price_threshold']:.1%}")
            print(f"   Expected signal rate: {best['signal_rate']:.1%}")
            print(f"   Signals per 100 markets: {best['signals_detected']}")
            
            return best
        else:
            print(f"❌ No parameters found in ideal range (5-20%)")
            if results:
                most_signals = results[0]
                print(f"⚠️  Most signals detected:")
                print(f"   Volume threshold: {most_signals['volume_threshold']:.1f}x")
                print(f"   Price threshold: {most_signals['price_threshold']:.1%}")
                print(f"   Signal rate: {most_signals['signal_rate']:.1%}")
                
                return most_signals
            
        return None
    
    def show_sample_signals(self, markets: List[Dict], volume_thresh: float, price_thresh: float):
        """Show sample markets that would trigger signals"""
        print(f"\n🎯 SAMPLE SIGNALS (Vol>{volume_thresh:.1f}x, Price>{price_thresh:.1%}):")
        print("=" * 60)
        
        count = 0
        for market in markets:
            if count >= 5:  # Show max 5 samples
                break
                
            try:
                volume = float(market.get('volume', 0))
                volume_24h = float(market.get('volume_24h', 0))
                
                if volume > 0 and volume_24h > 0:
                    volume_avg_24h = volume_24h / 24
                    volume_ratio = volume / volume_avg_24h if volume_avg_24h > 0 else 0
                    
                    outcome_prices = market.get('outcome_prices', [0.5, 0.5])
                    if outcome_prices:
                        price = float(outcome_prices[0])
                        deviation = abs(price - 0.5)
                        
                        if volume_ratio >= volume_thresh and deviation >= price_thresh:
                            direction = "YES" if price < 0.5 else "NO"
                            print(f"🚨 {market.get('title', 'Unknown')[:50]}...")
                            print(f"   Direction: {direction} | Price: {price:.1%} | Volume: {volume_ratio:.1f}x")
                            count += 1
                            
            except:
                continue

def main():
    """Run parameter analysis"""
    tuner = PMParameterTuner()
    
    print("🚀 POLYMARKET PARAMETER ANALYSIS")
    print("📊 Finding optimal parameters for Volume Spike signal")
    print("=" * 60)
    
    # Fetch sample markets
    markets = tuner.fetch_sample_markets(limit=200)
    
    if not markets:
        print("❌ No market data available")
        return
    
    # Analyze distributions
    vol_ratios, price_devs = tuner.analyze_volume_distributions(markets)
    
    # Test parameter combinations
    results = tuner.test_parameter_combinations(markets)
    
    # Get recommendations
    recommended = tuner.recommend_parameters(results)
    
    # Show sample signals
    if recommended:
        tuner.show_sample_signals(
            markets, 
            recommended['volume_threshold'], 
            recommended['price_threshold']
        )
    
    print(f"\n🧪 Parameter analysis complete!")

if __name__ == "__main__":
    main()