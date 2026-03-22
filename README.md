# PM-HL-Trading-System

Clean implementation of the Polymarket + Hyperliquid paper trading system with institutional-grade protection.

## Overview

This repository contains the **production-ready** trading system built in March 2026 with comprehensive risk management and correlation protection.

## Directory Structure

```
core/
├── unified_signal_system.py      # Main 15-signal trading engine
├── btc_correlation_system.py     # BTC correlation protection
├── signal_validation_framework.py # Signal testing and validation

docs/
├── LEARNINGS.md                   # Key discoveries and fixes  
├── ARCHITECTURE.md                # System architecture

data/                              # Signal and market data
logs/                              # System logs
```

## Key Features

- **15 Validated Signals**: RSI, MACD, Stochastic, OI Divergence, Whale Entry, Funding Arbitrage, etc.
- **BTC Correlation Protection**: Prevents contradictory crypto positions
- **Anti-Chaos Protection**: Asset cooldown + price validation + position conflict resolution
- **Institutional Risk Management**: Stop losses, position limits, correlation blocking
- **Real-time Monitoring**: Telegram notifications + dashboard integration

## Database

- **Host**: localhost
- **Database**: agentfloor
- **User**: agentfloor
- **Tables**: simple_hl_trades, hl_signals, signal_performance

## Current Status (March 22, 2026)

- ✅ System stable with comprehensive protection suite
- ✅ 5 open positions: All correlation-aligned SHORT positions
- ✅ Total deployed capital: $10,680 (including learning curve trades)
- ✅ Capital at risk: $2,020 (current open positions)

## Trust Rebuilding Protocol

After initial system failures that cost real money, all changes follow strict verification:
1. Double-check all calculations with database/API
2. Test changes in isolation
3. Verify basic trading concepts
4. Always confirm with live data
5. Be transparent about uncertainty

## Recent Fixes (March 22, 2026)

- ✅ BTC correlation system strengthened (crypto-specific thresholds)
- ✅ Anti-chaos protections (asset cooldown, price validation)
- ✅ Process management (prevent duplicate signal firing)
- ✅ Dashboard accuracy fixes (deployed capital calculation)

Built with institutional-grade precision after learning from early system failures.