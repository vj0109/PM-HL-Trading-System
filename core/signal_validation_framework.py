#!/usr/bin/env python3
"""
SIGNAL VALIDATION FRAMEWORK
Rigorous backtesting system for new signal development
"""

import requests
import pandas as pd
import numpy as np
import talib
import psycopg2
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalValidator:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # VALIDATION THRESHOLDS (VJ Requirements)
        self.validation_criteria = {
            'min_trades': 50,           # Minimum 50 trades required
            'min_win_rate': 55.0,       # Minimum 55% win rate  
            'min_profit': 0.0,          # Must be profitable (positive P&L)
            'max_drawdown': 20.0,       # Maximum 20% drawdown
            'min_sharpe': 0.5,          # Minimum Sharpe ratio
            'required_assets': ['BTC', 'ETH', 'SOL', 'HYPE']  # Must work across all 4
        }
        
        # Trading parameters for backtesting
        self.trading_params = {
            'stop_loss': 0.04,          # 4% stop loss
            'take_profit': 0.07,        # 7% take profit  
            'position_size': 600,       # $600 base position
            'max_hold_hours': 48,       # Max 48 hours hold time
        }
        
        self.results = {}
        
    def get_historical_data(self, asset: str, timeframe: str = '4h', lookback_days: int = 60) -> pd.DataFrame:
        """Get historical candle data from Hyperliquid"""
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
            
            # Convert timeframe to minutes
            timeframe_minutes = {
                '1h': 60,
                '4h': 240,
                '1d': 1440
            }.get(timeframe, 240)
            
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={
                    'type': 'candleSnapshot',
                    'req': {
                        'coin': asset,
                        'interval': timeframe,
                        'startTime': start_time,
                        'endTime': end_time
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get {asset} data: {response.status_code}")
                return pd.DataFrame()
                
            candles = response.json()
            
            if not candles:
                logger.error(f"No candle data for {asset}")
                return pd.DataFrame()
            
            # Convert to DataFrame (handle dictionary format)
            if candles and isinstance(candles[0], dict):
                # Dictionary format from Hyperliquid API
                df = pd.DataFrame(candles)
                
                # Map column names  
                column_mapping = {
                    't': 'timestamp',
                    'o': 'open',
                    'h': 'high', 
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume'
                }
                
                # Rename columns and select needed ones
                df = df.rename(columns=column_mapping)
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                
            else:
                # Array format fallback
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"✅ {asset}: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting {asset} historical data: {e}")
            return pd.DataFrame()
    
    def calculate_trade_pnl(self, entry_price: float, exit_price: float, direction: str) -> float:
        """Calculate P&L for a trade"""
        if direction == 'LONG':
            return ((exit_price - entry_price) / entry_price) * self.trading_params['position_size']
        else:  # SHORT
            return ((entry_price - exit_price) / entry_price) * self.trading_params['position_size']
    
    def simulate_trade_execution(self, df: pd.DataFrame, signals: List[Dict]) -> List[Dict]:
        """Simulate trade execution with stops and targets"""
        trades = []
        
        for signal in signals:
            entry_idx = signal['index']
            entry_price = signal['entry_price']
            direction = signal['direction']
            
            if entry_idx >= len(df) - 1:
                continue
                
            # Look for exit conditions
            exit_price = None
            exit_reason = None
            exit_idx = None
            
            max_look_ahead = min(len(df) - entry_idx - 1, 
                               self.trading_params['max_hold_hours'] // (4 if '4h' in str(df['timestamp'].iloc[1] - df['timestamp'].iloc[0]) else 1))
            
            for i in range(1, max_look_ahead + 1):
                if entry_idx + i >= len(df):
                    break
                    
                candle = df.iloc[entry_idx + i]
                high, low, close = candle['high'], candle['low'], candle['close']
                
                if direction == 'LONG':
                    # Check stop loss first
                    if low <= entry_price * (1 - self.trading_params['stop_loss']):
                        exit_price = entry_price * (1 - self.trading_params['stop_loss'])
                        exit_reason = 'STOP_LOSS'
                        exit_idx = entry_idx + i
                        break
                    # Check take profit
                    elif high >= entry_price * (1 + self.trading_params['take_profit']):
                        exit_price = entry_price * (1 + self.trading_params['take_profit'])
                        exit_reason = 'TAKE_PROFIT'
                        exit_idx = entry_idx + i
                        break
                        
                else:  # SHORT
                    # Check stop loss first
                    if high >= entry_price * (1 + self.trading_params['stop_loss']):
                        exit_price = entry_price * (1 + self.trading_params['stop_loss'])
                        exit_reason = 'STOP_LOSS'
                        exit_idx = entry_idx + i
                        break
                    # Check take profit
                    elif low <= entry_price * (1 - self.trading_params['take_profit']):
                        exit_price = entry_price * (1 - self.trading_params['take_profit'])
                        exit_reason = 'TAKE_PROFIT'
                        exit_idx = entry_idx + i
                        break
            
            # If no exit found, exit at current price (time-based exit)
            if exit_price is None:
                exit_idx = min(entry_idx + max_look_ahead, len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_reason = 'TIME_EXIT'
            
            # Calculate P&L
            pnl = self.calculate_trade_pnl(entry_price, exit_price, direction)
            
            trades.append({
                'entry_time': df.iloc[entry_idx]['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'direction': direction,
                'pnl': pnl,
                'exit_reason': exit_reason,
                'signal_data': signal.get('signal_data', {})
            })
            
        return trades
    
    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'profitable_trades': 0,
                'losing_trades': 0,
                'avg_winner': 0,
                'avg_loser': 0
            }
        
        pnls = [t['pnl'] for t in trades]
        
        # Basic metrics
        total_trades = len(trades)
        profitable_trades = len([p for p in pnls if p > 0])
        losing_trades = len([p for p in pnls if p < 0])
        win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(pnls)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Winner/loser analysis
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]
        avg_winner = np.mean(winners) if winners else 0
        avg_loser = np.mean(losers) if losers else 0
        
        # Drawdown calculation
        cumulative_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = (cumulative_pnl - running_max) / running_max * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        # Sharpe ratio
        sharpe_ratio = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252) if len(pnls) > 1 and np.std(pnls) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser
        }
    
    def validate_signal_across_assets(self, signal_function, signal_name: str, signal_params: Dict) -> Dict:
        """Validate a signal across all required assets"""
        
        logger.info(f"🧪 VALIDATING SIGNAL: {signal_name}")
        logger.info("=" * 60)
        
        all_results = {}
        passed_assets = []
        failed_assets = []
        
        for asset in self.validation_criteria['required_assets']:
            logger.info(f"📊 Testing {signal_name} on {asset}...")
            
            # Get historical data
            df = self.get_historical_data(asset, '4h', lookback_days=90)
            
            if df.empty:
                logger.error(f"❌ {asset}: No historical data available")
                failed_assets.append(asset)
                continue
            
            # Generate signals using the provided function
            try:
                signals = signal_function(df, signal_params)
                logger.info(f"📈 {asset}: Generated {len(signals)} signals")
                
            except Exception as e:
                logger.error(f"❌ {asset}: Signal generation failed - {e}")
                failed_assets.append(asset)
                continue
            
            # Simulate trades
            trades = self.simulate_trade_execution(df, signals)
            
            # Calculate metrics
            metrics = self.calculate_performance_metrics(trades)
            
            # Store results
            all_results[asset] = {
                'signals_generated': len(signals),
                'trades_executed': len(trades),
                'metrics': metrics,
                'data_period': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
                'candles_analyzed': len(df)
            }
            
            # Check if passes validation criteria
            passes_validation = (
                metrics['total_trades'] >= self.validation_criteria['min_trades'] and
                metrics['win_rate'] >= self.validation_criteria['min_win_rate'] and
                metrics['total_pnl'] >= self.validation_criteria['min_profit'] and
                metrics['max_drawdown'] <= self.validation_criteria['max_drawdown'] and
                metrics['sharpe_ratio'] >= self.validation_criteria['min_sharpe']
            )
            
            if passes_validation:
                passed_assets.append(asset)
                status = "✅ PASSED"
            else:
                failed_assets.append(asset)
                status = "❌ FAILED"
            
            logger.info(f"   {status} - {metrics['total_trades']} trades, {metrics['win_rate']:.1f}% WR, ${metrics['total_pnl']:.2f} P&L")
        
        # Overall validation result
        overall_pass = len(passed_assets) == len(self.validation_criteria['required_assets'])
        
        validation_result = {
            'signal_name': signal_name,
            'signal_params': signal_params,
            'overall_pass': overall_pass,
            'passed_assets': passed_assets,
            'failed_assets': failed_assets,
            'asset_results': all_results,
            'validation_criteria': self.validation_criteria,
            'summary': self.generate_validation_summary(all_results, overall_pass)
        }
        
        # Store results
        self.results[signal_name] = validation_result
        
        return validation_result
    
    def generate_validation_summary(self, asset_results: Dict, overall_pass: bool) -> Dict:
        """Generate summary statistics across all assets"""
        
        if not asset_results:
            return {}
        
        all_metrics = [result['metrics'] for result in asset_results.values()]
        
        return {
            'total_signals': sum(result['signals_generated'] for result in asset_results.values()),
            'total_trades': sum(metrics['total_trades'] for metrics in all_metrics),
            'avg_win_rate': np.mean([metrics['win_rate'] for metrics in all_metrics]),
            'total_pnl': sum(metrics['total_pnl'] for metrics in all_metrics),
            'avg_sharpe': np.mean([metrics['sharpe_ratio'] for metrics in all_metrics]),
            'max_drawdown': max(metrics['max_drawdown'] for metrics in all_metrics),
            'recommendation': 'APPROVED FOR INTEGRATION' if overall_pass else 'REJECTED - DOES NOT MEET CRITERIA'
        }
    
    def print_validation_report(self, signal_name: str):
        """Print detailed validation report"""
        
        if signal_name not in self.results:
            logger.error(f"No results found for {signal_name}")
            return
        
        result = self.results[signal_name]
        
        print(f"\n🎯 SIGNAL VALIDATION REPORT: {signal_name}")
        print("=" * 80)
        
        print(f"📊 OVERALL RESULT: {result['summary']['recommendation']}")
        print(f"✅ Passed assets: {len(result['passed_assets'])}/{len(self.validation_criteria['required_assets'])}")
        
        if result['failed_assets']:
            print(f"❌ Failed assets: {', '.join(result['failed_assets'])}")
        
        print(f"\n📈 AGGREGATE PERFORMANCE:")
        summary = result['summary']
        print(f"   Total signals generated: {summary['total_signals']}")
        print(f"   Total trades backtested: {summary['total_trades']}")
        print(f"   Average win rate: {summary['avg_win_rate']:.1f}%")
        print(f"   Total P&L: ${summary['total_pnl']:.2f}")
        print(f"   Average Sharpe ratio: {summary['avg_sharpe']:.2f}")
        print(f"   Maximum drawdown: {summary['max_drawdown']:.1f}%")
        
        print(f"\n📊 ASSET BREAKDOWN:")
        for asset, data in result['asset_results'].items():
            metrics = data['metrics']
            status = "✅" if asset in result['passed_assets'] else "❌"
            
            print(f"   {status} {asset}:")
            print(f"      Trades: {metrics['total_trades']}, WR: {metrics['win_rate']:.1f}%, P&L: ${metrics['total_pnl']:.2f}")
            print(f"      Sharpe: {metrics['sharpe_ratio']:.2f}, Max DD: {metrics['max_drawdown']:.1f}%")
        
        print(f"\n🎯 VALIDATION CRITERIA:")
        criteria = result['validation_criteria']
        print(f"   Minimum trades: {criteria['min_trades']}")
        print(f"   Minimum win rate: {criteria['min_win_rate']}%")
        print(f"   Minimum profit: ${criteria['min_profit']}")
        print(f"   Maximum drawdown: {criteria['max_drawdown']}%")
        print(f"   Minimum Sharpe: {criteria['min_sharpe']}")
        
        if result['overall_pass']:
            print(f"\n🚀 RECOMMENDATION: APPROVE FOR INTEGRATION")
            print(f"   This signal meets all validation criteria")
            print(f"   Ready to add to unified signal system")
        else:
            print(f"\n❌ RECOMMENDATION: REJECT")
            print(f"   Signal does not meet minimum requirements")
            print(f"   Requires optimization or different approach")

if __name__ == "__main__":
    validator = SignalValidator()
    print("🎯 Signal Validation Framework Ready")
    print("=" * 50)
    print("📊 Validation Criteria:")
    for key, value in validator.validation_criteria.items():
        print(f"   {key}: {value}")