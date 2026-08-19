import os
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

data = {
    "chat_id": "YOUR_CHAT_ID",
    "text": "✅ Forex3324 Bot is working!\n\nTelegram connection successful."
}

response = requests.post(url, data=data)
print(response.text)
