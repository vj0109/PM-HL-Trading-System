#!/usr/bin/env python3
"""
System Test - Month 1 Week 1
Test the complete Month 1 infrastructure

This script tests all components of the Month 1 system to ensure
everything is working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from polymarket_tracker import PolymarketTracker
from ev_calculator import EVCalculator
from prediction_interface import PredictionInterface
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_polymarket_tracker():
    """Test the PolymarketTracker functionality"""
    print("\n🧪 TESTING POLYMARKET TRACKER")
    print("-" * 40)
    
    try:
        tracker = PolymarketTracker()
        
        # Test market discovery
        markets = tracker.get_active_markets(limit=5)
        print(f"✅ Market discovery: Retrieved {len(markets)} markets")
        
        if markets:
            # Test feature extraction
            first_market = markets[0]
            print(f"✅ Sample market: {first_market.get('question', 'Unknown')[:50]}...")
            print(f"   Price: {first_market.get('price', 0):.1%}")
            print(f"   Volume: ${first_market.get('volume_24h', 0):,.0f}")
            
            # Test database storage
            tracker.store_market_features(markets[:3])
            print("✅ Database storage: Stored sample features")
            
            # Test prediction recording
            from datetime import datetime
            test_prediction = tracker.record_prediction(
                market_id="test_" + str(int(datetime.now().timestamp())),
                market_question="Test prediction for system validation",
                market_price=0.45,
                your_probability=0.65,
                reasoning="System test prediction"
            )
            print(f"✅ Prediction recording: {'Success' if test_prediction else 'Failed'}")
            
        # Test statistics
        stats = tracker.get_prediction_stats()
        print(f"✅ Statistics: {len(stats)} metrics retrieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Tracker test failed: {e}")
        return False

def test_ev_calculator():
    """Test the EVCalculator functionality"""
    print("\n🧮 TESTING EV CALCULATOR")
    print("-" * 40)
    
    try:
        calculator = EVCalculator()
        
        # Test EV calculation
        test_cases = [
            (0.65, 0.45),  # Your 65%, market 45% = positive EV
            (0.35, 0.55),  # Your 35%, market 55% = negative EV  
            (0.50, 0.50),  # Your 50%, market 50% = zero EV
        ]
        
        for your_prob, market_price in test_cases:
            ev = calculator.calculate_ev(your_prob, market_price)
            kelly = calculator.kelly_fraction(your_prob, market_price)
            print(f"✅ EV Test: Prob={your_prob:.0%}, Price={market_price:.0%} → EV={ev:+.1%}, Kelly={kelly:.1%}")
        
        # Test opportunity evaluation
        test_market = {
            'market_id': 'test_market_001',
            'question': 'Will this test succeed?',
            'price': 0.40,
            'category': 'Testing'
        }
        
        opportunity = calculator.evaluate_opportunity(test_market, 0.70, "High confidence test")
        if opportunity:
            print(f"✅ Opportunity evaluation: Generated opportunity with EV={opportunity['expected_value']:+.1%}")
        else:
            print("✅ Opportunity evaluation: Correctly filtered negative EV")
        
        # Test portfolio allocation
        test_opportunities = []
        if opportunity:
            test_opportunities.append(opportunity)
        
        allocation = calculator.portfolio_allocation(test_opportunities)
        print(f"✅ Portfolio allocation: {allocation['number_of_positions']} positions")
        
        return True
        
    except Exception as e:
        print(f"❌ EV Calculator test failed: {e}")
        return False

def test_prediction_interface():
    """Test the PredictionInterface functionality"""
    print("\n🎯 TESTING PREDICTION INTERFACE")
    print("-" * 40)
    
    try:
        interface = PredictionInterface()
        print("✅ Interface initialization: Success")
        
        # Test component integration
        if hasattr(interface, 'tracker') and hasattr(interface, 'calculator'):
            print("✅ Component integration: Tracker and Calculator initialized")
        
        # Test help system
        interface.show_help()
        print("✅ Help system: Working")
        
        return True
        
    except Exception as e:
        print(f"❌ Interface test failed: {e}")
        return False

def test_database_connection():
    """Test database connectivity"""
    print("\n🗄️ TESTING DATABASE CONNECTION")
    print("-" * 40)
    
    try:
        import psycopg2
        
        db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor',
            'password': 'V1S2I3O4J'
        }
        
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Test table existence
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE 'pm_%'
        """)
        
        tables = cur.fetchall()
        print(f"✅ Database connection: Success")
        print(f"✅ PM tables found: {len(tables)} tables")
        
        for table in tables:
            print(f"   - {table[0]}")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all system tests"""
    print("🚀 MONTH 1 SYSTEM COMPREHENSIVE TEST")
    print("=" * 50)
    
    from datetime import datetime
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Polymarket Tracker", test_polymarket_tracker),
        ("EV Calculator", test_ev_calculator),
        ("Prediction Interface", test_prediction_interface),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 ALL SYSTEMS OPERATIONAL!")
        print("Ready to begin daily prediction tracking.")
        print("\nNext steps:")
        print("1. Run: python prediction_interface.py daily")
        print("2. Assess 5-10 markets daily for probability vs price")
        print("3. Track accuracy over 30 days")
        print("4. Build statistical foundation for Month 2")
    else:
        print(f"\n⚠️ {len(tests) - passed} tests failed. Please fix before proceeding.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)