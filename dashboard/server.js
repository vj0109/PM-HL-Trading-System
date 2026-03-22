const express = require('express');
const { Pool } = require('pg');
const path = require('path');

const app = express();
const PORT = 3004;

// Database connection
const pool = new Pool({
  host: 'localhost',
  database: 'agentfloor',
  user: 'agentfloor',
  password: 'V1S2I3O4J'
});

// Serve static files
app.use(express.static('public'));

// Get current prices from Hyperliquid
async function getCurrentPrices() {
  try {
    const response = await fetch('https://api.hyperliquid.xyz/info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'allMids' })
    });
    
    if (!response.ok) return {};
    
    const data = await response.json();
    const prices = {};
    
    // Hyperliquid returns object with coin names as keys
    for (const [coin, price] of Object.entries(data)) {
      if (price && !isNaN(parseFloat(price))) {
        prices[coin] = parseFloat(price);
      }
    }
    
    console.log('Fetched prices:', prices);
    return prices;
  } catch (error) {
    console.error('Error fetching prices:', error);
    return {};
  }
}

// Calculate unrealized P&L
function calculateUnrealizedPnL(position, currentPrice) {
  if (!currentPrice) return 0;
  
  const entryPrice = parseFloat(position.entry_price);
  const positionSize = parseFloat(position.position_size);
  
  let priceDiff;
  if (position.side === 'LONG') {
    priceDiff = currentPrice - entryPrice;
  } else { // SHORT
    priceDiff = entryPrice - currentPrice;
  }
  
  return (priceDiff / entryPrice) * positionSize;
}

// Get trading data
app.get('/api/trading-data', async (req, res) => {
  try {
    // Get current prices
    const currentPrices = await getCurrentPrices();
    
    // Get open positions
    const openResult = await pool.query(`
      SELECT id, coin, side, entry_price, position_size, entry_time, reason
      FROM simple_hl_trades 
      WHERE status = 'OPEN'
      ORDER BY entry_time DESC
    `);

    // Get closed positions today
    const closedResult = await pool.query(`
      SELECT id, coin, side, entry_price, exit_price, position_size, exit_time, pnl, exit_reason
      FROM simple_hl_trades 
      WHERE status = 'CLOSED' 
      AND exit_time >= CURRENT_DATE
      ORDER BY exit_time DESC
    `);

    // Get total realized P&L
    const pnlResult = await pool.query(`
      SELECT SUM(pnl) as total_pnl
      FROM simple_hl_trades 
      WHERE status = 'CLOSED'
    `);

    const realizedPnL = parseFloat(pnlResult.rows[0]?.total_pnl || 0);
    const dailyPnL = closedResult.rows.reduce((sum, trade) => sum + parseFloat(trade.pnl || 0), 0);
    
    // Calculate unrealized P&L for open positions
    let totalUnrealizedPnL = 0;
    const openPositionsWithPrices = openResult.rows.map(position => {
      const currentPrice = currentPrices[position.coin];
      const unrealizedPnL = calculateUnrealizedPnL(position, currentPrice);
      totalUnrealizedPnL += unrealizedPnL;
      
      const pnlPercent = (unrealizedPnL / parseFloat(position.position_size)) * 100;
      
      return {
        ...position,
        current_price: currentPrice,
        unrealized_pnl: unrealizedPnL,
        pnl_percent: pnlPercent
      };
    });
    
    // Calculate total deployed capital (all positions ever)
    const allTradesResult = await pool.query(`
      SELECT SUM(position_size) as total_deployed
      FROM simple_hl_trades
    `);
    const totalDeployedCapital = parseFloat(allTradesResult.rows[0]?.total_deployed || 0);
    
    // Calculate current capital at risk (open positions)
    const currentCapitalAtRisk = openResult.rows.reduce((sum, pos) => 
      sum + parseFloat(pos.position_size), 0);
    
    // Calculate win rate from all closed trades
    const winRateResult = await pool.query(`
      SELECT 
        COUNT(*) as total_trades,
        COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades
      FROM simple_hl_trades 
      WHERE status = 'CLOSED'
    `);
    const totalTrades = parseInt(winRateResult.rows[0]?.total_trades || 0);
    const winningTrades = parseInt(winRateResult.rows[0]?.winning_trades || 0);
    const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;
    
    // Cumulative P&L (all realized gains/losses)
    const cumulativePnL = realizedPnL;
    
    res.json({
      openPositions: openPositionsWithPrices,
      closedPositions: closedResult.rows,
      totalDeployedCapital: parseFloat(totalDeployedCapital.toFixed(2)),
      currentCapitalAtRisk: parseFloat(currentCapitalAtRisk.toFixed(2)),
      cumulativePnL: parseFloat(cumulativePnL.toFixed(2)),
      runningPnL: parseFloat(totalUnrealizedPnL.toFixed(2)), // P&L of open positions
      dailyPnL: parseFloat(dailyPnL.toFixed(2)),
      winRate: parseFloat(winRate.toFixed(1)),
      openCount: openResult.rows.length
    });
  } catch (error) {
    console.error('Database error:', error);
    res.status(500).json({ error: 'Database error' });
  }
});

app.get('/admin/PM-HL-Trading', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'dashboard.html'));
});

// Default route
app.get('/', (req, res) => {
  res.redirect('/admin/PM-HL-Trading');
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`Myhunch Trading Dashboard running on port ${PORT}`);
});