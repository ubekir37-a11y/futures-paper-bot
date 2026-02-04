import ccxt
import time
import pandas as pd
import numpy as np
from datetime import datetime

# =====================
# CONFIG
# =====================
SCAN_INTERVAL = 20
TIMEFRAME = '5m'
CANDLE_LIMIT = 30
TOP_N = 10
MIN_QUOTE_VOLUME = 5_000_000  # USDT

# =====================
# BYBIT FUTURES (USDT PERP)
# =====================
exchange = ccxt.bybit({
    "enableRateLimit": True,
    "options": {
        "defaultType": "linear"  # USDT perpetual
    }
})

def get_usdt_perp_symbols():
    markets = exchange.load_markets()
    symbols = []
    for s, m in markets.items():
        if (
            m.get('linear')
            and m.get('quote') == 'USDT'
            and m.get('active')
        ):
            symbols.append(s)
    return symbols

def compute_metrics(ohlcv):
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
    recent = df.tail(5)

    price_change = (recent['close'].iloc[-1] / recent['close'].iloc[0] - 1) * 100

    vol_recent = recent['volume'].sum()
    vol_prev = df.tail(10).head(5)['volume'].sum() if len(df) >= 10 else np.nan
    vol_ratio = (vol_recent / vol_prev) if vol_prev and vol_prev > 0 else np.nan

    return price_change, vol_ratio

def scan_once(symbols):
    results = []

    for s in symbols:
        try:
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

        except:
            continue

    if not results:
        return []

    df = pd.DataFrame(results)
    return df.sort_values('score', ascending=False).head(TOP_N)

def main():
    print("🚀 BYBIT FUTURES SCANNER BAŞLADI")
    symbols = get_usdt_perp_symbols()
    print(f"🔎 Taranan USDT perp market sayısı: {len(symbols)}")

    while True:
        now = datetime.utcnow().strftime('%H:%M:%S')
        top = scan_once(symbols)

        print("\n" + "="*70)
        print(f"⏱️ {now} | En hareketli {len(top)} coin (son 5m)")
        print("="*70)

        if len(top) == 0:
            print("— Uygun coin bulunamadı")
        else:
            for _, r in top.iterrows():
                print(
                    f"{r['symbol']:12} | "
                    f"Δ%: {r['price_change_%']:>6.2f} | "
                    f"Vol x: {0 if pd.isna(r['volume_ratio']) else r['volume_ratio']:.2f}"
                )

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
