import os
import requests
import hashlib
import json
from pathlib import Path

# =========================
# SETTINGS
# =========================

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_KEY = os.environ["TWELVE_DATA_API_KEY"]

INTERVAL = "30min"
OUTPUT_SIZE = 100

SYMBOLS = {
    "XAU/USD": "🟡 GOLD",
    "BTC/USD": "₿ BTC",
    "EUR/USD": "💶 EURUSD",
    "XAU/EUR": "🟠 XAUEUR",
}

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# File used to remember the last signal between GitHub Actions runs
STATE_FILE = Path("signal_state.json")


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    response = requests.post(
        TELEGRAM_URL,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()
    print("Telegram:", response.text)


# =========================
# INDICATORS
# =========================

def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) <= period:
        return None

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
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# =========================
# LOAD / SAVE SIGNAL STATE
# =========================

def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# =========================
# GET MARKET DATA
# =========================

def get_candles(symbol):
    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "outputsize": OUTPUT_SIZE,
        "apikey": API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        print(f"{symbol} data error:", data)
        return None

    if "values" not in data:
        print(f"{symbol}: No candle data received")
        return None

    candles = list(reversed(data["values"]))

    return candles


# =========================
# ANALYZE ONE SYMBOL
# =========================

def analyze_symbol(symbol, state):

    candles = get_candles(symbol)

    if not candles or len(candles) < 30:
        print(f"{symbol}: Not enough data")
        return

    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    times = [c.get("datetime", "") for c in candles]

    current = closes[-1]
    previous = closes[-2]

    current_high = highs[-1]
    current_low = lows[-1]

    candle_time = times[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    rsi14 = rsi(closes, 14)

    if ema9 is None or ema21 is None or rsi14 is None:
        print(f"{symbol}: Indicator calculation failed")
        return

    # =========================
    # STRONG BUY CONDITIONS
    # =========================

    buy_conditions = [
        ema9 > ema21,
        rsi14 >= 55,
        current > previous,
        current > ema9
    ]

    buy_score = sum(buy_conditions)

    # =========================
    # STRONG SELL CONDITIONS
    # =========================

    sell_conditions = [
        ema9 < ema21,
        rsi14 <= 45,
        current < previous,
        current < ema9
    ]

    sell_score = sum(sell_conditions)

    signal = None
    strength = 0

    # Require ALL 4 confirmations
    if buy_score == 4:
        signal = "BUY"
        strength = 4

    elif sell_score == 4:
        signal = "SELL"
        strength = 4

    # =========================
    # NO SIGNAL
    # =========================

    if signal is None:

        print(
            f"NO SIGNAL | {symbol} | "
            f"Price={current:.5f} | "
            f"EMA9={ema9:.5f} | "
            f"EMA21={ema21:.5f} | "
            f"RSI={rsi14:.1f}"
        )

        return

    # =========================
    # DUPLICATE PROTECTION
    # =========================

    signal_id = f"{symbol}_{candle_time}_{signal}"

    old_signal = state.get(symbol)

    if old_signal == signal_id:

        print(
            f"DUPLICATE BLOCKED | "
            f"{symbol} {signal} | "
            f"Candle={candle_time}"
        )

        return

    # =========================
    # SL / TP
    # =========================

    if signal == "BUY":

        risk = current - current_low

        if risk <= 0:
            risk = current * 0.001

        sl = current - risk
        tp = current + (risk * 1.5)

        emoji = "🟢"

    else:

        risk = current_high - current

        if risk <= 0:
            risk = current * 0.001

        sl = current + risk
        tp = current - (risk * 1.5)

        emoji = "🔴"

    market_name = SYMBOLS.get(symbol, symbol)

    # =========================
    # TELEGRAM MESSAGE
    # =========================

    message = (
        f"{emoji} STRONG {signal} — {market_name}\n"
        f"📊 {symbol} | 30M\n\n"

        f"💰 Entry: {current:.5f}\n"
        f"🛑 SL: {sl:.5f}\n"
        f"🎯 TP: {tp:.5f}\n\n"

        f"📈 EMA 9: {ema9:.5f}\n"
        f"📉 EMA 21: {ema21:.5f}\n"
        f"📊 RSI: {rsi14:.1f}\n"
        f"💪 Confirmation: {strength}/4\n\n"

        f"🕐 Candle: {candle_time}\n\n"

        "⚠️ Indicator-based signal. "
        "Trading involves risk; no signal is guaranteed."
    )

    # =========================
    # SEND TELEGRAM
    # =========================

    send_telegram(message)

    # Save signal so it isn't repeated
    state[symbol] = signal_id

    print(
        f"SIGNAL SENT | {symbol} | "
        f"{signal} | Candle={candle_time}"
    )


# =========================
# MAIN
# =========================

def main():

    print("=" * 60)
    print("XAU/BTC/EUR SIGNAL BOT")
    print("Timeframe:", INTERVAL)
    print("Markets:", ", ".join(SYMBOLS.keys()))
    print("=" * 60)

    state = load_state()

    for symbol in SYMBOLS:

        try:

            analyze_symbol(
                symbol,
                state
            )

        except Exception as e:

            print(
                f"ERROR processing {symbol}: {e}"
            )

    save_state(state)

    print("=" * 60)
    print("CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
