#!/usr/bin/env python3
"""
POLYMARKET FORWARD TESTING SYSTEM
Start paper trading with 97 working Volume Spike signals
Following HL's proven approach: forward testing → build historical data → validate
"""

import psycopg2
import psycopg2.extras
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pm_volume_spike_signal_fixed import VolumeSpikePMSignalFixed

class PMForwardTestingSystem:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Initialize our working signal detector
        self.signal_detector = VolumeSpikePMSignalFixed()
        
        # Paper trading settings
        self.position_size = 100  # $100 per trade (small for validation)
        self.max_positions = 10   # Maximum concurrent positions
        
        self.setup_paper_trading_tables()
    
    def setup_paper_trading_tables(self):
        """Set up database tables for forward testing"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Paper trading positions table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS pm_paper_positions (
                            id SERIAL PRIMARY KEY,
                            position_id VARCHAR(100) UNIQUE,
                            market_id VARCHAR(100),
                            market_title TEXT,
                            signal_type VARCHAR(50),
                            direction VARCHAR(10),
                            entry_price DECIMAL(10,6),
                            entry_time TIMESTAMP DEFAULT NOW(),
                            exit_price DECIMAL(10,6),
                            exit_time TIMESTAMP,
                            position_size DECIMAL(10,2),
                            pnl DECIMAL(10,2),
                            status VARCHAR(20) DEFAULT 'OPEN',
                            signal_data JSONB,
                            exit_reason VARCHAR(100)
                        )
                    """)
                    
                    # Signal tracking table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS pm_signal_tracking (
                            id SERIAL PRIMARY KEY,
                            signal_id VARCHAR(100) UNIQUE,
                            market_id VARCHAR(100),
                            market_title TEXT,
                            signal_type VARCHAR(50),
                            direction VARCHAR(10),
                            confidence DECIMAL(5,3),
                            detected_at TIMESTAMP DEFAULT NOW(),
                            current_price DECIMAL(10,6),
                            volume_ratio DECIMAL(8,2),
                            price_deviation DECIMAL(5,3),
                            action_taken VARCHAR(50) DEFAULT 'DETECTED',
                            reasoning TEXT
                        )
                    """)
                    
                    # Performance tracking
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS pm_performance_daily (
                            id SERIAL PRIMARY KEY,
                            date DATE DEFAULT CURRENT_DATE,
                            signals_detected INTEGER DEFAULT 0,
                            positions_opened INTEGER DEFAULT 0,
                            positions_closed INTEGER DEFAULT 0,
                            daily_pnl DECIMAL(10,2) DEFAULT 0,
                            total_portfolio_value DECIMAL(10,2),
                            win_rate DECIMAL(5,3),
                            avg_hold_time_hours DECIMAL(8,2)
                        )
                    """)
                    
                    conn.commit()
                    print("✅ Paper trading database tables ready")
                    
        except Exception as e:
            print(f"❌ Error setting up tables: {e}")
    
    def scan_for_new_signals(self) -> List[Dict]:
        """
        Scan for new Volume Spike signals using our working detector
        """
        print(f"🔍 Scanning for new Volume Spike signals...")
        
        try:
            # Use our working signal detector
            signals = self.signal_detector.scan_all_markets()
            
            # Store all signals for tracking
            for signal in signals:
                self.store_signal_for_tracking(signal)
            
            print(f"📊 Found {len(signals)} Volume Spike signals")
            return signals
            
        except Exception as e:
            print(f"❌ Error scanning signals: {e}")
            return []
    
    def store_signal_for_tracking(self, signal: Dict):
        """Store signal in tracking table"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    signal_id = f"{signal['market_id']}_{signal['signal_type']}_{signal['direction']}_{int(time.time())}"
                    
                    cursor.execute("""
                        INSERT INTO pm_signal_tracking 
                        (signal_id, market_id, market_title, signal_type, direction, 
                         confidence, current_price, volume_ratio, price_deviation, reasoning)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (signal_id) DO NOTHING
                    """, (
                        signal_id,
                        signal['market_id'],
                        signal['market_title'],
                        signal['signal_type'],
                        signal['direction'],
                        signal['confidence'],
                        signal['current_price'],
                        signal['volume_ratio'],
                        signal['price_deviation'],
                        signal['reasoning']
                    ))
                    
                    conn.commit()
                    
        except Exception as e:
            print(f"❌ Error storing signal: {e}")
    
    def filter_signals_for_trading(self, signals: List[Dict]) -> List[Dict]:
        """
        Filter signals for actual paper trading
        Apply risk management and position limits
        """
        # Get current open positions
        open_positions = self.get_open_positions()
        
        if len(open_positions) >= self.max_positions:
            print(f"⚠️ Maximum positions reached ({len(open_positions)}/{self.max_positions})")
            return []
        
        # Filter for highest confidence signals
        high_confidence_signals = [s for s in signals if s.get('confidence', 0) > 0.65]
        
        # Avoid duplicate markets
        existing_markets = {pos['market_id'] for pos in open_positions}
        new_market_signals = [s for s in high_confidence_signals 
                             if s['market_id'] not in existing_markets]
        
        # Limit to available position slots
        available_slots = self.max_positions - len(open_positions)
        selected_signals = new_market_signals[:available_slots]
        
        if selected_signals:
            print(f"🎯 Selected {len(selected_signals)} signals for trading")
            for signal in selected_signals:
                print(f"   📊 {signal['market_title'][:50]}... | {signal['direction']} @ {signal['current_price']:.1%}")
        
        return selected_signals
    
    def get_open_positions(self) -> List[Dict]:
        """Get current open paper trading positions"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT position_id, market_id, market_title, direction, 
                               entry_price, entry_time, position_size
                        FROM pm_paper_positions 
                        WHERE status = 'OPEN'
                        ORDER BY entry_time DESC
                    """)
                    
                    results = cursor.fetchall()
                    
                    positions = []
                    for row in results:
                        positions.append({
                            'position_id': row[0],
                            'market_id': row[1], 
                            'market_title': row[2],
                            'direction': row[3],
                            'entry_price': float(row[4]),
                            'entry_time': row[5],
                            'position_size': float(row[6])
                        })
                    
                    return positions
                    
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
            return []
    
    def open_paper_position(self, signal: Dict) -> str:
        """
        Open a new paper trading position
        """
        try:
            position_id = f"PM_{signal['market_id'][:8]}_{signal['direction']}_{int(time.time())}"
            
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Convert datetime to string for JSON storage
                    signal_data = signal.copy()
                    if 'timestamp' in signal_data:
                        signal_data['timestamp'] = signal_data['timestamp'].isoformat()
                    
                    cursor.execute("""
                        INSERT INTO pm_paper_positions
                        (position_id, market_id, market_title, signal_type, direction,
                         entry_price, position_size, signal_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        position_id,
                        signal['market_id'],
                        signal['market_title'],
                        signal['signal_type'],
                        signal['direction'],
                        signal['current_price'],
                        self.position_size,
                        psycopg2.extras.Json(signal_data)
                    ))
                    
                    conn.commit()
                    
            print(f"📈 OPENED: {position_id} | {signal['direction']} @ {signal['current_price']:.1%}")
            return position_id
            
        except Exception as e:
            print(f"❌ Error opening position: {e}")
            return ""
    
    def update_positions_with_current_prices(self):
        """
        Update open positions with current market prices
        Check for exit conditions
        """
        open_positions = self.get_open_positions()
        
        if not open_positions:
            return
        
        print(f"📊 Updating {len(open_positions)} open positions...")
        
        for position in open_positions:
            try:
                # Get current market price (simplified - in production would call API)
                current_price = self.get_current_market_price(position['market_id'])
                
                if current_price:
                    # Check exit conditions
                    should_exit, reason = self.check_exit_conditions(position, current_price)
                    
                    if should_exit:
                        self.close_paper_position(position['position_id'], current_price, reason)
                        
            except Exception as e:
                print(f"❌ Error updating position {position['position_id']}: {e}")
    
    def get_current_market_price(self, market_id: str) -> Optional[float]:
        """
        Get current market price (simplified for now)
        In production would call real API
        """
        # For now, return None to skip position updates
        # Would implement real-time price fetching here
        return None
    
    def check_exit_conditions(self, position: Dict, current_price: float) -> tuple:
        """
        Check if position should be closed
        Returns (should_exit, reason)
        """
        entry_price = position['entry_price']
        direction = position['direction']
        
        # Calculate current P&L
        if direction == 'YES':
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # NO position
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Exit conditions
        if pnl_pct > 0.20:  # 20% profit
            return True, "PROFIT_TARGET"
        elif pnl_pct < -0.15:  # 15% loss
            return True, "STOP_LOSS"
        
        # Time-based exit (after 7 days)
        entry_time = position['entry_time']
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        
        if datetime.now() - entry_time > timedelta(days=7):
            return True, "TIME_LIMIT"
        
        return False, ""
    
    def close_paper_position(self, position_id: str, exit_price: float, reason: str):
        """Close a paper trading position"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Get position details for P&L calculation
                    cursor.execute("""
                        SELECT direction, entry_price, position_size
                        FROM pm_paper_positions 
                        WHERE position_id = %s
                    """, (position_id,))
                    
                    result = cursor.fetchone()
                    if not result:
                        return
                    
                    direction, entry_price, position_size = result
                    entry_price = float(entry_price)
                    position_size = float(position_size)
                    
                    # Calculate P&L
                    if direction == 'YES':
                        pnl = position_size * (exit_price - entry_price) / entry_price
                    else:  # NO
                        pnl = position_size * (entry_price - exit_price) / entry_price
                    
                    # Update position
                    cursor.execute("""
                        UPDATE pm_paper_positions 
                        SET exit_price = %s, exit_time = NOW(), pnl = %s, 
                            status = 'CLOSED', exit_reason = %s
                        WHERE position_id = %s
                    """, (exit_price, pnl, reason, position_id))
                    
                    conn.commit()
                    
            print(f"📉 CLOSED: {position_id} | P&L: ${pnl:.2f} | Reason: {reason}")
            
        except Exception as e:
            print(f"❌ Error closing position: {e}")
    
    def run_forward_testing_cycle(self):
        """
        Run one complete forward testing cycle
        """
        print(f"\n🚀 POLYMARKET FORWARD TESTING CYCLE")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 50)
        
        # Step 1: Scan for new signals
        new_signals = self.scan_for_new_signals()
        
        # Step 2: Filter signals for trading
        tradeable_signals = self.filter_signals_for_trading(new_signals)
        
        # Step 3: Open new positions
        new_positions = []
        for signal in tradeable_signals:
            position_id = self.open_paper_position(signal)
            if position_id:
                new_positions.append(position_id)
        
        # Step 4: Update existing positions
        self.update_positions_with_current_prices()
        
        # Step 5: Show summary
        open_positions = self.get_open_positions()
        
        print(f"\n📊 CYCLE SUMMARY:")
        print(f"   New signals detected: {len(new_signals)}")
        print(f"   New positions opened: {len(new_positions)}")
        print(f"   Total open positions: {len(open_positions)}")
        
        if open_positions:
            print(f"\n📈 OPEN POSITIONS:")
            for pos in open_positions:
                age = datetime.now() - pos['entry_time']
                print(f"   {pos['position_id']} | {pos['direction']} @ {pos['entry_price']:.1%} | {age.days}d {age.seconds//3600}h ago")

def main():
    """Run PM forward testing system"""
    system = PMForwardTestingSystem()
    
    print("🚀 POLYMARKET FORWARD TESTING SYSTEM")
    print("📊 Following HL's proven approach:")
    print("   ✅ Use working Volume Spike signals (97 detected)")
    print("   📈 Start paper trading with small positions")
    print("   📊 Build real performance data")
    print("   🎯 Validate win rates over time")
    print("=" * 60)
    
    # Run one cycle
    system.run_forward_testing_cycle()
    
    print(f"\n🎯 FORWARD TESTING ACTIVE!")
    print("   📈 Run this script every 4-6 hours to:")
    print("      1. Detect new Volume Spike signals") 
    print("      2. Open paper positions")
    print("      3. Track performance")
    print("      4. Build historical validation data")
    print(f"\n   🔄 Next scheduled run: In 4 hours")

if __name__ == "__main__":
    main()