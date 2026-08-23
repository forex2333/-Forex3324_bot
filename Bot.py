import os
import requests
import time

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Test signal message
message = """
🟡 XAUUSD — GOLD 5M

⚠️ TEST SIGNAL

BUY / SELL analysis system is being connected.

Timeframe: 5 Minutes
Status: Bot is working ✅

This is NOT a real trading signal yet.
"""

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

data = {
    "chat_id": CHAT_ID,
    "text": message
}

response = requests.post(url, data=data)

print(response.text)
