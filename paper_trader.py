import json
import os
from datetime import datetime

# ============================================================
# PAPER TRADER
# Simulates buying and selling tokens with fake money
# Tracks performance so we know if the strategy works
# before risking a single real dollar
# ============================================================

PAPER_TRADE_FILE = "paper_trades.json"
STARTING_BALANCE = 1000.00  # Fake starting balance in USD
MAX_POSITION_SIZE = 50.00   # Max fake dollars per trade
MIN_RISK_SCORE = 45         # Only paper buy if risk score is this or higher

# ============================================================
# LOAD / SAVE
# ============================================================

def load_trades():
    if os.path.exists(PAPER_TRADE_FILE):
        with open(PAPER_TRADE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return get_fresh_state()
    return get_fresh_state()


def get_fresh_state():
    return {
        "balance": STARTING_BALANCE,
        "total_invested": 0.0,
        "open_positions": [],
        "closed_positions": [],
        "trade_count": 0,
        "wins": 0,
        "losses": 0,
        "total_profit_loss": 0.0,
    }


def save_trades(data):
    with open(PAPER_TRADE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ============================================================
# OPEN A PAPER TRADE
# Called when scanner finds a token that passes risk filter
# ============================================================

def open_paper_trade(name, symbol, address, entry_price, risk_score, dex_url):
    state = load_trades()

    # Check if we already have a position in this token
    existing = [p for p in state["open_positions"] if p["address"] == address]
    if existing:
        return False, "Already have open position in this token"

    # Check we have enough fake balance
    if state["balance"] < MAX_POSITION_SIZE:
        return False, "Insufficient paper balance"

    # Calculate how many tokens we are paper buying
    if not entry_price or float(entry_price) <= 0:
        return False, "Invalid entry price"

    price = float(entry_price)
    amount_usd = MAX_POSITION_SIZE
    tokens_bought = amount_usd / price

    # Create the position
    position = {
        "name": name,
        "symbol": symbol,
        "address": address,
        "entry_price": price,
        "tokens_bought": tokens_bought,
        "amount_invested_usd": amount_usd,
        "risk_score": risk_score,
        "dex_url": dex_url,
        "opened_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "stop_loss_price": price * 0.65,    # Auto stop loss at -35%
        "take_profit_price": price * 2.0,   # Auto take profit at 2x
        "highest_price_seen": price,
        "status": "open",
    }

    # Deduct from balance
    state["balance"] -= amount_usd
    state["total_invested"] += amount_usd
    state["open_positions"].append(position)
    state["trade_count"] += 1
    save_trades(state)

    return True, position


# ============================================================
# UPDATE POSITIONS
# Called every scan to check if any open positions
# have hit their take profit or stop loss
# ============================================================

def update_positions(current_prices: dict):
    """
    current_prices: dict of { address: current_price_usd }
    """
    state = load_trades()
    still_open = []
    closed_this_update = []

    for position in state["open_positions"]:
        address = position["address"]
        current_price = current_prices.get(address)

        if current_price is None:
            # We don't have a current price for this token yet
            still_open.append(position)
            continue

        current_price = float(current_price)

        # Update highest price seen (for trailing stop later)
        if current_price > position["highest_price_seen"]:
            position["highest_price_seen"] = current_price

        # Calculate current value
        current_value = position["tokens_bought"] * current_price
        profit_loss = current_value - position["amount_invested_usd"]
        profit_loss_pct = (profit_loss / position["amount_invested_usd"]) * 100

        # Check stop loss
        if current_price <= position["stop_loss_price"]:
            position["exit_price"] = current_price
            position["exit_reason"] = "STOP LOSS"
            position["profit_loss_usd"] = profit_loss
            position["profit_loss_pct"] = profit_loss_pct
            position["closed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            position["status"] = "closed"
            state["balance"] += current_value
            state["total_profit_loss"] += profit_loss
            state["losses"] += 1
            state["closed_positions"].append(position)
            closed_this_update.append(position)
            continue

        # Check take profit
        if current_price >= position["take_profit_price"]:
            position["exit_price"] = current_price
            position["exit_reason"] = "TAKE PROFIT"
            position["profit_loss_usd"] = profit_loss
            position["profit_loss_pct"] = profit_loss_pct
            position["closed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            position["status"] = "closed"
            state["balance"] += current_value
            state["total_profit_loss"] += profit_loss
            state["wins"] += 1
            state["closed_positions"].append(position)
            closed_this_update.append(position)
            continue

        still_open.append(position)

    state["open_positions"] = still_open
    save_trades(state)
    return closed_this_update


# ============================================================
# PRINT PORTFOLIO SUMMARY
# Shows current state of all paper trades
# ============================================================

def print_portfolio():
    state = load_trades()

    print("\n" + "=" * 60)
    print("   PAPER TRADING PORTFOLIO")
    print("=" * 60)
    print(f"   Starting Balance  : $1,000.00")
    print(f"   Current Balance   : ${state['balance']:,.2f}")
    print(f"   Total P/L         : ${state['total_profit_loss']:,.2f}")
    print(f"   Total Trades      : {state['trade_count']}")
    print(f"   Wins              : {state['wins']}")
    print(f"   Losses            : {state['losses']}")

    if state['trade_count'] > 0:
        win_rate = (state['wins'] / state['trade_count']) * 100
        print(f"   Win Rate          : {win_rate:.1f}%")

    print("=" * 60)

    if state["open_positions"]:
        print(f"\n   OPEN POSITIONS ({len(state['open_positions'])}):")
        print("-" * 60)
        for pos in state["open_positions"]:
            print(f"   {pos['name']} ({pos['symbol']})")
            print(f"   Entry Price  : ${pos['entry_price']:.8f}")
            print(f"   Invested     : ${pos['amount_invested_usd']:,.2f}")
            print(f"   Stop Loss    : ${pos['stop_loss_price']:.8f}")
            print(f"   Take Profit  : ${pos['take_profit_price']:.8f}")
            print(f"   Opened At    : {pos['opened_at']}")
            print("-" * 60)
    else:
        print("\n   No open positions.")

    if state["closed_positions"]:
        print(f"\n   RECENT CLOSED TRADES:")
        print("-" * 60)
        for pos in state["closed_positions"][-5:]:
            result = "WIN" if pos["profit_loss_usd"] > 0 else "LOSS"
            print(f"   {pos['name']} ({pos['symbol']}) --- {result}")
            print(f"   Exit Reason  : {pos['exit_reason']}")
            print(f"   P/L          : ${pos['profit_loss_usd']:,.2f} ({pos['profit_loss_pct']:.1f}%)")
            print(f"   Closed At    : {pos['closed_at']}")
            print("-" * 60)