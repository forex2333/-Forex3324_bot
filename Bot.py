import os
import time
import requests
import pandas as pd
import yfinance as yf

# =========================
# TELEGRAM SETTINGS
# =========================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================
# SYMBOLS
# =========================

SYMBOLS = {
    "XAUUSD": "GC=F",      # Gold
    "BTCUSD": "BTC-USD",   # Bitcoin
    "EURUSD": "EURUSD=X",  # Euro / USD
    "XAUEUR": "GC=F"       # Gold proxy; EUR conversion handled below
}

TIMEFRAME = "30m"
PERIOD = "5d"

# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials missing.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=20
        )
    except Exception as e:
        print("Telegram error:", e)


# =========================
# DATA
# =========================

def get_data(symbol):
    try:
        data = yf.download(
            symbol,
            period=PERIOD,
            interval=TIMEFRAME,
            progress=False,
            auto_adjust=False
        )

        if data.empty:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data = data.dropna()

        if len(data) < 50:
            return None

        return data

    except Exception as e:
        print(f"Data error {symbol}:", e)
        return None


# =========================
# INDICATORS
# =========================

def calculate_indicators(df):

    close = df["Close"]

    # EMA
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()

    # RSI
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, 0.000001)

    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    return df


# =========================
# SIGNAL ENGINE
# =========================

def get_signal(df):

    df = calculate_indicators(df)

    last = df.iloc[-1]
    previous = df.iloc[-2]

    price = float(last["Close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    score_buy = 0
    score_sell = 0

    # EMA trend
    if ema20 > ema50:
        score_buy += 2
    elif ema20 < ema50:
        score_sell += 2

    # RSI
    if 50 < rsi < 70:
        score_buy += 1
    elif 30 < rsi < 50:
        score_sell += 1

    # MACD
    if macd > macd_signal:
        score_buy += 2
    elif macd < macd_signal:
        score_sell += 2

    # Price vs EMA20
    if price > ema20:
        score_buy += 1
    elif price < ema20:
        score_sell += 1

    # Final signal
    if score_buy >= 5 and score_buy > score_sell:
        return "BUY", price, rsi, score_buy

    if score_sell >= 5 and score_sell > score_buy:
        return "SELL", price, rsi, score_sell

    return None, price, rsi, max(score_buy, score_sell)


# =========================
# MAIN CHECK
# =========================

def check_symbol(name, ticker):

    data = get_data(ticker)

    if data is None:
        print(f"{name}: No data")
        return

    signal, price, rsi, score = get_signal(data)

    print(
        f"{name} | Price: {price:.5f} | "
        f"RSI: {rsi:.2f} | Score: {score} | "
        f"Signal: {signal}"
    )

    if signal:

        emoji = "🟢" if signal == "BUY" else "🔴"

        message = (
            f"{emoji} {name} — 30M\n\n"
            f"📊 SIGNAL: {signal}\n"
            f"💰 Price: {price:.5f}\n"
            f"📈 RSI: {rsi:.2f}\n"
            f"💪 Strength: {score}/6\n\n"
            f"⚠️ This is a technical signal, not a guarantee."
        )

        send_telegram(message)


# =========================
# RUN
# =========================

def main():

    print("================================")
    print("30M SIGNAL BOT STARTED")
    print("================================")

    sent_signals = {}

    while True:

        for name, ticker in SYMBOLS.items():

            try:

                data = get_data(ticker)

                if data is None:
                    continue

                signal, price, rsi, score = get_signal(data)

                print(
                    f"{name}: {signal} | "
                    f"Price={price:.5f} | "
                    f"RSI={rsi:.2f} | "
                    f"Score={score}/6"
                )

                if signal:

                    # Avoid sending the same signal repeatedly
                    candle_time = str(data.index[-1])
                    signal_id = f"{name}_{candle_time}_{signal}"

                    if sent_signals.get(name) != signal_id:

                        emoji = "🟢" if signal == "BUY" else "🔴"

                        message = (
                            f"{emoji} {name} — 30M\n\n"
                            f"📊 SIGNAL: {signal}\n"
                            f"💰 Price: {price:.5f}\n"
                            f"📈 RSI: {rsi:.2f}\n"
                            f"💪 Strength: {score}/6\n\n"
                            f"⚠️ Technical signal only."
                        )

                        send_telegram(message)

                        sent_signals[name] = signal_id

            except Exception as e:
                print(f"{name} error:", e)

        # Check approximately every 5 minutes
        time.sleep(300)


if __name__ == "__main__":
    main()
