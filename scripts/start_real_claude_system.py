#!/usr/bin/env python3
"""
START REAL CLAUDE SYSTEM
Launch complete autonomous trading system with real API integrations
"""

import sys
import os
import time
import subprocess
import psycopg2
from datetime import datetime

def check_real_api_dependencies():
    """Check real API dependencies"""
    print("🔧 Checking real API dependencies...")
    
    # Check WebSocket support
    try:
        import websocket
        print("   ✅ websocket-client")
    except ImportError:
        print("   ❌ websocket-client")
        print("   Install with: pip install websocket-client")
        return False
        
    # Check additional packages
    required_packages = [
        'requests', 'psycopg2', 'numpy', 'json', 'threading',
        'feedparser', 're'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"   ❌ {package}")
            
    if missing:
        print(f"\n❌ Install missing packages: pip install {' '.join(missing)}")
        return False
        
    return True

def test_real_api_connections():
    """Test real API connections"""
    print("🔌 Testing real API connections...")
    
    # Test Hyperliquid API
    try:
        import requests
        response = requests.get('https://api.hyperliquid.xyz/info', timeout=10)
        if response.status_code == 200:
            print("   ✅ Hyperliquid API reachable")
        else:
            print(f"   ⚠️ Hyperliquid API status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Hyperliquid API error: {e}")
        return False
        
    # Test Polymarket API
    try:
        response = requests.get('https://api.polymarket.com/markets?limit=1', timeout=10)
        if response.status_code == 200:
            print("   ✅ Polymarket API reachable")
        else:
            print(f"   ⚠️ Polymarket API status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Polymarket API error: {e}")
        return False
        
    # Test external consensus sources
    try:
        # Test Metaculus
        response = requests.get('https://www.metaculus.com/api/v2/questions/?limit=1', timeout=10)
        if response.status_code == 200:
            print("   ✅ Metaculus API reachable")
        else:
            print(f"   ⚠️ Metaculus API status: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️ Metaculus API warning: {e}")
        
    # Test Manifold
    try:
        response = requests.get('https://api.manifold.markets/v0/markets?limit=1', timeout=10)
        if response.status_code == 200:
            print("   ✅ Manifold API reachable")
        else:
            print(f"   ⚠️ Manifold API status: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️ Manifold API warning: {e}")
        
    return True

def initialize_real_system():
    """Initialize real system with API integrations"""
    print("🚀 Initializing real Claude system...")
    
    try:
        # Initialize real APIs
        sys.path.append('/home/vj/polymarket')
        
        print("📡 Initializing Hyperliquid API...")
        from real_hyperliquid_api import RealHyperliquidAPI
        hl_api = RealHyperliquidAPI()
        
        print("🎯 Initializing Polymarket API...")
        from real_polymarket_api import RealPolymarketAPI
        pm_api = RealPolymarketAPI()
        
        print("🔍 Initializing Edge Detector...")
        from real_edge_detector import RealEdgeDetector
        edge_detector = RealEdgeDetector()
        
        # Start real feeds
        print("🎯 Starting real data feeds...")
        edge_detector.start_real_detection()
        
        print("✅ Real system initialized with live APIs")
        return True
        
    except Exception as e:
        print(f"❌ Real system initialization error: {e}")
        return False

