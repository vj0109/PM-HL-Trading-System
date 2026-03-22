module.exports = {
  apps: [
    // CLAUDE MASTER AUTONOMOUS SYSTEM - The brain
    {
      name: 'claude-master-system',
      script: 'python3',
      args: '/home/vj/polymarket/claude_master_autonomous_system.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/vj/polymarket'
      },
      error_file: './logs/claude-master.error.log',
      out_file: './logs/claude-master.out.log',
      log_file: './logs/claude-master.log',
      time: true,
      max_restarts: 10,
      min_uptime: '10s'
    },

    // PHASE 0: FOUNDATION SYSTEM - Risk management
    {
      name: 'claude-foundation',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase0_foundation.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: './logs/foundation.error.log',
      out_file: './logs/foundation.out.log',
      log_file: './logs/foundation.log',
      time: true
    },

    // PHASE 1: EDGE DETECTION MODULES
    {
      name: 'claude-funding-arbitrage',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase1_funding_arbitrage.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '*/5 * * * *', // Restart every 5 minutes for fresh data
      error_file: './logs/funding.error.log',
      out_file: './logs/funding.out.log',
      time: true
    },

    {
      name: 'claude-oi-divergence', 
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase1_oi_divergence.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '*/15 * * * *', // Every 15 minutes
      error_file: './logs/oi-divergence.error.log',
      out_file: './logs/oi-divergence.out.log',
      time: true
    },

    {
      name: 'claude-liquidation-cascade',
      script: 'python3', 
      args: '/home/vj/polymarket/claude_phase1_liquidation_cascade.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '*/10 * * * *', // Every 10 minutes
      error_file: './logs/liquidation.error.log',
      out_file: './logs/liquidation.out.log',
      time: true
    },

    {
      name: 'claude-pm-mispricing',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase1_polymarket_mispricing.py', 
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '*/30 * * * *', // Every 30 minutes
      error_file: './logs/pm-mispricing.error.log',
      out_file: './logs/pm-mispricing.out.log',
      time: true
    },

    // PHASE 2: EXECUTION OPTIMIZATION
    {
      name: 'claude-execution',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase2_execution_optimization.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: './logs/execution.error.log',
      out_file: './logs/execution.out.log',
      time: true
    },

    // PHASE 3: MONITORING & LEARNING
    {
      name: 'claude-monitoring',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase3_monitoring_learning.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '0 */6 * * *', // Every 6 hours for signal weight updates
      error_file: './logs/monitoring.error.log',
      out_file: './logs/monitoring.out.log', 
      time: true
    },

    // PHASE 4: SCALING
    {
      name: 'claude-scaling',
      script: 'python3',
      args: '/home/vj/polymarket/claude_phase4_scaling.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '0 9 * * 1', // Weekly scaling review - Monday 9 AM
      error_file: './logs/scaling.error.log',
      out_file: './logs/scaling.out.log',
      time: true
    },

    // PHASE 5: ADVANCED SCALING
    {
      name: 'claude-advanced-scaling',
      script: 'python3', 
      args: '/home/vj/polymarket/claude_phase5_advanced_scaling.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      cron_restart: '0 0 1 * *', // Monthly rebalancing - 1st of month
      error_file: './logs/advanced-scaling.error.log',
      out_file: './logs/advanced-scaling.out.log',
      time: true
    },

    // EXISTING HYPERLIQUID COMPONENTS (preserved)
    {
      name: 'hl-paper-trader',
      script: 'python3',
      args: '/home/vj/polymarket/hl_paper_trader.py',
      cwd: '/home/vj/polymarket', 
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '0 */4 * * *', // Every 4 hours
      error_file: './logs/hl-trader.error.log',
      out_file: './logs/hl-trader.out.log',
      time: true
    },

    {
      name: 'hl-resolver',
      script: 'python3',
      args: '/home/vj/polymarket/hl_resolve.py', 
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      cron_restart: '0 * * * *', // Every hour
      error_file: './logs/hl-resolver.error.log',
      out_file: './logs/hl-resolver.out.log',
      time: true
    },

    {
      name: 'hyperliquid-signals',
      script: 'python3',
      args: '/home/vj/polymarket/hyperliquid_signals.py',
      cwd: '/home/vj/polymarket',
      instances: 1, 
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '0 */2 * * *', // Every 2 hours
      error_file: './logs/hl-signals.error.log',
      out_file: './logs/hl-signals.out.log',
      time: true
    },

    // EXISTING POLYMARKET COMPONENTS (preserved)
    {
      name: 'polymarket-daily-picks',
      script: 'python3',
      args: '/home/vj/polymarket/daily_picks.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      cron_restart: '49 8 * * *', // Daily 8:49 AM
      error_file: './logs/pm-daily.error.log',
      out_file: './logs/pm-daily.out.log',
      time: true
    },

    {
      name: 'polymarket-resolve',
      script: 'python3', 
      args: '/home/vj/polymarket/resolve_trades.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      cron_restart: '50 9 * * *', // Daily 9:50 AM
      error_file: './logs/pm-resolve.error.log',
      out_file: './logs/pm-resolve.out.log',
      time: true
    },

    {
      name: 'polymarket-whale',
      script: 'python3',
      args: '/home/vj/polymarket/whale_tracker.py',
      cwd: '/home/vj/polymarket',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      cron_restart: '51 */4 * * *', // Every 4 hours
      error_file: './logs/pm-whale.error.log',
      out_file: './logs/pm-whale.out.log',
      time: true
    }
  ]
}