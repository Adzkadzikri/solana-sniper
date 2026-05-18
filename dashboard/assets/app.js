/**
 * Dashboard App - Polls bot status and updates UI
 */
const POLL_INTERVAL = 5000;
const INITIAL_CAPITAL = 40;
const TARGET = 1000;

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

function $(id) { return document.getElementById(id); }

function fmt(n, d = 2) { return '$' + Number(n).toFixed(d); }

function updateUI(data) {
  if (!data) return;

  // Status
  const statusEl = $('botStatus');
  if (data.running) {
    statusEl.className = 'status-badge online';
    statusEl.textContent = '● Running';
  } else if (data.risk && data.risk.paused) {
    statusEl.className = 'status-badge paused';
    statusEl.textContent = '● Paused';
  } else {
    statusEl.className = 'status-badge offline';
    statusEl.textContent = '● Offline';
  }

  if (data.paper_trading) {
    $('paperBadge').style.display = 'block';
  }

  // Equity
  const equity = data.equity || INITIAL_CAPITAL;
  const ret = ((equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100);
  $('equity').textContent = fmt(equity);
  $('equity').className = 'metric-value ' + (ret >= 0 ? 'green' : 'red');
  $('equityReturn').textContent = (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%';
  $('equityReturn').className = 'metric-sub ' + (ret >= 0 ? 'green' : 'red');

  $('peakEquity').textContent = fmt(data.peak_equity || equity);

  // Drawdown
  const dd = data.drawdown || 0;
  $('drawdown').textContent = dd.toFixed(1) + '%';
  $('drawdown').className = 'metric-value ' + (dd > 10 ? 'red' : dd > 5 ? 'yellow' : 'green');
  $('ddBar').style.width = Math.min(dd / 15 * 100, 100) + '%';

  // Mode
  const mode = data.mode || 'N/A';
  const modeEl = $('mode');
  modeEl.textContent = mode;
  const modeColors = { 'AGGRESSIVE': 'green', 'MODERATE': 'yellow', 'BALANCED': 'blue', 'PASSIVE': 'purple', 'STOPPED': 'red' };
  modeEl.className = 'metric-value mode-text ' + (modeColors[mode] || '');
  $('tier').textContent = data.tier || '';

  // Win Rate
  $('winRate').textContent = (data.win_rate || 0).toFixed(0) + '%';
  $('winRate').className = 'metric-value ' + ((data.win_rate || 0) >= 50 ? 'green' : 'yellow');
  $('tradeCount').textContent = (data.total_trades || 0) + ' trades';

  // Target Progress
  const progress = Math.min(((equity - INITIAL_CAPITAL) / (TARGET - INITIAL_CAPITAL)) * 100, 100);
  $('targetPct').textContent = Math.max(0, progress).toFixed(1) + '%';
  $('targetPct').className = 'metric-value ' + (progress >= 100 ? 'green' : 'blue');
  $('targetBar').style.width = Math.max(0, progress) + '%';

  // Risk
  const risk = data.risk || {};
  const dailyPnl = risk.daily_pnl || 0;
  $('dailyPnl').textContent = (dailyPnl >= 0 ? '+' : '') + fmt(dailyPnl);
  $('dailyPnl').className = dailyPnl >= 0 ? 'green' : 'red';
  $('dailyLimit').textContent = fmt(risk.daily_limit || 0);
  $('winStreak').textContent = risk.win_streak || 0;
  $('loseStreak').textContent = risk.lose_streak || 0;
  $('regime').textContent = data.regime || 'Unknown';
  $('cycle').textContent = data.cycle || 0;

  // Positions
  $('posCount').textContent = data.active_positions || 0;

  // Stats
  const stats = data.stats || {};
  $('totalTrades').textContent = stats.total_trades || 0;
  $('winningTrades').textContent = stats.winning || 0;
  $('losingTrades').textContent = stats.losing || 0;
  $('profitFactor').textContent = (stats.profit_factor || 0).toFixed(2);
  $('profitFactor').className = 'stat-value ' + ((stats.profit_factor || 0) >= 1.5 ? 'green' : 'yellow');
  $('avgWin').textContent = fmt(stats.avg_win || 0);
  $('avgLoss').textContent = fmt(stats.avg_loss || 0);
  const totalPnl = stats.total_pnl || 0;
  $('totalPnl').textContent = (totalPnl >= 0 ? '+' : '') + fmt(totalPnl);
  $('totalPnl').className = 'stat-value ' + (totalPnl >= 0 ? 'green' : 'red');
}

async function pollStatus() {
  try {
    const res = await fetch('status.json?t=' + Date.now());
    if (res.ok) {
      const data = await res.json();
      updateUI(data);
    }
  } catch (e) {
    // Bot offline
    $('botStatus').className = 'status-badge offline';
    $('botStatus').textContent = '● Offline';
  }
}

setInterval(pollStatus, POLL_INTERVAL);
pollStatus();
