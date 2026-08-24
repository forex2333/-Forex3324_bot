import os
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_KEY = os.environ["TWELVE_DATA_API_KEY"]

URL = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "30min",
    "outputsize": 100,
    "apikey": API_KEY
}

response = requests.get(URL, params=params, timeout=20)
data = response.json()

if data.get("status") == "error" or "values" not in data:
    print("XAUUSD data error:", data)
    raise SystemExit(1)

candles = data["values"]

# Twelve Data returns newest candle first
candles = list(reversed(candles))

closes = [float(c["close"]) for c in candles]
highs = [float(c["high"]) for c in candles]
lows = [float(c["low"]) for c in candles]

def ema(values, period):
    multiplier = 2 / (period + 1)
    result = values[0]

    for price in values[1:]:
        result = (price - result) * multiplier + result

    return result

def rsi(values, period=14):
    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

ema9 = ema(closes, 9)
ema21 = ema(closes, 21)
rsi14 = rsi(closes, 14)

current = closes[-1]
previous = closes[-2]

last_high = highs[-1]
last_low = lows[-1]

# Strong BUY
buy = (
    ema9 > ema21
    and rsi14 >= 55
    and current > previous
    and current > ema9
)

# Strong SELL
sell = (
    ema9 < ema21
    and rsi14 <= 45
    and current < previous
    and current < ema9
)

signal = None

if buy:
    signal = "BUY"
elif sell:
    signal = "SELL"

if signal == "BUY":

    risk = current - last_low

    if risk <= 0:
        risk = current * 0.001

    sl = current - risk
    tp = current + (risk * 1.5)

    message = (
        "🟢 STRONG BUY — XAUUSD 30M\n\n"
        f"Entry: {current:.2f}\n"
        f"SL: {sl:.2f}\n"
        f"TP: {tp:.2f}\n\n"
        f"EMA 9: {ema9:.2f}\n"
        f"EMA 21: {ema21:.2f}\n"
        f"RSI: {rsi14:.1f}\n\n"
        "⚠️ Signal is indicator-based, not guaranteed."
    )

elif signal == "SELL":

    risk = last_high - current

    if risk <= 0:
        risk = current * 0.001

    sl = current + risk
    tp = current - (risk * 1.5)

    message = (
        "🔴 STRONG SELL — XAUUSD 30M\n\n"
        f"Entry: {current:.2f}\n"
        f"SL: {sl:.2f}\n"
        f"TP: {tp:.2f}\n\n"
        f"EMA 9: {ema9:.2f}\n"
        f"EMA 21: {ema21:.2f}\n"
        f"RSI: {rsi14:.1f}\n\n"
        "⚠️ Signal is indicator-based, not guaranteed."
    )

else:
    print(
        f"NO TRADE | Price={current:.2f} "
        f"EMA9={ema9:.2f} EMA21={ema21:.2f} RSI={rsi14:.1f}"
    )
    raise SystemExit(0)

telegram_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

result = requests.post(
    telegram_url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=20
)

print(result.text)
