# POLYMARKET SIGNAL TESTING & VALIDATION PLAN

**Status:** Infrastructure built, validation NOT yet completed
**Critical Gap:** Need historical backtesting before any deployment

---

## 🎯 TIER 1 SIGNALS TO VALIDATE

### **1. VOLUME SPIKE + PROBABILITY MOVE**
**File:** `pm_volume_spike_signal.py`
**Logic:** Volume >3x average + probability move >5%
**Current Parameters:**
- `volume_multiplier = 3.0` (3x volume threshold)
- `min_probability_move = 0.05` (5% move minimum)
- `lookback_hours = 24` (24h baseline)

**Data Requirements:**
- ✅ **Available:** Current volume, 24h volume (Gamma API)
- ❌ **Missing:** Historical time series for proper baseline calculation
- ❌ **Missing:** Historical price movements to validate 5% threshold

**Current Issues:**
- Simplified volume calculation (volume vs 24h average)
- No time series data for proper volume baseline
- 0 signals detected = parameters likely too restrictive

**Validation Plan:**
1. Collect 30+ days historical volume data
2. Calculate proper rolling averages
3. Test thresholds: 2x, 3x, 4x volume multipliers
4. Test price move thresholds: 3%, 5%, 8%
5. Backtest on 6 months historical data

---

### **2. RESOLUTION PROXIMITY EFFECT**
**File:** `pm_proximity_signal.py` 
**Logic:** Markets at ~50% with <48h to resolution
**Current Parameters:**
- `max_hours_to_resolution = 48` (48h maximum)
- `min_hours_to_resolution = 2` (2h minimum)
- `price_range_min = 0.35` (35% minimum)
- `price_range_max = 0.65` (65% maximum)

**Data Requirements:**
- ❌ **CRITICAL ISSUE:** 0 markets with resolution data found
- ❌ **API Gap:** Gamma API may not include resolution times
- ❌ **Missing:** Need CLOB API or alternative source for resolution data

**Current Issues:**
- API returning 0 markets with resolution time data
- Need to investigate CLOB API for resolution timestamps
- Logic untested due to data availability

**Validation Plan:**
1. **URGENT:** Investigate CLOB API for resolution time data
2. Manual verification of resolution times for active markets
3. Adjust parameters based on real market distribution
4. Test on markets approaching known resolution dates

---

### **3. CONTRARIAN REVERSAL**
**File:** `pm_contrarian_signal.py`
**Logic:** >10% move without news catalyst
**Current Parameters:**
- `min_price_move = 0.10` (10% minimum move)
- `lookback_hours = 24` (24h window)
- `max_volume_threshold = 5000` (news proxy filter)

**Data Requirements:**
- ❌ **Missing:** Historical price data for calculating moves
- ❌ **Missing:** News correlation data to validate catalyst filter
- ❌ **Simplified:** Using volume as news proxy (inadequate)

**Current Issues:**
- No historical price time series for move calculation
- Volume-based news filter is crude approximation
- 0 signals = parameters or logic needs adjustment

**Validation Plan:**
1. Collect historical price time series data
2. Identify actual 10%+ moves in historical data
3. Correlate with news events to validate catalyst detection
4. Test move thresholds: 8%, 10%, 12%
5. Improve news detection beyond volume proxy

---

## 📊 DATA SOURCE ANALYSIS

### **AVAILABLE APIs:**
1. **Gamma API** (`gamma-api.polymarket.com`)
   - ✅ Market data, current prices, volume
   - ❌ Limited historical time series
   - ❌ No resolution time data observed

2. **CLOB API** (`clob.polymarket.com`)
   - ✅ Real-time trading data
   - ❓ Unknown: Historical data availability
   - ❓ Unknown: Resolution time inclusion

3. **py-clob-client** 
   - ✅ Installed and functional
   - ❌ Not yet explored for historical data

### **CRITICAL DATA GAPS:**
1. **Historical time series** for volume baselines
2. **Historical price movements** for reversal detection  
3. **Resolution timestamps** for proximity signals
4. **News correlation data** for catalyst filtering

---

## 🧪 VALIDATION FRAMEWORK NEEDED

### **Phase 1: Data Collection (Week 1)**
```python
# Build historical data collector
class PMHistoricalDataCollector:
    def collect_market_history(self, days=90):
        # Collect 90 days of price/volume data
        pass
    
    def collect_resolution_data(self):
        # Map markets to resolution times
        pass
    
    def collect_news_events(self):
        # Correlate major moves with news
        pass
```

### **Phase 2: Parameter Optimization (Week 2)**
```python
# Test parameter ranges
volume_multipliers = [2.0, 2.5, 3.0, 3.5, 4.0]
price_move_thresholds = [0.03, 0.05, 0.08, 0.10, 0.12]
time_windows = [12, 24, 48, 72]

for params in parameter_combinations:
    backtest_results = backtest_signal(params)
    if meets_validation_criteria(backtest_results):
        approved_signals.append(params)
```

### **Phase 3: Backtesting (Week 3)**
```python
# Apply HL validation standards to PM
validation_criteria = {
    'min_trades': 50,
    'min_win_rate': 0.55,
    'min_profit': 0,
    'max_drawdown': 0.20
}
```

---

## 🚨 CRITICAL ISSUES TO RESOLVE

### **Immediate Blockers:**
1. **No historical data collection system** 
2. **Resolution time data unavailable** via current API
3. **All signals returning 0 detections** (parameters or logic issues)

### **Data Quality Issues:**
1. **Simplified volume calculations** (need proper time series)
2. **No news correlation** (volume proxy inadequate)
3. **Price movement detection** relies on estimation

### **Testing Gaps:**
1. **No backtesting completed** on any PM signal
2. **No parameter optimization** conducted
3. **No win rate validation** performed

---

## 📋 IMMEDIATE ACTION PLAN

### **Priority 1: Data Investigation**
1. Explore CLOB API for historical data availability
2. Test py-clob-client for resolution time access
3. Build data collection system for 30+ day history

### **Priority 2: Parameter Tuning**
1. Adjust volume thresholds (try 2x instead of 3x)
2. Reduce price move requirements (try 3% instead of 5%)
3. Expand time windows for proximity signals

### **Priority 3: Validation Setup**
1. Build PM-specific backtesting framework
2. Apply HL validation standards (55%+ WR, 50+ trades)
3. Set up continuous data collection for future backtesting

---

## 🎯 SUCCESS CRITERIA

### **Signal Validation Requirements:**
- **Minimum 50 trades** in 90-day backtest
- **55%+ win rate** consistently
- **Positive expected value** 
- **<20% maximum drawdown**

### **Data Quality Requirements:**
- **90+ days historical data** for robust backtesting
- **Real resolution times** for proximity signals
- **News event correlation** for reversal validation

---

**BOTTOM LINE: We have built the infrastructure but need to complete data collection and historical validation before any PM signal can be considered ready for deployment.**