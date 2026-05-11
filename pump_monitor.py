import requests
import time
from datetime import datetime, timezone
from colorama import Fore, init
from alerts import alert_pump_launch
init(autoreset=True)

# ============================================================
# PUMP.FUN MONITOR
# Watches for brand new token launches
# Catches tokens in first 10-30 minutes of launch
# ============================================================

PUMP_API = "https://frontend-api.pump.fun/coins"
SEEN_TOKENS = set()  # Track tokens we've already processed

def get_new_launches():
    """Fetch the latest token launches from Pump.fun"""
    try:
        params = {
            "offset": 0,
            "limit": 50,
            "sort": "created_timestamp",
            "order": "DESC",
            "includeNsfw": False,
        }
        response = requests.get(PUMP_API, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(Fore.RED + f"[PUMP] Error fetching launches: {e}")
        return []


def get_token_age_minutes(created_timestamp):
    """Calculate how many minutes ago a token was created."""
    try:
        now = datetime.now(timezone.utc).timestamp() * 1000
        age_ms = now - created_timestamp
        age_minutes = age_ms / (1000 * 60)
        return age_minutes
    except Exception:
        return 999


def check_pump_token_quality(token):
    """
    Check if a Pump.fun token meets our quality standards.
    Returns (passes, reasons)
    """
    reasons = []
    passes = True

    name = token.get("name", "")
    symbol = token.get("symbol", "")
    description = token.get("description", "")
    market_cap = token.get("usd_market_cap", 0) or 0
    reply_count = token.get("reply_count", 0) or 0
    has_twitter = bool(token.get("twitter"))
    has_telegram = bool(token.get("telegram"))
    has_website = bool(token.get("website"))
    created_timestamp = token.get("created_timestamp", 0)
    age_minutes = get_token_age_minutes(created_timestamp)

    # Must have a real name
    if not name or name.lower() == "unknown":
        passes = False
        reasons.append("No name")
        return passes, reasons

    # Must be between 5 and 60 minutes old
    # Too new = bundlers still active
    # Too old = already pumped
    if age_minutes < 5:
        passes = False
        reasons.append(f"Too new ({age_minutes:.1f} mins)")
    elif age_minutes > 60:
        passes = False
        reasons.append(f"Too old ({age_minutes:.1f} mins)")

    # Must have at least one social
    has_social = has_twitter or has_telegram or has_website
    if not has_social:
        passes = False
        reasons.append("No socials")

    # Market cap sweet spot
    if market_cap > 500_000:
        passes = False
        reasons.append(f"MCap too high ${market_cap:,.0f}")
    elif market_cap < 5_000:
        passes = False
        reasons.append(f"MCap too low ${market_cap:,.0f}")

    # Community engagement
    if reply_count < 3:
        passes = False
        reasons.append("No community engagement")

    return passes, reasons


def scan_pump_fun():
    """Main scan function - finds new quality launches."""
    global SEEN_TOKENS

    print(Fore.CYAN + "\n[PUMP.FUN] Scanning for new launches...")

    launches = get_new_launches()

    if not launches:
        print(Fore.YELLOW + "[PUMP.FUN] No launches found.")
        return []

    new_quality_tokens = []

    for token in launches:
        mint = token.get("mint", "")
        if not mint or mint in SEEN_TOKENS:
            continue

        SEEN_TOKENS.add(mint)

        name = token.get("name", "Unknown")
        symbol = token.get("symbol", "?")
        market_cap = token.get("usd_market_cap", 0) or 0
        created_timestamp = token.get("created_timestamp", 0)
        age_minutes = get_token_age_minutes(created_timestamp)
        has_twitter = bool(token.get("twitter"))
        has_telegram = bool(token.get("telegram"))
        has_website = bool(token.get("website"))
        reply_count = token.get("reply_count", 0) or 0
        description = token.get("description", "")

        passes, reasons = check_pump_token_quality(token)

        socials = []
        if has_twitter:
            socials.append("Twitter")
        if has_telegram:
            socials.append("Telegram")
        if has_website:
            socials.append("Website")

        if passes:
            print(Fore.GREEN + f"\n[PUMP.FUN] QUALITY LAUNCH FOUND!")
            print(Fore.WHITE + f"Name      : {name} ({symbol})")
            print(f"MCap      : ${market_cap:,.0f}")
            print(f"Age       : {age_minutes:.1f} minutes")
            print(f"Socials   : {', '.join(socials) if socials else 'None'}")
            print(f"Community : {reply_count} replies")
            print(f"Desc      : {description[:80] if description else 'N/A'}")
            print(f"Link      : https://pump.fun/{mint}")
            print("-" * 60)

            new_quality_tokens.append({
                "name": name,
                "symbol": symbol,
                "mint": mint,
                "market_cap": market_cap,
                "age_minutes": age_minutes,
                "socials": socials,
                "reply_count": reply_count,
                "description": description,
                "pump_url": f"https://pump.fun/{mint}",
                "dex_url": f"https://dexscreener.com/solana/{mint}",
            })

            # Send Telegram alert for quality launch
            alert_pump_launch(
                name=name,
                symbol=symbol,
                market_cap=market_cap,
                age_minutes=age_minutes,
                socials=socials,
                reply_count=reply_count,
                pump_url=f"https://pump.fun/{mint}",
                dex_url=f"https://dexscreener.com/solana/{mint}",
            )
        else:
            print(Fore.YELLOW + f"[PUMP.FUN] Skipped {name} ({symbol}) — {', '.join(reasons)}")

    if not new_quality_tokens:
        print(Fore.YELLOW + "[PUMP.FUN] No quality launches this scan.")

    return new_quality_tokens