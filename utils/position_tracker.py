#!/usr/bin/env python3
"""
POSITION TRACKER
Real-time P&L tracking, stop loss/take profit management, and performance logging
"""

import psycopg2
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class PositionTracker:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Claude's risk management parameters
        self.config = {
            'stop_loss_pct': 4.0,             # Claude's 4% stops
            'take_profit_pct': 7.0,           # Claude's 7% targets
            'partial_profit_pct': 33.3,       # Claude's 33% partial exits
            'max_position_age_hours': 48,     # Auto-close after 48h
            'trailing_stop_trigger': 3.0,     # Start trailing at +3%
            'trailing_stop_distance': 2.0,    # Trail 2% behind peak (VJ's specification)
        }
        
        print("📊 POSITION TRACKER")
        print("=" * 40)
        print("⚡ Real-time P&L tracking")
        print("🛑 Automated stop loss management")
        print("🎯 Take profit execution")
        print("📈 Performance logging and learnings")
        
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions with current prices"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get open positions with current prices
            cur.execute('''
                SELECT 
                    t.id, t.coin, t.side, t.entry_price, t.position_size,
                    t.confidence, t.entry_time, t.external_signal_id,
                    t.max_favorable_price,
                    p.price as current_price
                FROM simple_hl_trades t
                LEFT JOIN LATERAL (
                    SELECT price 
                    FROM real_price_data 
                    WHERE asset = t.coin 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ) p ON true
                WHERE t.status = 'OPEN'
            ''')
            
            positions = []
            for row in cur.fetchall():
                (trade_id, coin, side, entry_price, position_size, 
                 confidence, entry_time, signal_id, max_favorable_price, current_price) = row
                
                if current_price:
                    # Calculate P&L
                    entry_px = float(entry_price)
                    current_px = float(current_price)
                    size = float(position_size)
                    
                    if side == 'LONG':
                        pnl_pct = (current_px - entry_px) / entry_px
                    else:  # SHORT
                        pnl_pct = (entry_px - current_px) / entry_px
                        
                    pnl_usd = size * pnl_pct
                    
                    # Calculate stop loss and take profit prices
                    peak_price = float(max_favorable_price) if max_favorable_price else entry_px
                    
                    # Check if we should use trailing stop
                    profit_pct = pnl_pct * 100
                    use_trailing_stop = profit_pct >= self.config['trailing_stop_trigger']
                    
                    if side == 'LONG':
                        # Original stop loss
                        basic_stop = entry_px * (1 - self.config['stop_loss_pct']/100)
                        
                        # Trailing stop (if profit > 3%)
                        if use_trailing_stop:
                            trailing_stop = peak_price * (1 - self.config['trailing_stop_distance']/100)
                            stop_price = max(basic_stop, trailing_stop)  # Use higher of the two
                        else:
                            stop_price = basic_stop
                            
                        target_price = entry_px * (1 + self.config['take_profit_pct']/100)
                    else:  # SHORT
                        # Original stop loss
                        basic_stop = entry_px * (1 + self.config['stop_loss_pct']/100)
                        
                        # Trailing stop (if profit > 3%)
                        if use_trailing_stop:
                            trailing_stop = peak_price * (1 + self.config['trailing_stop_distance']/100)
                            stop_price = min(basic_stop, trailing_stop)  # Use lower of the two
                        else:
                            stop_price = basic_stop
                            
                        target_price = entry_px * (1 - self.config['take_profit_pct']/100)
                    
                    # Calculate position age
                    age_hours = (datetime.now() - entry_time).total_seconds() / 3600
                    
                    position = {
                        'trade_id': trade_id,
                        'coin': coin,
                        'side': side,
                        'entry_price': entry_px,
                        'current_price': current_px,
                        'position_size': size,
                        'pnl_usd': pnl_usd,
                        'pnl_pct': pnl_pct * 100,
                        'stop_price': stop_price,
                        'target_price': target_price,
                        'confidence': float(confidence or 0),
                        'age_hours': age_hours,
                        'signal_id': signal_id,
                        'entry_time': entry_time,
                        'peak_price': peak_price,
                        'is_trailing': use_trailing_stop
                    }
                    
                    positions.append(position)
                    
            cur.close()
            conn.close()
            
            return positions
            
        except Exception as e:
            print(f"❌ Position fetch error: {e}")
            return []
            
    def check_exit_conditions(self, position: Dict) -> Optional[Dict]:
        """Check if position should be closed"""
        
        # Check stop loss with stop-limit orders (prevent slippage)
        if position['side'] == 'LONG' and position['current_price'] <= position['stop_price']:
            # Use stop-limit: exit at stop price (not current price) to prevent slippage
            exit_price = position['stop_price']
            return {
                'reason': 'STOP_LOSS',
                'exit_price': exit_price,
                'message': f"Stop-limit triggered: exit at ${exit_price:.2f} (4% stop)",
                'order_type': 'stop_limit'
            }
        elif position['side'] == 'SHORT' and position['current_price'] >= position['stop_price']:
            # Use stop-limit: exit at stop price (not current price) to prevent slippage
            exit_price = position['stop_price']
            return {
                'reason': 'STOP_LOSS',
                'exit_price': exit_price,
                'message': f"Stop-limit triggered: exit at ${exit_price:.2f} (4% stop)",
                'order_type': 'stop_limit'
            }
            
        # Check partial profit FIRST (Claude's 33% rule at 7% gain)
        profit_threshold = self.config['take_profit_pct']  # Exactly 7% gain
        if position['pnl_pct'] >= profit_threshold:
            # Check if partial exit already taken
            if not self.has_partial_exit(position['trade_id']):
                return {
                    'reason': 'PARTIAL_PROFIT',
                    'exit_price': position['current_price'],
                    'message': f"Partial profit: {position['pnl_pct']:.2f}% gain",
                    'partial_size': position['position_size'] * (self.config['partial_profit_pct'] / 100),
                    'order_type': 'market'  # Profits can use market orders
                }
            
        # Check full take profit (only after partial has been taken)
        if position['side'] == 'LONG' and position['current_price'] >= position['target_price']:
            return {
                'reason': 'TAKE_PROFIT',
                'exit_price': position['current_price'],
                'message': f"Take profit triggered: {position['pnl_pct']:.2f}% gain",
                'order_type': 'market'  # Profits can use market orders
            }
        elif position['side'] == 'SHORT' and position['current_price'] <= position['target_price']:
            return {
                'reason': 'TAKE_PROFIT',
                'exit_price': position['current_price'],
                'message': f"Take profit triggered: {position['pnl_pct']:.2f}% gain",
                'order_type': 'market'  # Profits can use market orders
            }
            
        # Check position timeout
        if position['age_hours'] >= self.config['max_position_age_hours']:
            return {
                'reason': 'TIMEOUT',
                'exit_price': position['current_price'],
                'message': f"Position timeout: {position['age_hours']:.1f} hours old",
                'order_type': 'market'  # Timeouts use market orders for immediate exit
            }
                
        return None
        
    def has_partial_exit(self, trade_id: int) -> bool:
        """Check if position already had partial exit"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Check if we've recorded any profit levels for this trade
            cur.execute('''
                SELECT profit_levels_taken FROM simple_hl_trades
                WHERE id = %s
            ''', (trade_id,))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result and result[0]:
                profit_levels = result[0] if isinstance(result[0], list) else []
                return len(profit_levels) > 0
                
            return False
            
        except Exception as e:
            print(f"❌ Partial exit check error: {e}")
            return False
            
    def execute_stop_limit_order(self, position: Dict, exit_condition: Dict) -> float:
        """
        Simulate stop-limit order execution
        For stop losses: guarantee the stop price (no slippage)
        For profits/timeouts: use current market price
        """
        order_type = exit_condition.get('order_type', 'market')
        
        if order_type == 'stop_limit' and exit_condition['reason'] == 'STOP_LOSS':
            # Stop-limit: execute at exactly the stop price to prevent slippage
            executed_price = exit_condition['exit_price']  # This is the stop_price
            print(f"🛡️  Stop-limit executed at ${executed_price:.2f} (prevented slippage)")
            return executed_price
        else:
            # Market order: use current price (for profits and timeouts)
            return exit_condition['exit_price']

    def close_position(self, position: Dict, exit_condition: Dict) -> bool:
        """Close position and update database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Execute order with proper order type
            exit_price = self.execute_stop_limit_order(position, exit_condition)
            reason = exit_condition['reason']
            
            # Calculate final P&L
            if position['side'] == 'LONG':
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
            else:
                pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
                
            # Handle partial exits
            if reason == 'PARTIAL_PROFIT':
                partial_size = exit_condition['partial_size']
                partial_pnl = partial_size * pnl_pct
                remaining_size = position['position_size'] - partial_size
                
                # Update position size and record partial exit
                cur.execute('''
                    UPDATE simple_hl_trades
                    SET position_size = %s,
                        profit_levels_taken = COALESCE(profit_levels_taken, '[]'::jsonb) || %s::jsonb
                    WHERE id = %s
                ''', (remaining_size, json.dumps([{
                    'level': '33%',
                    'size': partial_size,
                    'pnl': partial_pnl,
                    'exit_price': exit_price,
                    'exit_time': datetime.now().isoformat()
                }]), position['trade_id']))
                
                # Send partial exit notification
                self.send_exit_notification(position, exit_condition, partial_pnl, partial=True)
                
            else:
                # Full exit
                final_pnl = position['position_size'] * pnl_pct
                
                cur.execute('''
                    UPDATE simple_hl_trades
                    SET status = 'CLOSED',
                        exit_price = %s,
                        exit_time = NOW(),
                        pnl = %s,
                        exit_reason = %s
                    WHERE id = %s
                ''', (exit_price, final_pnl, reason, position['trade_id']))
                
                # Send exit notification
                self.send_exit_notification(position, exit_condition, final_pnl)
                
                # Log learning if significant
                self.log_trade_learning(position, exit_condition, final_pnl)
                
            conn.commit()
            cur.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Position close error: {e}")
            return False
            
    def update_position_pnl(self, position: Dict):
        """Update real-time P&L in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Update unrealized P&L and max favorable/adverse
            cur.execute('''
                UPDATE simple_hl_trades
                SET pnl = %s,
                    max_favorable_price = CASE 
                        WHEN side = 'LONG' THEN GREATEST(COALESCE(max_favorable_price, entry_price), %s)
                        ELSE LEAST(COALESCE(max_favorable_price, entry_price), %s)
                    END
                WHERE id = %s
            ''', (position['pnl_usd'], position['current_price'], position['current_price'], position['trade_id']))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ P&L update error: {e}")
            
    def send_exit_notification(self, position: Dict, exit_condition: Dict, realized_pnl: float, partial: bool = False):
        """Send position exit notification"""
        exit_icons = {
            'STOP_LOSS': '🛑',
            'TAKE_PROFIT': '🎯',
            'PARTIAL_PROFIT': '💰',
            'TIMEOUT': '⏰'
        }
        
        icon = exit_icons.get(exit_condition['reason'], '📊')
        exit_type = "PARTIAL EXIT" if partial else "POSITION CLOSED"
        
        message = f"""{icon} **{exit_type}**

