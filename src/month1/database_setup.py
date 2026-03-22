#!/usr/bin/env python3
"""
Month 1 Week 1-2: Database Schema Setup
Create prediction tracking and market features tables as per ML strategy
"""

import psycopg2
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSetup:
    """Setup database schema for ML strategy Month 1"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
    def create_prediction_tables(self):
        """Create database tables as specified in ML strategy"""
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Main predictions table (from strategy document)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) NOT NULL,
                    market_question TEXT NOT NULL,
                    market_price DECIMAL(5,4) NOT NULL,
                    your_probability DECIMAL(5,4) NOT NULL,
                    reasoning TEXT,
                    prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolution_date TIMESTAMP,
                    actual_outcome BOOLEAN,
                    correct_prediction BOOLEAN
                );
            ''')
            
            # Market features table (from strategy document)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS market_features (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100) NOT NULL,
                    volume_24h DECIMAL(15,2),
                    days_to_resolution INTEGER,
                    category VARCHAR(50),
                    market_cap DECIMAL(15,2),
                    feature_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create indexes
            cur.execute('CREATE INDEX IF NOT EXISTS idx_predictions_market_id ON predictions(market_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_market_features_market_id ON market_features(market_id)')
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info("✅ Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database setup error: {e}")
            return False
    
    def verify_setup(self):
        """Verify tables were created correctly"""
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Check predictions table
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'predictions'
                ORDER BY ordinal_position
            """)
            predictions_columns = cur.fetchall()
            
            # Check market_features table
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'market_features'
                ORDER BY ordinal_position
            """)
            features_columns = cur.fetchall()
            
            cur.close()
            conn.close()
            
            print("📊 PREDICTIONS TABLE COLUMNS:")
            for col_name, data_type in predictions_columns:
                print(f"  {col_name}: {data_type}")
                
            print("\n📊 MARKET_FEATURES TABLE COLUMNS:")
            for col_name, data_type in features_columns:
                print(f"  {col_name}: {data_type}")
                
            logger.info("✅ Database schema verification complete")
            return True
            
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False

def main():
    """Main setup function"""
    print("🏗️  MONTH 1 WEEK 1-2: DATABASE SETUP")
    print("Creating prediction tracking schema as per ML strategy...")
    
    setup = DatabaseSetup()
    
    # Create tables
    if setup.create_prediction_tables():
        print("✅ Database tables created")
        
        # Verify setup
        if setup.verify_setup():
            print("✅ Database setup complete and verified")
            print("\n🎯 READY FOR NEXT STEP: Market discovery system")
        else:
            print("❌ Database verification failed")
    else:
        print("❌ Database setup failed")

if __name__ == "__main__":
    main()