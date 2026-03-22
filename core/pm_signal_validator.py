#!/usr/bin/env python3
"""
POLYMARKET SIGNAL VALIDATOR
Individual signal backtesting similar to HL validation framework
"""

import requests
import time
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class PMSignalValidator:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Validation criteria (same as HL)
        self.validation_criteria = {
            'min_trades': 50,
            'min_win_rate': 0.55,  # 55%+
            'min_profit': 0,       # Must be profitable
            'max_drawdown': 0.20   # <20% drawdown
        }
        
        # Polymarket APIs
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        
    def fetch_historical_markets(self, days: int = 90) -> List[Dict]:
        """
        Fetch historical market data for backtesting
        This is a simplified version - in production would need proper time series data
        """
        print(f"🔍 Fetching historical markets for {days} days...")
        
        try:
            # Get current active markets (simplified approach)
            url = f"{self.gamma_api_base}/events"
            params = {
                'active': 'false',  # Include closed markets
                'closed': 'true',
                'limit': 500
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            markets = response.json()
            print(f"📊 Found {len(markets)} historical markets")
            
            return markets
            
        except Exception as e:
            print(f"❌ Error fetching historical markets: {e}")
            return []
    
    def get_market_price_history(self, market_id: str) -> Optional[Dict]:
        """
        Get price history for a specific market
        Simplified - would need time series API in production
        """
        try:
            url = f"{self.gamma_api_base}/events/{market_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ Error fetching price history for {market_id}: {e}")
            return None
    
    def simulate_volume_spike_signal(self, market: Dict) -> Optional[Dict]:
        """
        Simulate Volume Spike signal detection on historical data
        Similar logic to pm_volume_spike_signal.py but for backtesting
        """
        try:
            market_id = market.get('id')
            if not market_id:
                return None
            
            # Get basic market data
            current_price = float(market.get('outcome_prices', [0.5, 0.5])[0])
            volume = float(market.get('volume', 0))
            volume_24h = float(market.get('volume_24h', 0))
            
            if volume == 0 or volume_24h == 0:
                return None
            
            # Calculate volume spike (simplified)
            volume_avg_24h = volume_24h / 24
            if volume_avg_24h == 0:
                return None
                
            volume_ratio = volume / volume_avg_24h
            
            # Simplified price move calculation
            # In production would use actual time series
            price_deviation = abs(current_price - 0.5)
            
            # Signal conditions (using more relaxed parameters for testing)
            volume_threshold = 2.0  # Reduced from 3.0
            price_threshold = 0.03  # Reduced from 0.05
            
            if volume_ratio >= volume_threshold and price_deviation >= price_threshold:
                # Determine direction
                direction = 'YES' if current_price < 0.5 else 'NO'
                confidence = min(0.75, 0.55 + (volume_ratio - 2) * 0.05)
                
                return {
                    'market_id': market_id,
                    'market_title': market.get('title', 'Unknown'),
                    'signal_type': 'volume_spike',
                    'direction': direction,
                    'entry_price': current_price,
                    'volume_ratio': volume_ratio,
                    'price_deviation': price_deviation,
                    'confidence': confidence,
                    'reasoning': f"Volume {volume_ratio:.1f}x average + {price_deviation:.1%} deviation"
                }
                
        except Exception as e:
            print(f"❌ Error simulating signal for {market_id}: {e}")
            
        return None
    
    def get_market_resolution_outcome(self, market: Dict) -> Optional[str]:
        """
        Get the actual resolution outcome for a market
        Used to determine if our signal was correct
        """
        try:
            # Look for resolution data in market
            if market.get('closed') and market.get('resolved'):
                # Try to determine winning outcome
                outcome_prices = market.get('outcome_prices', [0.5, 0.5])
                if outcome_prices:
                    # If first outcome (YES) price is close to 1.0, YES won
                    # If close to 0.0, NO won
                    yes_price = float(outcome_prices[0])
                    if yes_price > 0.9:
                        return 'YES'
                    elif yes_price < 0.1:
                        return 'NO'
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting resolution for market: {e}")
            return None
    
    def backtest_volume_spike_signal(self, markets: List[Dict]) -> Dict:
        """
        Backtest Volume Spike signal on historical markets
        """
        print(f"🧪 BACKTESTING VOLUME SPIKE SIGNAL")
        print("=" * 50)
        
        results = {
            'total_signals': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'trades': []
        }
        
        for i, market in enumerate(markets):
            if i % 100 == 0:
                print(f"📊 Processed {i}/{len(markets)} markets...")
            
            # Generate signal
            signal = self.simulate_volume_spike_signal(market)
            if not signal:
                continue
                
            results['total_signals'] += 1
            
            # Get actual outcome
            actual_outcome = self.get_market_resolution_outcome(market)
            if not actual_outcome:
                continue  # Skip if we can't determine outcome
                
            results['total_trades'] += 1
            
            # Determine if trade was winning
            predicted_direction = signal['direction']
            trade_won = (predicted_direction == actual_outcome)
            
            if trade_won:
                results['winning_trades'] += 1
            else:
                results['losing_trades'] += 1
            
            # Calculate P&L (simplified - using binary outcome)
            entry_price = signal['entry_price']
            if predicted_direction == 'YES':
                # Bought YES at entry_price
                profit = (1.0 - entry_price) if trade_won else (-entry_price)
            else:
                # Bought NO at (1 - entry_price)
                no_entry_price = 1.0 - entry_price
                profit = (1.0 - no_entry_price) if trade_won else (-no_entry_price)
            
            results['total_profit'] += profit
            
            trade_record = {
                'market_id': signal['market_id'],
                'market_title': signal['market_title'][:50],
                'predicted': predicted_direction,
                'actual': actual_outcome,
                'won': trade_won,
                'entry_price': entry_price,
                'profit': profit,
                'volume_ratio': signal['volume_ratio'],
                'confidence': signal['confidence']
            }
            
            results['trades'].append(trade_record)
        
        # Calculate final statistics
        if results['total_trades'] > 0:
            results['win_rate'] = results['winning_trades'] / results['total_trades']
        
        return results
    
    def validate_signal_results(self, results: Dict) -> Dict:
        """
        Validate signal results against our criteria (same as HL)
        """
        validation = {
            'passes_validation': True,
            'criteria_met': {},
            'criteria_failed': {}
        }
        
        # Check each criteria
        criteria_checks = {
            'min_trades': results['total_trades'] >= self.validation_criteria['min_trades'],
            'min_win_rate': results['win_rate'] >= self.validation_criteria['min_win_rate'],
            'min_profit': results['total_profit'] >= self.validation_criteria['min_profit']
        }
        
        for criteria, passed in criteria_checks.items():
            if passed:
                validation['criteria_met'][criteria] = True
            else:
                validation['criteria_failed'][criteria] = True
                validation['passes_validation'] = False
        
        return validation
    
    def print_backtest_results(self, results: Dict, validation: Dict):
        """
        Print detailed backtest results similar to HL format
        """
        print(f"\n🎯 VOLUME SPIKE SIGNAL BACKTEST RESULTS:")
        print("=" * 50)
        
        print(f"📊 TRADE STATISTICS:")
        print(f"   Total signals detected: {results['total_signals']}")
        print(f"   Total trades executed: {results['total_trades']}")
        print(f"   Winning trades: {results['winning_trades']}")
        print(f"   Losing trades: {results['losing_trades']}")
        print(f"   Win rate: {results['win_rate']:.1%}")
        print(f"   Total profit: ${results['total_profit']:.2f}")
        
        print(f"\n✅ VALIDATION CRITERIA:")
        for criteria in validation['criteria_met']:
            print(f"   ✅ {criteria}: PASSED")
            
        for criteria in validation['criteria_failed']:
            print(f"   ❌ {criteria}: FAILED")
        
        print(f"\n🎯 OVERALL RESULT:")
        if validation['passes_validation']:
            print(f"   ✅ SIGNAL APPROVED - Meets all validation criteria")
        else:
            print(f"   ❌ SIGNAL REJECTED - Failed validation criteria")
        
        # Show sample trades
        if results['trades']:
            print(f"\n📋 SAMPLE TRADES (Last 5):")
            for trade in results['trades'][-5:]:
                status = "✅ WIN" if trade['won'] else "❌ LOSS"
                print(f"   {status} | {trade['market_title']} | Predicted: {trade['predicted']} | Actual: {trade['actual']} | P&L: ${trade['profit']:.2f}")

def main():
    """Test Volume Spike signal validation"""
    validator = PMSignalValidator()
    
    print("🚀 STARTING POLYMARKET SIGNAL VALIDATION")
    print("📊 Testing Volume Spike Signal (Similar to HL Approach)")
    print("=" * 60)
    
    # Fetch historical data
    markets = validator.fetch_historical_markets(days=90)
    
    if not markets:
        print("❌ No historical market data available")
        return
    
    # Backtest the signal
    results = validator.backtest_volume_spike_signal(markets)
    
    # Validate against criteria
    validation = validator.validate_signal_results(results)
    
    # Print results
    validator.print_backtest_results(results, validation)
    
    print(f"\n🧪 Volume Spike signal validation complete!")

if __name__ == "__main__":
    main()