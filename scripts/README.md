# Scripts Directory

Essential operational scripts for the PM-HL Trading System.

## Files

### `dashboard_bridge.py` (230 lines)
- Bridges real trading signals to myhunch.xyz dashboard
- Connects system output to live dashboard tables
- Provides real-time data feed for web interface

### `start_real_claude_system.py` (443 lines) 
- Main system launcher script
- Launches complete autonomous trading system
- Handles real API integrations and process management

### `test_api_connections.py` (90 lines)
- Tests real API connections for system health checks
- Validates Hyperliquid and Polymarket API connectivity
- Used for system diagnostics and troubleshooting

## Usage

All scripts should be run from the project root directory and assume the main trading system files are in the `core/` directory.