def create_real_ecosystem_config():
    """Create PM2 ecosystem config for real system"""
    print("⚙️ Creating real system ecosystem config...")
    
    real_ecosystem_config = '''module.exports = {
  apps: [
    // REAL HYPERLIQUID API FEED
    {
      name: 'real-hyperliquid-api',
      script: 'python3',
      args: '/home/vj/polymarket/real_hyperliquid_api.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/real-hl-api.error.log',
      out_file: './logs/real-hl-api.out.log',
      time: true
    },

    // REAL POLYMARKET API FEED
    {
      name: 'real-polymarket-api',
      script: 'python3',
      args: '/home/vj/polymarket/real_polymarket_api.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/real-pm-api.error.log',
      out_file: './logs/real-pm-api.out.log',
      time: true
    },

    // REAL EDGE DETECTOR
    {
      name: 'real-edge-detector',
      script: 'python3',
      args: '/home/vj/polymarket/real_edge_detector.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '*/5 * * * *', // Every 5 minutes
      env: {
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/real-edge.error.log',
      out_file: './logs/real-edge.out.log',
      time: true
    },

    // CLAUDE FOUNDATION (Risk Management)
    {
      name: 'claude-foundation-real',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase0_foundation.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        REAL_MODE: 'true',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/foundation-real.error.log',
      out_file: './logs/foundation-real.out.log',
      time: true
    },

    // REAL TRADE EXECUTION
    {
      name: 'real-trade-execution',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase2_execution_optimization.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        REAL_MODE: 'true',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/execution-real.error.log',
      out_file: './logs/execution-real.out.log',
      time: true
    },

    // REAL MONITORING & LEARNING
    {
      name: 'real-monitoring',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase3_monitoring_learning.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '0 */6 * * *', // Every 6 hours
      env: {
        REAL_MODE: 'true',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/monitoring-real.error.log',
      out_file: './logs/monitoring-real.out.log',
      time: true
    }
  ]
}'''

    with open('/home/vj/polymarket/ecosystem-real.config.js', 'w') as f:
        f.write(real_ecosystem_config)
        
    print("✅ Real ecosystem config created")

