module.exports = {
  apps: [
    // REAL HYPERLIQUID API FEED
    {
      name: 'real-hyperliquid-api',
      script: 'python3',
      args: '/home/vj/polymarket/real_hyperliquid_api.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/real-hl-api.error.log',
      out_file: './logs/real-hl-api.out.log',
      time: true
    },

    // REAL POLYMARKET API FEED
    {
      name: 'real-polymarket-api',
      script: 'python3',
      args: '/home/vj/polymarket/real_polymarket_api.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/real-pm-api.error.log',
      out_file: './logs/real-pm-api.out.log',
      time: true
    },

    // REAL EDGE DETECTOR
    {
      name: 'real-edge-detector',
      script: 'python3',
      args: '/home/vj/polymarket/real_edge_detector.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '*/5 * * * *', // Every 5 minutes
      env: {
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/real-edge.error.log',
      out_file: './logs/real-edge.out.log',
      time: true
    },

    // CLAUDE FOUNDATION (Risk Management)
    {
      name: 'claude-foundation-real',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase0_foundation.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        REAL_MODE: 'true',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/foundation-real.error.log',
      out_file: './logs/foundation-real.out.log',
      time: true
    },

    // REAL TRADE EXECUTION
    {
      name: 'real-trade-execution',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase2_execution_optimization.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        REAL_MODE: 'true',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/execution-real.error.log',
      out_file: './logs/execution-real.out.log',
      time: true
    },

    // REAL MONITORING & LEARNING
    {
      name: 'real-monitoring',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase3_monitoring_learning.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '0 */6 * * *', // Every 6 hours
      env: {
        REAL_MODE: 'true',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/monitoring-real.error.log',
      out_file: './logs/monitoring-real.out.log',
      time: true
    }
  ]
}