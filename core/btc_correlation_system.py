#!/usr/bin/env python3
"""
BTC CORRELATION-AWARE POSITION MANAGEMENT
Critical system to prevent contradictory crypto positions
"""

import requests
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BTCCorrelationManager:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor', 
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Correlation parameters
        self.correlation_lookback_hours = 168  # 7 days (168 hours)
        self.min_correlation_threshold = 0.4   # Crypto-specific: even 0.4+ correlation = high risk
        self.btc_trend_period = 24            # Hours to determine BTC trend
        self.strong_trend_threshold = 0.015   # Crypto-specific: 1.5% move = significant trend
        
        # Override thresholds
        self.max_conflicting_exposure = 1000  # Max $1000 in conflicting direction
        
    def get_price_data(self, asset: str, hours: int) -> pd.DataFrame:
        """Get hourly price data for correlation analysis"""
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
            
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={
                    'type': 'candleSnapshot',
                    'req': {
                        'coin': asset,
                        'interval': '1h',
                        'startTime': start_time,
                        'endTime': end_time
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return pd.DataFrame()
                
            candles = response.json()
            if not candles:
                return pd.DataFrame()
            
            # Parse data
            if isinstance(candles[0], dict):
                df = pd.DataFrame(candles)
                df = df.rename(columns={'t': 'timestamp', 'c': 'close'})
                df = df[['timestamp', 'close']]
            else:
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df = df[['timestamp', 'close']]
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close'] = pd.to_numeric(df['close'])
            
            return df.sort_values('timestamp').reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"Error getting price data for {asset}: {e}")
            return pd.DataFrame()
    
    def calculate_btc_trend(self) -> Dict:
        """Calculate BTC trend over specified period"""
        try:
            df = self.get_price_data('BTC', self.btc_trend_period + 5)
            
            if df.empty or len(df) < 10:
                return {'direction': 'NEUTRAL', 'strength': 0.0, 'confidence': 'LOW'}
            
            # Calculate trend
            start_price = df['close'].iloc[0]
            end_price = df['close'].iloc[-1]
            price_change = (end_price - start_price) / start_price
            
            # Determine trend direction and strength
            if price_change > self.strong_trend_threshold:
                direction = 'BULLISH'
                strength = abs(price_change)
                confidence = 'HIGH' if strength > self.strong_trend_threshold * 2 else 'MEDIUM'
            elif price_change < -self.strong_trend_threshold:
                direction = 'BEARISH' 
                strength = abs(price_change)
                confidence = 'HIGH' if strength > self.strong_trend_threshold * 2 else 'MEDIUM'
            else:
                direction = 'NEUTRAL'
                strength = abs(price_change)
                confidence = 'LOW'
            
            logger.info(f"📊 BTC Trend: {direction} ({price_change:.3f}, strength: {strength:.3f}, confidence: {confidence})")
            
            return {
                'direction': direction,
                'price_change': price_change,
                'strength': strength,
                'confidence': confidence,
                'start_price': start_price,
                'end_price': end_price,
                'period_hours': self.btc_trend_period
            }
            
        except Exception as e:
            logger.error(f"Error calculating BTC trend: {e}")
            return {'direction': 'NEUTRAL', 'strength': 0.0, 'confidence': 'LOW'}
    
    def calculate_correlation(self, asset: str) -> Dict:
        """Calculate correlation between asset and BTC"""
        try:
            # Get data for both assets
            btc_df = self.get_price_data('BTC', self.correlation_lookback_hours)
            asset_df = self.get_price_data(asset, self.correlation_lookback_hours)
            
            if btc_df.empty or asset_df.empty:
                return {'correlation': 0.0, 'confidence': 'LOW', 'data_points': 0}
            
            # Align timestamps and calculate returns
            merged = pd.merge(btc_df, asset_df, on='timestamp', suffixes=('_btc', f'_{asset.lower()}'))
            
            if len(merged) < 24:  # Need at least 24 hours
                return {'correlation': 0.0, 'confidence': 'LOW', 'data_points': len(merged)}
            
            # Calculate hourly returns
            merged['btc_returns'] = merged['close_btc'].pct_change()
            merged[f'{asset.lower()}_returns'] = merged[f'close_{asset.lower()}'].pct_change()
            
            # Remove NaN values
            merged = merged.dropna()
            
            if len(merged) < 20:
                return {'correlation': 0.0, 'confidence': 'LOW', 'data_points': len(merged)}
            
            # Calculate correlation
            correlation = merged['btc_returns'].corr(merged[f'{asset.lower()}_returns'])
            
            # Determine confidence based on data points and correlation strength
            data_points = len(merged)
            if data_points >= 100 and abs(correlation) > 0.5:
                confidence = 'HIGH'
            elif data_points >= 50:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'
            
            logger.info(f"📊 {asset}-BTC Correlation: {correlation:.3f} ({confidence} confidence, {data_points} points)")
            
            return {
                'correlation': correlation,
                'confidence': confidence,
                'data_points': data_points,
                'abs_correlation': abs(correlation)
            }
            
        except Exception as e:
            logger.error(f"Error calculating correlation for {asset}: {e}")
            return {'correlation': 0.0, 'confidence': 'LOW', 'data_points': 0}
    
    def get_current_positions(self) -> List[Dict]:
        """Get current open positions"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, coin, side, entry_price, position_size, reason
                FROM simple_hl_trades 
                WHERE exit_price IS NULL
                ORDER BY coin
            """)
            
            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'id': row[0],
                    'coin': row[1],
                    'side': row[2],
                    'entry_price': float(row[3]),
                    'position_size': float(row[4]),
                    'reason': row[5]
                })
            
            cursor.close()
            conn.close()
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting current positions: {e}")
            return []
    
    def check_position_conflicts(self, new_asset: str, new_direction: str, new_size: float) -> Dict:
        """Check if new position conflicts with BTC trend and current positions"""
        
        # Get BTC trend
        btc_trend = self.calculate_btc_trend()
        
        # Get current positions
        positions = self.get_current_positions()
        
        # Calculate correlation if not BTC
        correlation_data = None
        if new_asset != 'BTC':
            correlation_data = self.calculate_correlation(new_asset)
        
        # Check for conflicts
        conflicts = []
        
        # BTC trend conflict check for alts - CRYPTO-AGGRESSIVE BLOCKING
        if new_asset != 'BTC':
            if correlation_data and correlation_data['abs_correlation'] > self.min_correlation_threshold:
                
                # CRYPTO SPECIAL: Very high correlation (>0.7) = ALWAYS block regardless of BTC trend confidence
                crypto_high_correlation = correlation_data['abs_correlation'] > 0.7
                btc_has_trend = btc_trend['confidence'] in ['MEDIUM', 'HIGH']
                
                # Block if: (high correlation + BTC trend) OR (very high correlation regardless)
                should_check_conflicts = btc_has_trend or crypto_high_correlation
                
            if correlation_data and correlation_data['abs_correlation'] > self.min_correlation_threshold and should_check_conflicts:
                
                # High correlation - ALWAYS HIGH severity for crypto (not traditional markets)
                if (btc_trend['direction'] == 'BEARISH' and new_direction == 'LONG'):
                    conflicts.append({
                        'type': 'BTC_TREND_CONFLICT',
                        'reason': f'BTC is {btc_trend["direction"]} ({btc_trend["price_change"]:.2%}), but trying to go {new_direction} on {new_asset} (correlation: {correlation_data["correlation"]:.2f})',
                        'severity': 'HIGH'  # CRYPTO: Always HIGH severity for correlation conflicts
                    })
                
                elif (btc_trend['direction'] == 'BULLISH' and new_direction == 'SHORT'):
                    conflicts.append({
                        'type': 'BTC_TREND_CONFLICT',
                        'reason': f'BTC is {btc_trend["direction"]} ({btc_trend["price_change"]:.2%}), but trying to go {new_direction} on {new_asset} (correlation: {correlation_data["correlation"]:.2f})',
                        'severity': 'HIGH'  # CRYPTO: Always HIGH severity for correlation conflicts
                    })
        
        # Portfolio conflict check
        btc_exposure = 0
        alt_exposure = 0
        
        for pos in positions:
            if pos['coin'] == 'BTC':
                if pos['side'] == 'LONG':
                    btc_exposure += pos['position_size']
                else:
                    btc_exposure -= pos['position_size']
            else:
                if pos['side'] == 'LONG':
                    alt_exposure += pos['position_size']
                else:
                    alt_exposure -= pos['position_size']
        
        # Add new position to exposure
        if new_asset == 'BTC':
            if new_direction == 'LONG':
                btc_exposure += new_size
            else:
                btc_exposure -= new_size
        else:
            if new_direction == 'LONG':
                alt_exposure += new_size
            else:
                alt_exposure -= new_size
        
        # CRYPTO PORTFOLIO-LEVEL BLOCKING: Much more aggressive than traditional markets
        # Block ANY significant opposing crypto exposure (not just max threshold)
        significant_opposing_exposure = 200  # $200+ = significant in crypto
        
        if (btc_exposure > 0 and alt_exposure < -significant_opposing_exposure) or \
           (btc_exposure < 0 and alt_exposure > significant_opposing_exposure):
            conflicts.append({
                'type': 'PORTFOLIO_CONFLICT',
                'reason': f'CRYPTO Portfolio conflict: BTC net ${btc_exposure:.0f}, Alts net ${alt_exposure:.0f} (opposing exposures >$200)',
                'severity': 'HIGH'
            })
        
        # ADDITIONAL: Block any major alt LONG when we have BTC SHORT (crypto-specific)
        has_btc_short = any(pos['coin'] == 'BTC' and pos['side'] == 'SHORT' for pos in positions)
        high_corr_alt_long = (new_asset in ['ETH', 'SOL', 'HYPE'] and 
                             new_direction == 'LONG' and 
                             correlation_data and 
                             correlation_data['abs_correlation'] > 0.4)
        
        if has_btc_short and high_corr_alt_long:
            conflicts.append({
                'type': 'BTC_SHORT_ALT_LONG_CONFLICT',
                'reason': f'CRYPTO: BTC SHORT position exists, blocking {new_asset} LONG (correlation: {correlation_data["correlation"]:.2f})',
                'severity': 'HIGH'
            })
        
        # Decision logic
        high_severity_conflicts = [c for c in conflicts if c['severity'] == 'HIGH']
        
        if high_severity_conflicts:
            recommendation = 'BLOCK'
            reason = high_severity_conflicts[0]['reason']
        elif len(conflicts) > 0:
            recommendation = 'WARNING'
            reason = conflicts[0]['reason']
        else:
            recommendation = 'ALLOW'
            reason = 'No correlation conflicts detected'
        
        return {
            'recommendation': recommendation,
            'reason': reason,
            'conflicts': conflicts,
            'btc_trend': btc_trend,
            'correlation_data': correlation_data,
            'portfolio_exposure': {
                'btc_net': btc_exposure,
                'alt_net': alt_exposure
            }
        }
    
    def analyze_current_portfolio(self) -> Dict:
        """Analyze current portfolio for conflicts"""
        
        positions = self.get_current_positions()
        btc_trend = self.calculate_btc_trend()
        
        if not positions:
            return {'conflicts': [], 'recommendation': 'PORTFOLIO_CLEAN'}
        
        print("🔍 CURRENT PORTFOLIO CONFLICT ANALYSIS")
        print("=" * 60)
        
        conflicts = []
        
        # Analyze each position
        for pos in positions:
            print(f"\n📊 {pos['coin']} {pos['side']} ${pos['position_size']}")
            
            if pos['coin'] != 'BTC':
                correlation_data = self.calculate_correlation(pos['coin'])
                
                # Check for BTC trend conflicts
                if (btc_trend['confidence'] in ['MEDIUM', 'HIGH'] and 
                    correlation_data['abs_correlation'] > self.min_correlation_threshold):
                    
                    if (btc_trend['direction'] == 'BEARISH' and pos['side'] == 'LONG'):
                        conflict = {
                            'position': pos,
                            'type': 'BTC_TREND_CONFLICT',
                            'reason': f"BTC {btc_trend['direction']} but {pos['coin']} LONG (corr: {correlation_data['correlation']:.2f})",
                            'severity': 'HIGH'
                        }
                        conflicts.append(conflict)
                        print(f"   🚨 HIGH RISK: {conflict['reason']}")
                    
                    elif (btc_trend['direction'] == 'BULLISH' and pos['side'] == 'SHORT'):
                        conflict = {
                            'position': pos,
                            'type': 'BTC_TREND_CONFLICT', 
                            'reason': f"BTC {btc_trend['direction']} but {pos['coin']} SHORT (corr: {correlation_data['correlation']:.2f})",
                            'severity': 'HIGH'
                        }
                        conflicts.append(conflict)
                        print(f"   🚨 HIGH RISK: {conflict['reason']}")
                    else:
                        print(f"   ✅ Aligned with BTC trend")
                else:
                    print(f"   ⚠️ Low correlation or weak BTC trend")
        
        # Overall recommendation
        if len(conflicts) > 0:
            high_risk = [c for c in conflicts if c['severity'] == 'HIGH']
            if high_risk:
                recommendation = 'CLOSE_CONFLICTING_POSITIONS'
            else:
                recommendation = 'MONITOR_CLOSELY'
        else:
            recommendation = 'PORTFOLIO_HEALTHY'
        
        return {
            'conflicts': conflicts,
            'recommendation': recommendation,
            'btc_trend': btc_trend,
            'position_count': len(positions),
            'conflict_count': len(conflicts)
        }