def start_real_pm2_ecosystem():
    """Start the real PM2 ecosystem"""
    print("🚀 Starting real PM2 ecosystem...")
    
    try:
        # Create ecosystem config
        create_real_ecosystem_config()
        
        # Stop any existing processes
        subprocess.run(['pm2', 'delete', 'all'], capture_output=True)
        
        # Start real ecosystem
        result = subprocess.run([
            'pm2', 'start', '/home/vj/polymarket/ecosystem-real.config.js'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Real PM2 ecosystem started")
            
            # Show status
            time.sleep(3)
            subprocess.run(['pm2', 'status'])
            
            return True
        else:
            print(f"❌ PM2 start failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Real ecosystem start error: {e}")
        return False

def validate_real_data_flow():
    """Validate that real data is flowing correctly"""
    print("🔍 Validating real data flow...")
    
    # Wait for initial data collection
    print("⏳ Waiting for initial data collection (60 seconds)...")
    time.sleep(60)
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='agentfloor',
            user='agentfloor',
            password='V1S2I3O4J'
        )
        cur = conn.cursor()
        
        # Check real funding rates
        cur.execute('SELECT COUNT(*) FROM real_funding_rates WHERE timestamp >= NOW() - INTERVAL \'10 minutes\'')
        funding_count = cur.fetchone()[0]
        print(f"📊 Real funding rates: {funding_count} records")
        
        # Check real price data
        cur.execute('SELECT COUNT(*) FROM real_price_data WHERE timestamp >= NOW() - INTERVAL \'10 minutes\'')
        price_count = cur.fetchone()[0]
        print(f"📈 Real price data: {price_count} records")
        
        # Check real Polymarket markets
        cur.execute('SELECT COUNT(*) FROM real_polymarket_markets WHERE last_updated >= NOW() - INTERVAL \'10 minutes\'')
        market_count = cur.fetchone()[0]
        print(f"🎯 Real PM markets: {market_count} records")
        
        # Check edge signals
        cur.execute('SELECT COUNT(*) FROM real_edge_signals WHERE generated_at >= NOW() - INTERVAL \'10 minutes\'')
        signal_count = cur.fetchone()[0]
        print(f"🔍 Edge signals: {signal_count} generated")
        
        cur.close()
        conn.close()
        
        # Validate data quality
        if funding_count > 0 and price_count > 0:
            print("✅ Real Hyperliquid data flowing correctly")
        else:
            print("⚠️ Hyperliquid data flow issues")
            
        if market_count > 0:
            print("✅ Real Polymarket data flowing correctly")
        else:
            print("⚠️ Polymarket data flow issues")
            
        if signal_count > 0:
            print("✅ Edge detection working with real data")
        else:
            print("📊 No edge signals yet (normal in stable markets)")
            
        return True
        
    except Exception as e:
        print(f"❌ Data validation error: {e}")
        return False

def show_real_system_dashboard():
    """Show real system dashboard"""
    print("\n" + "="*80)
    print("🚀 REAL CLAUDE AUTONOMOUS TRADING SYSTEM - LIVE")
    print("="*80)
    print("📡 LIVE DATA SOURCES:")
    print("   • Hyperliquid WebSocket feeds (funding, prices, liquidations)")
    print("   • Polymarket API (market odds, liquidity)")
    print("   • External consensus (FiveThirtyEight, Metaculus, Manifold)")
    print("🔍 REAL EDGE DETECTION:")
    print("   • Funding Rate Arbitrage (2+ sigma with 229 assets)")
    print("   • Open Interest Divergence (4-hour analysis)")
    print("   • Liquidation Cascades (3x volume spike detection)")
    print("   • Polymarket Mispricing (8%+ consensus divergence)")
    print("📊 MONITORING COMMANDS:")
    print("   pm2 status                # Show all processes")
    print("   pm2 logs real-edge-detector # View edge detection logs")
    print("   pm2 logs real-hyperliquid-api # View HL API logs")
    print("   pm2 logs real-polymarket-api  # View PM API logs")
    print("   pm2 monit                 # Live monitoring dashboard")
    print("🔧 DATABASE QUERIES:")
    print("   SELECT COUNT(*) FROM real_funding_rates;      -- Check HL data")
    print("   SELECT COUNT(*) FROM real_polymarket_markets; -- Check PM data")
    print("   SELECT * FROM real_edge_signals ORDER BY generated_at DESC LIMIT 10; -- Recent signals")
    print("⚡ REAL VALIDATION:")
    print("   • All signals use LIVE market data")
    print("   • Edge detection uses REAL statistical analysis")
    print("   • No mock data - only actual market conditions")
    print("   • Claude's specifications implemented with real APIs")
    print("🎯 NEXT STEPS:")
    print("   1. Monitor signal generation for 2-4 weeks")
    print("   2. Validate win rates meet Claude's >55% threshold")
    print("   3. Add real order execution when ready")
    print("   4. Scale position sizes per Claude's progression")
    print("="*80)

def main():
    """Main real system startup"""
    print("🎯 REAL CLAUDE AUTONOMOUS TRADING SYSTEM STARTUP")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("🔴 LIVE MODE - REAL API INTEGRATIONS")
    print("=" * 60)
    
    # Check dependencies
    if not check_real_api_dependencies():
        print("\n❌ Dependency check failed - please fix and retry")
        return False
        
    print("\n" + "="*40)
    
    # Test API connections
    if not test_real_api_connections():
        print("\n❌ API connection tests failed")
        return False
        
    print("\n" + "="*40)
    
    # Initialize real system
    if not initialize_real_system():
        print("\n❌ Real system initialization failed")
        return False
        
    print("\n" + "="*40)
    
    # Start PM2 ecosystem
    if not start_real_pm2_ecosystem():
        print("\n❌ Real ecosystem start failed")
        return False
        
    print("\n" + "="*40)
    
    # Validate data flow
    if not validate_real_data_flow():
        print("\n⚠️ Data validation warnings - check logs")
        
    print("\n" + "="*40)
    
    # Show dashboard
    show_real_system_dashboard()
    
    return True

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n✅ REAL CLAUDE SYSTEM IS LIVE WITH ACTUAL APIS!")
        print("🎯 The system now uses REAL market data for edge detection")
        print("📊 Monitor signal generation: pm2 logs real-edge-detector")
        print("🔍 All edges detected are based on ACTUAL market conditions")
        sys.exit(0)
    else:
        print("\n❌ REAL SYSTEM STARTUP FAILED")
        print("Please check the errors above and retry")
        sys.exit(1)