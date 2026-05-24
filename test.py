import requests

# Check GTA6 GoPlus score
address = "AQNaCQHzkGUGMegLbB6a72HxQPkbSbw685SF51tSpump"
r = requests.get(f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={address}")
data = r.json()
result = data.get("result", {}).get(address.lower(), data.get("result", {}).get(address, {}))

if result:
    holders = result.get("holders", [])
    print(f"Holder count: {result.get('holder_count')}")
    print(f"Mintable: {result.get('mintable', {}).get('status')}")
    print(f"Freezable: {result.get('freezable', {}).get('status')}")
    if holders:
        print(f"Top holder %: {float(holders[0].get('percent', 0)) * 100:.1f}%")
        print(f"Top 5 holders:")
        for h in holders[:5]:
            pct = float(h.get("percent", 0)) * 100
            print(f"  {pct:.1f}% - {h.get('account','')[:20]}")
else:
    print("No GoPlus data found")
    print(data)