📈 **{position['coin']} {position['side']}**
💰 **Realized P&L: ${realized_pnl:+.2f}**
📊 **Exit Reason:** {exit_condition['message']}

💵 **Entry:** ${position['entry_price']:.4f}
💵 **Exit:** ${exit_condition['exit_price']:.4f}
⏰ **Held:** {position['age_hours']:.1f} hours

🎲 **Signal ID:** {position['signal_id'] or 'N/A'} ({position['confidence']:.1%} confidence)
🔗 **Dashboard:** myhunch.xyz/admin/PM-HL-Trading"""

        try:
            import subprocess
            cmd = ['openclaw', 'message', 'send', '--channel', 'telegram', '--target', '1083598779', '--message', message]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print(f"⚠️ Notification failed: {result.stderr}")
            else:
                print(f"📱 Exit notification sent for {position['coin']} {position['side']}")
        except Exception as e:
            print(f"❌ Notification error: {e}")
            
    def log_trade_learning(self, position: Dict, exit_condition: Dict, realized_pnl: float):
        """Log trade learnings for system improvement"""
        learning_entry = f"""
# Trade Learning - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

## Trade Details
- **Asset:** {position['coin']} {position['side']}
- **Entry:** ${position['entry_price']:.4f} | **Exit:** ${exit_condition['exit_price']:.4f}
- **P&L:** ${realized_pnl:+.2f} ({((realized_pnl/position['position_size'])*100):+.2f}%)
- **Duration:** {position['age_hours']:.1f} hours
- **Exit Reason:** {exit_condition['reason']}

