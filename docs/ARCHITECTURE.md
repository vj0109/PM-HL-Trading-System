# Signal Engine — Technical Architecture
*Last updated: 2026-03-16*

## System Overview
Multi-asset signal generation system with PostgreSQL database, PM2 process management, and web dashboard integration.

## PM2 Process Management

### Active Processes (as of Mar 16, 2026)
| ID | Name | Status | Uptime | Purpose |
|----|------|--------|--------|---------|
| 0 | agentfloor | online | 6D | Main app server (Next.js) |
| 60 | djgigs | online | 2D | DJGigs platform |
| 33 | hunch | online | 84s | MyHunch app (frequent restarts) |
| 42 | hunch-sub-check | online | 2h | Subscription validation |
| 3 | polymarket-arb | online | 12s | Arbitrage scanner (high CPU) |
| 2 | polymarket-oracle | online | 7D | Price feeds & market data |
| 4 | polymarket-scanner | online | 6D | Market discovery |

### Stopped Signal Processes (CRITICAL ISSUE)
| ID | Name | Status | Purpose |
|----|------|--------|---------|
| 63 | hl-paper-trader | stopped | HL position management |
| 55 | hl-resolve | stopped | HL trade resolution |
| 56 | tradfi-signals | stopped | TradFi signal generation |
| 57 | tradfi-resolve | stopped | TradFi trade resolution |
| 49 | polymarket-daily-picks | stopped | PM signal generation |
| 50 | polymarket-resolve | stopped | PM trade resolution |
| 52 | hyperliquid-signals | stopped | HL signal generation |
| 51 | polymarket-whale | stopped | Whale tracking |
| 58 | news-monitor | stopped | News sentiment |
| 59 | platform-checker | stopped | Cross-platform monitoring |

### Individual Signal Processes (All Stopped)
| ID | Name | Status | Purpose |
|----|------|--------|---------|
| 64 | btc-regime | stopped | BTC trend detection |
| 65 | fear-greed | stopped | Fear & Greed Index |
| 66 | dxy-signal | stopped | Dollar strength |
| 67 | sector-rotation | stopped | Sector momentum |
| 68 | earnings-signal | stopped | Post-earnings drift |
| 69 | tradfi-watchlist | stopped | Asset monitoring |

## Database Schema (PostgreSQL)

### Connection Details
- **Host**: localhost
- **Database**: agentfloor  
- **User**: agentfloor
- **Password**: V1S2I3O4J
- **Port**: 5432

### Core Signal Tables (68 total tables)

#### Hyperliquid Tables
```sql
-- Live positions and signals
hl_paper_trades          -- Active HL paper positions
hl_signals               -- Historical signal data (12,700+ entries)
hl_signal_performance    -- Performance summaries by signal type
```

#### TradFi Tables  
```sql
-- Backtest and live data
tradfi_backtest_results     -- Historical backtest (4,646 trades)
tradfi_signal_performance   -- Signal performance by asset
tradfi_paper_trades        -- Live TradFi positions
tradfi_correlations        -- Cross-asset correlations
```

#### Polymarket Tables
```sql
-- Prediction market data
polymarket_paper_trades     -- PM trade history and positions
pick_signal_attribution     -- Which signals drove which picks
```

#### System Tables
```sql
-- Configuration and monitoring
signal_weights             -- Auto-computed signal weights
signal_firings            -- Individual signal events
signal_performance        -- Cross-platform performance stats
platform_comparisons     -- Price divergence tracking
news_checks              -- News sentiment monitoring
```

#### Application Tables (Non-Signal)
```sql
-- MyHunch app
hunch_markets, hunch_bets, hunch_users, hunch_tournaments
-- DJGigs platform  
djgigs_events, djgigs_djs, djgigs_venues
-- Agentora platform
agents, attestations, jobs, transactions
```

## File Structure

