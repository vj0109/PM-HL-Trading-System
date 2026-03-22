#!/usr/bin/env python3
"""
ML Feature Engineering - Month 2 Week 1
Extract 38+ features from prediction data for Random Forest training
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PolymarketFeatureEngine:
    """Extract comprehensive features from prediction and market data"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'agentfloor',
            'user': 'agentfloor', 
            'password': 'V1S2I3O4J'
        }
        
        self.label_encoders = {}
        self.scaler = StandardScaler()
        
        logger.info("Feature Engineering system initialized")
    
    def load_prediction_data(self) -> pd.DataFrame:
        """Load all prediction data for feature extraction"""
        try:
            conn = psycopg2.connect(**self.db_config)
            
            query = '''
                SELECT 
                    p.id, p.market_id, p.market_question, p.market_price, 
                    p.your_probability, p.reasoning, p.prediction_date,
                    p.resolved_outcome, p.correct_prediction, p.expected_value,
                    p.kelly_fraction, p.recommendation, p.edge,
                    mf.volume_24h, mf.days_to_resolution, mf.category, mf.market_cap,
                    rm.total_volume, rm.volume_1w, rm.volume_1m, rm.liquidity,
                    rm.question_length, rm.has_image, rm.end_date, rm.created_at,
                    rm.winning_outcome, rm.data_quality_score
                FROM predictions p
                LEFT JOIN market_features mf ON p.market_id = mf.market_id
                LEFT JOIN pm_resolved_markets_final rm ON p.market_id = rm.market_id::text
                WHERE p.resolved_outcome IS NOT NULL  -- Only use resolved predictions for training
                ORDER BY p.prediction_date
            '''
            
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"Loaded {len(df)} predictions with resolution outcomes for ML training")
            return df
            
        except Exception as e:
            logger.error(f"Error loading prediction data: {e}")
            return pd.DataFrame()
    
    def extract_text_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from question text and reasoning"""
        
        # Question text features
        df['question_length'] = df['market_question'].str.len().fillna(0)
        df['question_word_count'] = df['market_question'].str.split().str.len().fillna(0)
        df['question_has_numbers'] = df['market_question'].str.contains(r'\d+', na=False).astype(int)
        df['question_has_dollar'] = df['market_question'].str.contains(r'\$', na=False).astype(int)
        df['question_has_percentage'] = df['market_question'].str.contains(r'%', na=False).astype(int)
        
        # Question complexity indicators
        df['question_has_conditional'] = df['market_question'].str.contains(
            r'\b(if|when|unless|before|after|by)\b', case=False, na=False
        ).astype(int)
        
        df['question_has_comparison'] = df['market_question'].str.contains(
            r'\b(above|below|more than|less than|exceed|higher|lower)\b', case=False, na=False
        ).astype(int)
        
        # Sentiment and category indicators from question text
        political_keywords = ['trump', 'biden', 'election', 'president', 'republican', 'democrat', 'vote']
        crypto_keywords = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coin', 'token']
        economic_keywords = ['fed', 'rate', 'inflation', 'gdp', 'unemployment', 'market', 'price']
        
        df['is_political'] = df['market_question'].str.lower().str.contains(
            '|'.join(political_keywords), na=False
        ).astype(int)
        
        df['is_crypto'] = df['market_question'].str.lower().str.contains(
            '|'.join(crypto_keywords), na=False
        ).astype(int)
        
        df['is_economic'] = df['market_question'].str.lower().str.contains(
            '|'.join(economic_keywords), na=False
        ).astype(int)
        
        # Reasoning features
        df['reasoning_length'] = df['reasoning'].str.len().fillna(0)
        df['reasoning_confidence'] = df['reasoning'].str.contains(
            r'\b(confident|certain|sure|likely|probable)\b', case=False, na=False
        ).astype(int)
        
        df['reasoning_uncertainty'] = df['reasoning'].str.contains(
            r'\b(uncertain|doubt|maybe|possibly|might)\b', case=False, na=False
        ).astype(int)
        
        logger.info("Extracted text-based features")
        return df
    
    def extract_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract market-specific features"""
        
        # Price features
        df['market_price_bucket'] = pd.cut(df['market_price'], 
                                         bins=[0, 0.1, 0.3, 0.7, 0.9, 1.0], 
                                         labels=['very_low', 'low', 'medium', 'high', 'very_high'])
        
        df['probability_bucket'] = pd.cut(df['your_probability'], 
                                        bins=[0, 0.1, 0.3, 0.7, 0.9, 1.0], 
                                        labels=['very_low', 'low', 'medium', 'high', 'very_high'])
        
        # Edge magnitude and direction
        df['edge_magnitude'] = np.abs(df['edge']).fillna(0)
        df['edge_direction'] = np.sign(df['edge']).fillna(0)
        df['large_edge'] = (df['edge_magnitude'] > 0.2).astype(int)
        
        # Volume features (with log transformation for better distribution)
        df['log_volume_24h'] = np.log1p(pd.to_numeric(df['volume_24h'], errors='coerce').fillna(0))
        df['log_total_volume'] = np.log1p(pd.to_numeric(df['total_volume'], errors='coerce').fillna(0))
        df['log_market_cap'] = np.log1p(pd.to_numeric(df['market_cap'], errors='coerce').fillna(0))
        
        # Volume ratios and patterns
        df['volume_ratio_24h_total'] = (df['volume_24h'] / (df['total_volume'] + 1)).fillna(0)
        df['high_volume_24h'] = (df['volume_24h'] > 10000).astype(int)
        df['very_high_volume'] = (df['volume_24h'] > 50000).astype(int)
        
        # Time-based features
        df['days_to_resolution'] = df['days_to_resolution'].fillna(365)  # Default to 1 year
        df['short_term'] = (df['days_to_resolution'] < 30).astype(int)
        df['medium_term'] = ((df['days_to_resolution'] >= 30) & (df['days_to_resolution'] < 180)).astype(int)
        df['long_term'] = (df['days_to_resolution'] >= 180).astype(int)
        
        # Time since creation (if available)
        current_time = pd.Timestamp.now()
        df['prediction_date'] = pd.to_datetime(df['prediction_date'])
        df['days_since_prediction'] = (current_time - df['prediction_date']).dt.days
        
        # EV and Kelly features
        df['high_ev'] = (df['expected_value'] > 0.1).astype(int)
        df['kelly_bucket'] = pd.cut(df['kelly_fraction'].fillna(0), 
                                   bins=[0, 0.01, 0.05, 0.15, 0.25, 1.0], 
                                   labels=['none', 'small', 'medium', 'large', 'very_large'])
        
        # Quality and metadata features
        df['data_quality_score'] = df['data_quality_score'].fillna(60)  # Default quality
        df['high_quality'] = (df['data_quality_score'] > 70).astype(int)
        df['has_image_market'] = df['has_image'].fillna(False).astype(int)
        
        logger.info("Extracted market-based features")
        return df
    
    def extract_probability_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features related to probability assessments"""
        
        # Probability vs market price relationships
        df['prob_market_diff'] = df['your_probability'] - df['market_price']
        df['prob_market_ratio'] = df['your_probability'] / (df['market_price'] + 0.001)  # Avoid division by zero
        
        # Extreme probability indicators
        df['extreme_prob_high'] = (df['your_probability'] > 0.9).astype(int)
        df['extreme_prob_low'] = (df['your_probability'] < 0.1).astype(int)
        df['moderate_prob'] = ((df['your_probability'] >= 0.3) & (df['your_probability'] <= 0.7)).astype(int)
        
        # Market efficiency indicators
        df['market_extreme_high'] = (df['market_price'] > 0.9).astype(int)
        df['market_extreme_low'] = (df['market_price'] < 0.1).astype(int)
        df['market_moderate'] = ((df['market_price'] >= 0.3) & (df['market_price'] <= 0.7)).astype(int)
        
        # Confidence and uncertainty proxies
        df['probability_confidence'] = 1 - 2 * np.abs(df['your_probability'] - 0.5)  # Higher when closer to 0 or 1
        df['market_confidence'] = 1 - 2 * np.abs(df['market_price'] - 0.5)
        
        # Contrarian vs momentum indicators
        df['contrarian_signal'] = ((df['your_probability'] > 0.5) & (df['market_price'] < 0.5)).astype(int) | \
                                 ((df['your_probability'] < 0.5) & (df['market_price'] > 0.5)).astype(int)
        
        df['momentum_signal'] = ((df['your_probability'] > 0.5) & (df['market_price'] > 0.5)).astype(int) | \
                               ((df['your_probability'] < 0.5) & (df['market_price'] < 0.5)).astype(int)
        
        logger.info("Extracted probability-based features")
        return df
    
    def encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features for ML"""
        
        categorical_columns = ['market_price_bucket', 'probability_bucket', 'kelly_bucket']
        
        for col in categorical_columns:
            if col in df.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                
                # Handle missing values
                df[col] = df[col].astype(str).fillna('unknown')
                
                # Fit and transform
                try:
                    df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col])
                except Exception as e:
                    logger.warning(f"Error encoding {col}: {e}")
                    df[f'{col}_encoded'] = 0
        
        # Category encoding (if available)
        if 'category' in df.columns:
            df['category'] = df['category'].fillna('unknown').astype(str)
            if 'category' not in self.label_encoders:
                self.label_encoders['category'] = LabelEncoder()
            df['category_encoded'] = self.label_encoders['category'].fit_transform(df['category'])
        
        logger.info("Encoded categorical features")
        return df
    
    def create_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Create final feature matrix for ML training"""
        
        # Define feature columns (38+ features)
        feature_columns = [
            # Basic market features
            'market_price', 'your_probability', 'edge', 'edge_magnitude', 'edge_direction',
            'expected_value', 'kelly_fraction',
            
            # Volume features
            'log_volume_24h', 'log_total_volume', 'log_market_cap', 'volume_ratio_24h_total',
            'high_volume_24h', 'very_high_volume',
            
            # Time features
            'days_to_resolution', 'short_term', 'medium_term', 'long_term',
            'days_since_prediction',
            
            # Text features
            'question_length', 'question_word_count', 'question_has_numbers', 
            'question_has_dollar', 'question_has_percentage', 'question_has_conditional',
            'question_has_comparison', 'reasoning_length',
            
            # Category features
            'is_political', 'is_crypto', 'is_economic',
            
            # Probability features
            'prob_market_diff', 'prob_market_ratio', 'extreme_prob_high', 'extreme_prob_low',
            'moderate_prob', 'market_extreme_high', 'market_extreme_low', 'market_moderate',
            'probability_confidence', 'market_confidence', 'contrarian_signal', 'momentum_signal',
            
            # Quality and metadata
            'data_quality_score', 'high_quality', 'has_image_market',
            'high_ev', 'large_edge',
            
            # Encoded categorical features
            'market_price_bucket_encoded', 'probability_bucket_encoded', 'kelly_bucket_encoded'
        ]
        
        # Add category encoding if available
        if 'category_encoded' in df.columns:
            feature_columns.append('category_encoded')
        
        # Select features that exist in the dataframe
        available_features = [col for col in feature_columns if col in df.columns]
        missing_features = [col for col in feature_columns if col not in df.columns]
        
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
        
        logger.info(f"Using {len(available_features)} features for ML training")
        
        # Create feature matrix
        X = df[available_features].fillna(0).values
        
        # Target variable (resolved_outcome: True=1, False=0)
        y = df['resolved_outcome'].astype(int).values
        
        return X, y, available_features
    
    def process_all_features(self) -> Tuple[np.ndarray, np.ndarray, List[str], pd.DataFrame]:
        """Complete feature engineering pipeline"""
        
        logger.info("🚀 Starting comprehensive feature engineering")
        
        # Load data
        df = self.load_prediction_data()
        
        if df.empty:
            logger.error("No data available for feature engineering")
            return np.array([]), np.array([]), [], pd.DataFrame()
        
        logger.info(f"Processing {len(df)} predictions for feature extraction")
        
        # Extract all feature types
        df = self.extract_text_features(df)
        df = self.extract_market_features(df)
        df = self.extract_probability_features(df)
        df = self.encode_categorical_features(df)
        
        # Create final feature matrix
        X, y, feature_names = self.create_feature_matrix(df)
        
        logger.info(f"✅ Feature engineering complete:")
        logger.info(f"   Feature matrix: {X.shape}")
        logger.info(f"   Target vector: {y.shape}")
        logger.info(f"   Features: {len(feature_names)}")
        logger.info(f"   Positive class ratio: {y.mean():.3f}")
        
        return X, y, feature_names, df

def main():
    """Test feature engineering pipeline"""
    print("🧠 TESTING ML FEATURE ENGINEERING PIPELINE")
    
    feature_engine = PolymarketFeatureEngine()
    
    # Process all features
    X, y, feature_names, df = feature_engine.process_all_features()
    
    if len(X) > 0:
        print(f"\n✅ FEATURE ENGINEERING SUCCESSFUL:")
        print(f"   Samples: {X.shape[0]}")
        print(f"   Features: {X.shape[1]}")
        print(f"   Target balance: {y.mean():.1%} positive class")
        
        print(f"\n📊 FEATURE OVERVIEW:")
        for i, name in enumerate(feature_names[:10]):  # Show first 10 features
            print(f"   {i+1:2d}. {name}: μ={X[:, i].mean():.3f}, σ={X[:, i].std():.3f}")
        
        if len(feature_names) > 10:
            print(f"   ... and {len(feature_names) - 10} more features")
        
        print(f"\n🎯 READY FOR ML MODEL TRAINING")
        
    else:
        print("❌ Feature engineering failed - no data available")

if __name__ == "__main__":
    main()