## Signal Performance
- **Signal ID:** {position['signal_id']}
- **Confidence:** {position['confidence']:.1%}
- **Performance vs Confidence:** {'✅ Exceeded' if realized_pnl > 0 else '❌ Underperformed'}

## Key Insights
- **Entry Timing:** {'Good' if abs(position['pnl_pct']) > 2 else 'Could improve'}
- **Exit Trigger:** {exit_condition['message']}
- **Signal Quality:** {'High' if position['confidence'] > 0.7 else 'Medium' if position['confidence'] > 0.6 else 'Low'}

---
"""
        
        # Append to learnings file
        try:
            with open('/home/vj/polymarket/docs/LEARNINGS.md', 'a') as f:
                f.write(learning_entry)
        except:
            pass
            
    def run_tracking_cycle(self):
        """Run one complete position tracking cycle"""
        print(f"\n📊 POSITION TRACKING CYCLE - {datetime.now().strftime('%H:%M:%S UTC')}")
        
        positions = self.get_open_positions()
        
        if not positions:
            print("📊 No open positions to track")
            return {'positions_tracked': 0, 'exits_executed': 0}
            
        print(f"📊 Tracking {len(positions)} open positions")
        
        exits_executed = 0
        
        for position in positions:
            # Update real-time P&L
            self.update_position_pnl(position)
            
            # Check exit conditions
            exit_condition = self.check_exit_conditions(position)
            
            if exit_condition:
                print(f"⚡ Exit trigger: {position['coin']} {position['side']} - {exit_condition['message']}")
                
                if self.close_position(position, exit_condition):
                    exits_executed += 1
                    
            else:
                trailing_indicator = " 🔄" if position.get('is_trailing', False) else ""
                print(f"📈 {position['coin']} {position['side']}: ${position['pnl_usd']:+.2f} ({position['pnl_pct']:+.2f}%){trailing_indicator}")
                
        print(f"✅ Tracking cycle complete: {len(positions)} positions, {exits_executed} exits executed")
        
        return {
            'positions_tracked': len(positions),
            'exits_executed': exits_executed
        }
        
    def start_continuous_tracking(self):
        """Start continuous position tracking"""
        print("🔄 Starting continuous position tracking...")
        print("📊 Checking positions every 30 seconds")
        
        while True:
            try:
                self.run_tracking_cycle()
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                print("\n🛑 Position tracking stopped")
                break
            except Exception as e:
                print(f"❌ Tracking cycle error: {e}")
                time.sleep(60)

def main():
    tracker = PositionTracker()
    
    print("🧪 Testing position tracker...")
    
    result = tracker.run_tracking_cycle()
    
    print(f"\n✅ Tracker test complete: {result}")
    
    return tracker

if __name__ == "__main__":
    import sys
    tracker = PositionTracker()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'continuous':
        tracker.start_continuous_tracking()
    else:
        tracker.run_tracking_cycle()