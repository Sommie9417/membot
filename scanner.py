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
# CONFIGURATION
# ============================================================
MIN_LIQUIDITY_USD = 5000
MIN_VOLUME_5M = 500
CHECK_INTERVAL_SECONDS = 60
CHAIN = "solana"
BLACKLIST_SYMBOLS = ["SOL", "USDC", "USDT", "ETH", "BTC", "BNB", "WBTC", "WETH", "WSOL"]

# ============================================================
# RISK SCORER
# ============================================================
def calculate_risk_score(token):
    score = 100

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

        if liquidity < 5000:
            score -= 30
        elif liquidity < 20000:
            score -= 15
        elif liquidity < 50000:
            score -= 5

        if volume_h24 < 1000:
            score -= 20
        elif volume_h24 < 10000:
            score -= 10

        if abs(price_change_h1) > 200:
            score -= 25
        elif abs(price_change_h1) > 100:
            score -= 10

        if buys_h1 + sells_h1 > 0:
            sell_ratio = sells_h1 / (buys_h1 + sells_h1)
            if sell_ratio > 0.75:
                score -= 25
            elif sell_ratio > 0.60:
                score -= 10

        if fdv > 0 and liquidity > 0:
            if fdv / liquidity > 1000:
                score -= 15

        if buys_h1 == 0 and sells_h1 == 0:
            score -= 20

    except Exception:
        score -= 50

    return max(0, min(100, score))


# ============================================================
# RISK LABEL
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
# ============================================================
def scan_tokens():
    print(Fore.CYAN + "\n[SCANNER] Scanning for new Solana tokens...")

    url = "https://api.dexscreener.com/token-profiles/latest/v1"

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

        for token in solana_tokens[:10]:
            name = token.get("description", "Unknown")
            address = token.get("tokenAddress", "N/A")
            url_link = token.get("url", "N/A")

            print(Fore.WHITE + f"Token   : {name}")
            print(f"Address : {address}")
            print(f"Link    : {url_link}")
            log_new_token(token)
            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Network error: {e}")
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}")


# ============================================================
# TRENDING SCANNER
# ============================================================
def scan_trending():
    print(Fore.CYAN + "\n[SCANNER] Scanning trending Solana pairs...")

    url = "https://api.dexscreener.com/token-boosts/top/v1"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            print(Fore.YELLOW + "No trending data found.")
            return

        solana_tokens = [t for t in data if t.get("chainId") == "solana"]

        if not solana_tokens:
            print(Fore.YELLOW + "No Solana tokens in trending list.")
            return

        print(Fore.CYAN + f"Found {len(solana_tokens)} boosted Solana tokens, fetching details...\n")

        filtered = []
        for token in solana_tokens[:20]:
            token_address = token.get("tokenAddress", "")
            if not token_address:
                continue

            try:
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                pair_response = requests.get(pair_url, timeout=10)
                pair_data = pair_response.json()
                pairs = pair_data.get("pairs", [])

                if not pairs:
                    continue

                pair = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0) or 0)

                liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
                volume_5m = pair.get("volume", {}).get("m5", 0) or 0
                fdv = pair.get("fdv", 0) or 0
                symbol = pair.get("baseToken", {}).get("symbol", "").upper()

                if symbol in BLACKLIST_SYMBOLS:
                    continue

                if fdv > 10_000_000:
                    continue

                if liquidity > 500_000:
                    continue

                if liquidity >= MIN_LIQUIDITY_USD and volume_5m >= MIN_VOLUME_5M:
                    filtered.append(pair)

            except Exception:
                continue

        if not filtered:
            print(Fore.YELLOW + "No pairs passed the filters this scan.")
            return

        filtered.sort(key=lambda x: x.get("volume", {}).get("m5", 0), reverse=True)

        print(Fore.CYAN + f"{len(filtered)} pair(s) passed filters:\n")
        print("-" * 60)

        for pair in filtered[:5]:
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
            log_trending_pair(pair, risk_score)

            if risk_score >= 70:
                alert_trending_token(name, symbol, price, liquidity, vol_5m, price_1h, risk_score, dex_url)

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
                    print(Fore.GREEN + f"   [PAPER TRADE OPENED] Bought $50 of {symbol} at ${price}")
                    alert_paper_trade_opened(name, symbol, price, 50, risk_score)
                else:
                    print(Fore.YELLOW + f"   [PAPER TRADE SKIPPED] {result}")

            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Network error: {e}")
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}")


# ============================================================
# MAIN
# ============================================================
def run_scan():
    scan_tokens()
    scan_trending()
    print_log_summary()
    print_portfolio()


print(Fore.GREEN + "=" * 60)
print(Fore.GREEN + "   MEMBOT - Solana Token Scanner STARTED")
print(Fore.GREEN + "=" * 60)
print(f"   Scanning every {CHECK_INTERVAL_SECONDS} seconds")
print(f"   Min Liquidity : ${MIN_LIQUIDITY_USD:,}")
print(f"   Min 5m Volume : ${MIN_VOLUME_5M:,}")
print(Fore.GREEN + "=" * 60)

alert_startup()

run_scan()

schedule.every(CHECK_INTERVAL_SECONDS).seconds.do(run_scan)

while True:
    schedule.run_pending()
    time.sleep(1)