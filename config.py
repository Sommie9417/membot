import json
import os

# ============================================================
# CONFIG MANAGER
# Stores and loads bot settings like strategy mode
# ============================================================

CONFIG_FILE = "config.json"

# Strategy mode definitions
STRATEGIES = {
    "conservative": {
        "name": "Conservative",
        "description": "Low risk, smaller positions, strict filters",
        "max_position_size": 25.0,
        "min_risk_score": 70,
        "min_goplus_score": 80,
        "min_liquidity_usd": 50000,
        "min_volume_5m": 2000,
        "max_fdv": 5_000_000,
        "stop_loss_pct": 0.20,
        "profit_levels": [
            (1.5, 0.30),
            (3.0, 0.50),
            (5.0, 0.75),
        ],
    },
    "balanced": {
        "name": "Balanced",
        "description": "Medium risk, standard positions, balanced filters",
        "max_position_size": 50.0,
        "min_risk_score": 55,
        "min_goplus_score": 60,
        "min_liquidity_usd": 20000,
        "min_volume_5m": 1000,
        "max_fdv": 10_000_000,
        "stop_loss_pct": 0.35,
        "profit_levels": [
            (2.0, 0.30),
            (5.0, 0.50),
            (10.0, 0.75),
        ],
    },
    "aggressive": {
        "name": "Aggressive",
        "description": "Higher risk, larger positions, loose filters",
        "max_position_size": 100.0,
        "min_risk_score": 35,
        "min_goplus_score": 40,
        "min_liquidity_usd": 5000,
        "min_volume_5m": 500,
        "max_fdv": 20_000_000,
        "stop_loss_pct": 0.50,
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
    """Load config from file or return defaults."""
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
    """Get the current active strategy settings."""
    config = load_config()
    strategy_key = config.get("strategy", DEFAULT_STRATEGY)
    return STRATEGIES.get(strategy_key, STRATEGIES[DEFAULT_STRATEGY])


def get_strategy_name():
    """Get just the current strategy name."""
    config = load_config()
    return config.get("strategy", DEFAULT_STRATEGY)


def set_strategy(strategy_key):
    """Change the active strategy."""
    if strategy_key not in STRATEGIES:
        return False, f"Unknown strategy: {strategy_key}"
    config = load_config()
    config["strategy"] = strategy_key
    from datetime import datetime
    config["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    save_config(config)
    return True, f"Strategy changed to {STRATEGIES[strategy_key]['name']}"


def is_kill_switch_active():
    """Check if kill switch is on."""
    config = load_config()
    return config.get("kill_switch", False)


def set_kill_switch(active: bool):
    """Turn kill switch on or off."""
    config = load_config()
    config["kill_switch"] = active
    save_config(config)