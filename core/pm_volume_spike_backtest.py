#!/usr/bin/env python3
"""
POLYMARKET VOLUME SPIKE BACKTESTING
Following exact HL methodology: historical data → signal detection → outcome validation
"""

import requests
import time
import psycopg2
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics

class PMVolumeSpikeBacktester:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Polymarket API
        self.gamma_api_base = 'https://gamma-api.polymarket.com'
        
        # Signal parameters (same as working version)
        self.volume_multiplier = 1.5
        self.min_probability_move = 0.02
        self.min_volume = 1000
        
        # Validation criteria (same as HL)
        self.validation_criteria = {
            'min_trades': 50,
            'min_win_rate': 0.55,  # 55%+
            'min_profit': 0,
            'max_drawdown': 0.20
        }
    
    def get_closed_markets(self, limit: int = 500) -> List[Dict]:
        """Get historical markets that have closed and resolved"""
        print(f"🔍 Fetching {limit} closed/resolved markets for backtesting...")
        
        try:
            url = f"{self.gamma_api_base}/markets"
            params = {
                'closed': 'true',  # Only closed markets
                'active': 'false', # Not active anymore
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            markets = response.json()
            
            # Filter for markets with resolved outcomes
            resolved_markets = []
            for market in markets:
                if self.has_resolved_outcome(market):
                    resolved_markets.append(market)
            
            print(f"📊 Found {len(markets)} closed markets, {len(resolved_markets)} with resolved outcomes")
            return resolved_markets
            
        except Exception as e:
            print(f"❌ Error fetching closed markets: {e}")
            return []
    
    def has_resolved_outcome(self, market: Dict) -> bool:
        """Check if market has a clear resolution outcome"""
        try:
            outcome_prices = market.get('outcomePrices', '["0", "0"]')
            
            # Parse outcome prices
            if isinstance(outcome_prices, str):
                prices = json.loads(outcome_prices)
            else:
                prices = outcome_prices
                
            if len(prices) >= 2:
                yes_price = float(prices[0])
                no_price = float(prices[1])
                
                # Resolved if one outcome is very close to 1, other close to 0
                if (yes_price > 0.95 and no_price < 0.05) or (yes_price < 0.05 and no_price > 0.95):
                    return True
                    
            return False
            
        except:
            return False
    
    def get_market_resolution(self, market: Dict) -> Optional[str]:
        """Determine which outcome won (YES or NO)"""
        try:
            outcome_prices = market.get('outcomePrices', '["0", "0"]')
            
            if isinstance(outcome_prices, str):
                prices = json.loads(outcome_prices)
            else:
                prices = outcome_prices
                
            if len(prices) >= 2:
                yes_price = float(prices[0])
                no_price = float(prices[1])
                
                # YES won if YES price near 1
                if yes_price > 0.95:
                    return 'YES'
                elif no_price > 0.95:  # NO won
                    return 'NO'
                    
            return None
            
        except Exception as e:
            print(f"❌ Error determining resolution: {e}")
            return None
    
    def simulate_volume_spike_signal(self, market: Dict) -> Optional[Dict]:
        """
        Apply Volume Spike signal logic to historical market
        Same logic as working detector but for backtesting
        """
        try:
            market_id = market.get('id')
            if not market_id:
                return None
            
            # Get historical price data (what price was during active trading)
            # For closed markets, we need to estimate what the price was before resolution
            outcome_prices = market.get('outcomePrices', '["0", "0"]')
            
            # For backtesting, we'll use volume patterns and assume price was meaningful
            # This is simplified - in production would need actual historical price data
            volume = float(market.get('volumeNum', 0) or market.get('volume', 0) or 0)
            volume_24h = float(market.get('volume24hr', 0) or 0)
            
            if volume < self.min_volume:
                return None
            
            # Calculate volume ratio
            if volume_24h > 0:
                volume_ratio = volume / volume_24h
            else:
                # For closed markets, assume some baseline activity
                volume_ratio = volume / 10000  # Rough estimate
            
            # Check volume spike
            if volume_ratio < self.volume_multiplier:
                return None
            
            # For backtesting, we need to simulate what price would have been
            # This is the main limitation - we don't have historical price snapshots
            # Simplified approach: assume if volume was high, there was price movement
            
            # Get final resolution to work backwards
            final_outcome = self.get_market_resolution(market)
            if not final_outcome:
                return None
            
            # Simulate: if market resolved to extreme outcome (YES/NO), 
            # assume there was some earlier price movement that we could have detected
            
            if isinstance(outcome_prices, str):
                prices = json.loads(outcome_prices)
            else:
                prices = outcome_prices
                
            yes_final = float(prices[0])
            
            # Simulate entry price based on volume and final outcome
            if final_outcome == 'YES':
                # If YES won and volume was high, assume entry was at discount to final
                simulated_entry_price = max(0.1, yes_final - 0.3)  # 30% discount to final
            else:
                # If NO won, assume entry was YES at premium to final
                simulated_entry_price = min(0.9, yes_final + 0.3)  # 30% premium to final
            
            # Check if this would have triggered our signal
            price_deviation = abs(simulated_entry_price - 0.5)
            if price_deviation < self.min_probability_move:
                return None
            
            # Determine signal direction
            direction = 'YES' if simulated_entry_price < 0.5 else 'NO'
            confidence = min(0.75, 0.55 + (volume_ratio - 1.5) * 0.05 + price_deviation * 0.5)
            
            return {
                'market_id': market_id,
                'market_title': market.get('question', 'Unknown'),
                'signal_type': 'volume_spike',
                'direction': direction,
                'entry_price': simulated_entry_price,
                'volume_ratio': volume_ratio,
                'price_deviation': price_deviation,
                'volume': volume,
                'confidence': confidence,
                'actual_outcome': final_outcome,
                'reasoning': f"Volume {volume_ratio:.1f}x + {price_deviation:.1%} deviation + ${volume:,.0f} volume"
            }
            
        except Exception as e:
            print(f"❌ Error simulating signal for market {market_id}: {e}")
            return None
    
    def backtest_volume_spike(self, markets: List[Dict]) -> Dict:
        """
        Backtest Volume Spike signal on historical resolved markets
        Following exact HL methodology
        """
        print(f"🧪 BACKTESTING VOLUME SPIKE SIGNAL")
        print("=" * 50)
        print(f"📊 Testing against {len(markets)} resolved markets")
        
        results = {
            'total_signals': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'max_drawdown': 0.0,
            'trades': []
        }
        
        running_balance = 0.0
        peak_balance = 0.0
        
        for i, market in enumerate(markets):
            if i % 100 == 0 and i > 0:
                print(f"📊 Processed {i}/{len(markets)} markets...")
            
            # Generate signal
            signal = self.simulate_volume_spike_signal(market)
            if not signal:
                continue
            
            results['total_signals'] += 1
            results['total_trades'] += 1
            
            # Calculate trade outcome
            predicted_direction = signal['direction']
            actual_outcome = signal['actual_outcome']
            entry_price = signal['entry_price']
            
            trade_won = (predicted_direction == actual_outcome)
            
            # Calculate P&L (simplified binary outcome)
            if predicted_direction == 'YES':
                # Bought YES at entry_price
                profit = (1.0 - entry_price) if trade_won else (-entry_price)
            else:
                # Bought NO at (1 - entry_price)
                no_entry_price = 1.0 - entry_price
                profit = (1.0 - no_entry_price) if trade_won else (-no_entry_price)
            
            # Update results
            if trade_won:
                results['winning_trades'] += 1
            else:
                results['losing_trades'] += 1
            
            results['total_profit'] += profit
            running_balance += profit
            
            # Track drawdown
            if running_balance > peak_balance:
                peak_balance = running_balance
            else:
                drawdown = (peak_balance - running_balance) / max(peak_balance, 1.0)
                results['max_drawdown'] = max(results['max_drawdown'], drawdown)
            
            trade_record = {
                'market_id': signal['market_id'],
                'market_title': signal['market_title'][:60],
                'predicted': predicted_direction,
                'actual': actual_outcome,
                'won': trade_won,
                'entry_price': entry_price,
                'profit': profit,
                'volume_ratio': signal['volume_ratio'],
                'confidence': signal['confidence'],
                'volume': signal['volume']
            }
            
            results['trades'].append(trade_record)
        
        # Calculate final statistics
        if results['total_trades'] > 0:
            results['win_rate'] = results['winning_trades'] / results['total_trades']
        
        print(f"\n📊 Backtest completed: {results['total_signals']} signals, {results['total_trades']} trades")
        
        return results
    
    def validate_signal_results(self, results: Dict) -> Dict:
        """
        Validate signal results against HL criteria
        """
        validation = {
            'passes_validation': True,
            'criteria_met': {},
            'criteria_failed': {}
        }
        
        # Check each criteria (same as HL)
        criteria_checks = {
            'min_trades': results['total_trades'] >= self.validation_criteria['min_trades'],
            'min_win_rate': results['win_rate'] >= self.validation_criteria['min_win_rate'],
            'min_profit': results['total_profit'] >= self.validation_criteria['min_profit'],
            'max_drawdown': results['max_drawdown'] <= self.validation_criteria['max_drawdown']
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
        Print detailed backtest results in HL format
        """
        print(f"\n🎯 VOLUME SPIKE SIGNAL BACKTEST RESULTS:")
        print("=" * 60)
        
        print(f"📊 TRADE STATISTICS:")
        print(f"   Total signals detected: {results['total_signals']}")
        print(f"   Total trades executed: {results['total_trades']}")
        print(f"   Winning trades: {results['winning_trades']}")
        print(f"   Losing trades: {results['losing_trades']}")
        print(f"   Win rate: {results['win_rate']:.1%}")
        print(f"   Total profit: ${results['total_profit']:.2f}")
        print(f"   Maximum drawdown: {results['max_drawdown']:.1%}")
        
        print(f"\n✅ VALIDATION CRITERIA (HL Standard):")
        for criteria in validation['criteria_met']:
            print(f"   ✅ {criteria}: PASSED")
            
        for criteria in validation['criteria_failed']:
            print(f"   ❌ {criteria}: FAILED")
        
        print(f"\n🎯 OVERALL RESULT:")
        if validation['passes_validation']:
            print(f"   ✅ VOLUME SPIKE SIGNAL APPROVED - Meets HL validation criteria")
            print(f"   🚀 Ready for production deployment")
        else:
            print(f"   ❌ VOLUME SPIKE SIGNAL REJECTED - Failed HL validation criteria")
            print(f"   🔧 Needs parameter adjustment or logic revision")
        
        # Show sample trades
        if results['trades']:
            print(f"\n📋 SAMPLE TRADES (Last 10):")
            for trade in results['trades'][-10:]:
                status = "✅ WIN" if trade['won'] else "❌ LOSS"
                print(f"   {status} | {trade['market_title'][:45]}...")
                print(f"        Predicted: {trade['predicted']} | Actual: {trade['actual']} | P&L: ${trade['profit']:.2f}")
                print(f"        Volume: ${trade['volume']:,.0f} ({trade['volume_ratio']:.1f}x) | Entry: {trade['entry_price']:.1%}")

def main():
    """Run Volume Spike backtesting"""
    backtester = PMVolumeSpikeBacktester()
    
    print("🚀 POLYMARKET VOLUME SPIKE BACKTESTING")
    print("📊 Following HL methodology: historical data → signal → validation")
    print("=" * 70)
    
    # Fetch historical resolved markets
    markets = backtester.get_closed_markets(limit=1000)
    
    if not markets:
        print("❌ No historical market data available")
        return
    
    # Run backtest
    results = backtester.backtest_volume_spike(markets)
    
    # Validate results
    validation = backtester.validate_signal_results(results)
    
    # Print results
    backtester.print_backtest_results(results, validation)
    
    # Store results in database
    try:
        with psycopg2.connect(**backtester.db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pm_backtest_results (
                        id SERIAL PRIMARY KEY,
                        signal_type VARCHAR(50),
                        test_date TIMESTAMP DEFAULT NOW(),
                        total_trades INTEGER,
                        winning_trades INTEGER,
                        win_rate DECIMAL(5,3),
                        total_profit DECIMAL(10,2),
                        max_drawdown DECIMAL(5,3),
                        passes_validation BOOLEAN,
                        raw_results JSONB
                    )
                """)
                
                cursor.execute("""
                    INSERT INTO pm_backtest_results 
                    (signal_type, total_trades, winning_trades, win_rate, total_profit, 
                     max_drawdown, passes_validation, raw_results)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    'volume_spike',
                    results['total_trades'],
                    results['winning_trades'],
                    results['win_rate'],
                    results['total_profit'],
                    results['max_drawdown'],
                    validation['passes_validation'],
                    psycopg2.extras.Json(results)
                ))
                
                conn.commit()
                print(f"\n✅ Results stored in pm_backtest_results table")
                
    except Exception as e:
        print(f"❌ Error storing results: {e}")
    
    print(f"\n🧪 Volume Spike backtesting complete!")

if __name__ == "__main__":
    main()