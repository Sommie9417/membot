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
                data = json.load(f)
                for pos in data.get("open_positions", []):
                    if "take_profit_price" not in pos:
                        pos["take_profit_price"] = pos.get("entry_price", 0) * 2.0
                    if "tokens_remaining" not in pos:
                        pos["tokens_remaining"] = pos.get("tokens_bought", 0)
                    if "realized_profit" not in pos:
                        pos["realized_profit"] = 0.0
                    if "profit_levels_hit" not in pos:
                        pos["profit_levels_hit"] = []
                    if "partial_exits" not in pos:
                        pos["partial_exits"] = []
                    if "trailing_stop_price" not in pos:
                        pos["trailing_stop_price"] = pos.get("stop_loss_price", 0)
                return data
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
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEMBOT</title>
    <style>
        :root[data-theme="dark"] {
            --bg: #0a0a0a;
            --bg2: #111111;
            --bg3: #1a1a1a;
            --border: #1e1e1e;
            --text: #e0e0e0;
            --text2: #aaaaaa;
            --text3: #555555;
            --green: #00ff88;
            --red: #ff4444;
            --yellow: #ffaa00;
            --blue: #4488ff;
            --nav-bg: #0f0f0f;
            --card-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }

        :root[data-theme="light"] {
            --bg: #f4f4f4;
            --bg2: #ffffff;
            --bg3: #eeeeee;
            --border: #dddddd;
            --text: #111111;
            --text2: #444444;
            --text3: #999999;
            --green: #00aa55;
            --red: #dd2222;
            --yellow: #cc8800;
            --blue: #2255cc;
            --nav-bg: #ffffff;
            --card-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Courier New', monospace;
            min-height: 100vh;
            padding-bottom: 80px;
            transition: background 0.3s, color 0.3s;
        }

        /* TOP BAR */
        .topbar {
            background: var(--bg2);
            border-bottom: 1px solid var(--border);
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .topbar h1 {
            color: var(--green);
            font-size: 22px;
            letter-spacing: 3px;
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .topbar-sub {
            color: var(--text3);
            font-size: 10px;
            letter-spacing: 1px;
        }

        /* THEME TOGGLE */
        .theme-toggle {
            background: var(--bg3);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 8px 14px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
        }

        .theme-toggle:hover {
            border-color: var(--green);
            color: var(--green);
        }

        /* MAIN CONTENT */
        .main {
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }

        /* PAGES */
        .page { display: none; }
        .page.active { display: block; }

        .page-header {
            margin-bottom: 20px;
        }

        .page-header h2 {
            color: var(--green);
            font-size: 18px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .page-header p {
            color: var(--text3);
            font-size: 12px;
            margin-top: 4px;
        }

        /* CARDS */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }

        .card {
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            box-shadow: var(--card-shadow);
        }

        .card h3 {
            color: var(--text3);
            font-size: 10px;
            letter-spacing: 1px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .card .value {
            font-size: 22px;
            font-weight: bold;
            color: var(--green);
        }

        .card .value.red { color: var(--red); }
        .card .value.yellow { color: var(--yellow); }
        .card .value.white { color: var(--text); }

        /* SECTIONS */
        .section {
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: var(--card-shadow);
        }

        .section h3 {
            color: var(--green);
            font-size: 12px;
            letter-spacing: 1px;
            margin-bottom: 16px;
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }

        /* TABLES */
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            overflow-x: auto;
            display: block;
        }

        th {
            color: var(--text3);
            text-align: left;
            padding: 8px;
            font-size: 10px;
            letter-spacing: 1px;
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }

        td {
            padding: 10px 8px;
            border-bottom: 1px solid var(--bg3);
            color: var(--text2);
            white-space: nowrap;
        }

        tr:hover td { background: var(--bg3); }

        /* BADGES */
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
        }

        .badge.green { background: #00ff8815; color: var(--green); }
        .badge.yellow { background: #ffaa0015; color: var(--yellow); }
        .badge.red { background: #ff444415; color: var(--red); }
        .badge.blue { background: #4488ff15; color: var(--blue); }

        .positive { color: var(--green); }
        .negative { color: var(--red); }
        .no-data {
            color: var(--text3);
            text-align: center;
            padding: 30px;
            font-size: 12px;
        }

        a { color: var(--green); text-decoration: none; }
        a:hover { text-decoration: underline; }

        /* REFRESH BAR */
        .refresh-bar {
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--text3);
        }

        .refresh-bar span { color: var(--green); }

        /* STRATEGY CARDS */
        .strategy-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }

        .strategy-card {
            background: var(--bg3);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .strategy-card:hover { border-color: var(--text3); }

        .active-strategy {
            border-color: var(--green) !important;
            background: #00ff8808 !important;
        }

        /* BOTTOM NAV */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--nav-bg);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 10px 0 14px;
            z-index: 100;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
        }

        .nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            color: var(--text3);
            font-size: 10px;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 4px 12px;
            border-radius: 8px;
            transition: all 0.2s;
            min-width: 60px;
        }

        .nav-item:hover { color: var(--text); }

        .nav-item.active {
            color: var(--green);
        }

        .nav-icon {
            font-size: 20px;
            line-height: 1;
        }

        .nav-label {
            font-size: 9px;
            letter-spacing: 0.5px;
        }

        /* KILL SWITCH BUTTONS */
        .btn-danger {
            background: #ff444420;
            color: var(--red);
            border: 1px solid var(--red);
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            letter-spacing: 1px;
            transition: all 0.2s;
        }

        .btn-danger:hover { background: #ff444430; }

        .btn-success {
            background: #00ff8820;
            color: var(--green);
            border: 1px solid var(--green);
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            letter-spacing: 1px;
            transition: all 0.2s;
        }

        .btn-success:hover { background: #00ff8830; }
    </style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
    <div>
        <h1>MEMBOT</h1>
        <div class="topbar-sub">SOLANA TRADING BOT</div>
    </div>
    <div class="topbar-right">
        <div style="color: var(--text3); font-size:11px;" id="timestamp"></div>
        <button class="theme-toggle" onclick="toggleTheme()" id="theme-btn">🌙</button>
    </div>
</div>

<!-- MAIN CONTENT -->
<div class="main">

    <!-- REFRESH BAR -->
    <div class="refresh-bar">
        <div>Strategy: <span>{{ strategy_name|upper }}</span></div>
        <div>Auto-refreshes every <span>60s</span></div>
    </div>

    <!-- PAGE: OVERVIEW -->
    <div class="page active" id="page-overview">
        <div class="page-header">
            <h2>Overview</h2>
            <p>Your bot's performance at a glance</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Balance</h3>
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
                <h3>Trades</h3>
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
                <h3>Open</h3>
                <div class="value yellow">{{ open_count }}</div>
            </div>
            <div class="card">
                <h3>Logged</h3>
                <div class="value white">{{ token_count }}</div>
            </div>
        </div>

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
                    <td><strong>{{ token.name[:30] if token.name else 'Unknown' }}</strong></td>
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
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Change</th>
                    <th>Value</th>
                    <th>Invested</th>
                    <th>Stop Loss</th>
                    <th>Take Profit</th>
                    <th>Risk</th>
                    <th>Opened</th>
                    <th>Link</th>
                </tr>
                {% for pos in open_positions %}
                <tr>
                    <td><strong>{{ pos.name }}</strong><br>
                        <span style="color:var(--text3)">{{ pos.symbol }}</span>
                    </td>
                    <td>${{ "%.8f"|format(pos.entry_price) }}</td>
                    <td id="price-{{ pos.address }}" style="color:var(--text3)">Loading...</td>
                    <td id="change-{{ pos.address }}" style="color:var(--text3)">...</td>
                    <td id="value-{{ pos.address }}" style="color:var(--text3)">...</td>
                    <td>${{ "%.2f"|format(pos.amount_invested_usd) }}</td>
                    <td class="negative">${{ "%.8f"|format(pos.stop_loss_price) }}</td>
                    <td class="positive">${{ "%.8f"|format(pos.take_profit_price) }}</td>
                    <td>
                        {% if pos.risk_score >= 70 %}
                            <span class="badge green">{{ pos.risk_score }}</span>
                        {% elif pos.risk_score >= 45 %}
                            <span class="badge yellow">{{ pos.risk_score }}</span>
                        {% else %}
                            <span class="badge red">{{ pos.risk_score }}</span>
                        {% endif %}
                    </td>
                    <td>{{ pos.opened_at }}</td>
                    <td><a href="{{ pos.dex_url }}" target="_blank">View</a></td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="no-data">No open positions yet.</div>
            {% endif %}
        </div>
    </div>

    <!-- PAGE: TRADE HISTORY -->
    <div class="page" id="page-history">
        <div class="page-header">
            <h2>Trade History</h2>
            <p>All closed trades and results</p>
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
                    <th>Exit</th>
                    <th>Entry</th>
                    <th>Exit Price</th>
                    <th>P/L USD</th>
                    <th>P/L %</th>
                    <th>Closed</th>
                </tr>
                {% for pos in closed_positions|reverse %}
                <tr>
                    <td><strong>{{ pos.name }}</strong><br>
                        <span style="color:var(--text3)">{{ pos.symbol }}</span>
                    </td>
                    <td>
                        {% if pos.exit_reason == 'TAKE PROFIT' %}
                            <span class="badge green">TP</span>
                        {% elif pos.exit_reason == 'FULLY EXITED' %}
                            <span class="badge blue">FULL</span>
                        {% else %}
                            <span class="badge red">SL</span>
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
            <div class="no-data">No closed trades yet.</div>
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
                    <th>Risk</th>
                    <th>Logged</th>
                    <th>Link</th>
                </tr>
                {% for token in recent_tokens %}
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
                    <td>
                        {% if token.dex_url and token.dex_url != 'N/A' %}
                            <a href="{{ token.dex_url }}" target="_blank">View</a>
                        {% else %} - {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="no-data">No tokens logged yet.</div>
            {% endif %}
        </div>
    </div>

    <!-- PAGE: SETTINGS -->
    <div class="page" id="page-settings">
        <div class="page-header">
            <h2>Settings</h2>
            <p>Control your bot behaviour</p>
        </div>

        <div class="section">
            <h3>Strategy Mode</h3>
            <p style="color:var(--text3); font-size:12px; margin-bottom:16px;">
                Current: <span style="color:var(--green); font-weight:bold;">{{ strategy_name|upper }}</span>
            </p>
            <div class="strategy-grid">
                <div class="strategy-card {{ 'active-strategy' if strategy_name == 'conservative' }}"
                     onclick="setStrategy('conservative')">
                    <h4 style="color:var(--blue); margin-bottom:8px;">Conservative</h4>
                    <p style="color:var(--text3); font-size:11px; margin-bottom:12px;">Low risk, strict filters</p>
                    <div style="font-size:11px; color:var(--text2); line-height:1.8;">
                        <div>Position: $25</div>
                        <div>Min risk: 70/100</div>
                        <div>Min liquidity: $50,000</div>
                        <div>Stop loss: -20%</div>
                        <div>TP levels: 1.5x, 3x, 5x</div>
                    </div>
                </div>
                <div class="strategy-card {{ 'active-strategy' if strategy_name == 'balanced' }}"
                     onclick="setStrategy('balanced')">
                    <h4 style="color:var(--green); margin-bottom:8px;">Balanced</h4>
                    <p style="color:var(--text3); font-size:11px; margin-bottom:12px;">Medium risk, standard filters</p>
                    <div style="font-size:11px; color:var(--text2); line-height:1.8;">
                        <div>Position: $50</div>
                        <div>Min risk: 55/100</div>
                        <div>Min liquidity: $20,000</div>
                        <div>Stop loss: -35%</div>
                        <div>TP levels: 2x, 5x, 10x</div>
                    </div>
                </div>
                <div class="strategy-card {{ 'active-strategy' if strategy_name == 'aggressive' }}"
                     onclick="setStrategy('aggressive')">
                    <h4 style="color:var(--red); margin-bottom:8px;">Aggressive</h4>
                    <p style="color:var(--text3); font-size:11px; margin-bottom:12px;">Higher risk, loose filters</p>
                    <div style="font-size:11px; color:var(--text2); line-height:1.8;">
                        <div>Position: $100</div>
                        <div>Min risk: 35/100</div>
                        <div>Min liquidity: $5,000</div>
                        <div>Stop loss: -50%</div>
                        <div>TP levels: 2x, 5x, 10x, 20x</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <h3>Kill Switch</h3>
            <p style="color:var(--text3); font-size:12px; margin-bottom:16px;">
                Instantly stops all new trading activity.
            </p>
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <button class="btn-danger" onclick="setKillSwitch(true)">STOP ALL TRADING</button>
                <button class="btn-success" onclick="setKillSwitch(false)">RESUME TRADING</button>
            </div>
            <p id="kill-switch-status" style="margin-top:15px; font-size:12px; color:var(--text3);">
                Status: <strong>{{ 'STOPPED' if kill_switch_active else 'RUNNING' }}</strong>
            </p>
        </div>
    </div>

</div>

<!-- BOTTOM NAV -->
<div class="bottom-nav">
    <div class="nav-item active" onclick="showPage('overview', this)">
        <span class="nav-icon">▣</span>
        <span class="nav-label">Overview</span>
    </div>
    <div class="nav-item" onclick="showPage('positions', this)">
        <span class="nav-icon">◎</span>
        <span class="nav-label">Positions</span>
    </div>
    <div class="nav-item" onclick="showPage('history', this)">
        <span class="nav-icon">◈</span>
        <span class="nav-label">History</span>
    </div>
    <div class="nav-item" onclick="showPage('tokens', this)">
        <span class="nav-icon">◆</span>
        <span class="nav-label">Tokens</span>
    </div>
    <div class="nav-item" onclick="showPage('settings', this)">
        <span class="nav-icon">⚙</span>
        <span class="nav-label">Settings</span>
    </div>
</div>

<script>
    // Page navigation
    function showPage(pageId, navItem) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById('page-' + pageId).classList.add('active');
        navItem.classList.add('active');
        window.scrollTo(0, 0);
    }

    // Timestamp
    function updateTimestamp() {
        const now = new Date();
        document.getElementById('timestamp').textContent = now.toLocaleTimeString();
    }
    updateTimestamp();
    setInterval(updateTimestamp, 1000);

    // Theme toggle
    const html = document.documentElement;
    const btn = document.getElementById('theme-btn');
    const saved = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', saved);
    btn.textContent = saved === 'dark' ? '🌙' : '☀️';

    function toggleTheme() {
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        btn.textContent = next === 'dark' ? '🌙' : '☀️';
        localStorage.setItem('theme', next);
    }

    // Live prices
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
                        el.style.color = '';

                        const changeEl = document.getElementById('change-' + address);
                        if (changeEl) {
                            const sign = changePct >= 0 ? '+' : '';
                            changeEl.textContent = sign + changePct.toFixed(2) + '%';
                            changeEl.style.color = changePct >= 0 ? 'var(--green)' : 'var(--red)';
                        }

                        const valueEl = document.getElementById('value-' + address);
                        if (valueEl) {
                            const sign = pnl >= 0 ? '+' : '';
                            valueEl.textContent = '$' + currentValue.toFixed(2) + ' (' + sign + '$' + pnl.toFixed(2) + ')';
                            valueEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';
                        }
                    }
                });
            })
            .catch(err => console.log('Price error:', err));
    }

    updateLivePrices();
    setInterval(updateLivePrices, 30000);

    // Strategy switcher
    function setStrategy(strategy) {
        fetch('/api/set_strategy', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({strategy: strategy})
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('Strategy changed to ' + strategy);
                location.reload();
            }
        });
    }

    // Kill switch
    function setKillSwitch(active) {
        const action = active ? 'STOP all trading?' : 'RESUME trading?';
        if (!confirm('Are you sure you want to ' + action)) return;
        fetch('/api/kill_switch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({active: active})
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('kill-switch-status').innerHTML =
                'Status: <strong>' + (active ? 'STOPPED' : 'RUNNING') + '</strong>';
            alert(active ? 'Trading STOPPED.' : 'Trading RESUMED.');
        });
    }

    // Auto refresh
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

    from config import get_strategy_name, is_kill_switch_active
    strategy_name = get_strategy_name()
    kill_switch_active = is_kill_switch_active()

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
        strategy_name=strategy_name,
        kill_switch_active=kill_switch_active,
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


@app.route("/api/set_strategy", methods=["POST"])
def set_strategy_route():
    from config import set_strategy
    data = request.json
    strategy = data.get("strategy")
    success, message = set_strategy(strategy)
    return jsonify({"success": success, "message": message})


@app.route("/api/kill_switch", methods=["POST"])
def kill_switch_route():
    from config import set_kill_switch
    data = request.json
    active = data.get("active", False)
    set_kill_switch(active)
    return jsonify({"success": True, "active": active})


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