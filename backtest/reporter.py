"""
Backtest Reporter - Generates HTML report with charts and metrics.
"""
import json
from pathlib import Path
from config.settings import DATA_DIR


class BacktestReporter:
    """Generates an interactive HTML backtest report."""
    
    def generate(self, results: dict, output_path: str = None):
        """Generate HTML report from backtest results."""
        if not output_path:
            output_path = str(DATA_DIR / 'backtest_report.html')
        
        equity_data = []
        for point in results.get('equity_curve', []):
            equity_data.append({
                'x': str(point['timestamp']),
                'y': round(point['equity'], 2)
            })
        
        # Sample every Nth point for performance
        if len(equity_data) > 2000:
            step = len(equity_data) // 2000
            equity_data = equity_data[::step]
        
        trades_data = []
        for t in results.get('trades', []):
            trades_data.append({
                'id': t.id, 'symbol': t.symbol,
                'dir': t.direction, 'strategy': t.strategy,
                'entry': round(t.entry_price, 2),
                'exit': round(t.exit_price, 2),
                'pnl': round(t.pnl, 2),
                'pnl_pct': round(t.pnl_pct, 1),
                'reason': t.exit_reason,
                'entry_time': str(t.entry_time),
                'exit_time': str(t.exit_time),
            })
        
        r = results
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Backtest Report | $40 → $1,000 Challenge</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:#0a0e17;color:#e0e6ed;padding:20px}}
.header{{text-align:center;padding:30px;background:linear-gradient(135deg,#1a1f2e,#0d1321);border-radius:16px;margin-bottom:20px;border:1px solid #1e293b}}
.header h1{{font-size:28px;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.target{{font-size:18px;margin-top:10px;color:{'#4ade80' if r.get('target_reached') else '#f87171'}}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px}}
.card{{background:#111827;border-radius:12px;padding:16px;border:1px solid #1e293b}}
.card .label{{font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px}}
.card .value{{font-size:24px;font-weight:700;margin-top:4px}}
.green{{color:#4ade80}} .red{{color:#f87171}} .blue{{color:#60a5fa}} .yellow{{color:#fbbf24}}
.chart-container{{background:#111827;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #1e293b}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#1e293b;padding:8px 12px;text-align:left;font-weight:600;color:#94a3b8}}
td{{padding:6px 12px;border-bottom:1px solid #1e293b}}
tr:hover{{background:#1e293b44}}
.strat-bar{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.strat-item{{background:#1e293b;padding:10px 16px;border-radius:8px;font-size:13px}}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 Backtest Report</h1>
  <div class="target">{'🎯 TARGET $1,000 REACHED!' if r.get('target_reached') else '❌ Target $1,000 not reached'}</div>
  <p style="color:#64748b;margin-top:8px">${r['initial_capital']:.0f} → ${r['final_equity']:.2f} USDT | Return: {r['total_return']:.1f}%</p>
</div>

<div class="grid">
  <div class="card"><div class="label">Final Equity</div><div class="value green">${r['final_equity']:.2f}</div></div>
  <div class="card"><div class="label">Total Return</div><div class="value {'green' if r['total_return']>0 else 'red'}">{r['total_return']:.1f}%</div></div>
  <div class="card"><div class="label">Max Drawdown</div><div class="value red">{r['max_drawdown']:.1f}%</div></div>
  <div class="card"><div class="label">Total Trades</div><div class="value blue">{r['total_trades']}</div></div>
  <div class="card"><div class="label">Win Rate</div><div class="value {'green' if r['win_rate']>50 else 'yellow'}">{r['win_rate']:.1f}%</div></div>
  <div class="card"><div class="label">Profit Factor</div><div class="value {'green' if r['profit_factor']>1.5 else 'yellow'}">{r['profit_factor']:.2f}</div></div>
  <div class="card"><div class="label">Avg Win</div><div class="value green">${r['avg_win']:.2f}</div></div>
  <div class="card"><div class="label">Avg Loss</div><div class="value red">${r['avg_loss']:.2f}</div></div>
</div>

<div class="strat-bar">
{''.join(f'<div class="strat-item"><b>{name}</b>: {s["trades"]} trades | WR: {(s["wins"]/s["trades"]*100) if s["trades"]>0 else 0:.0f}% | P/L: <span class="{"green" if s["pnl"]>=0 else "red"}">${s["pnl"]:.2f}</span></div>' for name, s in r.get('strategy_breakdown', {}).items())}
</div>

<div class="chart-container">
  <h3 style="margin-bottom:12px">📈 Equity Curve</h3>
  <canvas id="equityChart" height="100"></canvas>
</div>

<div class="chart-container">
  <h3 style="margin-bottom:12px">📋 Trade Log (Last 200)</h3>
  <div style="overflow-x:auto;max-height:500px;overflow-y:auto">
  <table>
    <tr><th>#</th><th>Symbol</th><th>Dir</th><th>Strategy</th><th>Entry</th><th>Exit</th><th>P/L</th><th>P/L%</th><th>Reason</th></tr>
    {''.join(f'<tr><td>{t["id"]}</td><td>{t["symbol"]}</td><td>{"🟢" if t["dir"]=="LONG" else "🔴"} {t["dir"]}</td><td>{t["strategy"][:15]}</td><td>${t["entry"]:,.2f}</td><td>${t["exit"]:,.2f}</td><td class="{"green" if t["pnl"]>=0 else "red"}">${t["pnl"]:.2f}</td><td class="{"green" if t["pnl_pct"]>=0 else "red"}">{t["pnl_pct"]:.1f}%</td><td>{t["reason"]}</td></tr>' for t in trades_data[-200:])}
  </table>
  </div>
</div>

<script>
const ctx = document.getElementById('equityChart').getContext('2d');
const data = {json.dumps(equity_data)};
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: data.map(d => d.x.substring(0,10)),
    datasets: [{{
      label: 'Equity (USDT)',
      data: data.map(d => d.y),
      borderColor: '#60a5fa',
      backgroundColor: 'rgba(96,165,250,0.1)',
      fill: true, tension: 0.1, pointRadius: 0, borderWidth: 2
    }}, {{
      label: 'Target ($1,000)',
      data: data.map(() => 1000),
      borderColor: '#4ade8044', borderDash: [5,5],
      pointRadius: 0, borderWidth: 1, fill: false
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{legend: {{labels: {{color: '#94a3b8'}}}}}},
    scales: {{
      x: {{display: true, ticks: {{color:'#64748b',maxTicksLimit:12}}, grid: {{color:'#1e293b'}}}},
      y: {{ticks: {{color:'#94a3b8'}}, grid: {{color:'#1e293b'}}}}
    }}
  }}
}});
</script>
</body></html>"""
        
        Path(output_path).write_text(html, encoding='utf-8')
        print(f"\n📄 Report saved: {output_path}")
        return output_path
