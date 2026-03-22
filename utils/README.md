# Utils Directory

Essential utility and management scripts for the trading system.

## Files

### `risk_management_system.py` (24KB, 443 lines)
- Comprehensive risk management system
- Position sizing, stop losses, correlation checks
- Portfolio-level risk controls and circuit breakers

### `position_tracker.py` (20KB, 443 lines) 
- Real-time position tracking and P&L monitoring
- Automated position status updates
- Integration with database for live position data

### `close_all_positions.py` (1KB, 43 lines)
- Emergency position closure utility
- Closes all open positions in database
- Use for system shutdown or emergency risk management

## Usage

These utilities work with the core trading system and should be run from the project root directory.