### Signal Engine Repository (`/home/vj/polymarket/`)
```
├── README.md                    # Main documentation
├── docs/                       # Documentation (this restructure)
│   ├── PRODUCT.md              # Master product doc
│   ├── LEARNINGS.md            # Daily learnings journal
│   ├── STRATEGY_PM.md          # Polymarket strategy
│   ├── STRATEGY_HL.md          # Hyperliquid strategy
│   ├── STRATEGY_TRADFI.md      # TradFi strategy
│   └── ARCHITECTURE.md         # This file
│
├── # TradFi Signal System
├── tradfi_signals.py           # Main TradFi signal generator
├── tradfi_watchlist.py         # 375-asset monitoring
├── tradfi_backtest.py          # Historical backtesting
├── tradfi_resolve.py           # Trade resolution
├── correlation_signals.py      # Cross-asset correlations
├── signal_weights.py           # Auto signal weighting
├── populate_signal_performance.py  # Performance aggregation
│
├── # Hyperliquid System
├── hyperliquid_signals.py      # HL signal generation
├── hl_paper_trader.py          # Position management
├── hl_resolve.py               # Trade resolution
├── hl_backtest.py              # Historical backtesting
│
├── # Polymarket System  
├── daily_picks.py              # Daily signal generation
├── resolve_picks.py            # Trade resolution
├── whale_tracker.py            # Whale position tracking
├── enhanced_scanner.py         # Multi-factor scanning
├── backtest.py                 # Historical backtesting
├── arb_scanner.py              # Cross-platform arbitrage
│
├── # Market Data Sync
├── hunch_market_sync.py        # PM → MyHunch sync
├── hunch_event_sync.py         # Event market sync
├── daily_sports_sync.py        # Sports market creation
├── manifold_sync.py            # Manifold integration
├── metaculus_sync.py           # Metaculus integration
├── quality_filter.py           # Market quality scoring
│
├── # Monitoring & Analysis
├── news_monitor.py             # News sentiment tracking
├── platform_checker.py        # Price divergence alerts
│
└── # Data Storage
    ├── db_dumps/               # Database backups
    │   ├── signal_tables_schema_and_data.sql
    │   └── *.csv              # Exported performance data
    ├── backtest_results/       # Historical analysis
    ├── backtest_results.json   # PM backtest output
    ├── hl_backtest_results.json # HL backtest output
    ├── hl_signals.json         # Latest HL signals
    └── whale_signals.json      # Latest whale positions
```

## Data Flow Architecture

### 1. Signal Generation Pipeline
```
Individual Signal Scripts → Database Tables → Performance Analysis
     ↓                           ↓                    ↓
[Every 2-4 hours]         [signal_firings]    [signal_performance]
     ↓                           ↓                    ↓
  Signal Weights         Paper Trade Tables    Dashboard Display
```

### 2. Paper Trading Flow
```
Signal Generation → Trade Creation → Position Monitoring → Resolution → Performance Update
       ↓                 ↓               ↓                ↓              ↓
signal_firings → *_paper_trades → PM2 monitoring → *_resolve.py → signal_performance
```

### 3. Dashboard Integration
```
Database Tables → API Endpoints → MyHunch Dashboard → User Interface
       ↓               ↓              ↓                  ↓
 Live signal data → myhunch.xyz → Admin panel → Performance charts
```

## Cron Schedules (Intended - Currently Stopped)

### Polymarket Processes
```bash
# Daily signal generation
polymarket-daily-picks: "0 8 * * *"    # 8 AM daily

# Trade resolution  
polymarket-resolve: "0 9 * * *"        # 9 AM daily

# Whale monitoring
polymarket-whale: "0 */4 * * *"        # Every 4 hours
```

### Hyperliquid Processes
```bash
# Signal generation
hyperliquid-signals: "0 */2 * * *"     # Every 2 hours

# Paper trading
hl-paper-trader: "0 */4 * * *"         # Every 4 hours

# Trade resolution (frequent)
hl-resolve: "*/15 * * * *"              # Every 15 minutes
```

### TradFi Processes  
```bash
# Signal generation
tradfi-signals: "0 */4 * * *"          # Every 4 hours

# Trade resolution
tradfi-resolve: "0 */1 * * *"          # Every hour
```

### Monitoring & Maintenance
```bash
# News sentiment
news-monitor: "0 */6 * * *"            # Every 6 hours

# Platform divergence
platform-checker: "0 */6 * * *"       # Every 6 hours

# Market data sync
hunch-market-sync: "0 */1 * * *"       # Hourly
```

