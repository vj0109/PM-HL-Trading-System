# Database Directory

Database schema and backup files for the PM-HL Trading System.

## Files

### `signal_tables_schema_and_data.sql` (37MB)
- Complete database dump including:
  - All signal performance tables
  - Trading history and paper trades  
  - Signal weights and configurations
  - Historical performance data

## Database Configuration

- **Host**: localhost
- **Database**: agentfloor
- **User**: agentfloor
- **Password**: V1S2I3O4J

## Key Tables

- `simple_hl_trades` - Main trading records
- `hl_signals` - Signal firing history
- `signal_performance` - Performance tracking
- `hl_paper_trades` - Paper trading records

## Restore Instructions

```bash
psql -h localhost -U agentfloor -d agentfloor < signal_tables_schema_and_data.sql
```