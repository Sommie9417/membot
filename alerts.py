import requests

# ============================================================
# TELEGRAM ALERTS
# Sends messages directly to your Telegram when
# the bot finds something interesting
# ============================================================

TELEGRAM_TOKEN = "8492337730:AAHWMPLw2MD1Cy9NW1k32rVcLE0yHixKll4"
TELEGRAM_CHAT_ID = "5856502370"

def send_telegram(message):
    """Send a message to your Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def alert_new_token(name, address, dex_url):
    """Alert when a brand new token is discovered."""
    message = (
        f"<b>NEW TOKEN SPOTTED</b>\n\n"
        f"Name    : {name}\n"
        f"Address : <code>{address}</code>\n"
        f"Link    : {dex_url}\n\n"
        f"<i>No risk score yet - brand new launch</i>"
    )
    return send_telegram(message)


def alert_trending_token(name, symbol, price, liquidity,
                          vol_5m, price_change_1h, risk_score, dex_url):
    """Alert when a trending token passes our risk filter."""

    if risk_score >= 70:
        risk_label = "LOW RISK"
    elif risk_score >= 45:
        risk_label = "MEDIUM RISK"
    else:
        risk_label = "HIGH RISK"

    message = (
        f"<b>TRENDING TOKEN ALERT</b>\n\n"
        f"Token       : {name} ({symbol})\n"
        f"Price       : ${price}\n"
        f"Liquidity   : ${liquidity:,.0f}\n"
        f"Vol (5m)    : ${vol_5m:,.0f}\n"
        f"1h Change   : {price_change_1h}%\n"
        f"Risk Score  : {risk_score}/100 - {risk_label}\n\n"
        f"Link : {dex_url}"
    )
    return send_telegram(message)


def alert_paper_trade_opened(name, symbol, price, amount, risk_score):
    """Alert when a paper trade is opened."""
    message = (
        f"<b>PAPER TRADE OPENED</b>\n\n"
        f"Token     : {name} ({symbol})\n"
        f"Entry     : ${price}\n"
        f"Invested  : ${amount}\n"
        f"Risk      : {risk_score}/100\n\n"
        f"Stop Loss   : -35%\n"
        f"Take Profit : +100% (2x)"
    )
    return send_telegram(message)


def alert_paper_trade_closed(name, symbol, exit_reason, pnl_usd, pnl_pct):
    """Alert when a paper trade closes at TP or SL."""
    result = "WIN" if pnl_usd >= 0 else "LOSS"
    sign = "+" if pnl_usd >= 0 else ""

    message = (
        f"<b>PAPER TRADE CLOSED - {result}</b>\n\n"
        f"Token      : {name} ({symbol})\n"
        f"Exit       : {exit_reason}\n"
        f"P/L        : {sign}${pnl_usd:,.2f} ({sign}{pnl_pct:.1f}%)"
    )
    return send_telegram(message)


def alert_startup():
    """Send a message when the bot starts up."""
    message = (
        f"<b>MEMBOT STARTED</b>\n\n"
        f"Your Solana scanner is now live.\n"
        f"You will receive alerts when:\n\n"
        f"- A new token is discovered\n"
        f"- A trending token passes risk filter\n"
        f"- A paper trade opens or closes"
    )
    return send_telegram(message)