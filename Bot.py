import os
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_KEY = os.environ["TWELVE_DATA_API_KEY"]

# Twelve Data XAU/USD
url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "5min",
    "outputsize": 100,
    "apikey": API_KEY
}

response = requests.get(url, params=params, timeout=20)
data = response.json()

# Don't send a trading signal if the data source fails
if data.get("status") == "error" or "values" not in data:
    print("XAUUSD data error:", data)
    raise SystemExit(1)

values = data["values"]

# Show that live 5M data is working
latest = values[0]

message = (
    "🟡 XAUUSD — 5M\n\n"
    "✅ Live price data connected\n"
    f"Current price: {latest['close']}\n\n"
    "⚠️ Signal engine is not enabled yet."
)

telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

result = requests.post(
    telegram_url,
    data={"chat_id": CHAT_ID, "text": message},
    timeout=20
)

print(result.text)
