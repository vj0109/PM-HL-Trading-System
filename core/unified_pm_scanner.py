#!/usr/bin/env python3
"""
UNIFIED POLYMARKET SIGNAL SCANNER
Runs all Tier 1 signals and provides consolidated results
"""

import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List
from pm_volume_spike_signal import VolumeSpikePMSignal
from pm_proximity_signal import ProximityPMSignal
from pm_contrarian_signal import ContrarianPMSignal

class UnifiedPMScanner:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Initialize all signal detectors
        self.volume_detector = VolumeSpikePMSignal()
        self.proximity_detector = ProximityPMSignal()
        self.contrarian_detector = ContrarianPMSignal()
        
        self.signal_detectors = [
            ('Volume Spike', self.volume_detector),
            ('Resolution Proximity', self.proximity_detector),
            ('Contrarian Reversal', self.contrarian_detector)
        ]
    
    def run_full_scan(self) -> Dict:
        """Run all signal detectors and return consolidated results"""
        print(f"🚀 UNIFIED POLYMARKET SIGNAL SCAN")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 60)
        
        all_signals = []
        scan_summary = {
            'timestamp': datetime.now(),
            'total_signals': 0,
            'by_type': {},
            'by_direction': {'BUY': 0, 'SELL': 0, 'YES': 0, 'NO': 0},
            'highest_confidence': None,
            'scan_duration': 0
        }
        
        start_time = time.time()
        
        # Run each signal detector
        for signal_name, detector in self.signal_detectors:
            print(f"\n🔍 Running {signal_name} signal...")
            try:
                if hasattr(detector, 'scan_all_markets'):
                    signals = detector.scan_all_markets()
                elif hasattr(detector, 'scan_for_proximity_signals'):
                    signals = detector.scan_for_proximity_signals()
                elif hasattr(detector, 'scan_for_contrarian_signals'):
                    signals = detector.scan_for_contrarian_signals()
                else:
                    print(f"❌ Unknown scanner method for {signal_name}")
                    continue
                    
                if signals:
                    all_signals.extend(signals)
                    scan_summary['by_type'][signal_name] = len(signals)
                    
                    # Count directions
                    for signal in signals:
                        direction = signal.get('direction', 'UNKNOWN')
                        if direction in scan_summary['by_direction']:
                            scan_summary['by_direction'][direction] += 1
                            
                    print(f"   ✅ Found {len(signals)} {signal_name.lower()} signals")
                else:
                    scan_summary['by_type'][signal_name] = 0
                    print(f"   ❌ No {signal_name.lower()} signals detected")
                    
            except Exception as e:
                print(f"   ❌ Error in {signal_name} detector: {e}")
                scan_summary['by_type'][signal_name] = 0
        
        # Calculate summary statistics
        scan_summary['total_signals'] = len(all_signals)
        scan_summary['scan_duration'] = time.time() - start_time
        
        # Find highest confidence signal
        if all_signals:
            highest_conf_signal = max(all_signals, key=lambda s: s.get('confidence', 0))
            scan_summary['highest_confidence'] = {
                'type': highest_conf_signal.get('signal_type'),
                'market': highest_conf_signal.get('market_title', '')[:50],
                'direction': highest_conf_signal.get('direction'),
                'confidence': highest_conf_signal.get('confidence'),
                'price': highest_conf_signal.get('current_price')
            }
        
        # Store all signals in database
        for signal in all_signals:
            self.store_unified_signal(signal)
        
        # Print summary
        print(f"\n📊 SCAN SUMMARY:")
        print(f"   Total signals detected: {scan_summary['total_signals']}")
        print(f"   Scan duration: {scan_summary['scan_duration']:.1f}s")
        
        if scan_summary['total_signals'] > 0:
            print(f"   Signal breakdown:")
            for signal_type, count in scan_summary['by_type'].items():
                if count > 0:
                    print(f"     - {signal_type}: {count}")
                    
            print(f"   Direction breakdown:")
            for direction, count in scan_summary['by_direction'].items():
                if count > 0:
                    print(f"     - {direction}: {count}")
                    
            if scan_summary['highest_confidence']:
                hc = scan_summary['highest_confidence']
                print(f"   Highest confidence: {hc['confidence']:.1%} ({hc['type']}) - {hc['market']}")
        
        return {
            'signals': all_signals,
            'summary': scan_summary
        }
    
    def store_unified_signal(self, signal: Dict) -> bool:
        """Store signal with unified schema"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Ensure unified table exists
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS pm_unified_signals (
                            id SERIAL PRIMARY KEY,
                            signal_type VARCHAR(50),
                            market_id VARCHAR(100),
                            market_title TEXT,
                            direction VARCHAR(10),
                            current_price DECIMAL(10,6),
                            confidence DECIMAL(5,3),
                            reasoning TEXT,
                            detected_at TIMESTAMP DEFAULT NOW(),
                            status VARCHAR(20) DEFAULT 'DETECTED',
                            raw_data JSONB
                        )
                    """)
                    
                    cursor.execute("""
                        INSERT INTO pm_unified_signals 
                        (signal_type, market_id, market_title, direction, current_price, 
                         confidence, reasoning, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        signal.get('signal_type'),
                        signal.get('market_id'),
                        signal.get('market_title'),
                        signal.get('direction'),
                        signal.get('current_price'),
                        signal.get('confidence'),
                        signal.get('reasoning'),
                        psycopg2.extras.Json(signal)
                    ))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"❌ Error storing unified signal: {e}")
            return False
    
    def get_recent_signals(self, hours: int = 24) -> List[Dict]:
        """Get signals detected in the last N hours"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT signal_type, market_title, direction, current_price, 
                               confidence, detected_at, reasoning
                        FROM pm_unified_signals 
                        WHERE detected_at > NOW() - INTERVAL '%s hours'
                        ORDER BY detected_at DESC, confidence DESC
                    """, (hours,))
                    
                    results = cursor.fetchall()
                    
                    signals = []
                    for row in results:
                        signals.append({
                            'signal_type': row[0],
                            'market_title': row[1],
                            'direction': row[2],
                            'current_price': float(row[3]),
                            'confidence': float(row[4]),
                            'detected_at': row[5],
                            'reasoning': row[6]
                        })
                    
                    return signals
                    
        except Exception as e:
            print(f"❌ Error getting recent signals: {e}")
            return []
    
    def print_recent_signals(self, hours: int = 24):
        """Print summary of recent signals"""
        signals = self.get_recent_signals(hours)
        
        if signals:
            print(f"\n📋 SIGNALS DETECTED IN LAST {hours} HOURS:")
            print("=" * 60)
            
            for signal in signals:
                print(f"🎯 {signal['signal_type'].upper()} | {signal['direction']} | {signal['confidence']:.1%}")
                print(f"   {signal['market_title'][:60]}...")
                print(f"   Price: {signal['current_price']:.1%} | Detected: {signal['detected_at'].strftime('%H:%M')}")
                print(f"   {signal['reasoning']}")
                print()
        else:
            print(f"❌ No signals detected in last {hours} hours")

if __name__ == "__main__":
    # Run unified scan
    scanner = UnifiedPMScanner()
    
    print("🧪 TESTING UNIFIED POLYMARKET SCANNER")
    print("=" * 60)
    
    # Run full scan
    results = scanner.run_full_scan()
    
    # Show recent signals from database
    print(f"\n" + "=" * 60)
    scanner.print_recent_signals(hours=1)  # Last hour
    
    print(f"\n🧪 Unified scan complete!")
    print(f"🔗 Check database: SELECT * FROM pm_unified_signals ORDER BY detected_at DESC;")