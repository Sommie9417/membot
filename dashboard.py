from flask import Flask, jsonify, render_template_string
import json
import os

# ============================================================
# DASHBOARD
# A simple web interface to view your bot's activity
# ============================================================

app = Flask(__name__)

def load_trades():
    if os.path.exists("paper_trades.json"):
        with open("paper_trades.json", "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def load_log():
    if os.path.exists("token_log.json"):
        with open("token_log.json", "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

# ============================================================
# HTML TEMPLATE
# This is the actual webpage your browser will show
# ============================================================

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEMBOT Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: #0a0a0a;
            color: #e0e0e0;
            font-family: 'Courier New', monospace;
            padding: 20px;
        }

        h1 {
            color: #00ff88;
            font-size: 28px;
            margin-bottom: 5px;
            letter-spacing: 2px;
        }

        .subtitle {
            color: #666;
            font-size: 13px;
            margin-bottom: 30px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .card {
            background: #111;
            border: 1px solid #222;
            border-radius: 8px;
            padding: 20px;
        }

        .card h3 {
            color: #666;
            font-size: 11px;
            letter-spacing: 1px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .card .value {
            font-size: 26px;
            font-weight: bold;
            color: #00ff88;
        }

        .card .value.red { color: #ff4444; }
        .card .value.yellow { color: #ffaa00; }
        .card .value.white { color: #ffffff; }

        .section {
            background: #111;
            border: 1px solid #222;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .section h2 {
            color: #00ff88;
            font-size: 14px;
            letter-spacing: 1px;
            margin-bottom: 15px;
            text-transform: uppercase;
            border-bottom: 1px solid #222;
            padding-bottom: 10px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th {
            color: #666;
            text-align: left;
            padding: 8px;
            font-size: 11px;
            letter-spacing: 1px;
            text-transform: uppercase;
            border-bottom: 1px solid #222;
        }

        td {
            padding: 10px 8px;
            border-bottom: 1px solid #1a1a1a;
            color: #ccc;
        }

        tr:hover td { background: #1a1a1a; }

        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }

        .badge.green { background: #00ff8820; color: #00ff88; }
        .badge.yellow { background: #ffaa0020; color: #ffaa00; }
        .badge.red { background: #ff444420; color: #ff4444; }

        .refresh {
            color: #666;
            font-size: 12px;
            margin-bottom: 20px;
        }

        .no-data {
            color: #444;
            text-align: center;
            padding: 20px;
            font-size: 13px;
        }
    </style>
    <script>
        // Auto refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);
    </script>
</head>
<body>

    <h1>MEMBOT</h1>
    <div class="subtitle">Solana Token Scanner & Paper Trading Dashboard</div>
    <div class="refresh">Auto-refreshes every 60 seconds</div>

    <!-- PORTFOLIO STATS -->
    <div class="grid">
        <div class="card">
            <h3>Current Balance</h3>
            <div class="value {{ 'green' if balance >= 1000 else 'red' }}">${{ "%.2f"|format(balance) }}</div>
        </div>
        <div class="card">
            <h3>Total P/L</h3>
            <div class="value {{ 'green' if pnl >= 0 else 'red' }}">
                {{ '+' if pnl >= 0 else '' }}${{ "%.2f"|format(pnl) }}
            </div>
        </div>
        <div class="card">
            <h3>Total Trades</h3>
            <div class="value white">{{ trade_count }}</div>
        </div>
        <div class="card">
            <h3>Win Rate</h3>
            <div class="value {{ 'green' if win_rate >= 50 else 'red' }}">{{ "%.1f"|format(win_rate) }}%</div>
        </div>
        <div class="card">
            <h3>Wins</h3>
            <div class="value green">{{ wins }}</div>
        </div>
        <div class="card">
            <h3>Losses</h3>
            <div class="value red">{{ losses }}</div>
        </div>
        <div class="card">
            <h3>Open Positions</h3>
            <div class="value yellow">{{ open_count }}</div>
        </div>
        <div class="card">
            <h3>Tokens Logged</h3>
            <div class="value white">{{ token_count }}</div>
        </div>
    </div>

    <!-- OPEN POSITIONS -->
    <div class="section">
        <h2>Open Positions</h2>
        {% if open_positions %}
        <table>
            <tr>
                <th>Token</th>
                <th>Entry Price</th>
                <th>Invested</th>
                <th>Stop Loss</th>
                <th>Take Profit</th>
                <th>Risk Score</th>
                <th>Opened</th>
            </tr>
            {% for pos in open_positions %}
            <tr>
                <td><strong>{{ pos.name }}</strong> ({{ pos.symbol }})</td>
                <td>${{ "%.8f"|format(pos.entry_price) }}</td>
                <td>${{ "%.2f"|format(pos.amount_invested_usd) }}</td>
                <td>${{ "%.8f"|format(pos.stop_loss_price) }}</td>
                <td>${{ "%.8f"|format(pos.take_profit_price) }}</td>
                <td>
                    {% if pos.risk_score >= 70 %}
                        <span class="badge green">{{ pos.risk_score }}/100</span>
                    {% elif pos.risk_score >= 45 %}
                        <span class="badge yellow">{{ pos.risk_score }}/100</span>
                    {% else %}
                        <span class="badge red">{{ pos.risk_score }}/100</span>
                    {% endif %}
                </td>
                <td>{{ pos.opened_at }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="no-data">No open positions yet.</div>
        {% endif %}
    </div>

    <!-- CLOSED TRADES -->
    <div class="section">
        <h2>Recent Closed Trades</h2>
        {% if closed_positions %}
        <table>
            <tr>
                <th>Token</th>
                <th>Exit Reason</th>
                <th>P/L (USD)</th>
                <th>P/L (%)</th>
                <th>Closed</th>
            </tr>
            {% for pos in closed_positions[-10:]|reverse %}
            <tr>
                <td><strong>{{ pos.name }}</strong> ({{ pos.symbol }})</td>
                <td>
                    {% if pos.exit_reason == 'TAKE PROFIT' %}
                        <span class="badge green">TAKE PROFIT</span>
                    {% else %}
                        <span class="badge red">STOP LOSS</span>
                    {% endif %}
                </td>
                <td class="{{ 'green' if pos.profit_loss_usd >= 0 else 'red' }}">
                    {{ '+' if pos.profit_loss_usd >= 0 else '' }}${{ "%.2f"|format(pos.profit_loss_usd) }}
                </td>
                <td class="{{ 'green' if pos.profit_loss_pct >= 0 else 'red' }}">
                    {{ '+' if pos.profit_loss_pct >= 0 else '' }}{{ "%.1f"|format(pos.profit_loss_pct) }}%
                </td>
                <td>{{ pos.closed_at }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="no-data">No closed trades yet. Positions close when they hit take profit or stop loss.</div>
        {% endif %}
    </div>

    <!-- RECENT TOKENS LOGGED -->
    <div class="section">
        <h2>Recently Logged Tokens</h2>
        {% if recent_tokens %}
        <table>
            <tr>
                <th>Token</th>
                <th>Type</th>
                <th>Risk Score</th>
                <th>Logged At</th>
                <th>Link</th>
            </tr>
            {% for token in recent_tokens %}
            <tr>
                <td><strong>{{ token.name[:40] if token.name else 'Unknown' }}</strong></td>
                <td><span class="badge yellow">{{ token.type }}</span></td>
                <td>
                    {% if token.risk_score and token.risk_score != 'N/A' %}
                        {% if token.risk_score >= 70 %}
                            <span class="badge green">{{ token.risk_score }}/100</span>
                        {% elif token.risk_score >= 45 %}
                            <span class="badge yellow">{{ token.risk_score }}/100</span>
                        {% else %}
                            <span class="badge red">{{ token.risk_score }}/100</span>
                        {% endif %}
                    {% else %}
                        <span class="badge red">N/A</span>
                    {% endif %}
                </td>
                <td>{{ token.logged_at }}</td>
                <td><a href="{{ token.dex_url }}" target="_blank" style="color: #00ff88;">View</a></td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="no-data">No tokens logged yet.</div>
        {% endif %}
    </div>

</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    trades = load_trades()
    log = load_log()

    balance = trades.get("balance", 1000.0)
    pnl = trades.get("total_profit_loss", 0.0)
    trade_count = trades.get("trade_count", 0)
    wins = trades.get("wins", 0)
    losses = trades.get("losses", 0)
    open_positions = trades.get("open_positions", [])
    closed_positions = trades.get("closed_positions", [])
    win_rate = (wins / trade_count * 100) if trade_count > 0 else 0.0
    recent_tokens = log[-20:][::-1] if log else []

    return render_template_string(
        HTML,
        balance=balance,
        pnl=pnl,
        trade_count=trade_count,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        open_positions=open_positions,
        closed_positions=closed_positions,
        open_count=len(open_positions),
        token_count=len(log),
        recent_tokens=recent_tokens,
    )

@app.route("/api/stats")
def api_stats():
    trades = load_trades()
    log = load_log()
    return jsonify({
        "trades": trades,
        "token_count": len(log),
    })

# ============================================================
# RUN
# ============================================================

import threading
from scanner import run_scan
import schedule
import time

def run_scheduler():
    run_scan()
    schedule.every(60).seconds.do(run_scan)
    while True:
        schedule.run_pending()
        time.sleep(1)

import os

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=run_scheduler, daemon=True)
    scanner_thread.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)