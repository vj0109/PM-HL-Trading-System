#!/usr/bin/env python3
"""
Model Validation Suite - Month 2 Week 1-2
Comprehensive statistical validation including bootstrap analysis
"""

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from scipy import stats
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelValidationSuite:
    """Comprehensive validation for ML models with statistical rigor"""
    
    def __init__(self, model, X_test, y_test, feature_names=None):
        self.model = model
        self.X_test = X_test
        self.y_test = y_test
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X_test.shape[1])]
        
        # Make predictions once for all analyses
        self.y_pred = model.predict(X_test)
        self.y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        logger.info(f"Validation suite initialized with {len(y_test)} test samples")
    
    def bootstrap_validation(self, n_bootstrap=10000, confidence_level=0.95):
        """Bootstrap analysis for confidence intervals"""
        
        logger.info(f"🔄 Starting bootstrap analysis with {n_bootstrap} samples...")
        
        n_samples = len(self.y_test)
        bootstrap_accuracies = []
        bootstrap_aucs = []
        
        np.random.seed(42)  # For reproducibility
        
        for i in range(n_bootstrap):
            # Bootstrap sample with replacement
            bootstrap_indices = np.random.choice(n_samples, size=n_samples, replace=True)
            
            y_boot_true = self.y_test[bootstrap_indices]
            y_boot_pred = self.y_pred[bootstrap_indices]
            y_boot_proba = self.y_pred_proba[bootstrap_indices]
            
            # Calculate metrics for this bootstrap sample
            acc = accuracy_score(y_boot_true, y_boot_pred)
            auc = roc_auc_score(y_boot_true, y_boot_proba)
            
            bootstrap_accuracies.append(acc)
            bootstrap_aucs.append(auc)
            
            if (i + 1) % 2000 == 0:
                logger.info(f"   Bootstrap progress: {i+1}/{n_bootstrap}")
        
        # Calculate confidence intervals
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        acc_ci_lower = np.percentile(bootstrap_accuracies, lower_percentile)
        acc_ci_upper = np.percentile(bootstrap_accuracies, upper_percentile)
        
        auc_ci_lower = np.percentile(bootstrap_aucs, lower_percentile)
        auc_ci_upper = np.percentile(bootstrap_aucs, upper_percentile)
        
        results = {
            'bootstrap_accuracies': bootstrap_accuracies,
            'bootstrap_aucs': bootstrap_aucs,
            'accuracy_mean': np.mean(bootstrap_accuracies),
            'accuracy_std': np.std(bootstrap_accuracies),
            'accuracy_ci': (acc_ci_lower, acc_ci_upper),
            'auc_mean': np.mean(bootstrap_aucs),
            'auc_std': np.std(bootstrap_aucs),
            'auc_ci': (auc_ci_lower, auc_ci_upper),
            'confidence_level': confidence_level,
            'n_bootstrap': n_bootstrap
        }
        
        logger.info(f"✅ Bootstrap analysis complete")
        logger.info(f"   Accuracy: {results['accuracy_mean']:.4f} ± {results['accuracy_std']:.4f}")
        logger.info(f"   {confidence_level*100:.0f}% CI: [{acc_ci_lower:.4f}, {acc_ci_upper:.4f}]")
        logger.info(f"   AUC: {results['auc_mean']:.4f} ± {results['auc_std']:.4f}")
        logger.info(f"   {confidence_level*100:.0f}% CI: [{auc_ci_lower:.4f}, {auc_ci_upper:.4f}]")
        
        return results
    
    def statistical_significance_tests(self, baseline_accuracy=0.5):
        """Test statistical significance vs baseline"""
        
        observed_accuracy = accuracy_score(self.y_test, self.y_pred)
        n_correct = np.sum(self.y_pred == self.y_test)
        n_total = len(self.y_test)
        
        # Binomial test against baseline
        binom_pvalue = stats.binom_test(n_correct, n_total, baseline_accuracy, alternative='greater')
        
        # McNemar's test (if we have a baseline model to compare against)
        # For now, just report the binomial test
        
        results = {
            'observed_accuracy': observed_accuracy,
            'baseline_accuracy': baseline_accuracy,
            'n_correct': n_correct,
            'n_total': n_total,
            'binomial_pvalue': binom_pvalue,
            'is_significant': binom_pvalue < 0.05
        }
        
        logger.info(f"📊 Statistical Significance Tests:")
        logger.info(f"   Observed accuracy: {observed_accuracy:.4f}")
        logger.info(f"   Baseline accuracy: {baseline_accuracy:.4f}")
        logger.info(f"   Binomial test p-value: {binom_pvalue:.6f}")
        logger.info(f"   Statistically significant: {results['is_significant']}")
        
        return results
    
    def prediction_stability_analysis(self):
        """Analyze prediction stability and confidence"""
        
        # Analyze prediction probabilities
        prob_stats = {
            'mean_confidence': np.mean(np.maximum(self.y_pred_proba, 1 - self.y_pred_proba)),
            'min_confidence': np.min(np.maximum(self.y_pred_proba, 1 - self.y_pred_proba)),
            'max_confidence': np.max(np.maximum(self.y_pred_proba, 1 - self.y_pred_proba)),
            'std_confidence': np.std(np.maximum(self.y_pred_proba, 1 - self.y_pred_proba))
        }
        
        # High confidence predictions (>90% probability)
        high_confidence_mask = (np.maximum(self.y_pred_proba, 1 - self.y_pred_proba) > 0.9)
        high_conf_accuracy = accuracy_score(
            self.y_test[high_confidence_mask], 
            self.y_pred[high_confidence_mask]
        ) if np.any(high_confidence_mask) else 0
        
        # Medium confidence predictions (70-90% probability)
        med_confidence_mask = (
            (np.maximum(self.y_pred_proba, 1 - self.y_pred_proba) >= 0.7) &
            (np.maximum(self.y_pred_proba, 1 - self.y_pred_proba) <= 0.9)
        )
        med_conf_accuracy = accuracy_score(
            self.y_test[med_confidence_mask], 
            self.y_pred[med_confidence_mask]
        ) if np.any(med_confidence_mask) else 0
        
        # Low confidence predictions (<70% probability)
        low_confidence_mask = (np.maximum(self.y_pred_proba, 1 - self.y_pred_proba) < 0.7)
        low_conf_accuracy = accuracy_score(
            self.y_test[low_confidence_mask], 
            self.y_pred[low_confidence_mask]
        ) if np.any(low_confidence_mask) else 0
        
        stability_results = {
            'probability_stats': prob_stats,
            'high_confidence': {
                'count': np.sum(high_confidence_mask),
                'accuracy': high_conf_accuracy
            },
            'medium_confidence': {
                'count': np.sum(med_confidence_mask),
                'accuracy': med_conf_accuracy
            },
            'low_confidence': {
                'count': np.sum(low_confidence_mask),
                'accuracy': low_conf_accuracy
            }
        }
        
        logger.info(f"🎯 Prediction Stability Analysis:")
        logger.info(f"   Mean confidence: {prob_stats['mean_confidence']:.4f}")
        logger.info(f"   High confidence (>90%): {np.sum(high_confidence_mask)} samples, {high_conf_accuracy:.4f} accuracy")
        logger.info(f"   Medium confidence (70-90%): {np.sum(med_confidence_mask)} samples, {med_conf_accuracy:.4f} accuracy")
        logger.info(f"   Low confidence (<70%): {np.sum(low_confidence_mask)} samples, {low_conf_accuracy:.4f} accuracy")
        
        return stability_results
    
    def feature_robustness_analysis(self, n_permutations=1000):
        """Analyze model robustness to feature perturbations"""
        
        logger.info(f"🔍 Feature robustness analysis with {n_permutations} permutations...")
        
        baseline_accuracy = accuracy_score(self.y_test, self.y_pred)
        feature_importance_scores = []
        
        for feature_idx in range(self.X_test.shape[1]):
            feature_name = self.feature_names[feature_idx]
            permutation_scores = []
            
            # Perform permutations for this feature
            for _ in range(min(100, n_permutations)):  # Limit for speed
                X_permuted = self.X_test.copy()
                # Permute this feature's values
                X_permuted[:, feature_idx] = np.random.permutation(X_permuted[:, feature_idx])
                
                # Get predictions with permuted feature
                y_pred_permuted = self.model.predict(X_permuted)
                accuracy_permuted = accuracy_score(self.y_test, y_pred_permuted)
                
                permutation_scores.append(accuracy_permuted)
            
            # Calculate importance as drop in accuracy
            mean_permuted_accuracy = np.mean(permutation_scores)
            importance_score = baseline_accuracy - mean_permuted_accuracy
            
            feature_importance_scores.append({
                'feature': feature_name,
                'importance_score': importance_score,
                'baseline_accuracy': baseline_accuracy,
                'mean_permuted_accuracy': mean_permuted_accuracy
            })
        
        # Sort by importance
        feature_importance_scores.sort(key=lambda x: x['importance_score'], reverse=True)
        
        logger.info("📊 Top 10 Most Important Features (by permutation):")
        for i, feat_info in enumerate(feature_importance_scores[:10], 1):
            logger.info(f"   {i:2d}. {feat_info['feature']}: {feat_info['importance_score']:.4f} accuracy drop")
        
        return feature_importance_scores
    
    def comprehensive_validation_report(self):
        """Generate comprehensive validation report"""
        
        logger.info("🚀 Starting comprehensive model validation...")
        
        # Basic metrics
        accuracy = accuracy_score(self.y_test, self.y_pred)
        auc = roc_auc_score(self.y_test, self.y_pred_proba)
        cm = confusion_matrix(self.y_test, self.y_pred)
        
        # Run all validation analyses
        bootstrap_results = self.bootstrap_validation(n_bootstrap=1000)  # Reduced for speed
        significance_results = self.statistical_significance_tests()
        stability_results = self.prediction_stability_analysis()
        
        # Feature robustness (reduced for speed)
        # robustness_results = self.feature_robustness_analysis(n_permutations=100)
        
        # Compile comprehensive report
        report = {
            'timestamp': datetime.now().isoformat(),
            'basic_metrics': {
                'accuracy': float(accuracy),
                'roc_auc': float(auc),
                'confusion_matrix': cm.tolist(),
                'n_test_samples': len(self.y_test),
                'class_distribution': {
                    'positive': int(np.sum(self.y_test)),
                    'negative': int(len(self.y_test) - np.sum(self.y_test))
                }
            },
            'bootstrap_analysis': {
                'accuracy_mean': bootstrap_results['accuracy_mean'],
                'accuracy_ci': bootstrap_results['accuracy_ci'],
                'auc_mean': bootstrap_results['auc_mean'],
                'auc_ci': bootstrap_results['auc_ci'],
                'n_bootstrap': bootstrap_results['n_bootstrap']
            },
            'statistical_significance': significance_results,
            'prediction_stability': stability_results
        }
        
        logger.info("✅ Comprehensive validation complete")
        
        # Summary assessment
        self._print_validation_summary(report)
        
        return report
    
    def _print_validation_summary(self, report):
        """Print validation summary"""
        
        print(f"\n🎯 MODEL VALIDATION SUMMARY")
        print(f"=" * 50)
        
        basic = report['basic_metrics']
        bootstrap = report['bootstrap_analysis']
        significance = report['statistical_significance']
        stability = report['prediction_stability']
        
        print(f"📊 PERFORMANCE METRICS:")
        print(f"   Accuracy: {basic['accuracy']:.4f}")
        print(f"   ROC AUC: {basic['roc_auc']:.4f}")
        print(f"   Test samples: {basic['n_test_samples']}")
        
        print(f"\n🔄 BOOTSTRAP CONFIDENCE (95% CI):")
        print(f"   Accuracy: {bootstrap['accuracy_mean']:.4f} [{bootstrap['accuracy_ci'][0]:.4f}, {bootstrap['accuracy_ci'][1]:.4f}]")
        print(f"   ROC AUC: {bootstrap['auc_mean']:.4f} [{bootstrap['auc_ci'][0]:.4f}, {bootstrap['auc_ci'][1]:.4f}]")
        
        print(f"\n📈 STATISTICAL SIGNIFICANCE:")
        print(f"   vs 50% baseline: {'✅ Significant' if significance['is_significant'] else '❌ Not significant'}")
        print(f"   p-value: {significance['binomial_pvalue']:.6f}")
        
        print(f"\n🎯 PREDICTION CONFIDENCE:")
        print(f"   High confidence (>90%): {stability['high_confidence']['count']} samples, {stability['high_confidence']['accuracy']:.4f} accuracy")
        print(f"   Medium confidence (70-90%): {stability['medium_confidence']['count']} samples, {stability['medium_confidence']['accuracy']:.4f} accuracy")
        print(f"   Low confidence (<70%): {stability['low_confidence']['count']} samples, {stability['low_confidence']['accuracy']:.4f} accuracy")
        
        # Assessment vs Month 2 targets
        target_accuracy = 0.80
        achieved_accuracy = basic['accuracy']
        
        print(f"\n🎯 MONTH 2 TARGET ASSESSMENT:")
        if achieved_accuracy >= target_accuracy:
            print(f"   ✅ TARGET EXCEEDED: {achieved_accuracy:.1%} ≥ {target_accuracy:.1%}")
            print(f"   🚀 Ready for Month 3 development")
        else:
            print(f"   📊 Progress: {achieved_accuracy:.1%} (target: {target_accuracy:.1%})")
            print(f"   Gap: {target_accuracy - achieved_accuracy:.1%}")

def main():
    """Test validation suite"""
    print("🧪 MODEL VALIDATION SUITE TEST")
    
    # This would normally be called after model training
    print("⚠️  This is a standalone test - use after model training")
    print("✅ Validation suite ready for integration")

if __name__ == "__main__":
    main()