## API Endpoints & Integration

### MyHunch Dashboard
- **Base URL**: https://myhunch.xyz
- **Admin Panel**: /admin/polymarket
- **API Routes**: /api/signals, /api/performance, /api/trades

### External APIs Used
```yaml
# Polymarket
gamma-api.polymarket.com    # Market discovery
data-api.polymarket.com     # Positions & trades  
clob.polymarket.com         # Order book & prices

# Hyperliquid
api.hyperliquid.xyz         # Trading & market data

# TradFi Data
yfinance                    # Stock/commodity prices
alternative.me             # Fear & Greed Index
```

### Database Connections
```python
# Standard connection string used across all scripts
DATABASE_URL = "postgresql://agentfloor:V1S2I3O4J@localhost:5432/agentfloor"
```

## GitHub Repositories

### Primary Repositories
1. **Signal Engine**: `vj0109/signal-engine` (private)
   - All signal generation code
   - Database schemas and migrations
   - Backtest results and analysis

2. **MyHunch App**: `vj0109/hunchxyz-app` (private)  
   - Dashboard frontend
   - API endpoints for signal data
   - User interface and visualization

3. **Agentora Platform**: `vj0109/agentfloor-app` (private)
   - Main application server
   - Agent verification system
   - Job and transaction management

## Deployment & Operations

### Development Environment
- **Host**: VJopenclawdroplet2 (VPS)
- **OS**: Linux Ubuntu
- **Runtime**: Node.js v22.22.0, Python 3.x
- **Database**: PostgreSQL 13+
- **Process Management**: PM2

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://agentfloor:V1S2I3O4J@localhost:5432/agentfloor

# APIs (stored in respective app .env files)
POLYMARKET_API_KEY=...
HYPERLIQUID_API_KEY=...
OPENAI_API_KEY=...
```

### Backup Strategy
- **Database**: Weekly full dump to `db_dumps/`
- **Code**: Git commits required after every deployment
- **Logs**: PM2 logs retained for debugging
- **Performance Data**: CSV exports in `db_dumps/`

## Monitoring & Alerting

### Health Checks
- **Process monitoring**: PM2 automatic restarts
- **Database connectivity**: Connection pooling with retries  
- **API status**: External API health checks
- **Performance alerts**: Significant win rate drops

### Key Metrics Tracked
- **Signal performance**: Win rate, Sharpe ratio, drawdown
- **System health**: Process uptime, error rates
- **Trade attribution**: Which signals driving results
- **Cross-platform**: Price divergences and arbitrage opportunities

## Security Considerations

### API Key Management
- Keys stored in environment variables
- No hardcoded credentials in source code
- Rotation policy for external API keys

### Database Security
- Connection string not exposed in public repos
- User permissions limited to required tables
- Regular backups with encryption

### Process Isolation
- Each signal type runs in separate PM2 process
- Failure in one signal doesn't affect others
- Resource limits to prevent runaway processes

## Troubleshooting & Maintenance

### Common Issues
1. **PM2 processes stopped**: Check logs, restart with `pm2 restart <id>`
2. **Database connection errors**: Verify PostgreSQL service status
3. **API rate limits**: Implement backoff and retry logic
4. **Signal performance degradation**: Check for market regime changes

### Regular Maintenance
- **Weekly**: Review PM2 process status and logs
- **Monthly**: Database performance analysis and cleanup
- **Quarterly**: Full system backup and disaster recovery test
- **As needed**: Signal recalibration based on performance data

## Performance Optimization

### Database Indexing
```sql
-- Key indexes for performance
CREATE INDEX idx_hl_signals_timestamp ON hl_signals(timestamp);
CREATE INDEX idx_paper_trades_status ON hl_paper_trades(status);
CREATE INDEX idx_signal_performance_type ON signal_performance(signal_type);
```

### Process Resource Management
- **Memory limits**: 512MB per PM2 process
- **CPU throttling**: Prevent signal processes from consuming >50% CPU
- **Concurrent limits**: Max 15 active paper trades per platform

### API Rate Limiting
- **Polymarket**: Respect 10 req/sec limits
- **Hyperliquid**: 50 req/sec burst allowance
- **yfinance**: Batch requests to minimize API calls