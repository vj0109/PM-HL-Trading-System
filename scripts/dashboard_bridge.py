#!/usr/bin/env python3
"""
DASHBOARD BRIDGE - Connect Real Claude System to myhunch.xyz Dashboard
Bridge real edge signals to existing dashboard tables for live display
"""

import psycopg2
import json
from datetime import datetime, timedelta
import time

class DashboardBridge:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        print("🔗 DASHBOARD BRIDGE - Real Claude → myhunch.xyz")
        print("=" * 60)
        print("🎯 Connecting real edge signals to existing dashboard")
        print("📊 Dashboard: https://myhunch.xyz/admin/PM-HL-Trading")
        
    def bridge_real_signals_to_dashboard(self):
        """Bridge real edge signals to dashboard-compatible format"""
        
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        # Get new real edge signals not yet bridged to dashboard
        cur.execute('''
            SELECT id, signal_type, asset, direction, confidence, entry_price,
                   suggested_size, stop_loss, take_profit, reason, generated_at
            FROM real_edge_signals 
            WHERE status = 'ACTIVE'
            AND id NOT IN (
                SELECT COALESCE(external_signal_id::INTEGER, 0)
                FROM simple_hl_trades 
                WHERE external_signal_id IS NOT NULL
                UNION
                SELECT COALESCE(external_signal_id::INTEGER, 0)
                FROM polymarket_paper_trades
                WHERE external_signal_id IS NOT NULL
            )
            ORDER BY generated_at DESC
            LIMIT 20
        ''')
        
        real_signals = cur.fetchall()
        
        if not real_signals:
            print("📊 No new real signals to bridge")
            return 0
            
        bridged_count = 0
        
        for signal_id, signal_type, asset, direction, confidence, entry_price, suggested_size, stop_loss, take_profit, reason, generated_at in real_signals:
            
            try:
                if signal_type == 'polymarket_mispricing':
                    # Bridge to Polymarket dashboard table
                    self.bridge_to_polymarket_table(
                        signal_id, asset, direction, confidence, entry_price,
                        suggested_size, reason, generated_at, cur
                    )
                else:
                    # Bridge to HL dashboard table
                    self.bridge_to_hl_table(
                        signal_id, signal_type, asset, direction, confidence, entry_price,
                        suggested_size, stop_loss, take_profit, reason, generated_at, cur
                    )
                    
                bridged_count += 1
                
            except Exception as e:
                print(f"❌ Bridge error for signal {signal_id}: {e}")
                
        conn.commit()
        cur.close()
        conn.close()
        
        if bridged_count > 0:
            print(f"✅ Bridged {bridged_count} real signals to dashboard")
            
        return bridged_count
        
    def bridge_to_hl_table(self, signal_id, signal_type, asset, direction, confidence, 
                          entry_price, suggested_size, stop_loss, take_profit, reason, generated_at, cur):
        """Bridge real HL signal to simple_hl_trades table for dashboard display"""
        
        # Create dashboard-compatible entry (using correct column names)
        cur.execute('''
            INSERT INTO simple_hl_trades
            (coin, side, entry_price, position_size, confidence, 
             entry_time, status, reason, external_signal_id, signal_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            asset, direction, float(entry_price), float(suggested_size), float(confidence),
            generated_at, 'OPEN', f"[REAL-{signal_type.upper()}] {reason}", 
            str(signal_id), float(confidence)
        ))
        
        print(f"🔗 Bridged HL signal: {asset} {direction} (confidence: {confidence:.3f})")
        
    def bridge_to_polymarket_table(self, signal_id, market_id, direction, confidence, 
                                 entry_price, suggested_size, reason, generated_at, cur):
        """Bridge real PM signal to polymarket_paper_trades table for dashboard display"""
        
        # Convert direction to YES/NO
        pick = 'YES' if direction == 'LONG' else 'NO'
        
        # Create dashboard-compatible entry  
        cur.execute('''
            INSERT INTO polymarket_paper_trades
            (market_id, pick, size, confidence, entry_odds, signal_type, 
             picked_at, reason, external_signal_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            market_id, pick, float(suggested_size), float(confidence),
            float(entry_price), 'real_mispricing', generated_at, 
            f"[REAL-MISPRICING] {reason}", str(signal_id)
        ))
        
        print(f"🔗 Bridged PM signal: {market_id[:20]}... {pick} (confidence: {confidence:.3f})")
        
    def update_dashboard_performance_data(self):
        """Update dashboard performance data with real system metrics"""
        
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        # Get real system performance summary
        cur.execute('''
            SELECT 
                COUNT(*) as total_signals,
                AVG(confidence) as avg_confidence,
                COUNT(*) FILTER (WHERE confidence >= 0.7) as high_conf_signals,
                MAX(generated_at) as latest_signal
            FROM real_edge_signals
            WHERE generated_at >= NOW() - INTERVAL '24 hours'
        ''')
        
        result = cur.fetchone()
        if result:
            total, avg_conf, high_conf, latest = result
            
            # Update dashboard state with real system metrics
            cur.execute('''
                INSERT INTO dashboard_state
                (daily_realized_pnl, daily_unrealized_pnl, total_daily_pnl,
                 open_positions, signal_performance_json)
                VALUES (0, 0, 0, %s, %s)
            ''', (
                total,
                json.dumps({
                    'real_system': {
                        'total_signals_24h': total,
                        'avg_confidence': float(avg_conf or 0),
                        'high_conf_signals': high_conf,
                        'latest_signal': latest.isoformat() if latest else None,
                        'system_type': 'claude_real_apis'
                    }
                })
            ))
            
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"📊 Updated dashboard performance data")
        
    def run_bridge_cycle(self):
        """Run complete bridge cycle"""
        print(f"\n🔄 Bridge Cycle - {datetime.now().strftime('%H:%M:%S UTC')}")
        
        # Bridge new signals
        bridged = self.bridge_real_signals_to_dashboard()
        
        # Update performance data
        self.update_dashboard_performance_data()
        
        return bridged
        
    def start_continuous_bridge(self):
        """Start continuous bridging to dashboard"""
        print("🔄 Starting continuous bridge to dashboard...")
        print("📊 Real Claude signals → myhunch.xyz/admin/PM-HL-Trading")
        
        while True:
            try:
                bridged = self.run_bridge_cycle()
                
                # Bridge every 2 minutes to keep dashboard updated
                time.sleep(120)
                
            except KeyboardInterrupt:
                print("\n🛑 Bridge stopped")
                break
            except Exception as e:
                print(f"❌ Bridge error: {e}")
                time.sleep(60)

def main():
    """Test the dashboard bridge"""
    bridge = DashboardBridge()
    
    print("🧪 Testing dashboard bridge...")
    
    # Run one bridge cycle
    bridged = bridge.run_bridge_cycle()
    
    if bridged > 0:
        print(f"✅ Successfully bridged {bridged} signals to dashboard")
        print("🔗 Check dashboard: https://myhunch.xyz/admin/PM-HL-Trading")
    else:
        print("📊 No new signals to bridge (normal if system just started)")
        
    print("\n🎯 Bridge ready for continuous operation")
    print("Run: python3 dashboard_bridge.py to start continuous bridging")
    
    return bridge

if __name__ == "__main__":
    bridge = main()
    
    # Ask if user wants to start continuous bridge
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'continuous':
        bridge.start_continuous_bridge()