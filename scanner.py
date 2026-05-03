import requests
import schedule
import time
from colorama import Fore, init
from logger import log_new_token, log_trending_pair, print_log_summary
from paper_trader import open_paper_trade, update_positions, print_portfolio
from alerts import alert_trending_token, alert_paper_trade_opened, alert_startup, alert_daily_summary
from goplus import check_token_security, format_security_report
from config import get_strategy, get_strategy_name, is_kill_switch_active

init(autoreset=True)

CHECK_INTERVAL_SECONDS = 60
CHAIN = "solana"
BLACKLIST_SYMBOLS = ["SOL", "USDC", "USDT", "ETH", "BTC", "BNB", "WBTC", "WETH", "WSOL"]


def calculate_risk_score(token):
    score = 100
    try:
        liquidity = token.get("liquidity", {}).get("usd", 0) or 0
        volume_h24 = token.get("volume", {}).get("h24", 0) or 0
        price_change_h1 = token.get("priceChange", {}).get("h1", 0) or 0
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


def get_risk_label(score):
    if score >= 70:
        return Fore.GREEN + f"LOW RISK ({score}/100)"
    elif score >= 45:
        return Fore.YELLOW + f"MEDIUM RISK ({score}/100)"
    else:
        return Fore.RED + f"HIGH RISK ({score}/100)"


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

            security = check_token_security(address)
            score = security.get("score", 0)
            findings = security.get("findings", [])

            if score >= 70:
                score_color = Fore.GREEN
            elif score >= 45:
                score_color = Fore.YELLOW
            else:
                score_color = Fore.RED

            print(Fore.WHITE + f"Token    : {name}")
            print(f"Address  : {address}")
            print(f"Link     : {url_link}")
            print(score_color + f"GoPlus   : {score}/100 - {'SAFE' if security['safe'] else 'RISKY'}")
            if findings:
                for flag in findings[:3]:
                    print(Fore.RED + f"  Flag   : {flag}")
            log_new_token(token)
            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Network error: {e}")
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}")


def scan_trending():
    if is_kill_switch_active():
        print(Fore.RED + "\n[KILL SWITCH ACTIVE] Trading paused.")
        return

    strategy = get_strategy()
    strategy_name = get_strategy_name()
    MIN_LIQUIDITY_USD = strategy["min_liquidity_usd"]
    MIN_VOLUME_5M = strategy["min_volume_5m"]
    MIN_RISK_SCORE = strategy["min_risk_score"]
    MIN_GOPLUS_SCORE = strategy["min_goplus_score"]
    MAX_FDV = strategy["max_fdv"]
    MAX_POSITION_SIZE = strategy["max_position_size"]

    print(Fore.CYAN + f"\n[SCANNER] Scanning trending Solana pairs... [Mode: {strategy_name.upper()}]")

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
                if fdv > MAX_FDV:
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

            token_address = pair.get("baseToken", {}).get("address", "")
            security = check_token_security(token_address)
            security_report = format_security_report(security)

            print(Fore.WHITE + f"Token       : {name} ({symbol})")
            print(f"Price       : ${price}")
            print(f"Liquidity   : ${liquidity:,.0f}")
            print(f"Vol (5m)    : ${vol_5m:,.0f}")
            print(f"Vol (24h)   : ${vol_24h:,.0f}")
            print(f"1h Change   : {price_1h}%")
            print(f"24h Change  : {price_24h}%")
            print(f"Risk Score  : {risk_label}")
            print(f"Security    : {security_report}")
            print(f"Link        : {dex_url}")
            log_trending_pair(pair, risk_score)

            if risk_score >= 70 and security["safe"]:
                alert_trending_token(
                    name, symbol, price, liquidity, vol_5m, price_1h,
                    risk_score, dex_url,
                    goplus_score=security.get("score"),
                    goplus_flags=security.get("findings", [])
                )

            if (risk_score >= MIN_RISK_SCORE and security["safe"] and
                    security.get("score", 0) >= MIN_GOPLUS_SCORE and
                    price and float(price) > 0):
                success, result = open_paper_trade(
                    name=name,
                    symbol=symbol,
                    address=pair.get("baseToken", {}).get("address", ""),
                    entry_price=price,
                    risk_score=risk_score,
                    dex_url=dex_url,
                    max_position_size=MAX_POSITION_SIZE,
                )
                if success:
                    print(Fore.GREEN + f"   [PAPER TRADE OPENED] Bought ${MAX_POSITION_SIZE} of {symbol} at ${price}")
                    alert_paper_trade_opened(name, symbol, price, MAX_POSITION_SIZE, risk_score,
                                             goplus_score=security.get("score"))
                else:
                    print(Fore.YELLOW + f"   [PAPER TRADE SKIPPED] {result}")

            print("-" * 60)

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Network error: {e}")
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}")


