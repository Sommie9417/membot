from flask import Flask, jsonify, render_template_string, request
import json
import os
import threading
import schedule
import time

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

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEMBOT</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: #0a0a0a;
            color: #e0e0e0;
            font-family: 'Courier New', monospace;
            display: flex;
            min-height: 100vh;
        }

        /* SIDEBAR */
        .sidebar {
            width: 220px;
            background: #0f0f0f;
            border-right: 1px solid #1e1e1e;
            padding: 24px 0;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            z-index: 100;
        }

        .sidebar-logo {
            padding: 0 20px 24px;
            border-bottom: 1px solid #1e1e1e;
            margin-bottom: 16px;
        }

        .sidebar-logo h1 {
            color: #00ff88;
            font-size: 22px;
            letter-spacing: 3px;
        }

        .sidebar-logo p {
            color: #444;
            font-size: 10px;
            margin-top: 4px;
            letter-spacing: 1px;
        }

        .nav-item {
            display: flex;
            align-items: center;
            padding: 12px 20px;
            cursor: pointer;
            color: #666;
            font-size: 13px;
            letter-spacing: 1px;
            border-left: 3px solid transparent;
            transition: all 0.2s;
            text-transform: uppercase;
        }

        .nav-item:hover {
            color: #e0e0e0;
            background: #1a1a1a;
        }

        .nav-item.active {
            color: #00ff88;
            border-left: 3px solid #00ff88;
            background: #00ff8810;
        }

        .nav-icon {
            margin-right: 10px;
            font-size: 15px;
        }

        .sidebar-footer {
            position: absolute;
            bottom: 20px;
            left: 0;
            right: 0;
            padding: 0 20px;
            color: #333;
            font-size: 10px;
            text-align: center;
        }

        /* MAIN CONTENT */
        .main {
            margin-left: 220px;
            flex: 1;
            padding: 30px;
            min-height: 100vh;
        }

        .page {
            display: none;
        }

        .page.active {
            display: block;
        }

        .page-header {
            margin-bottom: 24px;
        }

        .page-header h2 {
            color: #00ff88;
            font-size: 20px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .page-header p {
            color: #444;
            font-size: 12px;
            margin-top: 4px;
        }

        /* CARDS */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 24px;
        }

        .card {
            background: #111;
            border: 1px solid #1e1e1e;
            border-radius: 8px;
            padding: 20px;
        }

        .card h3 {
            color: #444;
            font-size: 10px;
            letter-spacing: 1px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .card .value {
            font-size: 24px;
            font-weight: bold;
            color: #00ff88;
        }

        .card .value.red { color: #ff4444; }
        .card .value.yellow { color: #ffaa00; }
        .card .value.white { color: #ffffff; }

        /* TABLES */
        .section {
            background: #111;
            border: 1px solid #1e1e1e;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .section h3 {
            color: #00ff88;
            font-size: 12px;
            letter-spacing: 1px;
            margin-bottom: 16px;
            text-transform: uppercase;
            border-bottom: 1px solid #1e1e1e;
            padding-bottom: 10px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }

        th {
            color: #444;
            text-align: left;
            padding: 8px;
            font-size: 10px;
            letter-spacing: 1px;
            text-transform: uppercase;
            border-bottom: 1px solid #1e1e1e;
        }

        td {
            padding: 10px 8px;
            border-bottom: 1px solid #141414;
            color: #aaa;
        }

        tr:hover td { background: #161616; }

        /* BADGES */
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
        }

        .badge.green { background: #00ff8815; color: #00ff88; }
        .badge.yellow { background: #ffaa0015; color: #ffaa00; }
        .badge.red { background: #ff444415; color: #ff4444; }
        .badge.blue { background: #4488ff15; color: #4488ff; }

        .no-data {
            color: #333;
            text-align: center;
            padding: 30px;
            font-size: 12px;
        }

        .positive { color: #00ff88; }
        .negative { color: #ff4444; }

        /* REFRESH BAR */
        .refresh-bar {
            background: #111;
            border: 1px solid #1e1e1e;
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: #444;
        }

        .refresh-bar span { color: #00ff88; }

        a { color: #00ff88; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>

<!-- SIDEBAR -->
<div class="sidebar">
    <div class="sidebar-logo">
        <h1>MEMBOT</h1>
        <p>SOLANA TRADING BOT</p>
    </div>

    <div class="nav-item active" onclick="showPage('overview', this)">
        <span class="nav-icon">▣</span> Overview
    </div>
    <div class="nav-item" onclick="showPage('positions', this)">
        <span class="nav-icon">◎</span> Open Positions
    </div>
    <div class="nav-item" onclick="showPage('history', this)">
        <span class="nav-icon">◈</span> Trade History
    </div>
    <div class="nav-item" onclick="showPage('tokens', this)">
        <span class="nav-icon">◆</span> Token Log
    </div>

    <div class="sidebar-footer">
        Auto-refreshes every 60s
    </div>
</div>

<!-- MAIN CONTENT -->
<div class="main">

    <!-- REFRESH BAR -->
    <div class="refresh-bar">
        <div>Last updated: <span id="timestamp">Loading...</span></div>
        <div>Scanning every <span>60 seconds</span></div>
    </div>

    <!-- PAGE: OVERVIEW -->
    <div class="page active" id="page-overview">
        <div class="page-header">
            <h2>Overview</h2>
            <p>Your bot's performance at a glance</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Current Balance</h3>
                <div class="value {{ 'green' if balance >= 1000 else 'red' }}">
                    ${{ "%.2f"|format(balance) }}
                </div>
            </div>
            <div class="card">
                <h3>Total P/L</h3>
                <div class="value {{ 'green' if pnl >= 0 else 'red' }}">
                    {{ '+' if pnl >= 0 else '' }}${{ "%.2f"|format(pnl) }}
                </div>
            </div>
            <div class="card">
                <h3>Win Rate</h3>
                <div class="value {{ 'green' if win_rate >= 50 else 'red' }}">
                    {{ "%.1f"|format(win_rate) }}%
                </div>
            </div>
            <div class="card">
                <h3>Total Trades</h3>
                <div class="value white">{{ trade_count }}</div>
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

        <!-- Recent Activity -->
        <div class="section">
            <h3>Recent Activity</h3>
            {% if recent_tokens %}
            <table>
                <tr>
                    <th>Token</th>
                    <th>Type</th>
                    <th>Risk</th>
                    <th>Logged</th>
                    <th>Link</th>
                </tr>
                {% for token in recent_tokens[:8] %}
                <tr>
                    <td><strong>{{ token.name[:35] if token.name else 'Unknown' }}</strong></td>
                    <td><span class="badge blue">{{ token.type }}</span></td>
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
                    <td><a href="{{ token.dex_url }}" target="_blank">View</a></td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="no-data">No activity yet.</div>
            {% endif %}
        </div>
    </div>

    <!-- PAGE: OPEN POSITIONS -->
    <div class="page" id="page-positions">
        <div class="page-header">
            <h2>Open Positions</h2>
            <p>Currently active paper trades</p>
        </div>

        <div class="section">
            <h3>Active Trades ({{ open_count }})</h3>
            {% if open_positions %}
            <table>
                <tr>
                    <th>Token</th>
                    <th>Entry Price</th>
                    <th>Current Price</th>
                    <th>Change</th>
                    <th>Current Value</th>
                    <th>Invested</th>
                    <th>Stop Loss</th>
                    <th>Take Profit</th>
                    <th>Risk Score</th>
                    <th>Opened</th>
                    <th>Link</th>
                </tr>
                {% for pos in open_positions %}
                <tr>
                    <td><strong>{{ pos.name }}</strong><br>
                        <span style="color:#444">{{ pos.symbol }}</span>
                    </td>
                    <td>${{ "%.8f"|format(pos.entry_price) }}</td>
                    <td id="price-{{ pos.address }}" style="color:#444">Loading...</td>
                    <td id="change-{{ pos.address }}" style="color:#444">...</td>
                    <td id="value-{{ pos.address }}" style="color:#444">...</td>
                    <td>${{ "%.2f"|format(pos.amount_invested_usd) }}</td>
                    <td class="negative">${{ "%.8f"|format(pos.stop_loss_price) }}</td>
                    <td class="positive">${{ "%.8f"|format(pos.take_profit_price) }}</td>
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
                    <td><a href="{{ pos.dex_url }}" target="_blank">View</a></td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="no-data">No open positions. Bot will open trades automatically when it finds good tokens.</div>
            {% endif %}
        </div>
    </div>

    <!-- PAGE: TRADE HISTORY -->
    <div class="page" id="page-history">
        <div class="page-header">
            <h2>Trade History</h2>
            <p>All closed trades and their results</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Total Closed</h3>
                <div class="value white">{{ trade_count }}</div>
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
                <h3>Total P/L</h3>
                <div class="value {{ 'green' if pnl >= 0 else 'red' }}">
                    {{ '+' if pnl >= 0 else '' }}${{ "%.2f"|format(pnl) }}
                </div>
            </div>
        </div>

        <div class="section">
            <h3>Closed Trades</h3>
            {% if closed_positions %}
            <table>
                <tr>
                    <th>Token</th>
                    <th>Exit Reason</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>P/L (USD)</th>
                    <th>P/L (%)</th>
                    <th>Closed</th>
                </tr>
                {% for pos in closed_positions|reverse %}
                <tr>
                    <td><strong>{{ pos.name }}</strong><br>
                        <span style="color:#444">{{ pos.symbol }}</span>
                    </td>
                    <td>
                        {% if pos.exit_reason == 'TAKE PROFIT' %}
                            <span class="badge green">TAKE PROFIT</span>
                        {% else %}
                            <span class="badge red">STOP LOSS</span>
                        {% endif %}
                    </td>
                    <td>${{ "%.8f"|format(pos.entry_price) }}</td>
                    <td>${{ "%.8f"|format(pos.exit_price) }}</td>
                    <td class="{{ 'positive' if pos.profit_loss_usd >= 0 else 'negative' }}">
                        {{ '+' if pos.profit_loss_usd >= 0 else '' }}${{ "%.2f"|format(pos.profit_loss_usd) }}
                    </td>
                    <td class="{{ 'positive' if pos.profit_loss_pct >= 0 else 'negative' }}">
                        {{ '+' if pos.profit_loss_pct >= 0 else '' }}{{ "%.1f"|format(pos.profit_loss_pct) }}%
                    </td>
                    <td>{{ pos.closed_at }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="no-data">No closed trades yet. Positions close automatically when they hit take profit (+100%) or stop loss (-35%).</div>
            {% endif %}
        </div>
    </div>

    <!-- PAGE: TOKEN LOG -->
    <div class="page" id="page-tokens">
        <div class="page-header">
            <h2>Token Log</h2>
            <p>Every token the scanner has discovered</p>
        </div>

        <div class="section">
            <h3>All Logged Tokens ({{ token_count }})</h3>
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
                    <td><span class="badge blue">{{ token.type }}</span></td>
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
                    <td>
                        {% if token.dex_url and token.dex_url != 'N/A' %}
                            <a href="{{ token.dex_url }}" target="_blank">View</a>
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="no-data">No tokens logged yet.</div>
            {% endif %}
        </div>
    </div>

</div>

<script>
    /// Page navigation
    function showPage(pageId, navItem) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById('page-' + pageId).classList.add('active');
        navItem.classList.add('active');
    }

    // Show current timestamp
    function updateTimestamp() {
        const now = new Date();
        document.getElementById('timestamp').textContent = now.toLocaleTimeString();
    }
    updateTimestamp();

    // Fetch and display live prices
    function updateLivePrices() {
        fetch('/api/prices')
            .then(res => res.json())
            .then(prices => {
                const rows = document.querySelectorAll('[id^="price-"]');
                rows.forEach(el => {
                    const address = el.id.replace('price-', '');
                    const currentPrice = prices[address];
                    
                    if (currentPrice !== undefined) {
                        const row = el.closest('tr');
                        const entryPriceText = row.querySelector('td:nth-child(2)').textContent;
                        const entryPrice = parseFloat(entryPriceText.replace('$', ''));
                        const invested = parseFloat(row.querySelector('td:nth-child(6)').textContent.replace('$', '').replace(',', ''));

                        const changePct = ((currentPrice - entryPrice) / entryPrice) * 100;
                        const currentValue = (invested / entryPrice) * currentPrice;
                        const pnl = currentValue - invested;

                        el.textContent = '$' + currentPrice.toFixed(8);
                        el.style.color = '#e0e0e0';

                        const changeEl = document.getElementById('change-' + address);
                        if (changeEl) {
                            const sign = changePct >= 0 ? '+' : '';
                            changeEl.textContent = sign + changePct.toFixed(2) + '%';
                            changeEl.style.color = changePct >= 0 ? '#00ff88' : '#ff4444';
                        }

                        const valueEl = document.getElementById('value-' + address);
                        if (valueEl) {
                            const sign = pnl >= 0 ? '+' : '';
                            valueEl.textContent = '$' + currentValue.toFixed(2) + ' (' + sign + '$' + pnl.toFixed(2) + ')';
                            valueEl.style.color = pnl >= 0 ? '#00ff88' : '#ff4444';
                        }
                    }
                });
            })
            .catch(err => console.log('Price fetch error:', err));
    }

    // Load prices immediately then every 30 seconds
    updateLivePrices();
    setInterval(updateLivePrices, 30000);

    // Auto refresh page every 60 seconds
    setTimeout(() => location.reload(), 60000);
</script>

</body>
</html>
"""

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
    recent_tokens = log[::-1] if log else []

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

@app.route("/api/prices")
def api_prices():
    """Fetch live prices for all open positions."""
    import requests as req
    trades = load_trades()
    open_positions = trades.get("open_positions", [])
    
    prices = {}
    for position in open_positions:
        address = position.get("address", "")
        if not address:
            continue
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
            response = req.get(url, timeout=10)
            data = response.json()
            pairs = data.get("pairs", [])
            if pairs:
                pair = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0) or 0)
                price = pair.get("priceUsd")
                if price:
                    prices[address] = float(price)
        except Exception:
            continue
    
    return jsonify(prices)

def run_scheduler():
    try:
        from scanner import run_scan
        run_scan()
        schedule.every(60).seconds.do(run_scan)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        print(f"Scanner error: {e}")

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=run_scheduler, daemon=True)
    scanner_thread.start()
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting dashboard on port {port}")
    app.run(debug=False, host="0.0.0.0", port=port)