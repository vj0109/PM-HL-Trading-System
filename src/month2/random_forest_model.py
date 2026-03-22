#!/usr/bin/env python3
"""
Random Forest Model - Month 2 Week 1-2
Train ML model on 2200+ predictions with 50+ engineered features
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from ml_feature_engineering import PolymarketFeatureEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PolymarketRandomForest:
    """Random Forest model for Polymarket prediction accuracy"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.feature_importance_df = None
        self.training_history = {}
        
        logger.info("Random Forest model initialized")
    
    def prepare_data(self, X, y, test_size=0.2, random_state=42):
        """Prepare training and validation data with proper time series split"""
        
        # Scale features for better performance
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data (using random split for now, can implement time-based later)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=random_state, 
            stratify=y  # Ensure balanced classes in train/test
        )
        
        logger.info(f"Data split: Train {X_train.shape}, Test {X_test.shape}")
        logger.info(f"Class balance - Train: {y_train.mean():.3f}, Test: {y_test.mean():.3f}")
        
        return X_train, X_test, y_train, y_test
    
    def train_baseline_model(self, X_train, y_train):
        """Train baseline Random Forest model"""
        
        # Start with reasonable baseline parameters
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'  # Handle class imbalance
        )
        
        logger.info("Training baseline Random Forest model...")
        start_time = datetime.now()
        
        self.model.fit(X_train, y_train)
        
        training_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Model training completed in {training_time:.1f} seconds")
        
        return self.model
    
    def hyperparameter_optimization(self, X_train, y_train, cv_folds=3):
        """Optimize hyperparameters using GridSearchCV"""
        
        logger.info("Starting hyperparameter optimization...")
        
        # Define parameter grid (focused search for speed)
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [8, 12, 16, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None]
        }
        
        # Use GridSearchCV with cross-validation
        grid_search = GridSearchCV(
            RandomForestClassifier(random_state=42, n_jobs=-1, class_weight='balanced'),
            param_grid,
            cv=cv_folds,
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )
        
        start_time = datetime.now()
        grid_search.fit(X_train, y_train)
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Optimization completed in {optimization_time:.1f} seconds")
        logger.info(f"Best parameters: {grid_search.best_params_}")
        logger.info(f"Best cross-validation score: {grid_search.best_score_:.4f}")
        
        # Update model with best parameters
        self.model = grid_search.best_estimator_
        
        return grid_search.best_params_, grid_search.best_score_
    
    def evaluate_model(self, X_test, y_test):
        """Comprehensive model evaluation"""
        
        if self.model is None:
            logger.error("Model not trained yet")
            return {}
        
        # Make predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        # Classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        results = {
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'classification_report': class_report,
            'confusion_matrix': cm,
            'predictions': y_pred,
            'probabilities': y_pred_proba
        }
        
        logger.info(f"📊 Model Evaluation Results:")
        logger.info(f"   Accuracy: {accuracy:.4f}")
        logger.info(f"   ROC AUC: {roc_auc:.4f}")
        logger.info(f"   Precision (class 1): {class_report['1']['precision']:.4f}")
        logger.info(f"   Recall (class 1): {class_report['1']['recall']:.4f}")
        logger.info(f"   F1-score (class 1): {class_report['1']['f1-score']:.4f}")
        
        return results
    
    def analyze_feature_importance(self, feature_names):
        """Analyze and rank feature importance"""
        
        if self.model is None:
            logger.error("Model not trained yet")
            return None
        
        # Get feature importance
        importances = self.model.feature_importances_
        
        # Create DataFrame for analysis
        self.feature_importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        logger.info("📊 Top 10 Most Important Features:")
        for i, (_, row) in enumerate(self.feature_importance_df.head(10).iterrows(), 1):
            logger.info(f"   {i:2d}. {row['feature']}: {row['importance']:.4f}")
        
        return self.feature_importance_df
    
    def cross_validate_model(self, X, y, cv_folds=5):
        """Perform cross-validation for robust performance estimation"""
        
        if self.model is None:
            logger.error("Model not trained yet")
            return {}
        
        logger.info(f"Performing {cv_folds}-fold cross-validation...")
        
        # Cross-validation scores
        cv_scores = cross_val_score(self.model, X, y, cv=cv_folds, scoring='accuracy')
        
        cv_results = {
            'cv_scores': cv_scores,
            'mean_accuracy': cv_scores.mean(),
            'std_accuracy': cv_scores.std(),
            'min_accuracy': cv_scores.min(),
            'max_accuracy': cv_scores.max()
        }
        
        logger.info(f"📊 Cross-Validation Results:")
        logger.info(f"   Mean Accuracy: {cv_results['mean_accuracy']:.4f} ± {cv_results['std_accuracy']:.4f}")
        logger.info(f"   Range: [{cv_results['min_accuracy']:.4f}, {cv_results['max_accuracy']:.4f}]")
        
        return cv_results
    
    def save_model(self, model_path="models/polymarket_rf_model.pkl"):
        """Save trained model and scaler"""
        
        import os
        os.makedirs("models", exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance_df,
            'training_history': self.training_history
        }
        
        joblib.dump(model_data, model_path)
        logger.info(f"✅ Model saved to {model_path}")
        
        return model_path
    
    def load_model(self, model_path="models/polymarket_rf_model.pkl"):
        """Load saved model"""
        
        try:
            model_data = joblib.load(model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.feature_importance_df = model_data.get('feature_importance')
            self.training_history = model_data.get('training_history', {})
            
            logger.info(f"✅ Model loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def predict_new_data(self, X_new):
        """Make predictions on new data"""
        
        if self.model is None:
            logger.error("Model not trained yet")
            return None
        
        # Scale features
        X_new_scaled = self.scaler.transform(X_new)
        
        # Make predictions
        predictions = self.model.predict(X_new_scaled)
        probabilities = self.model.predict_proba(X_new_scaled)[:, 1]
        
        return {
            'predictions': predictions,
            'probabilities': probabilities
        }

def comprehensive_model_training():
    """Complete model training pipeline"""
    
    print("🧠 POLYMARKET RANDOM FOREST MODEL TRAINING")
    print("=" * 60)
    
    # Initialize components
    feature_engine = PolymarketFeatureEngine()
    rf_model = PolymarketRandomForest()
    
    # Feature engineering
    print("\n📊 FEATURE ENGINEERING...")
    X, y, feature_names, df = feature_engine.process_all_features()
    
    if len(X) == 0:
        print("❌ No data available for training")
        return None
    
    rf_model.feature_names = feature_names
    
    print(f"✅ Features extracted: {X.shape[1]} features, {X.shape[0]} samples")
    
    # Prepare data
    print("\n🔄 PREPARING TRAINING DATA...")
    X_train, X_test, y_train, y_test = rf_model.prepare_data(X, y)
    
    # Train baseline model
    print("\n🚀 TRAINING BASELINE MODEL...")
    rf_model.train_baseline_model(X_train, y_train)
    
    # Evaluate baseline
    print("\n📈 EVALUATING BASELINE MODEL...")
    baseline_results = rf_model.evaluate_model(X_test, y_test)
    
    # Hyperparameter optimization
    print("\n⚙️ HYPERPARAMETER OPTIMIZATION...")
    best_params, best_score = rf_model.hyperparameter_optimization(X_train, y_train)
    
    # Evaluate optimized model
    print("\n📈 EVALUATING OPTIMIZED MODEL...")
    optimized_results = rf_model.evaluate_model(X_test, y_test)
    
    # Cross-validation
    print("\n🔄 CROSS-VALIDATION...")
    cv_results = rf_model.cross_validate_model(X, y)
    
    # Feature importance analysis
    print("\n🔍 FEATURE IMPORTANCE ANALYSIS...")
    rf_model.analyze_feature_importance(feature_names)
    
    # Save model
    print("\n💾 SAVING MODEL...")
    model_path = rf_model.save_model()
    
    # Summary
    print("\n🎉 TRAINING COMPLETE!")
    print(f"   Baseline Accuracy: {baseline_results['accuracy']:.4f}")
    print(f"   Optimized Accuracy: {optimized_results['accuracy']:.4f}")
    print(f"   Cross-Val Mean: {cv_results['mean_accuracy']:.4f} ± {cv_results['std_accuracy']:.4f}")
    print(f"   Model saved to: {model_path}")
    
    # Performance assessment
    target_accuracy = 0.80  # Month 2 target
    achieved_accuracy = optimized_results['accuracy']
    
    if achieved_accuracy >= target_accuracy:
        print(f"✅ MONTH 2 TARGET ACHIEVED: {achieved_accuracy:.1%} ≥ {target_accuracy:.1%}")
    else:
        print(f"📊 Progress: {achieved_accuracy:.1%} (target: {target_accuracy:.1%})")
        print(f"   Gap: {target_accuracy - achieved_accuracy:.1%}")
    
    return {
        'model': rf_model,
        'baseline_results': baseline_results,
        'optimized_results': optimized_results,
        'cv_results': cv_results,
        'best_params': best_params,
        'feature_importance': rf_model.feature_importance_df
    }

def main():
    """Run comprehensive model training"""
    results = comprehensive_model_training()
    
    if results:
        print(f"\n🚀 READY FOR MONTH 2 WEEK 3-4: STATISTICAL VALIDATION")
        print(f"✅ Random Forest model trained and validated")
        print(f"✅ Feature importance analyzed")  
        print(f"✅ Cross-validation completed")
        print(f"✅ Model saved for production use")

if __name__ == "__main__":
    main()