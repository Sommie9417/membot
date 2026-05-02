import requests
import schedule
import time
from colorama import Fore, Style, init
from logger import log_new_token, log_trending_pair, print_log_summary
from paper_trader import open_paper_trade, update_positions, print_portfolio
from alerts import alert_new_token, alert_trending_token, alert_paper_trade_opened, alert_startup
# Initialize colorama for colored terminal output
init(autoreset=True)

# ============================================================
# CONFIGURATION - You can adjust these settings later
# ============================================================
MIN_LIQUIDITY_USD = 5000      # Minimum liquidity in USD
MIN_VOLUME_5M = 500           # Minimum 5 minute volume in USD
MAX_AGE_HOURS = 24            # Only show tokens newer than this
CHECK_INTERVAL_SECONDS = 60   # How often to scan (in seconds)
CHAIN = "solana"              # Blockchain to monitor

# ============================================================
# RISK SCORER
# Gives each token a score from 0-100
# Higher = safer, Lower = riskier
# ============================================================
def calculate_risk_score(token):
    score = 100  # Start with perfect score, deduct for red flags

    try:
        liquidity = token.get("liquidity", {}).get("usd", 0) or 0
        volume_h1 = token.get("volume", {}).get("h1", 0) or 0
        volume_h24 = token.get("volume", {}).get("h24", 0) or 0
        price_change_h1 = token.get("priceChange", {}).get("h1", 0) or 0
        price_change_h24 = token.get("priceChange", {}).get("h24", 0) or 0
        txns = token.get("txns", {})
        buys_h1 = txns.get("h1", {}).get("buys", 0) or 0
        sells_h1 = txns.get("h1", {}).get("sells", 0) or 0
        fdv = token.get("fdv", 0) or 0

        # Low liquidity = high risk
        if liquidity < 5000:
            score -= 30
        elif liquidity < 20000:
            score -= 15
        elif liquidity < 50000:
            score -= 5

        # Very low volume = suspicious
        if volume_h24 < 1000:
            score -= 20
        elif volume_h24 < 10000:
            score -= 10

        # Extreme price changes = manipulation risk
        if abs(price_change_h1) > 200:
            score -= 25
        elif abs(price_change_h1) > 100:
            score -= 10

        # Way more sells than buys = dump in progress
        if buys_h1 + sells_h1 > 0:
            sell_ratio = sells_h1 / (buys_h1 + sells_h1)
            if sell_ratio > 0.75:
                score -= 25
            elif sell_ratio > 0.60:
                score -= 10

        # Extremely high FDV with no liquidity = red flag
        if fdv > 0 and liquidity > 0:
            if fdv / liquidity > 1000:
                score -= 15

        # No transactions at all = very suspicious
        if buys_h1 == 0 and sells_h1 == 0:
            score -= 20

    except Exception:
        score -= 50  # If we can't read the data, assume risky

    return max(0, min(100, score))  # Keep score between 0 and 100


# ============================================================
# RISK LABEL
# Converts score into a human readable label and color
# ============================================================
def get_risk_label(score):
    if score >= 70:
        return Fore.GREEN + f"LOW RISK ({score}/100)"
    elif score >= 45:
        return Fore.YELLOW + f"MEDIUM RISK ({score}/100)"
    else:
        return Fore.RED + f"HIGH RISK ({score}/100)"


# ============================================================
# TOKEN SCANNER
# Fetches new Solana tokens from DexScreener
# ============================================================
def scan_tokens():
    print(Fore.CYAN + "\n[SCANNER] Scanning for new Solana tokens...")

    url = f"https://api.dexscreener.com/token-profiles/latest/v1"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            print(Fore.YELLOW + "No new tokens found this scan.")
            return

        solana_tokens = [t for t in data if t.get("chainId") == CHAIN]

        if not solana_tokens:
            print(Fore.YELLOW + "No new Solana tokens found this scan.")
            return

        print(Fore.CYAN + f"Found {len(solana_tokens)} new Solana token(s):\n")
        print("-" * 60)

        for token in solana_tokens[:10]:  # Show top 10 max
            name = token.get("description", "Unknown")
            address = token.get("tokenAddress", "N/A")
            url_link = token.get("url", "N/A")

            print(Fore.WHITE + f"Token   : {name}")
            print(f"Address : {address}")
            print(f"Link    : {url_link}")
            print("-" * 60)
            print(Fore.WHITE + f"Token   : {name}")
            print(f"Address : {address}")
            print(f"Link    : {url_link}")
            log_new_token(token)
            alert_new_token(name, address, url_link)
            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Network error: {e}")
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}")