def check_open_positions():
    from paper_trader import load_trades
    from alerts import alert_paper_trade_closed

    state = load_trades()
    open_positions = state.get("open_positions", [])

    if not open_positions:
        return

    print(Fore.CYAN + "\n[POSITIONS] Checking open positions...")

    current_prices = {}

    for position in open_positions:
        address = position.get("address", "")
        name = position.get("name", "Unknown")
        symbol = position.get("symbol", "?")

        if not address:
            continue

        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
            response = requests.get(url, timeout=10)
            data = response.json()
            pairs = data.get("pairs", [])

            if not pairs:
                print(Fore.YELLOW + f"   No price data for {name}")
                continue

            pair = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0) or 0)
            price = pair.get("priceUsd")

            if price:
                current_prices[address] = float(price)
                entry = position.get("entry_price", 0)
                current = float(price)
                if entry > 0:
                    change_pct = ((current - entry) / entry) * 100
                    print(Fore.WHITE + f"   {name} ({symbol}) | "
                          f"Entry: ${entry:.8f} | "
                          f"Now: ${current:.8f} | "
                          f"Change: {change_pct:+.1f}%")

        except Exception as e:
            print(Fore.RED + f"   Error fetching price for {name}: {e}")

    closed, partial_exits = update_positions(current_prices)

    for position in closed:
        name = position.get("name", "Unknown")
        symbol = position.get("symbol", "?")
        exit_reason = position.get("exit_reason", "Unknown")
        pnl_usd = position.get("profit_loss_usd", 0)
        pnl_pct = position.get("profit_loss_pct", 0)

        if pnl_usd >= 0:
            print(Fore.GREEN + f"   [CLOSED - WIN] {name} | {exit_reason} | "
                  f"+${pnl_usd:.2f} (+{pnl_pct:.1f}%)")
        else:
            print(Fore.RED + f"   [CLOSED - LOSS] {name} | {exit_reason} | "
                  f"-${abs(pnl_usd):.2f} ({pnl_pct:.1f}%)")

        alert_paper_trade_closed(name, symbol, exit_reason, pnl_usd, pnl_pct)

    for exit in partial_exits:
        name = exit.get("name", "Unknown")
        symbol = exit.get("symbol", "?")
        level = exit.get("level", "?")
        profit = exit.get("profit_usd", 0)
        print(Fore.GREEN + f"   [PARTIAL EXIT] {name} hit {level} | Profit: +${profit:.2f}")


def run_scan():
    scan_tokens()
    scan_trending()
    check_open_positions()
    print_log_summary()
    print_portfolio()


print(Fore.GREEN + "=" * 60)
print(Fore.GREEN + "   MEMBOT - Solana Token Scanner STARTED")
print(Fore.GREEN + "=" * 60)
print(f"   Scanning every {CHECK_INTERVAL_SECONDS} seconds")
print(Fore.GREEN + "=" * 60)

alert_startup()

run_scan()

schedule.every(CHECK_INTERVAL_SECONDS).seconds.do(run_scan)


def send_daily_summary():
    from paper_trader import load_trades

    state = load_trades()
    balance = state.get("balance", 1000.0)
    pnl = state.get("total_profit_loss", 0.0)
    trade_count = state.get("trade_count", 0)
    wins = state.get("wins", 0)
    losses = state.get("losses", 0)
    win_rate = (wins / trade_count * 100) if trade_count > 0 else 0.0
    open_positions = state.get("open_positions", [])

    best_position = None
    best_change = None
    for pos in open_positions:
        address = pos.get("address", "")
        if not address:
            continue
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
            response = requests.get(url, timeout=10)
            data = response.json()
            pairs = data.get("pairs", [])
            if pairs:
                pair = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0) or 0)
                price = pair.get("priceUsd")
                if price:
                    current = float(price)
                    entry = pos.get("entry_price", 0)
                    if entry > 0:
                        change = ((current - entry) / entry) * 100
                        if best_change is None or change > best_change:
                            best_change = change
                            best_position = {
                                "name": pos.get("name", "Unknown"),
                                "change": change
                            }
        except Exception:
            continue

    alert_daily_summary(
        balance=balance,
        pnl=pnl,
        trade_count=trade_count,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        open_count=len(open_positions),
        best_position=best_position
    )


schedule.every().day.at("08:00").do(send_daily_summary)

while True:
    schedule.run_pending()
    time.sleep(1)