def test_correlation_system():
    """Test the BTC correlation system"""
    
    manager = BTCCorrelationManager()
    
    print("🧪 TESTING BTC CORRELATION SYSTEM")
    print("=" * 50)
    
    # Test 1: Analyze current portfolio
    portfolio_analysis = manager.analyze_current_portfolio()
    
    print(f"\n🎯 PORTFOLIO ANALYSIS RESULTS:")
    print(f"   Conflicts detected: {portfolio_analysis['conflict_count']}")
    print(f"   Recommendation: {portfolio_analysis['recommendation']}")
    
    # Test 2: Test new position scenarios
    test_scenarios = [
        ('SOL', 'LONG', 600),   # Current conflict
        ('ETH', 'SHORT', 600),  # Should align with BTC SHORT
        ('HYPE', 'SHORT', 300), # Test small position
        ('BTC', 'LONG', 1000),  # BTC position (should be allowed)
    ]
    
    print(f"\n🧪 TESTING NEW POSITION SCENARIOS:")
    print("-" * 40)
    
    for asset, direction, size in test_scenarios:
        result = manager.check_position_conflicts(asset, direction, size)
        
        status_emoji = {
            'ALLOW': '✅',
            'WARNING': '⚠️', 
            'BLOCK': '🚫'
        }.get(result['recommendation'], '❓')
        
        print(f"   {status_emoji} {asset} {direction} ${size}: {result['recommendation']}")
        print(f"      Reason: {result['reason']}")
    
    return portfolio_analysis

if __name__ == "__main__":
    analysis = test_correlation_system()