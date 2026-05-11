import requests

# ============================================================
# TELEGRAM ALERTS - UPGRADED
# Clean, detailed alerts only for high quality tokens
# ============================================================

TELEGRAM_TOKEN = "8564559248:AAHhsssaA4iBDCx7jOlZ4-PghrxSjSDAelI"
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


def alert_trending_token(name, symbol, price, liquidity,
                          vol_5m, price_change_1h, risk_score, dex_url,
                          goplus_score=None, goplus_flags=None):
    """
    Alert for high quality trending tokens.
    Only called when risk score >= 70 AND GoPlus says safe.
    """
    if risk_score >= 70:
        risk_label = "LOW RISK"
        risk_icon = "🟢"
    elif risk_score >= 45:
        risk_label = "MEDIUM RISK"
        risk_icon = "🟡"
    else:
        risk_label = "HIGH RISK"
        risk_icon = "🔴"

    change_icon = "📈" if price_change_1h >= 0 else "📉"

    goplus_line = ""
    if goplus_score is not None:
        goplus_line = f"GoPlus Score  : {goplus_score}/100 - SAFE\n"

    flags_line = ""
    if goplus_flags:
        flags_line = f"Flags         : {', '.join(goplus_flags)}\n"
    else:
        flags_line = "Flags         : None\n"

    message = (
        f"<b>HIGH QUALITY TOKEN ALERT</b>\n"
        f"{'=' * 30}\n\n"
        f"<b>{name} ({symbol})</b>\n\n"
        f"Price         : ${price}\n"
        f"Liquidity     : ${liquidity:,.0f}\n"
        f"Vol (5m)      : ${vol_5m:,.0f}\n"
        f"1h Change     : {change_icon} {price_change_1h}%\n\n"
        f"Risk Score    : {risk_icon} {risk_score}/100 - {risk_label}\n"
        f"{goplus_line}"
        f"{flags_line}\n"
        f"<a href='{dex_url}'>View on DexScreener</a>"
    )
    return send_telegram(message)


def alert_paper_trade_opened(name, symbol, price, amount, risk_score, goplus_score=None):
    """Alert when a paper trade is opened."""
    message = (
        f"<b>PAPER TRADE OPENED</b>\n"
        f"{'=' * 30}\n\n"
        f"Token         : <b>{name} ({symbol})</b>\n"
        f"Entry Price   : ${price}\n"
        f"Invested      : ${amount}\n\n"
        f"Risk Score    : {risk_score}/100\n"
    )

    if goplus_score is not None:
        message += f"GoPlus Score  : {goplus_score}/100\n"

    message += (
        f"\n"
        f"Stop Loss     : -35%\n"
        f"Take Profit   : +100% (2x)\n"
    )
    return send_telegram(message)


def alert_paper_trade_closed(name, symbol, exit_reason, pnl_usd, pnl_pct):
    """Alert when a paper trade closes at TP or SL."""
    result = "WIN" if pnl_usd >= 0 else "LOSS"
    sign = "+" if pnl_usd >= 0 else ""
    icon = "✅" if pnl_usd >= 0 else "❌"

    message = (
        f"<b>PAPER TRADE CLOSED - {result} {icon}</b>\n"
        f"{'=' * 30}\n\n"
        f"Token         : <b>{name} ({symbol})</b>\n"
        f"Exit Reason   : {exit_reason}\n"
        f"P/L           : {sign}${pnl_usd:,.2f} ({sign}{pnl_pct:.1f}%)\n"
    )
    return send_telegram(message)


def alert_startup():
    """Send a message when the bot starts up."""
    message = (
        f"<b>MEMBOT STARTED</b>\n"
        f"{'=' * 30}\n\n"
        f"Solana scanner is live.\n\n"
        f"Alerts you will receive:\n"
        f"- High quality token spotted\n"
        f"- Paper trade opened\n"
        f"- Paper trade closed (win/loss)\n\n"
        f"Filters active:\n"
        f"- Risk score 70+ only\n"
        f"- GoPlus verified safe\n"
        f"- Under $10M market cap\n"
        f"- No SOL/BTC/ETH/stablecoins"
    )
    return send_telegram(message)


def alert_daily_summary(balance, pnl, trade_count, wins, losses,
                        win_rate, open_count, best_position=None):
    """Send a daily morning summary to Telegram."""
    
    sign = "+" if pnl >= 0 else ""
    performance = "up" if pnl >= 0 else "down"

    best_line = ""
    if best_position:
        best_line = (
            f"\nBest Position  : {best_position['name']} "
            f"({best_position['change']:+.1f}%)"
        )

    message = (
        f"<b>MEMBOT DAILY SUMMARY</b>\n"
        f"{'=' * 30}\n\n"
        f"Good morning Chisom!\n"
        f"Here is your overnight performance.\n\n"
        f"Balance        : ${balance:,.2f}\n"
        f"Total P/L      : {sign}${pnl:,.2f}\n"
        f"Total Trades   : {trade_count}\n"
        f"Wins           : {wins}\n"
        f"Losses         : {losses}\n"
        f"Win Rate       : {win_rate:.1f}%\n"
        f"Open Positions : {open_count}\n"
        f"{best_line}\n\n"
        f"Bot is running. Have a great day!"
    )
    return send_telegram(message)