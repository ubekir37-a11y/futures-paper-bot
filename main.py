import ccxt
import time
import pandas as pd
import numpy as np
from datetime import datetime

# =====================
# CONFIG
# =====================
SCAN_INTERVAL = 20          # saniye
TIMEFRAME = '5m'
CANDLE_LIMIT = 30
RISK_REWARD = 2.0           # TP = 2R
HOLD_MINUTES = 15           # max pozisyon süresi

# =====================
# BYBIT TESTNET FUTURES
# =====================
exchange = ccxt.bybit({
    "enableRateLimit": True,
    "options": {
        "defaultType": "linear"
    },
    "urls": {
        "api": {
            "public": "https://api-testnet.bybit.com",
            "private": "https://api-testnet.bybit.com"
        }
    }
})

active_trade = None

def get_symbols():
    response = exchange.publicGetV5MarketInstrumentsInfo({
        "category": "linear"
    })
    symbols = []
    for s in response["result"]["list"]:
        if s["quoteCoin"] == "USDT" and s["status"] == "Trading":
            symbols.append(f"{s['symbol']}/USDT")
    return symbols

def indicators(df):
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    return df

def analyze(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
    df = indicators(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Trend
    if last['ema20'] > last['ema50']:
        direction = "LONG"
        entry = last['close']
        sl = entry - last['atr']
        tp = entry + (entry - sl) * RISK_REWARD
    else:
        direction = "SHORT"
        entry = last['close']
        sl = entry + last['atr']
        tp = entry - (sl - entry) * RISK_REWARD

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "open_time": time.time()
    }

def check_trade(trade):
    price = exchange.fetch_ticker(trade["symbol"])["last"]

    if trade["direction"] == "LONG":
        if price >= trade["tp"]:
            return "TP"
        if price <= trade["sl"]:
            return "SL"
    else:
        if price <= trade["tp"]:
            return "TP"
        if price >= trade["sl"]:
            return "SL"

    if (time.time() - trade["open_time"]) / 60 >= HOLD_MINUTES:
        return "TIME_EXIT"

    return None

def main():
    global active_trade
    print("🚀 BYBIT TESTNET PAPER BOT BAŞLADI")

    symbols = get_symbols()
    print(f"🔎 Taranan market: {len(symbols)}")

    while True:
        try:
            if active_trade is None:
                sym = np.random.choice(symbols)
                trade = analyze(sym)
                active_trade = trade

                print("\n" + "="*70)
                print(f"📈 YENİ PAPER TRADE")
                print(f"Coin      : {trade['symbol']}")
                print(f"Yön       : {trade['direction']}")
                print(f"Entry     : {trade['entry']:.4f}")
                print(f"StopLoss  : {trade['sl']:.4f}")
                print(f"TakeProfit: {trade['tp']:.4f}")
                print("="*70)

            else:
                result = check_trade(active_trade)
                if result:
                    print(f"🏁 POZİSYON KAPANDI → {result}")
                    active_trade = None

        except Exception as e:
            print("HATA:", e)

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
