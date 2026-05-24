import json
import os

# ============================================================
# CONFIG MANAGER
# ============================================================

CONFIG_FILE = "config.json"

STRATEGIES = {
    "conservative": {
        "name": "Conservative",
        "description": "Low risk, strict filters",
        "max_position_size": 25.0,
        "min_risk_score": 75,
        "min_goplus_score": 80,
        "min_liquidity_usd": 50000,
        "min_volume_5m": 5000,
        "min_volume_h1": 20000,
        "max_fdv": 90_000,
        "min_fdv": 10_000,
        "min_buys_h1": 50,
        "max_sell_ratio": 0.45,
        "min_price_change_h1": -10,
        "max_price_change_h1": 80,
        "require_social": True,
        "require_name": True,
        "min_holder_threshold": 200,
        "stop_loss_pct": 0.20,
        "trailing_stop_pct": 0.15,
        "profit_levels": [
            (1.5, 0.30),
            (3.0, 0.50),
            (5.0, 0.75),
        ],
    },
    "balanced": {
    "name": "Balanced",
    "description": "Medium risk, balanced filters",
    "max_position_size": 50.0,
    "min_risk_score": 55,
    "min_goplus_score": 80,
    "min_liquidity_usd": 5000,
    "min_volume_5m": 500,
    "min_volume_h1": 2000,
    "max_fdv": 500_000,
    "min_fdv": 10_000,
    "min_buys_h1": 15,
    "max_sell_ratio": 0.60,
    "min_price_change_h1": -20,
    "max_price_change_h1": 200,
    "require_social": True,
    "require_name": True,
    "min_holder_threshold": 100,
    "daily_trade_limit": 5,
"min_buy_ratio": 0.65,
"min_age_minutes": 15,
"max_age_minutes": 180,
    "stop_loss_pct": 0.25,
    "trailing_stop_pct": 0.20,
    "profit_levels": [
        (2.0, 0.30),
        (5.0, 0.50),
        (10.0, 0.75),
    ],
},
    "aggressive": {
        "name": "Aggressive",
        "description": "Higher risk, loose filters",
        "max_position_size": 100.0,
        "min_risk_score": 45,
        "min_goplus_score": 50,
        "min_liquidity_usd": 10000,
        "min_volume_5m": 500,
        "min_volume_h1": 2000,
        "max_fdv": 90_000,
        "min_fdv": 10_000,
        "min_buys_h1": 10,
        "max_sell_ratio": 0.65,
        "min_price_change_h1": -30,
        "max_price_change_h1": 300,
        "require_social": False,
        "require_name": True,
        "min_holder_threshold": 50,
        "stop_loss_pct": 0.35,
        "trailing_stop_pct": 0.25,
        "profit_levels": [
            (2.0, 0.20),
            (5.0, 0.40),
            (10.0, 0.60),
            (20.0, 0.80),
        ],
    },
}

DEFAULT_STRATEGY = "balanced"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return get_default_config()
    return get_default_config()


def get_default_config():
    return {
        "strategy": DEFAULT_STRATEGY,
        "kill_switch": False,
        "updated_at": None,
    }


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_strategy():
    config = load_config()
    strategy_key = config.get("strategy", DEFAULT_STRATEGY)
    return STRATEGIES.get(strategy_key, STRATEGIES[DEFAULT_STRATEGY])


def get_strategy_name():
    config = load_config()
    return config.get("strategy", DEFAULT_STRATEGY)


def set_strategy(strategy_key):
    if strategy_key not in STRATEGIES:
        return False, f"Unknown strategy: {strategy_key}"
    config = load_config()
    config["strategy"] = strategy_key
    from datetime import datetime
    config["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    save_config(config)
    return True, f"Strategy changed to {STRATEGIES[strategy_key]['name']}"


def is_kill_switch_active():
    config = load_config()
    return config.get("kill_switch", False)


def set_kill_switch(active: bool):
    config = load_config()
    config["kill_switch"] = active
    save_config(config)