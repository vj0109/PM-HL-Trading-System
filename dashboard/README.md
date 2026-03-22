# Dashboard Directory

The myhunch.xyz trading dashboard web application.

## Files

### `server.js` (168 lines)
- Node.js Express server serving the trading dashboard
- Contains the deployed capital calculation fix (March 22)
- Connects to PostgreSQL database for live trading data
- Serves API endpoints for dashboard data

### `public/dashboard.html` (352 lines)  
- Main dashboard web interface
- Real-time trading positions and P&L display
- Shows total deployed capital vs capital at risk
- Auto-refresh trading data every 30 seconds

### `package.json`
- Node.js dependencies for dashboard server
- Express, PostgreSQL client, etc.

## Usage

```bash
cd dashboard/
npm install
node server.js
# Dashboard available at http://localhost:3004
```

## PM2 Production
- Service name: `myhunch-dashboard` 
- Port: 3004
- Auto-restart enabled

## Database Connection
- Host: localhost
- Database: agentfloor
- User: agentfloor
- Tables: simple_hl_trades, hl_signals