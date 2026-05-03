import requests
import time

# ============================================================
# GOPLUS SECURITY
# Checks every token for scam indicators
# Completely free, no API key needed
# ============================================================

GOPLUS_URL = "https://api.gopluslabs.io/api/v1/solana/token_security"

def check_token_security(token_address):
    """
    Checks a Solana token address against GoPlus security API.
    Returns a dict with security findings and a safety score.
    """
    try:
        url = f"{GOPLUS_URL}?contract_addresses={token_address}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        result = data.get("result", {})
        token_data = result.get(token_address.lower(), 
                     result.get(token_address, {}))

        if not token_data:
            return {
                "safe": False,
                "score": 0,
                "reason": "No security data found for this token",
                "details": {}
            }

        findings = []
        deductions = 0

        # Check honeypot
        is_honeypot = token_data.get("is_honeypot", "0")
        if is_honeypot == "1":
            findings.append("HONEYPOT DETECTED")
            deductions += 100

        # Check if mint authority is enabled (dev can create more tokens)
        mintable = token_data.get("mintable", "0")
        if mintable == "1":
            findings.append("Mint authority enabled - dev can print more tokens")
            deductions += 30

        # Check if freeze authority is enabled
        freezeable = token_data.get("freezeable", "0")
        if freezeable == "1":
            findings.append("Freeze authority enabled - dev can freeze wallets")
            deductions += 30

        # Check transfer pause ability
        transfer_pausable = token_data.get("transfer_pausable", "0")
        if transfer_pausable == "1":
            findings.append("Transfers can be paused by dev")
            deductions += 25

        # Check if token can be blacklisted
        can_blacklist = token_data.get("can_blacklist", "0")  
        if can_blacklist == "1":
            findings.append("Dev can blacklist wallets")
            deductions += 20

        # Check creator balance concentration
        creator_percent = token_data.get("creator_percent", "0")
        try:
            creator_pct = float(creator_percent) * 100
            if creator_pct > 50:
                findings.append(f"Creator holds {creator_pct:.1f}% of supply - very high")
                deductions += 40
            elif creator_pct > 20:
                findings.append(f"Creator holds {creator_pct:.1f}% of supply - high")
                deductions += 20
            elif creator_pct > 10:
                findings.append(f"Creator holds {creator_pct:.1f}% of supply - moderate")
                deductions += 10
        except (ValueError, TypeError):
            pass

        # Check top holder concentration
        top10_percent = token_data.get("top10_holder_percent", "0")
        try:
            top10_pct = float(top10_percent) * 100
            if top10_pct > 80:
                findings.append(f"Top 10 holders own {top10_pct:.1f}% - extremely concentrated")
                deductions += 30
            elif top10_pct > 60:
                findings.append(f"Top 10 holders own {top10_pct:.1f}% - highly concentrated")
                deductions += 15
        except (ValueError, TypeError):
            pass

        # Check buy tax
        buy_tax = token_data.get("buy_tax", "0")
        try:
            buy_tax_pct = float(buy_tax) * 100
            if buy_tax_pct > 10:
                findings.append(f"High buy tax: {buy_tax_pct:.1f}%")
                deductions += 20
            elif buy_tax_pct > 5:
                findings.append(f"Moderate buy tax: {buy_tax_pct:.1f}%")
                deductions += 10
        except (ValueError, TypeError):
            pass

        # Check sell tax
        sell_tax = token_data.get("sell_tax", "0")
        try:
            sell_tax_pct = float(sell_tax) * 100
            if sell_tax_pct > 10:
                findings.append(f"High sell tax: {sell_tax_pct:.1f}%")
                deductions += 25
            elif sell_tax_pct > 5:
                findings.append(f"Moderate sell tax: {sell_tax_pct:.1f}%")
                deductions += 10
        except (ValueError, TypeError):
            pass

        # Calculate final safety score
        safety_score = max(0, 100 - deductions)

        # Token is considered safe if score is above 60 and not a honeypot
        is_safe = safety_score >= 60 and is_honeypot != "1"

        return {
            "safe": is_safe,
            "score": safety_score,
            "findings": findings,
            "details": {
                "mintable": mintable,
                "freezeable": freezeable,
                "is_honeypot": is_honeypot,
                "creator_percent": creator_percent,
                "top10_holder_percent": top10_percent,
                "buy_tax": buy_tax,
                "sell_tax": sell_tax,
            }
        }

    except requests.exceptions.RequestException as e:
        return {
            "safe": False,
            "score": 0,
            "reason": f"Network error checking security: {e}",
            "details": {}
        }
    except Exception as e:
        return {
            "safe": False,
            "score": 0,
            "reason": f"Error checking security: {e}",
            "details": {}
        }


def format_security_report(security_result):
    """Returns a human readable security report."""
    score = security_result.get("score", 0)
    findings = security_result.get("findings", [])
    is_safe = security_result.get("safe", False)

    if score >= 80:
        label = "SAFE"
    elif score >= 60:
        label = "MODERATE RISK"
    elif score >= 40:
        label = "HIGH RISK"
    else:
        label = "DANGEROUS"

    report = f"GoPlus Score: {score}/100 - {label}\n"

    if findings:
        report += "Flags:\n"
        for f in findings:
            report += f"  - {f}\n"
    else:
        report += "No security flags found\n"

    return report