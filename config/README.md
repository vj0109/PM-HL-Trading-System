# Config Directory

Configuration files for PM2 process management and system deployment.

## Files

### `ecosystem.config.js`
- Main PM2 ecosystem configuration
- Process definitions for all trading system components
- Development and staging configurations

### `ecosystem-real.config.js` 
- Production PM2 configuration
- Real trading system deployment settings
- Optimized for live trading environment

## Usage

Deploy with PM2:
```bash
# Development/staging
pm2 start config/ecosystem.config.js

# Production
pm2 start config/ecosystem-real.config.js
```

## Process Management

PM2 manages multiple processes:
- Signal detection system
- Dashboard server
- Risk management
- Position tracking
- API bridges