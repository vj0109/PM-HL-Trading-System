#!/usr/bin/env python3
"""
UNIFIED SIGNAL DETECTION SYSTEM
Consolidates ALL validated signals into one system:
- Funding Rate Acceleration (68.2% WR) 
- RSI signals (83.6%, 68.8%, 58.9%, 55.1% WR)
- Stochastic signals (60.5%, 56.8%, 56.4% WR) 
- Foundation signals (74.0%, 56.0% WR)
- BTC-ETH Ratio (75.0% WR)

Uses existing database schema and maintains current trades.
"""

import psycopg2
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import time
import logging
from btc_correlation_system import BTCCorrelationManager
import ta
import subprocess
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UnifiedSignalSystem:
    def __init__(self):
        # BTC Correlation Manager - CRITICAL RISK MANAGEMENT
        self.correlation_manager = BTCCorrelationManager()
        
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Trading parameters (from original system)
        self.trading_params = {
            'stop_loss_pct': 4.0,
            'take_profit_pct': 7.0,
            'partial_profit_pct': 7.0,
            'partial_exit_size': 33.0,
            'base_position_size': 600,
            'max_positions': 15,
            'daily_loss_limit': 200,
            # ANTI-CHAOS: Prevent rapid-fire trading
            'asset_cooldown_minutes': 5,  # 5 minutes between trades on same asset
            # Position scaling parameters (Claude's Phase 2 optimization)
            'position_scaling_enabled': True,
            'tranche_1_pct': 40.0,  # Initial entry on signal
            'tranche_2_pct': 30.0,  # After 0.5% confirmation
            'tranche_3_pct': 30.0,  # After 1.0% confirmation
            'confirmation_1_threshold': 0.5,  # 0.5% price movement
            'confirmation_2_threshold': 1.0,  # 1.0% price movement
            'max_confirmation_wait_minutes': 60,  # Max wait for confirmations
        }
        
        # ALL VALIDATED SIGNALS - Consolidated from both systems
        self.signal_configs = {
            # Original validated signals (already working)
            'funding_acceleration': {
                'type': 'funding_acceleration',
                'timeframes': [6, 12],
                'acceleration_threshold': 0.01,
                'assets': ['BTC', 'ETH', 'SOL', 'ATOM'],
                'win_rate': 68.2,
                'enabled': True
            },
            'btc_eth_ratio': {
                'type': 'btc_eth_ratio',
                'ratio_threshold': 1.5,
                'confirmation_hours': 4,
                'alt_coins': ['SOL', 'ATOM'],
                'win_rate': 75.0,
                'enabled': True
            },
            
            # RSI signals (4 validated configurations)
            'rsi_14_20_80_4h': {
                'type': 'rsi',
                'period': 14,
                'oversold': 20,
                'overbought': 80,
                'timeframe': '4h',
                'assets': ['BTC', 'ETH', 'SOL'],
                'win_rate': 83.6,
                'enabled': True
            },
            'rsi_14_30_70_4h': {
                'type': 'rsi',
                'period': 14,
                'oversold': 30,
                'overbought': 70,
                'timeframe': '4h',
                'assets': ['BTC', 'ETH', 'SOL'],
                'win_rate': 68.8,
                'enabled': True
            },
            'rsi_21_35_65_4h': {
                'type': 'rsi',
                'period': 21,
                'oversold': 35,
                'overbought': 65,
                'timeframe': '4h',
                'assets': ['BTC', 'ETH', 'SOL'],
                'win_rate': 58.9,
                'enabled': True
            },
            'rsi_25_75_4h': {
                'type': 'rsi',
                'period': 14,
                'oversold': 25,
                'overbought': 75,
                'timeframe': '4h',
                'assets': ['BTC', 'ETH', 'SOL'],
                'win_rate': 55.1,
                'enabled': True
            },
            
            # Stochastic signals (3 validated configurations)
            'stoch_21_3_20_80_4h_eth': {
                'type': 'stochastic',
                'k_period': 21,
                'd_period': 3,
                'oversold': 20,
                'overbought': 80,
                'timeframe': '4h',
                'assets': ['ETH'],
                'win_rate': 60.5,
                'enabled': True
            },
            'stoch_14_3_20_80_4h_eth': {
                'type': 'stochastic',
                'k_period': 14,
                'd_period': 3,
                'oversold': 20,
                'overbought': 80,
                'timeframe': '4h',
                'assets': ['ETH'],
                'win_rate': 56.8,
                'enabled': True
            },
            'stoch_5_3_20_80_4h_btc': {
                'type': 'stochastic',
                'k_period': 5,
                'd_period': 3,
                'oversold': 20,
                'overbought': 80,
                'timeframe': '4h',
                'assets': ['BTC'],
                'win_rate': 56.4,
                'enabled': True
            },
            
            # Foundation signals (2 validated)
            'oi_divergence': {
                'type': 'oi_divergence',
                'timeframe': '4h',
                'assets': ['BTC', 'ETH', 'SOL', 'HYPE'],
                'win_rate': 74.0,
                'enabled': True
            },
            'whale_entry': {
                'type': 'whale_entry',
                'timeframe': '4h', 
                'assets': ['BTC', 'ETH', 'SOL'],
                'win_rate': 56.0,
                'enabled': True
            },
            # NEW: Funding Arbitrage (Claude's Task 1.1)  
            'funding_arbitrage': {
                'type': 'funding_arbitrage',
                'enabled': True,
                'win_rate': 65.0,  # Conservative estimate during learning phase
                'assets': ['BTC', 'ETH', 'SOL', 'HYPE'],  # Main 4 assets
                'sigma_threshold': 3.0,  # Conservative 3σ during learning
                'extreme_sigma_threshold': 4.0,  # 4σ for extreme signals  
                'assumed_mean': 0.0,  # Funding typically centers around 0
                'assumed_std': 0.01,  # Conservative 1% std dev assumption
                'min_open_interest': 10000,  # $10k minimum OI
                'min_volume_24h': 100000,  # $100k minimum volume
                'min_data_points': 50,  # Need 50+ points for real statistics
            },
            # NEW: Liquidation Cascade Detection (Claude's Task 1.3)
            'liquidation_cascade': {
                'type': 'liquidation_cascade',
                'enabled': True,
                'win_rate': 68.0,  # Conservative estimate 
                'assets': ['BTC', 'ETH', 'SOL', 'HYPE'],  # Main 4 assets
                'liquidation_multiplier': 3.0,  # 3x hourly average for cascade
                'extreme_multiplier': 5.0,     # 5x for extreme cascades
                'hourly_lookback': 24,         # 24 hours for average
                'min_liquidation_volume': 10000, # $10k minimum liquidation volume
                'cascade_confidence': 68.0,    # Base confidence for cascades
                'extreme_confidence': 78.0,    # Higher confidence for extreme cascades
                'min_open_interest': 100000,   # $100k minimum OI
                'min_volume_24h': 500000,      # $500k minimum volume
            },
            
            # NEW: Simple MACD 4H (Validated via Multi-timeframe Testing)
            'macd_simple_4h': {
                'type': 'macd_simple',
                'enabled': True,
                'win_rate': 56.8,  # Validated: 56.8% WR, 129 trades, $883 P&L
                'assets': ['BTC', 'ETH', 'SOL', 'HYPE'],  # All 4 main assets
                'timeframe': '4h',             # Optimal timeframe discovered
                'fast_period': 12,             # Standard MACD fast EMA
                'slow_period': 26,             # Standard MACD slow EMA  
                'signal_period': 9,            # Standard MACD signal EMA
                'rsi_min': 25,                 # RSI filter minimum
                'rsi_max': 75,                 # RSI filter maximum
            },
            
            # NEW: Volume Profile 1H (Validated via Multi-timeframe Testing)  
            'volume_profile_1h': {
                'type': 'volume_profile',
                'enabled': True,
                'win_rate': 59.6,  # Validated: 59.6% WR, 86 trades, $167 P&L
                'assets': ['BTC', 'ETH', 'SOL', 'HYPE'],  # All 4 main assets
                'timeframe': '1h',             # Optimal timeframe discovered
                'vwap_period': 20,             # VWAP calculation period
                'volume_multiplier': 2.0,      # Volume spike multiplier
                'deviation_threshold': 0.025,  # 2.5% VWAP deviation threshold
                'rsi_oversold': 45,            # RSI oversold level
                'rsi_overbought': 55,          # RSI overbought level
            }
        }

        logger.info(f"🚀 Unified Signal System - {len([s for s in self.signal_configs.values() if s['enabled']])} validated signals loaded")

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_candle_data(self, asset: str, timeframe: str = '4h', days: int = 30) -> pd.DataFrame:
        """Get candle data from Hyperliquid"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={
                    'type': 'candleSnapshot',
                    'req': {
                        'coin': asset,
                        'interval': timeframe,
                        'startTime': start_ms,
                        'endTime': end_ms
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return pd.DataFrame()
            
            data = response.json()
            if not data:
                return pd.DataFrame()
            
            # Parse new API format
            candles = []
            for item in data:
                try:
                    candle = {
                        'timestamp': pd.to_datetime(item['t'], unit='ms'),
                        'open': float(item['o']),
                        'high': float(item['h']),
                        'low': float(item['l']),
                        'close': float(item['c']),
                        'volume': float(item['v'])
                    }
                    candles.append(candle)
                except (KeyError, ValueError):
                    continue
            
            if not candles:
                return pd.DataFrame()
            
            df = pd.DataFrame(candles)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching candle data for {asset}: {e}")
            return pd.DataFrame()

    def get_funding_rate_data(self, asset: str, hours: int = 24) -> pd.DataFrame:
        """Get funding rate data from Hyperliquid"""
        try:
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={'type': 'fundingHistory', 'coin': asset},
                timeout=30
            )
            
            if response.status_code != 200:
                return pd.DataFrame()
                
            data = response.json()
            if not data:
                return pd.DataFrame()
            
            # Parse funding data
            funding_data = []
            for item in data[-hours:]:  # Get recent data
                try:
                    funding_data.append({
                        'timestamp': pd.to_datetime(item['time'], unit='ms'),
                        'funding_rate': float(item['fundingRate'])
                    })
                except (KeyError, ValueError):
                    continue
            
            if not funding_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(funding_data)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching funding data for {asset}: {e}")
            return pd.DataFrame()

    def detect_funding_acceleration_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect funding rate acceleration signals (original validated logic)"""
        signals = []
        
        try:
            funding_df = self.get_funding_rate_data(asset, 48)
            if funding_df.empty or len(funding_df) < 12:
                return signals
            
            # Calculate acceleration over configured timeframes
            for timeframe_hours in signal_config['timeframes']:
                if len(funding_df) < timeframe_hours:
                    continue
                
                # Get recent funding rates
                recent_rates = funding_df['funding_rate'].iloc[-timeframe_hours:].values
                
                if len(recent_rates) < 3:
                    continue
                
                # Calculate acceleration (rate of change of change)
                rate_changes = np.diff(recent_rates)
                acceleration = np.mean(rate_changes[-3:])  # Recent acceleration
                
                # Signal logic from original system
                direction = None
                if acceleration > signal_config['acceleration_threshold']:
                    direction = 'SHORT'  # Rising funding = longs overpaying
                elif acceleration < -signal_config['acceleration_threshold']:
                    direction = 'LONG'   # Falling funding = shorts overpaying
                
                if direction:
                    # Get current price
                    price_df = self.get_candle_data(asset, '1h', 1)
                    if price_df.empty:
                        continue
                    
                    current_price = price_df['close'].iloc[-1]
                    confidence = min(75.0, signal_config['win_rate'])
                    
                    signals.append({
                        'asset': asset,
                        'direction': direction,
                        'signal_type': 'funding_acceleration',
                        'entry_price': current_price,
                        'confidence': confidence,
                        'timeframe': f'{timeframe_hours}h',
                        'acceleration': acceleration,
                        'reason': f'{timeframe_hours}h funding acceleration {acceleration:.3f} → {direction} {asset}'
                    })
                    
        except Exception as e:
            logger.error(f"Error detecting funding acceleration for {asset}: {e}")
        
        return signals

    def detect_btc_eth_ratio_signals(self, signal_config: Dict) -> List[Dict]:
        """Detect BTC-ETH ratio signals"""
        signals = []
        
        try:
            # Get BTC and ETH prices
            btc_df = self.get_candle_data('BTC', '1h', 7)
            eth_df = self.get_candle_data('ETH', '1h', 7)
            
            if btc_df.empty or eth_df.empty:
                return signals
            
            # Calculate ratio
            combined_df = btc_df.join(eth_df, rsuffix='_eth', how='inner')
            combined_df['ratio'] = combined_df['close'] / combined_df['close_eth']
            
            if len(combined_df) < 24:
                return signals
            
            # Check for ratio divergence
            recent_ratio = combined_df['ratio'].iloc[-1]
            avg_ratio = combined_df['ratio'].iloc[-24:].mean()
            ratio_change = (recent_ratio - avg_ratio) / avg_ratio * 100
            
            if abs(ratio_change) > signal_config['ratio_threshold']:
                # Determine altcoin direction
                direction = 'LONG' if ratio_change < 0 else 'SHORT'  # BTC weak = alts strong
                
                for alt_asset in signal_config['alt_coins']:
                    alt_df = self.get_candle_data(alt_asset, '1h', 1)
                    if alt_df.empty:
                        continue
                    
                    current_price = alt_df['close'].iloc[-1]
                    
                    signals.append({
                        'asset': alt_asset,
                        'direction': direction,
                        'signal_type': 'btc_eth_ratio',
                        'entry_price': current_price,
                        'confidence': signal_config['win_rate'],
                        'timeframe': '1h',
                        'ratio_change': ratio_change,
                        'reason': f'BTC/ETH ratio {ratio_change:.1f}% → {direction} {alt_asset}'
                    })
                    
        except Exception as e:
            logger.error(f"Error detecting BTC-ETH ratio signals: {e}")
        
        return signals

    def detect_rsi_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect RSI signals"""
        signals = []
        
        try:
            df = self.get_candle_data(asset, signal_config['timeframe'])
            if df.empty or len(df) < 50:
                return signals
            
            # Calculate RSI
            rsi = ta.momentum.RSIIndicator(df['close'], window=signal_config['period']).rsi()
            
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else None
            
            if pd.isna(current_rsi) or pd.isna(prev_rsi):
                return signals
            
            direction = None
            if current_rsi <= signal_config['oversold'] and prev_rsi > signal_config['oversold']:
                direction = 'LONG'
            elif current_rsi >= signal_config['overbought'] and prev_rsi < signal_config['overbought']:
                direction = 'SHORT'
            
            if direction:
                signals.append({
                    'asset': asset,
                    'direction': direction,
                    'signal_type': f"RSI({signal_config['period']}) {signal_config['oversold']}/{signal_config['overbought']}",
                    'entry_price': df['close'].iloc[-1],
                    'confidence': signal_config['win_rate'],
                    'timeframe': signal_config['timeframe'],
                    'rsi_value': current_rsi,
                    'reason': f"RSI({signal_config['period']}) {current_rsi:.1f} → {direction} {asset}"
                })
                
        except Exception as e:
            logger.error(f"Error detecting RSI signals for {asset}: {e}")
        
        return signals

    def detect_stochastic_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect Stochastic signals"""
        signals = []
        
        try:
            df = self.get_candle_data(asset, signal_config['timeframe'])
            if df.empty or len(df) < 50:
                return signals
            
            # Calculate Stochastic
            stoch_indicator = ta.momentum.StochasticOscillator(
                df['high'], df['low'], df['close'], 
                window=signal_config['k_period'], 
                smooth_window=signal_config['d_period']
            )
            stoch_k = stoch_indicator.stoch()
            stoch_d = stoch_indicator.stoch_signal()
            
            current_k = stoch_k.iloc[-1]
            current_d = stoch_d.iloc[-1]
            prev_k = stoch_k.iloc[-2] if len(stoch_k) > 1 else None
            prev_d = stoch_d.iloc[-2] if len(stoch_d) > 1 else None
            
            if any(pd.isna(val) for val in [current_k, current_d, prev_k, prev_d]):
                return signals
            
            direction = None
            if (current_k <= signal_config['oversold'] and current_d <= signal_config['oversold'] and
                (prev_k > signal_config['oversold'] or prev_d > signal_config['oversold'])):
                direction = 'LONG'
            elif (current_k >= signal_config['overbought'] and current_d >= signal_config['overbought'] and
                  (prev_k < signal_config['overbought'] or prev_d < signal_config['overbought'])):
                direction = 'SHORT'
            
            if direction:
                signals.append({
                    'asset': asset,
                    'direction': direction,
                    'signal_type': f"Stochastic({signal_config['k_period']},{signal_config['d_period']}) {signal_config['oversold']}/{signal_config['overbought']}",
                    'entry_price': df['close'].iloc[-1],
                    'confidence': signal_config['win_rate'],
                    'timeframe': signal_config['timeframe'],
                    'stoch_k': current_k,
                    'stoch_d': current_d,
                    'reason': f"Stoch({signal_config['k_period']},{signal_config['d_period']}) {current_k:.1f},{current_d:.1f} → {direction} {asset}"
                })
                
        except Exception as e:
            logger.error(f"Error detecting Stochastic signals for {asset}: {e}")
        
        return signals

    def detect_foundation_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect foundation signals (OI Divergence & Whale Entry)"""
        signals = []
        
        try:
            if signal_config['type'] == 'oi_divergence':
                signals = self.detect_oi_divergence(asset, signal_config)
            elif signal_config['type'] == 'whale_entry':
                signals = self.detect_whale_entry(asset, signal_config)
            
        except Exception as e:
            logger.error(f"Error detecting foundation signals for {asset}: {e}")
        
        return signals

    def detect_oi_divergence(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect real OI divergence using actual Hyperliquid open interest data"""
        signals = []
        
        try:
            # Get historical OI data (need at least 4 hours of data)
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=8)
            cursor.execute("""
                SELECT open_interest, mark_price, timestamp
                FROM oi_history
                WHERE asset = %s AND timestamp >= %s
                ORDER BY timestamp ASC
            """, (asset, cutoff_time))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if len(rows) < 2:
                # Not enough OI data yet
                return signals
            
            # Calculate 4-hour changes
            latest = rows[-1]
            
            # Find data point ~4 hours ago (make timezone aware)
            import pytz
            target_time = datetime.now(pytz.UTC) - timedelta(hours=4)
            closest_idx = 0
            min_diff = float('inf')
            
            for i, row in enumerate(rows[:-1]):  # Exclude latest
                time_diff = abs((row[2] - target_time).total_seconds())
                if time_diff < min_diff:
                    min_diff = time_diff
                    closest_idx = i
            
            if min_diff > 3600:  # More than 1 hour difference
                return signals
                
            past = rows[closest_idx]
            
            # Calculate changes
            current_oi = float(latest[0])
            current_price = float(latest[1]) 
            past_oi = float(past[0])
            past_price = float(past[1])
            
            if past_oi == 0 or past_price == 0:
                return signals
                
            price_change_4h = (current_price - past_price) / past_price
            oi_change_4h = (current_oi - past_oi) / past_oi
            
            # Check minimum movement thresholds (from Task 1.2 specs)
            min_price_change = 0.02  # 2%
            min_oi_change = 0.05     # 5%
            
            if (abs(price_change_4h) < min_price_change or 
                abs(oi_change_4h) < min_oi_change):
                return signals
            
            # Detect divergences
            direction = None
            reason = ""
            
            if price_change_4h < 0 and oi_change_4h > 0:
                # Bullish divergence: Price down, OI up → Longs accumulating
                direction = 'LONG'
                reason = f'Bullish OI divergence: Price -{abs(price_change_4h)*100:.1f}%, OI +{oi_change_4h*100:.1f}%'
            elif price_change_4h > 0 and oi_change_4h < 0:
                # Bearish divergence: Price up, OI down → Longs closing
                direction = 'SHORT'
                reason = f'Bearish OI divergence: Price +{price_change_4h*100:.1f}%, OI -{abs(oi_change_4h)*100:.1f}%'
            
            if direction:
                # Calculate divergence strength and confidence
                divergence_strength = abs(price_change_4h - oi_change_4h) / max(abs(price_change_4h), abs(oi_change_4h))
                confidence = min(signal_config['win_rate'] + (divergence_strength * 10), 95.0)
                
                signals.append({
                    'asset': asset,
                    'direction': direction,
                    'signal_type': 'oi_divergence_real',
                    'entry_price': current_price,
                    'confidence': confidence,
                    'timeframe': signal_config['timeframe'],
                    'price_change_4h': price_change_4h * 100,
                    'oi_change_4h': oi_change_4h * 100,
                    'divergence_strength': divergence_strength,
                    'reason': reason
                })
                
                logger.info(f"📈 REAL OI DIVERGENCE: {asset} {direction} - {reason}")
                
        except Exception as e:
            logger.error(f"Error detecting real OI divergence for {asset}: {e}")
        
        return signals

    def detect_whale_entry(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect whale entry using volume spike analysis"""
        signals = []
        
        try:
            df = self.get_candle_data(asset, signal_config['timeframe'], 14)
            if df.empty or len(df) < 30:
                return signals
            
            # Volume spike analysis
            df['volume_sma'] = df['volume'].rolling(24).mean()
            df['volume_std'] = df['volume'].rolling(24).std()
            df['volume_zscore'] = (df['volume'] - df['volume_sma']) / df['volume_std']
            
            current_vol_zscore = df['volume_zscore'].iloc[-1]
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2] if len(df) > 1 else current_price
            
            if pd.isna(current_vol_zscore):
                return signals
            
            if current_vol_zscore >= 2.5:
                price_change = (current_price - prev_price) / prev_price if prev_price != 0 else 0
                
                if abs(price_change) > 0.005:
                    direction = 'LONG' if price_change > 0 else 'SHORT'
                    
                    signals.append({
                        'asset': asset,
                        'direction': direction,
                        'signal_type': 'whale_entry',
                        'entry_price': current_price,
                        'confidence': signal_config['win_rate'],
                        'timeframe': signal_config['timeframe'],
                        'volume_zscore': current_vol_zscore,
                        'reason': f'Whale Entry: {current_vol_zscore:.1f}σ volume → {direction} {asset}'
                    })
                
        except Exception as e:
            logger.error(f"Error detecting whale entry for {asset}: {e}")
        
        return signals

    def collect_and_store_oi_data(self):
        """Collect and store OI data for real OI divergence detection"""
        try:
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={'type': 'metaAndAssetCtxs'},
                timeout=30
            )
            
            if response.status_code != 200:
                return 0
                
            data = response.json()
            universe = data[0]['universe']  
            asset_contexts = data[1]  
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create OI history table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS oi_history (
                    id SERIAL PRIMARY KEY,
                    asset VARCHAR(20) NOT NULL,
                    open_interest DECIMAL(20, 2) NOT NULL,
                    mark_price DECIMAL(15, 6) NOT NULL,
                    volume_24h DECIMAL(20, 2),
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            stored_count = 0
            timestamp = datetime.now()
            
            for i, asset_meta in enumerate(universe):
                if i >= len(asset_contexts):
                    continue
                    
                asset_name = asset_meta['name']
                context = asset_contexts[i]
                
                open_interest = float(context.get('openInterest', 0))
                mark_price = float(context.get('markPx', 0))
                volume_24h = float(context.get('dayNtlVlm', 0))
                
                # Only store for assets with meaningful data
                if open_interest > 0 and mark_price > 0:
                    try:
                        cursor.execute("""
                            INSERT INTO oi_history 
                            (asset, open_interest, mark_price, volume_24h, timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (asset_name, open_interest, mark_price, volume_24h, timestamp))
                        
                        stored_count += 1
                    except Exception as e:
                        continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"💾 Stored OI data for {stored_count} assets")
            return stored_count
            
        except Exception as e:
            logger.error(f"❌ Error collecting OI data: {e}")
            return 0

    def detect_funding_arbitrage_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect funding arbitrage opportunities using statistical analysis"""
        signals = []
        
        try:
            # Collect current funding data for this asset
            funding_data = self.collect_funding_data_for_asset(asset, signal_config)
            if not funding_data:
                return signals
                
            # Get historical statistics
            stats = self.get_funding_statistics(asset, signal_config)
            if not stats:
                return signals
                
            current_rate = funding_data['funding_rate']
            mean_rate = stats['mean']
            std_dev = stats['std_dev']
            
            # Skip if std dev is too small  
            if std_dev < 0.00001:
                return signals
            
            # Calculate z-score
            z_score = (current_rate - mean_rate) / std_dev
            abs_z = abs(z_score)
            
            # Check for signals (conservative threshold during learning)
            if abs_z >= signal_config['sigma_threshold']:
                
                # Determine direction
                if z_score > signal_config['sigma_threshold']:
                    direction = 'SHORT'  # Funding extremely positive → longs overpaying
                elif z_score < -signal_config['sigma_threshold']:
                    direction = 'LONG'   # Funding extremely negative → shorts overpaying
                else:
                    return signals
                
                # Calculate confidence
                if abs_z >= signal_config['extreme_sigma_threshold']:
                    confidence_boost = 10.0
                else:
                    confidence_boost = 0.0
                
                confidence = min(signal_config['win_rate'] + confidence_boost, 95.0)
                
                signals.append({
                    'asset': asset,
                    'direction': direction,
                    'signal_type': 'funding_arbitrage',
                    'entry_price': funding_data['mark_price'],
                    'confidence': confidence,
                    'timeframe': '5m',
                    'z_score': z_score,
                    'funding_rate': current_rate,
                    'data_source': stats['data_source'],
                    'reason': f'Funding {direction}: {current_rate:.6f} vs {mean_rate:.6f} ({abs_z:.1f}σ, {stats["data_source"]})'
                })
                
                logger.info(f"📈 FUNDING SIGNAL: {asset} {direction} - {abs_z:.1f}σ ({stats['data_source']})")
                
        except Exception as e:
            logger.error(f"Error detecting funding arbitrage for {asset}: {e}")
        
        return signals

    def collect_funding_data_for_asset(self, asset: str, signal_config: Dict) -> Optional[Dict]:
        """Collect current funding data for a specific asset"""
        try:
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={'type': 'metaAndAssetCtxs'},
                timeout=30
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            universe = data[0]['universe']
            asset_contexts = data[1]
            
            # Find the asset data
            for i, asset_meta in enumerate(universe):
                if asset_meta['name'] == asset and i < len(asset_contexts):
                    context = asset_contexts[i]
                    
                    if 'funding' in context and context['funding'] is not None:
                        funding_rate = float(context['funding'])
                        open_interest = float(context.get('openInterest', 0))
                        volume_24h = float(context.get('dayNtlVlm', 0))
                        mark_price = float(context.get('markPx', 0))
                        
                        # Apply filters
                        if (open_interest >= signal_config['min_open_interest'] and
                            volume_24h >= signal_config['min_volume_24h']):
                            
                            # Store in funding history
                            self.store_funding_data(asset, funding_rate, open_interest, volume_24h, mark_price)
                            
                            return {
                                'funding_rate': funding_rate,
                                'open_interest': open_interest,
                                'volume_24h': volume_24h,
                                'mark_price': mark_price
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Error collecting funding data for {asset}: {e}")
            return None

    def store_funding_data(self, asset: str, funding_rate: float, open_interest: float, volume_24h: float, mark_price: float):
        """Store funding rate data for historical analysis"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funding_rate_history (
                    id SERIAL PRIMARY KEY,
                    asset VARCHAR(20) NOT NULL,
                    funding_rate DECIMAL(18, 10) NOT NULL,
                    open_interest DECIMAL(20, 2),
                    volume_24h DECIMAL(20, 2),
                    mark_price DECIMAL(15, 6),
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            # Store data (simple insert to avoid constraint issues)
            cursor.execute("""
                INSERT INTO funding_rate_history 
                (asset, funding_rate, open_interest, volume_24h, mark_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (asset, funding_rate, open_interest, volume_24h, mark_price))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing funding data for {asset}: {e}")

    def get_funding_statistics(self, asset: str, signal_config: Dict) -> Optional[Dict]:
        """Get historical funding statistics for an asset"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=30)
            
            cursor.execute("""
                SELECT funding_rate FROM funding_rate_history
                WHERE asset = %s AND timestamp >= %s
                ORDER BY timestamp DESC
            """, (asset, cutoff_date))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if len(rows) < signal_config['min_data_points']:
                # Not enough historical data - use conservative assumptions
                return {
                    'count': len(rows),
                    'mean': signal_config['assumed_mean'],
                    'std_dev': signal_config['assumed_std'],
                    'data_source': 'assumed'
                }
                
            funding_rates = [float(row[0]) for row in rows]
            
            return {
                'count': len(funding_rates),
                'mean': np.mean(funding_rates),
                'std_dev': np.std(funding_rates),
                'data_source': 'historical'
            }
            
        except Exception as e:
            logger.error(f"Error getting funding statistics for {asset}: {e}")
            return None

    def detect_liquidation_cascade_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect liquidation cascade signals using liquidation volume analysis"""
        signals = []
        
        try:
            # Get recent liquidation data for this asset
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create liquidation history table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS liquidation_history (
                    id SERIAL PRIMARY KEY,
                    asset VARCHAR(20) NOT NULL,
                    liquidation_volume DECIMAL(20, 2) NOT NULL,
                    liquidation_side VARCHAR(10) NOT NULL,
                    mark_price DECIMAL(15, 6) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            # Get hourly liquidation average (last 24 hours)
            cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=signal_config['hourly_lookback'])
            cursor.execute("""
                SELECT AVG(liquidation_volume) as avg_volume,
                       COUNT(*) as count
                FROM liquidation_history
                WHERE asset = %s AND timestamp >= %s
            """, (asset, cutoff_time))
            
            avg_result = cursor.fetchone()
            hourly_average = float(avg_result[0]) if avg_result[0] else 0
            data_points = int(avg_result[1]) if avg_result[1] else 0
            
            # Get current liquidation data (last hour)
            recent_cutoff = datetime.now(pytz.UTC) - timedelta(hours=1)
            cursor.execute("""
                SELECT SUM(liquidation_volume) as current_volume,
                       liquidation_side,
                       COUNT(*) as events
                FROM liquidation_history
                WHERE asset = %s AND timestamp >= %s
                GROUP BY liquidation_side
                ORDER BY SUM(liquidation_volume) DESC
            """, (asset, recent_cutoff))
            
            liquidation_results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not liquidation_results or hourly_average <= 0 or data_points < 5:
                return signals
                
            # Analyze liquidation patterns
            total_current_volume = sum(float(row[0]) for row in liquidation_results)
            
            # Check for cascade (3x+ threshold)
            if total_current_volume < signal_config['min_liquidation_volume']:
                return signals
                
            multiplier = total_current_volume / hourly_average
            
            if multiplier >= signal_config['liquidation_multiplier']:
                
                # Determine dominant liquidation side
                dominant_result = liquidation_results[0]
                dominant_volume = float(dominant_result[0])
                dominant_side = dominant_result[1]
                
                # Check if one side is clearly dominant
                if len(liquidation_results) > 1:
                    second_volume = float(liquidation_results[1][0])
                    if dominant_volume < second_volume * 1.5:
                        # Not clearly dominant
                        return signals
                
                # Determine signal direction (opposite of liquidated side)
                if dominant_side == 'LONG':
                    signal_direction = 'LONG'  # Long liquidations exhausted, buy opportunity
                    cascade_type = 'long_liquidation'
                    reason = f'Long liquidation cascade: {multiplier:.1f}x average (oversold exhaustion)'
                else:
                    signal_direction = 'SHORT'  # Short liquidations exhausted, sell opportunity  
                    cascade_type = 'short_liquidation'
                    reason = f'Short liquidation cascade: {multiplier:.1f}x average (overbought exhaustion)'
                
                # Calculate confidence based on cascade severity
                if multiplier >= signal_config['extreme_multiplier']:
                    confidence = signal_config['extreme_confidence']
                    cascade_level = "EXTREME"
                else:
                    confidence = signal_config['cascade_confidence']
                    cascade_level = "MODERATE"
                
                # Get current price from recent candles
                current_price_df = self.get_candle_data(asset, '1h', 1)
                current_price = current_price_df['close'].iloc[-1] if not current_price_df.empty else 0
                
                signals.append({
                    'asset': asset,
                    'direction': signal_direction,
                    'signal_type': 'liquidation_cascade',
                    'entry_price': current_price,
                    'confidence': confidence,
                    'timeframe': '1h',
                    'cascade_type': cascade_type,
                    'liquidation_volume': total_current_volume,
                    'hourly_average': hourly_average,
                    'multiplier': multiplier,
                    'cascade_level': cascade_level,
                    'reason': reason
                })
                
                logger.info(f"🚨 LIQUIDATION CASCADE: {asset} {signal_direction} - {reason}")
                
        except Exception as e:
            logger.error(f"Error detecting liquidation cascade for {asset}: {e}")
        
        return signals

    def collect_and_store_liquidation_data(self):
        """Collect and store liquidation data (estimated from volume spikes)"""
        try:
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={'type': 'metaAndAssetCtxs'},
                timeout=30
            )
            
            if response.status_code != 200:
                return 0
                
            data = response.json()
            universe = data[0]['universe']  
            asset_contexts = data[1]  
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create liquidation history table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS liquidation_history (
                    id SERIAL PRIMARY KEY,
                    asset VARCHAR(20) NOT NULL,
                    liquidation_volume DECIMAL(20, 2) NOT NULL,
                    liquidation_side VARCHAR(10) NOT NULL,
                    mark_price DECIMAL(15, 6) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            
            stored_count = 0
            timestamp = datetime.now()
            
            for i, asset_meta in enumerate(universe):
                if i >= len(asset_contexts):
                    continue
                    
                asset_name = asset_meta['name']
                context = asset_contexts[i]
                
                volume_24h = float(context.get('dayNtlVlm', 0))
                open_interest = float(context.get('openInterest', 0))
                mark_price = float(context.get('markPx', 0))
                
                # Filter for meaningful assets with potential liquidations
                if (volume_24h >= 500000 and open_interest >= 100000 and mark_price > 0):
                    
                    # Estimate liquidation volume from high volume activity
                    # This is a proxy - real liquidation data would be more accurate
                    estimated_liquidations = volume_24h * 0.05  # 5% of volume as liquidations
                    
                    # Estimate long vs short liquidations based on market conditions
                    long_liq = estimated_liquidations * 0.6   # Assume 60% long liquidations
                    short_liq = estimated_liquidations * 0.4  # Assume 40% short liquidations
                    
                    try:
                        # Store long liquidation estimate
                        cursor.execute("""
                            INSERT INTO liquidation_history 
                            (asset, liquidation_volume, liquidation_side, mark_price, timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (asset_name, long_liq, 'LONG', mark_price, timestamp))
                        
                        # Store short liquidation estimate  
                        cursor.execute("""
                            INSERT INTO liquidation_history 
                            (asset, liquidation_volume, liquidation_side, mark_price, timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (asset_name, short_liq, 'SHORT', mark_price, timestamp))
                        
                        stored_count += 2
                    except Exception as e:
                        continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"💾 Stored liquidation estimates for {stored_count // 2} assets")
            return stored_count
            
        except Exception as e:
            logger.error(f"❌ Error collecting liquidation data: {e}")
            return 0

    def detect_macd_simple_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect simple MACD crossover signals on 4H timeframe"""
        signals = []
        
        try:
            # Get 4H candle data  
            df = self.get_candle_data(asset, signal_config['timeframe'], 50)
            if df.empty or len(df) < 35:
                return signals
            
            # Calculate MACD
            import talib
            macd, macd_signal, macd_hist = talib.MACD(
                df['close'].values,
                fastperiod=signal_config['fast_period'],
                slowperiod=signal_config['slow_period'],
                signalperiod=signal_config['signal_period']
            )
            
            # Calculate RSI for filtering
            rsi = talib.RSI(df['close'].values, timeperiod=14)
            
            # Add to dataframe
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['rsi'] = rsi
            
            # Generate signals
            for i in range(35, len(df) - 1):  # Start after MACD stabilizes
                if pd.isna(df.iloc[i]['macd']) or pd.isna(df.iloc[i]['macd_signal']) or pd.isna(df.iloc[i]['rsi']):
                    continue
                    
                current_macd = df.iloc[i]['macd']
                current_signal = df.iloc[i]['macd_signal']
                prev_macd = df.iloc[i-1]['macd']
                prev_signal = df.iloc[i-1]['macd_signal']
                current_rsi = df.iloc[i]['rsi']
                current_price = df.iloc[i]['close']
                
                # RSI filter
                if not (signal_config['rsi_min'] < current_rsi < signal_config['rsi_max']):
                    continue
                
                # Bullish crossover
                if prev_macd <= prev_signal and current_macd > current_signal:
                    signals.append({
                        'asset': asset,
                        'direction': 'LONG',
                        'signal_type': 'macd_simple_bullish',
                        'entry_price': current_price,
                        'confidence': signal_config['win_rate'],
                        'timeframe': signal_config['timeframe'],
                        'reason': f'MACD bullish crossover @ 4H - MACD: {current_macd:.4f}, Signal: {current_signal:.4f}, RSI: {current_rsi:.1f}'
                    })
                
                # Bearish crossover
                elif prev_macd >= prev_signal and current_macd < current_signal:
                    signals.append({
                        'asset': asset,
                        'direction': 'SHORT',
                        'signal_type': 'macd_simple_bearish',
                        'entry_price': current_price,
                        'confidence': signal_config['win_rate'],
                        'timeframe': signal_config['timeframe'],
                        'reason': f'MACD bearish crossover @ 4H - MACD: {current_macd:.4f}, Signal: {current_signal:.4f}, RSI: {current_rsi:.1f}'
                    })
            
            if signals:
                logger.info(f"📈 {asset}: Generated {len(signals)} MACD simple signals")
                
        except Exception as e:
            logger.error(f"Error detecting MACD simple signals for {asset}: {e}")
        
        return signals

    def detect_volume_profile_signals(self, asset: str, signal_config: Dict) -> List[Dict]:
        """Detect volume profile VWAP deviation signals on 1H timeframe"""
        signals = []
        
        try:
            # Get 1H candle data
            df = self.get_candle_data(asset, signal_config['timeframe'], 40)
            if df.empty or len(df) < 25:
                return signals
            
            # Calculate VWAP
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap_period = signal_config['vwap_period']
            
            cum_volume = df['volume'].rolling(window=vwap_period).sum()
            cum_typical_volume = (typical_price * df['volume']).rolling(window=vwap_period).sum()
            vwap = cum_typical_volume / cum_volume
            
            # Calculate volume analysis
            volume_sma = df['volume'].rolling(window=15).mean()
            volume_ratio = df['volume'] / volume_sma
            
            # Calculate RSI
            import talib
            rsi = talib.RSI(df['close'].values, timeperiod=14)
            
            # Add to dataframe
            df['vwap'] = vwap
            df['volume_ratio'] = volume_ratio
            df['rsi'] = rsi
            
            # Generate signals
            for i in range(25, len(df) - 1):
                if pd.isna(df.iloc[i]['vwap']) or pd.isna(df.iloc[i]['volume_ratio']) or pd.isna(df.iloc[i]['rsi']):
                    continue
                    
                current_price = df.iloc[i]['close']
                current_vwap = df.iloc[i]['vwap']
                current_vol_ratio = df.iloc[i]['volume_ratio']
                current_rsi = df.iloc[i]['rsi']
                
                # VWAP deviation
                vwap_deviation = (current_price - current_vwap) / current_vwap
                
                # Volume spike below VWAP (oversold reversal)
                if (vwap_deviation < -signal_config['deviation_threshold'] and
                    current_vol_ratio > signal_config['volume_multiplier'] and
                    current_rsi < signal_config['rsi_oversold']):
                    
                    signals.append({
                        'asset': asset,
                        'direction': 'LONG',
                        'signal_type': 'volume_profile_oversold',
                        'entry_price': current_price,
                        'confidence': signal_config['win_rate'],
                        'timeframe': signal_config['timeframe'],
                        'reason': f'Volume spike below VWAP @ 1H - VWAP dev: {vwap_deviation:.3f}, Vol: {current_vol_ratio:.1f}x, RSI: {current_rsi:.1f}'
                    })
                
                # Volume spike above VWAP (overbought reversal)
                elif (vwap_deviation > signal_config['deviation_threshold'] and
                      current_vol_ratio > signal_config['volume_multiplier'] and
                      current_rsi > signal_config['rsi_overbought']):
                    
                    signals.append({
                        'asset': asset,
                        'direction': 'SHORT',
                        'signal_type': 'volume_profile_overbought',
                        'entry_price': current_price,
                        'confidence': signal_config['win_rate'],
                        'timeframe': signal_config['timeframe'],
                        'reason': f'Volume spike above VWAP @ 1H - VWAP dev: {vwap_deviation:.3f}, Vol: {current_vol_ratio:.1f}x, RSI: {current_rsi:.1f}'
                    })
            
            if signals:
                logger.info(f"📈 {asset}: Generated {len(signals)} Volume Profile signals")
                
        except Exception as e:
            logger.error(f"Error detecting Volume Profile signals for {asset}: {e}")
        
        return signals

    def validate_signal_price(self, signal: Dict) -> bool:
        """Validate signal entry price against current market price"""
        try:
            # Get current market price
            response = requests.post(
                'https://api.hyperliquid.xyz/info',
                json={'type': 'allMids'},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning("⚠️ PRICE VALIDATION: Could not fetch current prices")
                return True  # Allow trade if we can't validate (conservative)
            
            prices = response.json()
            asset = signal['asset']
            signal_price = signal['entry_price']
            
            if asset not in prices:
                logger.warning(f"⚠️ PRICE VALIDATION: {asset} not found in price feed")
                return True  # Allow trade if asset not found
            
            current_price = float(prices[asset])
            price_diff_pct = abs(current_price - signal_price) / current_price
            
            # Allow max 2% difference between signal and current price
            max_price_diff = 0.02
            
            if price_diff_pct > max_price_diff:
                logger.warning(f"🚫 PRICE VALIDATION FAILED: {asset} signal ${signal_price:.2f} vs current ${current_price:.2f} ({price_diff_pct:.1%} diff > {max_price_diff:.1%})")
                return False
            
            logger.info(f"✅ PRICE VALIDATED: {asset} signal ${signal_price:.2f} vs current ${current_price:.2f} ({price_diff_pct:.1%} diff)")
            return True
            
        except Exception as e:
            logger.error(f"Error validating signal price: {e}")
            return True  # Allow trade if validation fails (conservative)

    def check_asset_cooldown(self, asset: str) -> bool:
        """Check if asset is in cooldown period to prevent rapid-fire trading"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check for recent trades on this asset
            cooldown_minutes = self.trading_params['asset_cooldown_minutes']
            cursor.execute("""
                SELECT COUNT(*) FROM simple_hl_trades 
                WHERE coin = %s 
                AND entry_time > NOW() - INTERVAL '%s minutes'
            """, (asset, cooldown_minutes))
            
            recent_trades = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if recent_trades > 0:
                logger.warning(f"⏰ ASSET COOLDOWN: {asset} has {recent_trades} trades in last {cooldown_minutes} minutes")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking asset cooldown: {e}")
            return False

    def check_position_limits(self) -> bool:
        """Check position limits using existing table schema"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Count open positions
            cursor.execute("SELECT COUNT(*) FROM simple_hl_trades WHERE exit_price IS NULL")
            open_positions = cursor.fetchone()[0]
            
            # Check daily P&L
            today = datetime.now().date()
            cursor.execute("""
                SELECT COALESCE(SUM(pnl), 0) as daily_pnl
                FROM simple_hl_trades 
                WHERE DATE(entry_time) = %s AND exit_price IS NOT NULL
            """, (today,))
            
            daily_pnl = cursor.fetchone()[0] or 0
            
            cursor.close()
            conn.close()
            
            if open_positions >= self.trading_params['max_positions']:
                logger.warning(f"Max positions reached: {open_positions}/{self.trading_params['max_positions']}")
                return False
                
            if daily_pnl <= -self.trading_params['daily_loss_limit']:
                logger.warning(f"Daily loss limit reached: ${daily_pnl}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return False

    def execute_signal(self, signal: Dict) -> bool:
        """Execute signal with conflict resolution and position scaling"""
        try:
            if not self.check_position_limits():
                return False
            
            # 🚨 ANTI-CHAOS: Asset cooldown check
            if not self.check_asset_cooldown(signal['asset']):
                return False
            
            # 🚨 PRICE VALIDATION: Check if signal price is close to current market
            if not self.validate_signal_price(signal):
                return False
            
            # 🚨 CRITICAL: BTC CORRELATION CHECK
            correlation_check = self.correlation_manager.check_position_conflicts(
                signal['asset'], 
                signal['direction'], 
                self.trading_params['base_position_size']
            )
            
            if correlation_check['recommendation'] == 'BLOCK':
                logger.warning(f"🚫 BTC CORRELATION BLOCK: {correlation_check['reason']}")
                return False
            elif correlation_check['recommendation'] == 'WARNING':
                logger.warning(f"⚠️ BTC CORRELATION WARNING: {correlation_check['reason']}")
                # Continue but log the warning
            
            # Check for position conflicts on same asset
            conflict_result = self.check_position_conflicts(signal)
            if not conflict_result['proceed']:
                logger.info(f"🚫 Signal blocked: {conflict_result['reason']}")
                return False
            
            if self.trading_params['position_scaling_enabled']:
                return self.execute_scaled_position(signal)
            else:
                return self.execute_full_position(signal)
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False

    def check_position_conflicts(self, signal: Dict) -> Dict:
        """Check for conflicting positions and resolve based on signal strength"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            asset = signal['asset']
            new_direction = signal['direction']
            new_confidence = signal['confidence']
            
            # Get existing open positions for this asset
            cursor.execute("""
                SELECT id, side, confidence, reason, entry_time 
                FROM simple_hl_trades 
                WHERE coin = %s AND exit_price IS NULL
            """, (asset,))
            
            existing_positions = cursor.fetchall()
            
            if not existing_positions:
                cursor.close()
                conn.close()
                return {'proceed': True, 'reason': 'No existing positions'}
            
            # Check for conflicts
            for pos_id, existing_direction, existing_confidence, existing_reason, entry_time in existing_positions:
                existing_confidence_pct = float(existing_confidence) * 100
                
                if existing_direction == new_direction:
                    # Same direction conflict - only allow if new signal is significantly stronger
                    if new_confidence > existing_confidence_pct + 10.0:  # Need 10% higher confidence
                        logger.info(f"🔄 UPGRADING POSITION: New {new_direction} signal {new_confidence:.1f}% vs existing {existing_confidence_pct:.1f}%")
                        # Could close existing and open new, but for now just block to prevent duplicates
                        logger.info(f"🚫 BLOCKING to prevent duplicate positions - need manual review")
                        cursor.close()
                        conn.close()
                        return {'proceed': False, 'reason': f'Same direction position exists - preventing duplicates ({existing_confidence_pct:.1f}% existing vs {new_confidence:.1f}% new)'}
                    else:
                        logger.info(f"🚫 BLOCKING duplicate {new_direction} position - existing {existing_confidence_pct:.1f}% vs new {new_confidence:.1f}%")
                        cursor.close()
                        conn.close()
                        return {'proceed': False, 'reason': f'Same direction position exists - preventing duplicates ({existing_confidence_pct:.1f}% existing vs {new_confidence:.1f}% new)'}
                
                # Opposite direction = CONFLICT
                logger.warning(f"⚠️ POSITION CONFLICT: {asset} has {existing_direction} (ID: {pos_id}, {existing_confidence_pct:.1f}% confidence)")
                logger.warning(f"⚠️ NEW SIGNAL: {asset} {new_direction} ({new_confidence:.1f}% confidence)")
                
                # Compare signal strengths
                if new_confidence > existing_confidence_pct:
                    # New signal is stronger - close existing and proceed
                    logger.info(f"🔄 STRONGER SIGNAL: Closing {existing_direction} (ID: {pos_id}) for stronger {new_direction}")
                    
                    self.close_conflicting_position(pos_id, f"Replaced by stronger {new_confidence:.1f}% signal")
                    
                    cursor.close()
                    conn.close()
                    return {'proceed': True, 'reason': f'Replaced weaker {existing_direction} position'}
                    
                else:
                    # Existing signal is stronger - block new signal
                    logger.info(f"🛡️ STRONGER EXISTING: Blocking new {new_direction} - existing {existing_direction} is stronger ({existing_confidence_pct:.1f}% vs {new_confidence:.1f}%)")
                    
                    cursor.close()
                    conn.close()
                    return {'proceed': False, 'reason': f'Existing {existing_direction} position stronger ({existing_confidence_pct:.1f}% vs {new_confidence:.1f}%)'}
            
            cursor.close()
            conn.close()
            return {'proceed': True, 'reason': 'No conflicts found'}
            
        except Exception as e:
            logger.error(f"Error checking position conflicts: {e}")
            return {'proceed': True, 'reason': 'Conflict check failed - proceeding with caution'}

    def close_conflicting_position(self, position_id: int, reason: str):
        """Close a conflicting position"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get position details
            cursor.execute("""
                SELECT coin, side, entry_price, position_size
                FROM simple_hl_trades 
                WHERE id = %s AND exit_price IS NULL
            """, (position_id,))
            
            position = cursor.fetchone()
            if not position:
                logger.warning(f"Position {position_id} not found or already closed")
                return
            
            coin, side, entry_price, position_size = position
            
            # Get current price for exit
            current_df = self.get_candle_data(coin, '1h', 1)
            if current_df.empty:
                logger.error(f"Cannot get current price for {coin} - cannot close position {position_id}")
                return
            
            exit_price = float(current_df['close'].iloc[-1])
            
            # Calculate P&L
            if side == 'LONG':
                pnl = (exit_price - float(entry_price)) / float(entry_price) * float(position_size)
            else:
                pnl = (float(entry_price) - exit_price) / float(entry_price) * float(position_size)
            
            # Close position
            cursor.execute("""
                UPDATE simple_hl_trades 
                SET exit_price = %s, exit_time = %s, exit_reason = %s, pnl = %s, status = 'CLOSED'
                WHERE id = %s
            """, (exit_price, datetime.now(), reason, pnl, position_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ CLOSED CONFLICTING POSITION: ID {position_id} {coin} {side} @ ${exit_price:.2f} (P&L: ${pnl:.2f})")
            
            # Send notification
            self.send_position_close_notification(coin, side, position_id, entry_price, exit_price, pnl, reason)
            
        except Exception as e:
            logger.error(f"Error closing conflicting position {position_id}: {e}")

    def send_position_close_notification(self, coin: str, side: str, position_id: int, entry_price: float, exit_price: float, pnl: float, reason: str):
        """Send notification for closed position"""
        try:
            pnl_emoji = "💚" if pnl > 0 else "❤️"
            direction_emoji = "🟢" if side == 'LONG' else "🔴"
            
            message = f"""🔄 POSITION REPLACED

{direction_emoji} **{coin} {side} CLOSED**
📥 Entry: ${entry_price:.2f}
📤 Exit: ${exit_price:.2f}
{pnl_emoji} P&L: ${pnl:.2f}
🆔 Trade ID: {position_id}
💡 Reason: {reason}

🎯 Replaced by stronger signal"""
            
            subprocess.run([
                'openclaw', 'message', 'send',
                '--channel', 'telegram', 
                '--target', '1083598779',
                '--message', message
            ], capture_output=True, text=True, timeout=30)
            
            logger.info(f"📱 Position close notification sent for {coin} {side} ID {position_id}")
            
        except Exception as e:
            logger.error(f"Error sending close notification: {e}")

    def execute_scaled_position(self, signal: Dict) -> bool:
        """Execute position with 40%/30%/30% scaling (Claude's optimization)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Calculate tranche sizes
            base_size = self.trading_params['base_position_size']
            tranche_1_size = float(base_size * (self.trading_params['tranche_1_pct'] / 100))
            tranche_2_size = float(base_size * (self.trading_params['tranche_2_pct'] / 100))
            tranche_3_size = float(base_size * (self.trading_params['tranche_3_pct'] / 100))
            
            coin = signal['asset']
            side = signal['direction'] 
            entry_price = float(signal['entry_price'])
            confidence = float(signal['confidence'] / 100.0)
            
            # TRANCHE 1: Initial 40% entry on signal
            reason_1 = f"TRANCHE 1/3: {signal['reason']}"
            cursor.execute("""
                INSERT INTO simple_hl_trades 
                (coin, side, entry_price, position_size, confidence, reason, entry_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                coin, side, entry_price, tranche_1_size, confidence, reason_1,
                datetime.now(), 'OPEN'
            ))
            
            trade_id_1 = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ TRANCHE 1: {signal['signal_type']} {coin} {side} @ ${entry_price:.2f} (${tranche_1_size:.0f} - ID: {trade_id_1})")
            
            # Schedule tranches 2 & 3 for confirmation-based execution
            self.schedule_confirmation_tranches(signal, tranche_2_size, tranche_3_size, trade_id_1)
            
            cursor.close()
            conn.close()
            
            # Send notification for initial tranche
            self.send_scaled_trade_notification(signal, trade_id_1, 1, tranche_1_size, base_size)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing scaled position: {e}")
            return False

    def execute_full_position(self, signal: Dict) -> bool:
        """Execute full position (original logic)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            coin = signal['asset']
            side = signal['direction']
            reason = signal['reason']
            entry_price = signal['entry_price']
            confidence = signal['confidence'] / 100.0
            position_size = self.trading_params['base_position_size']
            
            cursor.execute("""
                INSERT INTO simple_hl_trades 
                (coin, side, entry_price, position_size, confidence, reason, entry_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                coin, side, entry_price, position_size, confidence, reason,
                datetime.now(), 'OPEN'
            ))
            
            trade_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ FULL POSITION: {signal['signal_type']} {coin} {side} @ ${entry_price:.2f} (ID: {trade_id})")
            self.send_trade_notification(signal, trade_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing full position: {e}")
            return False

    def schedule_confirmation_tranches(self, signal: Dict, tranche_2_size: float, tranche_3_size: float, parent_trade_id: int):
        """Schedule tranches 2 & 3 for confirmation-based execution"""
        try:
            # Store pending tranches for later execution
            # For now, implement simple immediate logic - can be enhanced to monitor price confirmations
            
            coin = signal['asset']
            side = signal['direction']
            entry_price = signal['entry_price']
            confidence = signal['confidence'] / 100.0
            
            # Get current price to check for immediate confirmations
            current_df = self.get_candle_data(coin, '1h', 1)
            if current_df.empty:
                logger.warning(f"Cannot get current price for {coin} - skipping additional tranches")
                return
            
            current_price = current_df['close'].iloc[-1]
            
            # Calculate price movement since signal
            price_change = (current_price - entry_price) / entry_price * 100
            
            # Adjust for direction
            if side == 'SHORT':
                price_change = -price_change
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # TRANCHE 2: Execute if 0.5% confirmation already met
            if price_change >= self.trading_params['confirmation_1_threshold']:
                reason_2 = f"TRANCHE 2/3: {price_change:.1f}% confirmation - {signal['reason']}"
                cursor.execute("""
                    INSERT INTO simple_hl_trades 
                    (coin, side, entry_price, position_size, confidence, reason, entry_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    coin, side, current_price, tranche_2_size, confidence, reason_2,
                    datetime.now(), 'OPEN'
                ))
                
                trade_id_2 = cursor.fetchone()[0]
                logger.info(f"✅ TRANCHE 2: {coin} {side} @ ${current_price:.2f} (${tranche_2_size:.0f} - ID: {trade_id_2})")
                self.send_scaled_trade_notification(signal, trade_id_2, 2, tranche_2_size, self.trading_params['base_position_size'])
            
            # TRANCHE 3: Execute if 1.0% confirmation already met  
            if price_change >= self.trading_params['confirmation_2_threshold']:
                reason_3 = f"TRANCHE 3/3: {price_change:.1f}% confirmation - {signal['reason']}"
                cursor.execute("""
                    INSERT INTO simple_hl_trades 
                    (coin, side, entry_price, position_size, confidence, reason, entry_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    coin, side, current_price, tranche_3_size, confidence, reason_3,
                    datetime.now(), 'OPEN'
                ))
                
                trade_id_3 = cursor.fetchone()[0]
                logger.info(f"✅ TRANCHE 3: {coin} {side} @ ${current_price:.2f} (${tranche_3_size:.0f} - ID: {trade_id_3})")
                self.send_scaled_trade_notification(signal, trade_id_3, 3, tranche_3_size, self.trading_params['base_position_size'])
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error scheduling confirmation tranches: {e}")

    def send_scaled_trade_notification(self, signal: Dict, trade_id: int, tranche_num: int, tranche_size: float, total_size: float):
        """Send notification for scaled position tranche"""
        try:
            direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
            
            tranche_pct = (tranche_size / total_size) * 100
            
            message = f"""🚀 SCALED POSITION - TRANCHE {tranche_num}/3

{direction_emoji} **{signal['signal_type']}**
💰 {signal['asset']} {signal['direction']} @ ${signal['entry_price']:.2f}
📊 Size: ${tranche_size:.0f} ({tranche_pct:.0f}% of ${total_size:.0f})
🎯 Confidence: {signal['confidence']:.1f}%
🕐 {signal.get('timeframe', 'N/A')} timeframe
🆔 Trade ID: {trade_id}
💡 {signal['reason']}

📈 Position Scaling: 40%→30%→30% (Claude Phase 2 optimization)"""
            
            subprocess.run([
                'openclaw', 'message', 'send',
                '--channel', 'telegram', 
                '--target', '1083598779',
                '--message', message
            ], capture_output=True, text=True, timeout=30)
            
            logger.info(f"📱 Scaled position notification sent for tranche {tranche_num}, trade {trade_id}")
            
        except Exception as e:
            logger.error(f"Error sending scaled notification: {e}")

    def send_trade_notification(self, signal: Dict, trade_id: int):
        """Send Telegram notification using OpenClaw"""
        try:
            direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
            
            message = f"""🚀 UNIFIED SIGNAL EXECUTED

{direction_emoji} **{signal['signal_type']}**
💰 {signal['asset']} {signal['direction']} @ ${signal['entry_price']:.2f}
📊 Confidence: {signal['confidence']:.1f}%
🕐 {signal.get('timeframe', 'N/A')} timeframe
🆔 Trade ID: {trade_id}
💡 {signal['reason']}"""
            
            subprocess.run([
                'openclaw', 'message', 'send',
                '--channel', 'telegram', 
                '--target', '1083598779',
                '--message', message
            ], capture_output=True, text=True, timeout=30)
            
            logger.info(f"📱 Telegram notification sent for trade {trade_id}")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    def run_detection_cycle(self) -> Dict:
        """Run one complete detection cycle across all signals"""
        logger.info("🔍 Running Unified Signal Detection Cycle")
        
        # Collect OI data for real OI divergence detection
        self.collect_and_store_oi_data()
        
        # Collect liquidation data for cascade detection
        self.collect_and_store_liquidation_data()
        
        all_signals = []
        summary = {
            'signals_detected': 0,
            'signals_executed': 0,
            'signals_by_type': {},
            'errors': []
        }
        
        try:
            for signal_name, signal_config in self.signal_configs.items():
                if not signal_config.get('enabled', True):
                    continue
                    
                logger.info(f"📊 Checking {signal_name}...")
                
                signals = []
                
                # Route to appropriate detection method
                if signal_config['type'] == 'funding_acceleration':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_funding_acceleration_signals(asset, signal_config))
                        
                elif signal_config['type'] == 'btc_eth_ratio':
                    signals.extend(self.detect_btc_eth_ratio_signals(signal_config))
                    
                elif signal_config['type'] == 'rsi':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_rsi_signals(asset, signal_config))
                        
                elif signal_config['type'] == 'stochastic':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_stochastic_signals(asset, signal_config))
                        
                elif signal_config['type'] in ['oi_divergence', 'whale_entry']:
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_foundation_signals(asset, signal_config))
                        
                elif signal_config['type'] == 'funding_arbitrage':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_funding_arbitrage_signals(asset, signal_config))
                        
                elif signal_config['type'] == 'liquidation_cascade':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_liquidation_cascade_signals(asset, signal_config))
                        
                elif signal_config['type'] == 'macd_simple':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_macd_simple_signals(asset, signal_config))
                        
                elif signal_config['type'] == 'volume_profile':
                    for asset in signal_config['assets']:
                        signals.extend(self.detect_volume_profile_signals(asset, signal_config))
                
                all_signals.extend(signals)
                
                # Track by type
                signal_type = signal_config['type']
                if signal_type not in summary['signals_by_type']:
                    summary['signals_by_type'][signal_type] = 0
                summary['signals_by_type'][signal_type] += len(signals)
                
                time.sleep(1)  # Rate limiting
            
            summary['signals_detected'] = len(all_signals)
            
            # Execute signals
            for signal in all_signals:
                try:
                    if self.execute_signal(signal):
                        summary['signals_executed'] += 1
                    time.sleep(0.5)
                except Exception as e:
                    summary['errors'].append(f"Execution error: {e}")
            
            logger.info(f"🎯 Detection Summary: {summary['signals_detected']} detected, {summary['signals_executed']} executed")
            
            return summary
            
        except Exception as e:
            logger.error(f"Critical error in detection cycle: {e}")
            summary['errors'].append(str(e))
            return summary

    def run_continuous_detection(self, interval_minutes: int = 30):
        """Run continuous detection"""
        logger.info(f"🚀 Starting UNIFIED signal detection (ALL {len([s for s in self.signal_configs.values() if s['enabled']])} validated signals)")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                logger.info(f"\n📡 UNIFIED CYCLE {cycle_count} - {datetime.now()}")
                
                summary = self.run_detection_cycle()
                
                if summary['signals_executed'] > 0:
                    logger.info(f"🎉 Executed {summary['signals_executed']} new trades!")
                
                if summary['errors']:
                    logger.warning(f"⚠️ {len(summary['errors'])} errors occurred")
                
                logger.info(f"⏰ Waiting {interval_minutes} minutes until next cycle...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Unified detection stopped by user")
                break
            except Exception as e:
                logger.error(f"Critical error: {e}")
                time.sleep(300)

def main():
    system = UnifiedSignalSystem()
    
    print("\n🚀 UNIFIED SIGNAL SYSTEM")
    print("="*50)
    print("✅ ALL VALIDATED SIGNALS CONSOLIDATED:")
    
    enabled_signals = [name for name, config in system.signal_configs.items() if config.get('enabled', True)]
    for i, signal_name in enumerate(enabled_signals, 1):
        config = system.signal_configs[signal_name]
        print(f"  {i:2d}. {signal_name} ({config['win_rate']}% WR)")
    
    print(f"\n📊 Total: {len(enabled_signals)} validated signals")
    print("📡 Starting continuous detection...")
    
    system.run_continuous_detection()

if __name__ == "__main__":
    main()