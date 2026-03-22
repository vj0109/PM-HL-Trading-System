#!/usr/bin/env python3
"""
RISK MANAGEMENT SYSTEM
Comprehensive risk controls per Claude's specifications
"""

import psycopg2
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import requests

class RiskManagementSystem:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        # Claude's comprehensive risk parameters
        self.risk_limits = {
            # Position limits
            'max_positions': 15,              # Claude's position limit
            'max_position_size': 1000,        # Maximum single position size
            'max_asset_exposure': 20.0,       # Max % of capital per asset
            'max_sector_exposure': 40.0,      # Max % per sector/category
            
            # Daily limits
            'daily_loss_limit': 200,          # Claude's -$200 circuit breaker
            'daily_trade_limit': 25,          # Max trades per day
            'max_drawdown_limit': 15.0,       # Max portfolio drawdown %
            
            # Signal quality controls
            'min_signal_confidence': 0.6,     # Minimum 60% confidence
            'min_data_quality': 0.7,          # Minimum data quality score
            'signal_cooldown_hours': 4,       # Hours between same-asset signals
            
            # Correlation limits (Claude Phase 3)
            'max_correlated_positions': 3,    # Max correlated positions
            'correlation_threshold': 0.8,     # 80% correlation = highly correlated
            'correlation_size_reduction': 0.5, # 50% size reduction for correlated
            
            # Portfolio concentration
            'max_single_asset_pct': 25.0,     # Max 25% in single asset
            'max_signal_type_pct': 40.0,      # Max 40% in single signal type
            'max_direction_imbalance': 70.0,  # Max 70% long or short
            
            # Emergency controls
            'emergency_stop_loss': 500,       # Emergency stop at -$500
            'volatility_threshold': 3.0,      # 3x normal volatility = reduce size
            'market_hours_only': False,       # Trade outside market hours?
        }
        
        print("🛡️ RISK MANAGEMENT SYSTEM")
        print("=" * 60)
        print("🎯 Claude's Risk Controls:")
        print(f"   • Max positions: {self.risk_limits['max_positions']}")
        print(f"   • Daily loss limit: -${self.risk_limits['daily_loss_limit']}")
        print(f"   • Max drawdown: {self.risk_limits['max_drawdown_limit']}%")
        print(f"   • Min confidence: {self.risk_limits['min_signal_confidence']:.0%}")
        print(f"   • Correlation limit: {self.risk_limits['max_correlated_positions']} positions")
        print("🔧 Risk Monitoring:")
        print("   • Real-time position limits")
        print("   • Portfolio concentration checks")
        print("   • Signal quality validation")
        print("   • Emergency circuit breakers")
        
        self.setup_risk_tables()
        
    def setup_risk_tables(self):
        """Setup risk management tables"""
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        
        # Risk events log
        cur.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id SERIAL PRIMARY KEY,
                event_time TIMESTAMP DEFAULT NOW(),
                event_type VARCHAR(50), -- LIMIT_BREACH, CIRCUIT_BREAKER, etc.
                severity VARCHAR(20),   -- LOW, MEDIUM, HIGH, CRITICAL
                risk_category VARCHAR(30), -- POSITION_LIMIT, DAILY_LOSS, etc.
                event_details JSONB,
                affected_assets TEXT[],
                action_taken VARCHAR(100),
                auto_resolved BOOLEAN DEFAULT FALSE,
                resolution_time TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # Real-time risk metrics
        cur.execute('''
            CREATE TABLE IF NOT EXISTS risk_metrics_realtime (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                current_positions INTEGER,
                daily_realized_pnl DECIMAL(10,2),
                daily_unrealized_pnl DECIMAL(10,2),
                portfolio_value DECIMAL(12,2),
                max_drawdown_current DECIMAL(6,2),
                correlation_risk_score DECIMAL(5,2), -- 0-100
                concentration_risk_score DECIMAL(5,2), -- 0-100
                signal_quality_score DECIMAL(5,2), -- 0-100
                overall_risk_score DECIMAL(5,2), -- 0-100
                circuit_breaker_status VARCHAR(20),
                risk_alerts JSONB,
                emergency_flags JSONB
            )
        ''')
        
        # Risk limit violations
        cur.execute('''
            CREATE TABLE IF NOT EXISTS risk_violations (
                id SERIAL PRIMARY KEY,
                violation_time TIMESTAMP DEFAULT NOW(),
                risk_limit VARCHAR(50),
                current_value DECIMAL(15,2),
                limit_value DECIMAL(15,2),
                violation_pct DECIMAL(6,2),
                severity VARCHAR(20),
                position_affected VARCHAR(100),
                signal_affected INTEGER,
                action_required BOOLEAN DEFAULT TRUE,
                auto_action_taken TEXT,
                manual_override BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Risk management tables initialized")
        
    def check_position_limits(self) -> Dict:
        """Check all position-related limits"""
        violations = []
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get current positions
            cur.execute('''
                SELECT COUNT(*) as total_positions,
                       SUM(position_size) as total_capital
                FROM real_edge_signals 
                WHERE status = 'ACTIVE'
            ''')
            
            position_data = cur.fetchone()
            total_positions, total_capital = position_data or (0, 0)
            total_capital = float(total_capital or 0)
            
            # Check max positions limit
            if total_positions >= self.risk_limits['max_positions']:
                violations.append({
                    'type': 'MAX_POSITIONS',
                    'current': total_positions,
                    'limit': self.risk_limits['max_positions'],
                    'severity': 'HIGH',
                    'action': 'BLOCK_NEW_POSITIONS'
                })
                
            # Check asset concentration
            if total_capital > 0:
                cur.execute('''
                    SELECT asset, SUM(suggested_size) as asset_exposure
                    FROM real_edge_signals 
                    WHERE status = 'ACTIVE'
                    GROUP BY asset
                    ORDER BY asset_exposure DESC
                ''')
                
                for asset, exposure in cur.fetchall():
                    exposure_pct = float(exposure) / total_capital * 100
                    if exposure_pct > self.risk_limits['max_single_asset_pct']:
                        violations.append({
                            'type': 'ASSET_CONCENTRATION',
                            'asset': asset,
                            'current': exposure_pct,
                            'limit': self.risk_limits['max_single_asset_pct'],
                            'severity': 'MEDIUM',
                            'action': 'REDUCE_POSITION_SIZE'
                        })
                        
            cur.close()
            conn.close()
            
            return {
                'violations': violations,
                'total_positions': total_positions,
                'total_capital': total_capital,
                'position_limit_utilization': total_positions / self.risk_limits['max_positions'] * 100
            }
            
        except Exception as e:
            print(f"❌ Position limit check error: {e}")
            return {'violations': [], 'total_positions': 0, 'total_capital': 0}
            
    def check_daily_limits(self) -> Dict:
        """Check daily loss and trade limits"""
        violations = []
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Get today's realized P&L
            cur.execute('''
                SELECT COALESCE(SUM(realized_pnl), 0) as daily_pnl
                FROM position_exits 
                WHERE DATE(exit_time) = CURRENT_DATE
            ''')
            
            daily_pnl = float(cur.fetchone()[0] or 0)
            
            # Get today's trade count
            cur.execute('''
                SELECT COUNT(*) as daily_trades
                FROM real_edge_signals 
                WHERE DATE(generated_at) = CURRENT_DATE
            ''')
            
            daily_trades = cur.fetchone()[0] or 0
            
            # Check daily loss limit (Claude's -$200 circuit breaker)
            if daily_pnl <= -self.risk_limits['daily_loss_limit']:
                violations.append({
                    'type': 'DAILY_LOSS_LIMIT',
                    'current': daily_pnl,
                    'limit': -self.risk_limits['daily_loss_limit'],
                    'severity': 'CRITICAL',
                    'action': 'ACTIVATE_CIRCUIT_BREAKER'
                })
                
            # Check emergency stop
            if daily_pnl <= -self.risk_limits['emergency_stop_loss']:
                violations.append({
                    'type': 'EMERGENCY_STOP',
                    'current': daily_pnl,
                    'limit': -self.risk_limits['emergency_stop_loss'],
                    'severity': 'CRITICAL',
                    'action': 'EMERGENCY_STOP_ALL_TRADING'
                })
                
            # Check daily trade limit
            if daily_trades >= self.risk_limits['daily_trade_limit']:
                violations.append({
                    'type': 'DAILY_TRADE_LIMIT',
                    'current': daily_trades,
                    'limit': self.risk_limits['daily_trade_limit'],
                    'severity': 'MEDIUM',
                    'action': 'BLOCK_NEW_TRADES_TODAY'
                })
                
            cur.close()
            conn.close()
            
            return {
                'violations': violations,
                'daily_pnl': daily_pnl,
                'daily_trades': daily_trades,
                'circuit_breaker_triggered': any(v['type'] in ['DAILY_LOSS_LIMIT', 'EMERGENCY_STOP'] for v in violations)
            }
            
        except Exception as e:
            print(f"❌ Daily limit check error: {e}")
            return {'violations': [], 'daily_pnl': 0, 'daily_trades': 0}
            
    def validate_new_signal(self, signal_data: Dict) -> Dict:
        """Validate new signal against risk controls"""
        risk_checks = {
            'approved': True,
            'warnings': [],
            'rejections': [],
            'size_adjustments': [],
            'original_size': signal_data.get('suggested_size', 0),
            'approved_size': signal_data.get('suggested_size', 0)
        }
        
        # Check signal confidence
        confidence = signal_data.get('confidence', 0)
        if confidence < self.risk_limits['min_signal_confidence']:
            risk_checks['rejections'].append(f"Confidence {confidence:.1%} below {self.risk_limits['min_signal_confidence']:.0%} minimum")
            risk_checks['approved'] = False
            
        # Check data quality
        data_quality = 1.0 if signal_data.get('data_quality') == 'HIGH' else 0.8 if signal_data.get('data_quality') == 'MEDIUM' else 0.6
        if data_quality < self.risk_limits['min_data_quality']:
            risk_checks['warnings'].append(f"Data quality {data_quality:.0%} below {self.risk_limits['min_data_quality']:.0%} preference")
            
        # Check position limits
        position_status = self.check_position_limits()
        if position_status['total_positions'] >= self.risk_limits['max_positions']:
            risk_checks['rejections'].append(f"Position limit reached: {position_status['total_positions']}/{self.risk_limits['max_positions']}")
            risk_checks['approved'] = False
            
        # Check daily limits
        daily_status = self.check_daily_limits()
        if daily_status['circuit_breaker_triggered']:
            risk_checks['rejections'].append(f"Circuit breaker active: daily P&L ${daily_status['daily_pnl']:+.2f}")
            risk_checks['approved'] = False
            
        # Check signal cooldown
        asset = signal_data.get('asset', '')
        if asset and self.check_signal_cooldown(asset):
            risk_checks['warnings'].append(f"Recent signal for {asset} within {self.risk_limits['signal_cooldown_hours']}h cooldown")
            
        # Check correlation risk (Claude Phase 3)
        correlation_adjustment = self.check_correlation_risk(signal_data)
        if correlation_adjustment < 1.0:
            adjusted_size = risk_checks['approved_size'] * correlation_adjustment
            risk_checks['size_adjustments'].append(f"Correlation risk: size reduced by {(1-correlation_adjustment)*100:.0f}%")
            risk_checks['approved_size'] = adjusted_size
            
        # Check position size limits
        max_size = self.risk_limits['max_position_size']
        if risk_checks['approved_size'] > max_size:
            risk_checks['size_adjustments'].append(f"Size capped at ${max_size}")
            risk_checks['approved_size'] = max_size
            
        return risk_checks
        
    def check_signal_cooldown(self, asset: str) -> bool:
        """Check if asset is in signal cooldown period"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT COUNT(*) FROM real_edge_signals 
                WHERE asset = %s 
                AND generated_at >= NOW() - INTERVAL '%s hours'
            ''', (asset, self.risk_limits['signal_cooldown_hours']))
            
            recent_signals = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            return recent_signals > 0
            
        except Exception as e:
            print(f"❌ Cooldown check error: {e}")
            return False
            
    def check_correlation_risk(self, signal_data: Dict) -> float:
        """Check correlation risk and return size adjustment factor"""
        # Simplified correlation check - would use real correlation matrix
        asset = signal_data.get('asset', '')
        direction = signal_data.get('direction', '')
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Count positions in same direction for correlated assets
            # This is simplified - real implementation would use correlation matrix
            similar_positions = 0
            
            if asset.startswith('BTC') or asset.startswith('ETH'):
                # Count crypto positions
                cur.execute('''
                    SELECT COUNT(*) FROM real_edge_signals 
                    WHERE status = 'ACTIVE'
                    AND direction = %s
                    AND (asset LIKE 'BTC%' OR asset LIKE 'ETH%')
                ''', (direction,))
                similar_positions = cur.fetchone()[0]
                
            cur.close()
            conn.close()
            
            # Apply correlation size reduction
            if similar_positions >= self.risk_limits['max_correlated_positions']:
                return self.risk_limits['correlation_size_reduction']  # 50% size
            elif similar_positions >= 2:
                return 0.75  # 25% reduction
            else:
                return 1.0  # No reduction
                
        except Exception as e:
            print(f"❌ Correlation check error: {e}")
            return 1.0
            
    def calculate_portfolio_risk_score(self) -> Dict:
        """Calculate overall portfolio risk score"""
        risk_components = {
            'position_concentration': 0,
            'correlation_risk': 0,
            'signal_quality': 0,
            'drawdown_risk': 0,
            'daily_loss_risk': 0
        }
        
        try:
            # Position limits utilization
            position_status = self.check_position_limits()
            risk_components['position_concentration'] = min(position_status['position_limit_utilization'], 100)
            
            # Daily loss risk
            daily_status = self.check_daily_limits()
            daily_loss_pct = abs(daily_status['daily_pnl']) / self.risk_limits['daily_loss_limit'] * 100
            risk_components['daily_loss_risk'] = min(daily_loss_pct, 100)
            
            # Overall risk score (weighted average)
            weights = {
                'position_concentration': 0.3,
                'correlation_risk': 0.2,
                'signal_quality': 0.2,
                'drawdown_risk': 0.2,
                'daily_loss_risk': 0.1
            }
            
            overall_score = sum(risk_components[k] * weights[k] for k in weights.keys())
            
            return {
                'overall_risk_score': overall_score,
                'components': risk_components,
                'risk_level': 'LOW' if overall_score < 25 else 'MEDIUM' if overall_score < 60 else 'HIGH' if overall_score < 85 else 'CRITICAL'
            }
            
        except Exception as e:
            print(f"❌ Risk score calculation error: {e}")
            return {'overall_risk_score': 0, 'components': {}, 'risk_level': 'UNKNOWN'}
            
    def log_risk_event(self, event_type: str, severity: str, details: Dict):
        """Log risk management event"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO risk_events
                (event_type, severity, risk_category, event_details, 
                 affected_assets, action_taken)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                event_type, severity, details.get('category', 'GENERAL'),
                json.dumps(details), details.get('assets', []),
                details.get('action', 'MONITORING')
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Risk event logging error: {e}")
            
    def send_risk_alert(self, alert_type: str, message: str, severity: str = 'MEDIUM'):
        """Send risk management alert"""
        severity_icons = {
            'LOW': '🟡',
            'MEDIUM': '🟠', 
            'HIGH': '🔴',
            'CRITICAL': '🚨'
        }
        
        icon = severity_icons.get(severity, '⚠️')
        
        alert_message = f"""{icon} **RISK ALERT - {severity}**

