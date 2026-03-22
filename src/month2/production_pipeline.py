#!/usr/bin/env python3
"""
Production ML Pipeline - Month 2 Week 2
End-to-end pipeline for live prediction scoring
"""

import numpy as np
import pandas as pd
import psycopg2
import joblib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PolymarketProductionPipeline:
    """Production pipeline for ML-powered market predictions"""
    
    def __init__(self, model_path="models/polymarket_rf_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = []
        
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
        self.load_model()
        logger.info("Production pipeline initialized")
    
    def load_model(self):
        """Load trained model and preprocessing components"""
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            
            logger.info(f"✅ Model loaded from {self.model_path}")
            logger.info(f"   Features: {len(self.feature_names)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_active_markets_for_scoring(self, limit=20):
        """Get active markets ready for ML scoring"""
        
        from sys import path
        path.append('../month1')
        from simple_tracker import SimplePolymarketTracker
        
        tracker = SimplePolymarketTracker()
        markets = tracker.get_active_markets(limit=limit)
        
        logger.info(f"Retrieved {len(markets)} active markets for ML scoring")
        return markets
    
    def engineer_features_for_market(self, market_data):
        """Engineer features for a single market (similar to training pipeline)"""
        
        # Create a minimal dataframe for feature engineering
        df = pd.DataFrame([{
            'market_id': market_data.get('market_id', ''),
            'market_question': market_data.get('question', ''),
            'market_price': market_data.get('current_price', 0.5),
            'your_probability': 0.5,  # Placeholder - will be predicted
            'reasoning': '',
            'prediction_date': datetime.now(),
            'resolved_outcome': None,
            'correct_prediction': None,
            'expected_value': 0,
            'kelly_fraction': 0,
            'recommendation': 'UNKNOWN',
            'edge': 0,
            'volume_24h': market_data.get('volume_24h', 0),
            'days_to_resolution': market_data.get('days_to_resolution', 30),
            'category': market_data.get('category', ''),
            'market_cap': market_data.get('market_cap', 0),
            'total_volume': market_data.get('total_volume', 0),
            'volume_1w': 0,
            'volume_1m': 0,
            'liquidity': 0,
            'question_length': len(market_data.get('question', '')),
            'has_image': False,
            'end_date': None,
            'created_at': None,
            'winning_outcome': None,
            'data_quality_score': 70
        }])
        
        # Apply same feature engineering as training
        df = self._extract_text_features_minimal(df)
        df = self._extract_market_features_minimal(df)
        df = self._extract_probability_features_minimal(df)
        df = self._encode_categorical_features_minimal(df)
        
        # Select only the features the model expects
        feature_vector = []
        
        for feature_name in self.feature_names:
            if feature_name in df.columns:
                value = df[feature_name].iloc[0]
                # Handle any NaN values
                if pd.isna(value):
                    value = 0.0
                feature_vector.append(float(value))
            else:
                # Missing feature - use default value
                logger.warning(f"Feature {feature_name} missing for market, using default 0.0")
                feature_vector.append(0.0)
        
        return np.array(feature_vector).reshape(1, -1)
    
    def _extract_text_features_minimal(self, df):
        """Minimal text feature extraction for production"""
        df['question_length'] = df['market_question'].str.len().fillna(0)
        df['question_word_count'] = df['market_question'].str.split().str.len().fillna(0)
        df['question_has_numbers'] = df['market_question'].str.contains(r'\d+', na=False).astype(int)
        df['question_has_dollar'] = df['market_question'].str.contains(r'\$', na=False).astype(int)
        df['question_has_percentage'] = df['market_question'].str.contains(r'%', na=False).astype(int)
        
        df['question_has_conditional'] = df['market_question'].str.contains(
            r'(?:if|when|unless|before|after|by)', case=False, na=False
        ).astype(int)
        
        df['question_has_comparison'] = df['market_question'].str.contains(
            r'(?:above|below|more than|less than|exceed|higher|lower)', case=False, na=False
        ).astype(int)
        
        # Category detection
        political_keywords = ['trump', 'biden', 'election', 'president', 'republican', 'democrat', 'vote']
        crypto_keywords = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coin', 'token']
        economic_keywords = ['fed', 'rate', 'inflation', 'gdp', 'unemployment', 'market', 'price']
        
        df['is_political'] = df['market_question'].str.lower().str.contains('|'.join(political_keywords), na=False).astype(int)
        df['is_crypto'] = df['market_question'].str.lower().str.contains('|'.join(crypto_keywords), na=False).astype(int)
        df['is_economic'] = df['market_question'].str.lower().str.contains('|'.join(economic_keywords), na=False).astype(int)
        
        # Reasoning features (empty for new predictions)
        df['reasoning_length'] = 0
        df['reasoning_confidence'] = 0
        df['reasoning_uncertainty'] = 0
        
        return df
    
    def _extract_market_features_minimal(self, df):
        """Minimal market feature extraction for production"""
        
        # Price features
        df['market_price_bucket'] = pd.cut(df['market_price'], 
                                         bins=[0, 0.1, 0.3, 0.7, 0.9, 1.0], 
                                         labels=['very_low', 'low', 'medium', 'high', 'very_high'])
        
        # Use market price as placeholder for probability bucket (will be updated)
        df['probability_bucket'] = df['market_price_bucket']
        
        # Edge features (placeholder)
        df['edge'] = 0
        df['edge_magnitude'] = 0
        df['edge_direction'] = 0
        df['large_edge'] = 0
        
        # Volume features
        df['log_volume_24h'] = np.log1p(pd.to_numeric(df['volume_24h'], errors='coerce').fillna(0))
        df['log_total_volume'] = np.log1p(pd.to_numeric(df['total_volume'], errors='coerce').fillna(0))
        df['log_market_cap'] = np.log1p(pd.to_numeric(df['market_cap'], errors='coerce').fillna(0))
        
        df['volume_ratio_24h_total'] = (df['volume_24h'] / (df['total_volume'] + 1)).fillna(0)
        df['high_volume_24h'] = (df['volume_24h'] > 10000).astype(int)
        df['very_high_volume'] = (df['volume_24h'] > 50000).astype(int)
        
        # Time features
        df['days_to_resolution'] = df['days_to_resolution'].fillna(365)
        df['short_term'] = (df['days_to_resolution'] < 30).astype(int)
        df['medium_term'] = ((df['days_to_resolution'] >= 30) & (df['days_to_resolution'] < 180)).astype(int)
        df['long_term'] = (df['days_to_resolution'] >= 180).astype(int)
        
        df['days_since_prediction'] = 0  # New prediction
        
        # EV and Kelly features (placeholder)
        df['high_ev'] = 0
        df['expected_value'] = 0
        df['kelly_fraction'] = 0
        df['kelly_bucket'] = 'none'
        
        # Quality features
        df['data_quality_score'] = 70
        df['high_quality'] = (df['data_quality_score'] > 70).astype(int)
        df['has_image_market'] = 0
        
        return df
    
    def _extract_probability_features_minimal(self, df):
        """Minimal probability features for production"""
        
        # Use market price as baseline for features
        df['your_probability'] = df['market_price']  # Will be updated with ML prediction
        
        df['prob_market_diff'] = 0  # Placeholder
        df['prob_market_ratio'] = 1  # Placeholder
        
        # Extreme probability indicators
        df['extreme_prob_high'] = (df['market_price'] > 0.9).astype(int)
        df['extreme_prob_low'] = (df['market_price'] < 0.1).astype(int)
        df['moderate_prob'] = ((df['market_price'] >= 0.3) & (df['market_price'] <= 0.7)).astype(int)
        
        # Market efficiency indicators
        df['market_extreme_high'] = (df['market_price'] > 0.9).astype(int)
        df['market_extreme_low'] = (df['market_price'] < 0.1).astype(int)
        df['market_moderate'] = ((df['market_price'] >= 0.3) & (df['market_price'] <= 0.7)).astype(int)
        
        # Confidence measures
        df['probability_confidence'] = 1 - 2 * np.abs(df['market_price'] - 0.5)
        df['market_confidence'] = 1 - 2 * np.abs(df['market_price'] - 0.5)
        
        # Signal indicators (placeholder)
        df['contrarian_signal'] = 0
        df['momentum_signal'] = 0
        
        return df
    
    def _encode_categorical_features_minimal(self, df):
        """Minimal categorical encoding for production"""
        
        # Simple label encoding for categorical buckets
        bucket_map = {'very_low': 0, 'low': 1, 'medium': 2, 'high': 3, 'very_high': 4}
        kelly_map = {'none': 0, 'small': 1, 'medium': 2, 'large': 3, 'very_large': 4}
        
        df['market_price_bucket_encoded'] = df['market_price_bucket'].astype(str).map(bucket_map).fillna(2)
        df['probability_bucket_encoded'] = df['probability_bucket'].astype(str).map(bucket_map).fillna(2)
        df['kelly_bucket_encoded'] = df['kelly_bucket'].map(kelly_map).fillna(0)
        
        # Category encoding
        if 'category' in df.columns:
            df['category_encoded'] = 0  # Default for unknown category
        
        return df
    
    def predict_market_outcome(self, market_data):
        """Predict outcome for a single market"""
        
        if self.model is None:
            logger.error("Model not loaded")
            return None
        
        try:
            # Engineer features
            X = self.engineer_features_for_market(market_data)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Make prediction
            prediction = self.model.predict(X_scaled)[0]
            probability = self.model.predict_proba(X_scaled)[0, 1]
            
            # Feature importance for this prediction
            if hasattr(self.model, 'feature_importances_'):
                feature_contributions = X_scaled[0] * self.model.feature_importances_
                top_features = sorted(
                    zip(self.feature_names, feature_contributions), 
                    key=lambda x: abs(x[1]), reverse=True
                )[:5]
            else:
                top_features = []
            
            result = {
                'market_id': market_data.get('market_id', ''),
                'market_question': market_data.get('question', ''),
                'market_price': market_data.get('current_price', 0.5),
                'ml_prediction': int(prediction),
                'ml_probability': float(probability),
                'confidence': float(abs(probability - 0.5) * 2),  # 0-1 scale
                'edge': float(probability - market_data.get('current_price', 0.5)),
                'recommendation': 'BUY' if probability > market_data.get('current_price', 0.5) + 0.05 else 'SKIP',
                'top_features': [(feat, float(contrib)) for feat, contrib in top_features],
                'prediction_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ ML prediction complete for: {market_data.get('question', '')[:50]}...")
            logger.info(f"   Prediction: {result['ml_prediction']} ({result['ml_probability']:.3f} probability)")
            logger.info(f"   Edge: {result['edge']:+.3f}, Recommendation: {result['recommendation']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return None
    
    def batch_predict_markets(self, markets):
        """Make predictions for multiple markets"""
        
        predictions = []
        
        logger.info(f"🔄 Making ML predictions for {len(markets)} markets...")
        
        for i, market in enumerate(markets, 1):
            prediction = self.predict_market_outcome(market)
            
            if prediction:
                predictions.append(prediction)
                
            if i % 5 == 0:
                logger.info(f"   Progress: {i}/{len(markets)} markets processed")
        
        logger.info(f"✅ Batch prediction complete: {len(predictions)} successful predictions")
        
        return predictions
    
    def store_ml_predictions(self, predictions):
        """Store ML predictions in database"""
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Create ML predictions table if it doesn't exist
            cur.execute('''
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    id SERIAL PRIMARY KEY,
                    market_id VARCHAR(100),
                    market_question TEXT,
                    market_price DECIMAL(6,4),
                    ml_prediction INTEGER,
                    ml_probability DECIMAL(6,4),
                    confidence DECIMAL(6,4),
                    edge DECIMAL(6,4),
                    recommendation VARCHAR(10),
                    top_features JSONB,
                    prediction_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Insert predictions
            stored_count = 0
            
            for pred in predictions:
                cur.execute('''
                    INSERT INTO ml_predictions (
                        market_id, market_question, market_price, ml_prediction,
                        ml_probability, confidence, edge, recommendation,
                        top_features, prediction_timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    pred['market_id'],
                    pred['market_question'],
                    pred['market_price'],
                    pred['ml_prediction'],
                    pred['ml_probability'],
                    pred['confidence'],
                    pred['edge'],
                    pred['recommendation'],
                    json.dumps(pred['top_features']),
                    pred['prediction_timestamp']
                ))
                
                if cur.fetchone():
                    stored_count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"✅ Stored {stored_count} ML predictions in database")
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing ML predictions: {e}")
            return 0
    
    def daily_ml_scoring(self, max_markets=20):
        """Daily ML scoring workflow"""
        
        logger.info("🚀 Starting daily ML scoring workflow")
        
        # Get active markets
        markets = self.get_active_markets_for_scoring(limit=max_markets)
        
        if not markets:
            logger.warning("No active markets available for scoring")
            return []
        
        # Make predictions
        predictions = self.batch_predict_markets(markets)
        
        # Store predictions
        stored_count = self.store_ml_predictions(predictions)
        
        # Summary
        high_confidence = [p for p in predictions if p['confidence'] > 0.7]
        buy_recommendations = [p for p in predictions if p['recommendation'] == 'BUY']
        
        logger.info(f"🎯 Daily ML scoring complete:")
        logger.info(f"   Total predictions: {len(predictions)}")
        logger.info(f"   Stored in database: {stored_count}")
        logger.info(f"   High confidence (>70%): {len(high_confidence)}")
        logger.info(f"   BUY recommendations: {len(buy_recommendations)}")
        
        return predictions

def main():
    """Test production pipeline"""
    print("🚀 PRODUCTION ML PIPELINE TEST")
    
    try:
        pipeline = PolymarketProductionPipeline()
        
        # Run daily scoring
        predictions = pipeline.daily_ml_scoring(max_markets=5)
        
        if predictions:
            print(f"\n✅ PRODUCTION PIPELINE TEST SUCCESSFUL")
            print(f"   Predictions made: {len(predictions)}")
            
            # Show sample prediction
            sample = predictions[0]
            print(f"\n📊 SAMPLE PREDICTION:")
            print(f"   Question: {sample['market_question'][:60]}...")
            print(f"   Market Price: {sample['market_price']:.3f}")
            print(f"   ML Probability: {sample['ml_probability']:.3f}")
            print(f"   Confidence: {sample['confidence']:.3f}")
            print(f"   Recommendation: {sample['recommendation']}")
        else:
            print("❌ No predictions generated")
            
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")

if __name__ == "__main__":
    main()