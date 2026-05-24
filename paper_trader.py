import json
import os
from datetime import datetime

# ============================================================
# PAPER TRADER - UPGRADED WITH PARTIAL PROFIT TAKING
# ============================================================

PAPER_TRADE_FILE = "paper_trades.json"
STARTING_BALANCE = 1000.00
MAX_POSITION_SIZE = 50.00
MIN_RISK_SCORE = 45

# Profit taking levels
PROFIT_LEVELS = [
    (1.5, 0.25),   # At 1.5x: sell 25% — secure early profit
    (2.0, 0.25),   # At 2x: sell 25% of remaining — lock more profit
    (5.0, 0.35),   # At 5x: sell 35% of remaining — let winners run
    (10.0, 0.50),  # At 10x: sell 50% of remaining — massive win
]

STOP_LOSS_PCT = 0.30
TRAILING_STOP_PCT = 0.40


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
        "daily_trades": 0,
        "last_trade_date": None,
    }


def save_trades(data):
    with open(PAPER_TRADE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def open_paper_trade(name, symbol, address, entry_price, risk_score, dex_url, max_position_size=None, mcap=None):
    state = load_trades()

    existing = [p for p in state["open_positions"] if p["address"] == address]
    if existing:
        return False, "Already have open position in this token"

    if state["balance"] < MAX_POSITION_SIZE:
        return False, "Insufficient paper balance"

    # Check daily trade limit
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if state.get("last_trade_date") != today:
        state["daily_trades"] = 0
        state["last_trade_date"] = today

    from config import get_strategy
    strategy = get_strategy()
    daily_limit = strategy.get("daily_trade_limit", 5)

    if state["daily_trades"] >= daily_limit:
        return False, f"Daily trade limit reached ({daily_limit} trades)"

    if not entry_price or float(entry_price) <= 0:
        return False, "Invalid entry price"

    price = float(entry_price)
    amount_usd = max_position_size if max_position_size else MAX_POSITION_SIZE
    tokens_bought = amount_usd / price

    position = {
        "name": name,
        "symbol": symbol,
        "address": address,
        "entry_price": price,
        "entry_mcap": mcap or 0,
        "tokens_bought": tokens_bought,
        "tokens_remaining": tokens_bought,
        "amount_invested_usd": amount_usd,
        "amount_remaining_usd": amount_usd,
        "realized_profit": 0.0,
        "risk_score": risk_score,
        "dex_url": dex_url,
        "opened_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "stop_loss_price": price * (1 - STOP_LOSS_PCT),
        "highest_price_seen": price,
        "trailing_stop_price": price * (1 - STOP_LOSS_PCT),
        "profit_levels_hit": [],
        "partial_exits": [],
        "status": "open",
    }

    state["balance"] -= amount_usd
    state["total_invested"] += amount_usd
    state["open_positions"].append(position)
    state["trade_count"] += 1
    state["daily_trades"] = state.get("daily_trades", 0) + 1
    state["last_trade_date"] = datetime.utcnow().strftime("%Y-%m-%d")
    save_trades(state)

    return True, position


def update_positions(current_prices: dict):
    state = load_trades()
    still_open = []
    closed_this_update = []
    partial_exits_this_update = []

    for position in state["open_positions"]:
        address = position["address"]
        current_price = current_prices.get(address)

        if current_price is None:
            still_open.append(position)
            continue

        current_price = float(current_price)

        if current_price > position["highest_price_seen"]:
            position["highest_price_seen"] = current_price
            # Only activate trailing stop after 1.5x gain
            # Before that use fixed stop loss only
            if current_price >= position["entry_price"] * 1.5:
                new_trailing = current_price * (1 - TRAILING_STOP_PCT)
                if new_trailing > position["trailing_stop_price"]:
                    position["trailing_stop_price"] = new_trailing

        multiplier = current_price / position["entry_price"]
        tokens_remaining = position["tokens_remaining"]
        for (target_multiplier, sell_fraction) in PROFIT_LEVELS:
            level_key = f"{target_multiplier}x"
            if multiplier >= target_multiplier and level_key not in position["profit_levels_hit"]:
                tokens_to_sell = tokens_remaining * sell_fraction
                sell_value = tokens_to_sell * current_price
                cost_basis = tokens_to_sell * position["entry_price"]
                partial_profit = sell_value - cost_basis

                position["tokens_remaining"] -= tokens_to_sell
                position["realized_profit"] += partial_profit
                position["profit_levels_hit"].append(level_key)
                state["balance"] += sell_value
                state["total_profit_loss"] += partial_profit

                exit_record = {
                    "level": level_key,
                    "price": current_price,
                    "tokens_sold": tokens_to_sell,
                    "value_usd": sell_value,
                    "profit_usd": partial_profit,
                    "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                }
                position["partial_exits"].append(exit_record)

                partial_exits_this_update.append({
                    "name": position["name"],
                    "symbol": position["symbol"],
                    "level": level_key,
                    "profit_usd": partial_profit,
                    "sell_value": sell_value,
                })

                print(f"[PARTIAL EXIT] {position['name']} hit {level_key} - "
                      f"Sold {sell_fraction*100:.0f}% | "
                      f"Profit: +${partial_profit:.2f}")

                tokens_remaining = position["tokens_remaining"]

        effective_stop = max(position["stop_loss_price"], position["trailing_stop_price"])

        # Emergency exit if token drops more than 40% from entry in one check
        emergency_exit = current_price <= position["entry_price"] * 0.60

        if current_price <= effective_stop or emergency_exit:
            remaining_value = position["tokens_remaining"] * current_price
            remaining_cost = position["tokens_remaining"] * position["entry_price"]
            remaining_pnl = remaining_value - remaining_cost
            total_pnl = position["realized_profit"] + remaining_pnl
            total_pnl_pct = (total_pnl / position["amount_invested_usd"]) * 100

            # Determine correct exit reason
            if total_pnl >= 0:
                exit_reason = "TAKE PROFIT"
            elif emergency_exit and current_price > position["stop_loss_price"]:
                exit_reason = "EMERGENCY EXIT"
            else:
                exit_reason = "STOP LOSS"

            position["exit_price"] = current_price
            position["exit_reason"] = exit_reason
            position["exit_mcap"] = current_price * position["tokens_bought"]
            position["profit_loss_usd"] = total_pnl
            position["profit_loss_pct"] = total_pnl_pct
            position["closed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            position["status"] = "closed"

            state["balance"] += remaining_value
            state["total_profit_loss"] += remaining_pnl

            if total_pnl >= 0:
                state["wins"] += 1
            else:
                state["losses"] += 1

            state["closed_positions"].append(position)
            closed_this_update.append(position)
            continue

        if position["tokens_remaining"] <= 0:
            total_pnl = position["realized_profit"]
            total_pnl_pct = (total_pnl / position["amount_invested_usd"]) * 100

            position["exit_price"] = current_price
            position["exit_reason"] = "TAKE PROFIT" if total_pnl >= 0 else "STOP LOSS"
            position["exit_mcap"] = current_price * position["tokens_bought"]
            position["profit_loss_usd"] = total_pnl
            position["profit_loss_pct"] = total_pnl_pct
            position["closed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            position["status"] = "closed"

            if total_pnl >= 0:
                state["wins"] += 1
            else:
                state["losses"] += 1

            state["closed_positions"].append(position)
            closed_this_update.append(position)
            continue

        still_open.append(position)

    state["open_positions"] = still_open
    save_trades(state)
    return closed_this_update, partial_exits_this_update


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
            levels_hit = ', '.join(pos.get('profit_levels_hit', [])) or 'None'
            print(f"   {pos['name']} ({pos['symbol']})")
            print(f"   Entry Price    : ${pos['entry_price']:.8f}")
            print(f"   Invested       : ${pos['amount_invested_usd']:,.2f}")
            print(f"   Realized P/L   : ${pos['realized_profit']:,.2f}")
            print(f"   Levels Hit     : {levels_hit}")
            print(f"   Trailing Stop  : ${pos['trailing_stop_price']:.8f}")
            print(f"   Opened At      : {pos['opened_at']}")
            print("-" * 60)
    else:
        print("\n   No open positions.")

    if state["closed_positions"]:
        print(f"\n   RECENT CLOSED TRADES:")
        print("-" * 60)
        for pos in state["closed_positions"][-5:]:
            result = "WIN" if pos["profit_loss_usd"] > 0 else "LOSS"
            print(f"   {pos['name']} ({pos['symbol']}) --- {result}")
            print(f"   Exit Reason    : {pos['exit_reason']}")
            print(f"   P/L            : ${pos['profit_loss_usd']:,.2f} ({pos['profit_loss_pct']:.1f}%)")
            print(f"   Closed At      : {pos['closed_at']}")
            print("-" * 60)