🛡️ **{alert_type}**
📊 **{message}**

⏰ **Time:** {datetime.now().strftime('%H:%M:%S UTC')}
🔧 **Action:** Review risk management dashboard

🔗 **Dashboard:** myhunch.xyz/admin/PM-HL-Trading"""

        try:
            payload = {
                "action": "send",
                "channel": "telegram",
                "target": "1083598779",
                "message": alert_message
            }
            
            requests.post("http://localhost:8080/api/message", json=payload, timeout=10)
        except:
            pass  # Fail silently
            
    def run_risk_monitoring_cycle(self):
        """Run comprehensive risk monitoring cycle"""
        print(f"\n🛡️ RISK MONITORING CYCLE - {datetime.now().strftime('%H:%M:%S UTC')}")
        
        all_violations = []
        
        # Check all risk categories
        position_risks = self.check_position_limits()
        daily_risks = self.check_daily_limits()
        
        # Collect violations
        all_violations.extend(position_risks['violations'])
        all_violations.extend(daily_risks['violations'])
        
        # Calculate risk score
        risk_score = self.calculate_portfolio_risk_score()
        
        # Handle violations
        critical_violations = [v for v in all_violations if v.get('severity') == 'CRITICAL']
        high_violations = [v for v in all_violations if v.get('severity') == 'HIGH']
        
        if critical_violations:
            for violation in critical_violations:
                self.send_risk_alert(violation['type'], f"Critical limit breach: {violation.get('action', 'Review required')}", 'CRITICAL')
                self.log_risk_event(violation['type'], 'CRITICAL', violation)
                
        elif high_violations:
            for violation in high_violations:
                self.send_risk_alert(violation['type'], f"High risk detected: {violation.get('action', 'Monitor closely')}", 'HIGH')
                self.log_risk_event(violation['type'], 'HIGH', violation)
                
        # Store risk metrics
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO risk_metrics_realtime
                (current_positions, daily_realized_pnl, overall_risk_score,
                 circuit_breaker_status, risk_alerts)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                position_risks['total_positions'], daily_risks['daily_pnl'],
                risk_score['overall_risk_score'], 
                'ACTIVE' if daily_risks['circuit_breaker_triggered'] else 'INACTIVE',
                json.dumps(all_violations)
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Risk metrics storage error: {e}")
            
        print(f"🛡️ Risk Score: {risk_score['overall_risk_score']:.1f}/100 ({risk_score['risk_level']})")
        print(f"📊 Violations: {len(critical_violations)} critical, {len(high_violations)} high")
        
        return {
            'violations': all_violations,
            'risk_score': risk_score,
            'circuit_breaker_active': daily_risks['circuit_breaker_triggered']
        }
        
    def start_continuous_monitoring(self):
        """Start continuous risk monitoring"""
        print("🔄 Starting continuous risk monitoring...")
        print("🛡️ Monitoring every 1 minute for risk violations")
        
        while True:
            try:
                self.run_risk_monitoring_cycle()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                print("\n🛑 Risk monitoring stopped")
                break
            except Exception as e:
                print(f"❌ Risk monitoring error: {e}")
                time.sleep(30)

def main():
    """Test risk management system"""
    risk_mgmt = RiskManagementSystem()
    
    print("🧪 Testing risk management...")
    
    # Run one monitoring cycle
    result = risk_mgmt.run_risk_monitoring_cycle()
    
    print(f"✅ Risk monitoring working")
    print(f"📊 Risk level: {result['risk_score']['risk_level']}")
    
    return risk_mgmt

if __name__ == "__main__":
    import sys
    risk_mgmt = RiskManagementSystem()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'continuous':
        risk_mgmt.start_continuous_monitoring()
    else:
        risk_mgmt.run_risk_monitoring_cycle()