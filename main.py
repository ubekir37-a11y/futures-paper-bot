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
CANDLE_LIMIT = 30           # son 30 mum
TOP_N = 10                  # en hareketli ilk N
MIN_QUOTE_VOLUME = 5_000_000  # USDT (likidite filtresi)

# =====================
# EXCHANGE
# =====================
exchange = ccxt.binance({
    "enableRateLimit": True,
    "options": {
        "defaultType": "future"
    }
})

def get_usdt_perp_symbols():
    markets = exchange.load_markets()
    symbols = []
    for s, m in markets.items():
        if m.get('linear') and m.get('quote') == 'USDT' and m.get('active'):
            symbols.append(s)
    return symbols

def compute_metrics(ohlcv):
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
    # son 5 mum
    recent = df.tail(5)

    # fiyat değişimi (%)
    price_change = (recent['close'].iloc[-1] / recent['close'].iloc[0] - 1) * 100

    # hacim artışı (son 5 mum / önceki 5 mum)
    vol_recent = recent['volume'].sum()
    vol_prev = df.tail(10).head(5)['volume'].sum() if len(df) >= 10 else np.nan
    vol_ratio = (vol_recent / vol_prev) if vol_prev and vol_prev > 0 else np.nan

    return price_change, vol_ratio

def get_quote_volume(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker.get('quoteVolume', 0) or 0
    except:
        return 0

def scan_once(symbols):
    results = []
    for s in symbols:
        try:
            # likidite filtresi
            qv = get_quote_volume(s)
            if qv < MIN_QUOTE_VOLUME:
                continue

            ohlcv = exchange.fetch_ohlcv(s, TIMEFRAME, limit=CANDLE_LIMIT)
            if len(ohlcv) < 10:
                continue

            price_change, vol_ratio = compute_metrics(ohlcv)

            score = abs(price_change) * (vol_ratio if not np.isnan(vol_ratio) else 1)

            results.append({
                'symbol': s,
                'price_change_%': price_change,
                'volume_ratio': vol_ratio,
                'score': score
            })

        except Exception as e:
            # rate limit / geçici hata
            continue

    if not results:
        return []

    df = pd.DataFrame(results)
    df = df.sort_values('score', ascending=False)
    return df.head(TOP_N)

def main():
    print("🚀 Binance Futures SCANNER başladı")
    symbols = get_usdt_perp_symbols()
    print(f"🔎 Taranan market sayısı: {len(symbols)}")

    while True:
        try:
            now = datetime.utcnow().strftime('%H:%M:%S')
            top = scan_once(symbols)

            print("\n" + "="*70)
            print(f"⏱️ {now} | En hareketli {len(top)} coin (son 5m)")
            print("="*70)

            if len(top) == 0:
                print("— Uygun coin bulunamadı")
            else:
                for i, r in top.iterrows():
                    print(
                        f"{r['symbol']:12} | "
                        f"Δ%: {r['price_change_%']:>6.2f} | "
                        f"Vol x: {0 if pd.isna(r['volume_ratio']) else r['volume_ratio']:.2f}"
                    )

        except Exception as e:
            print("HATA:", e)

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()