# ============================================================
# DEEPER SCAN
# Gets full market data + risk score for trending pairs
# ============================================================
def scan_trending():
    print(Fore.CYAN + "\n[SCANNER] Scanning trending Solana pairs...")

    url = url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        pairs = data.get("pairs", [])

        if not pairs:
            print(Fore.YELLOW + "No trending pairs found.")
            return

        # Filter pairs
        filtered = []
        for pair in pairs:
            liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
            volume_5m = pair.get("volume", {}).get("m5", 0) or 0

            if liquidity >= MIN_LIQUIDITY_USD and volume_5m >= MIN_VOLUME_5M:
                filtered.append(pair)

        if not filtered:
            print(Fore.YELLOW + "No pairs passed the filters this scan.")
            return

        # Sort by 5 minute volume (highest first)
        filtered.sort(key=lambda x: x.get("volume", {}).get("m5", 0), reverse=True)

        print(Fore.CYAN + f"{len(filtered)} pair(s) passed filters:\n")
        print("-" * 60)

        for pair in filtered[:5]:  # Show top 5
            name = pair.get("baseToken", {}).get("name", "Unknown")
            symbol = pair.get("baseToken", {}).get("symbol", "?")
            price = pair.get("priceUsd", "N/A")
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            vol_5m = pair.get("volume", {}).get("m5", 0)
            vol_24h = pair.get("volume", {}).get("h24", 0)
            price_1h = pair.get("priceChange", {}).get("h1", 0)
            price_24h = pair.get("priceChange", {}).get("h24", 0)
            dex_url = pair.get("url", "N/A")

            risk_score = calculate_risk_score(pair)
            risk_label = get_risk_label(risk_score)

            print(Fore.WHITE + f"Token       : {name} ({symbol})")
            print(f"Price       : ${price}")
            print(f"Liquidity   : ${liquidity:,.0f}")
            print(f"Vol (5m)    : ${vol_5m:,.0f}")
            print(f"Vol (24h)   : ${vol_24h:,.0f}")
            print(f"1h Change   : {price_1h}%")
            print(f"24h Change  : {price_24h}%")
            print(f"Risk Score  : {risk_label}")
            print(f"Link        : {dex_url}")
            print("-" * 60)
            print(f"Risk Score  : {risk_label}")
            print(f"Link        : {dex_url}")
            log_trending_pair(pair, risk_score)

            # Auto paper trade if risk score is good enough
            if risk_score >= 45 and price and float(price) > 0:
                success, result = open_paper_trade(
                    name=name,
                    symbol=symbol,
                    address=pair.get("baseToken", {}).get("address", ""),
                    entry_price=price,
                    risk_score=risk_score,
                    dex_url=dex_url,
                )
                if success:
                 if success:
                    print(Fore.GREEN + f"   [PAPER TRADE OPENED] Bought ${50} of {symbol} at ${price}")
                    alert_paper_trade_opened(name, symbol, price, 50, risk_score)
                else:
                    print(Fore.YELLOW + f"   [PAPER TRADE SKIPPED] {result}")

            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Network error: {e}")
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}")


# ============================================================
# MAIN - Runs everything on a schedule
# ============================================================
def run_scan():
    scan_tokens()
    scan_trending()
    print_log_summary()
    print_portfolio()

print(Fore.GREEN + "=" * 60)
print(Fore.GREEN + "   MEMBOT - Solana Token Scanner STARTED")
alert_startup()
print(Fore.GREEN + "=" * 60)
print(f"   Scanning every {CHECK_INTERVAL_SECONDS} seconds")
print(f"   Min Liquidity : ${MIN_LIQUIDITY_USD:,}")
print(f"   Min 5m Volume : ${MIN_VOLUME_5M:,}")
print(Fore.GREEN + "=" * 60)

# Run immediately on start
run_scan()

# Then run every 60 seconds
schedule.every(CHECK_INTERVAL_SECONDS).seconds.do(run_scan)

while True:
    schedule.run_pending()
    time.sleep(1)