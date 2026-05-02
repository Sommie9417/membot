import json
import os
from datetime import datetime

# ============================================================
# LOGGER
# Saves every token the scanner finds to a local file
# ============================================================

LOG_FILE = "token_log.json"

def load_log():
    """Load existing log file or create empty one."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_log(data):
    """Save data to log file."""
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_token(token_data):
    """Add a single token entry to the log."""
    log = load_log()

    # Add timestamp to the entry
    token_data["logged_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Avoid duplicate entries by checking address
    address = token_data.get("address", "")
    existing_addresses = [t.get("address", "") for t in log]

    if address and address in existing_addresses:
        return False  # Already logged this token

    log.append(token_data)
    save_log(log)
    return True


def log_trending_pair(pair, risk_score):
    """Log a trending pair with its risk score."""
    entry = {
        "type": "trending_pair",
        "name": pair.get("baseToken", {}).get("name", "Unknown"),
        "symbol": pair.get("baseToken", {}).get("symbol", "?"),
        "address": pair.get("baseToken", {}).get("address", "N/A"),
        "price_usd": pair.get("priceUsd", "N/A"),
        "liquidity_usd": pair.get("liquidity", {}).get("usd", 0),
        "volume_5m": pair.get("volume", {}).get("m5", 0),
        "volume_24h": pair.get("volume", {}).get("h24", 0),
        "price_change_1h": pair.get("priceChange", {}).get("h1", 0),
        "price_change_24h": pair.get("priceChange", {}).get("h24", 0),
        "risk_score": risk_score,
        "dex_url": pair.get("url", "N/A"),
    }
    added = log_token(entry)
    return added


def log_new_token(token):
    """Log a newly discovered token."""
    entry = {
        "type": "new_token",
        "name": token.get("description", "Unknown"),
        "address": token.get("tokenAddress", "N/A"),
        "chain": token.get("chainId", "N/A"),
        "dex_url": token.get("url", "N/A"),
    }
    added = log_token(entry)
    return added


def print_log_summary():
    """Print a summary of everything logged so far."""
    log = load_log()
    if not log:
        print("No tokens logged yet.")
        return

    print(f"\nTotal tokens logged: {len(log)}")
    print(f"Log file: {LOG_FILE}")
    print("-" * 40)

    # Show last 5 entries
    recent = log[-5:]
    for entry in recent:
        print(f"  {entry.get('logged_at', 'N/A')} | "
              f"{entry.get('name', 'Unknown')} | "
              f"Risk: {entry.get('risk_score', 'N/A')}")