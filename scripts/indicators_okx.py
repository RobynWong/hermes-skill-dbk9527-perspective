#!/usr/bin/env python3
"""BTC多周期技术指标计算 - OKX版本（Binance 451封锁替代方案）"""
import ccxt, math, sys

okx = ccxt.okx({
    'proxies': {'https': 'http://127.0.0.1:9981', 'http': 'http://127.0.0.1:9981'}
})

def ema(data, span):
    k = 2 / (span + 1)
    r = [data[0]]
    for d in data[1:]:
        r.append(d * k + r[-1] * (1 - k))
    return r

def calc_indicators(tf, limit=250):
    try:
        ohlcv = okx.fetch_ohlcv('BTC/USDT:USDT', tf, limit=limit)
    except Exception as e:
        print(f'  [{tf.upper()}] 获取失败: {e}')
        return
    
    closes = [c[4] for c in ohlcv]
    highs = [c[2] for c in ohlcv]
    lows = [c[3] for c in ohlcv]
    opens = [c[1] for c in ohlcv]
    vols = [c[5] for c in ohlcv]
    n = len(closes)
    price = closes[-1]
    
    # MA
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    ma200 = sum(closes[-200:]) / 200 if n >= 200 else 0
    
    # RSI(14)
    deltas = [closes[i] - closes[i-1] for i in range(1, n)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    # MACD(12,26,9)
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif = [ema12[i] - ema26[i] for i in range(n)]
    dea = ema(dif, 9)
    macd_hist = 2 * (dif[-1] - dea[-1])
    
    # Bollinger(20,2)
    mid = sum(closes[-20:]) / 20
    std = math.sqrt(sum((x - mid) ** 2 for x in closes[-20:]) / 20)
    bb_upper = mid + 2 * std
    bb_lower = mid - 2 * std
    
    # KDJ(9,3,3)
    k_vals = [50]
    d_vals = [50]
    for i in range(1, n):
        lo = min(lows[max(0, i-8):i+1])
        hi = max(highs[max(0, i-8):i+1])
        rsv = (closes[i] - lo) / (hi - lo) * 100 if hi != lo else 50
        k = rsv * (1/3) + k_vals[-1] * (2/3)
        d = k * (1/3) + d_vals[-1] * (2/3)
        k_vals.append(k)
        d_vals.append(d)
    k, d, j = k_vals[-1], d_vals[-1], 3 * k_vals[-1] - 2 * d_vals[-1]
    
    # ATR(14)
    trs = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atr = sum(trs[-14:]) / 14
    
    # Vegas Channel
    ema144 = ema(closes, 144)[-1]
    ema169 = ema(closes, 169)[-1]
    
    # Volume Ratio
    vol_now = vols[-1]
    vol_ma20 = sum(vols[-20:]) / 20
    vol_ratio = vol_now / vol_ma20 if vol_ma20 > 0 else 0
    
    # 判断信号
    ma_status = "多头" if ma20 > ma50 else "空头"
    macd_signal = "金叉" if dif[-1] > dea[-1] else "死叉"
    macd_pos = "零上" if dif[-1] > 0 else "零下"
    bb_pos = "上轨" if price > bb_upper else ("下轨" if price < bb_lower else "中轨")
    kdj_signal = "金叉" if k > d else "死叉"
    j_status = "超买" if j > 100 else ("超卖" if j < 0 else "正常")
    
    print(f'\n=== [{tf.upper()}] Price: {price:,.1f} ===')
    ma200_str = f'{ma200:,.0f}' if ma200 > 0 else 'N/A'
    print(f'  MA20={ma20:,.0f} MA50={ma50:,.0f} MA200={ma200_str} [{ma_status}]')
    print(f'  RSI={rsi:.1f}')
    print(f'  MACD: DIF={dif[-1]:,.1f} DEA={dea[-1]:,.1f} Hist={macd_hist:.1f} [{macd_pos} {macd_signal}]')
    print(f'  BB: U={bb_upper:,.0f} M={mid:,.0f} L={bb_lower:,.0f} [{bb_pos}]')
    print(f'  KDJ: K={k:.1f} D={d:.1f} J={j:.1f} [{kdj_signal} J={j_status}]')
    print(f'  ATR={atr:,.0f}')
    print(f'  Vegas: 144={ema144:,.0f} 169={ema169:,.0f}')
    print(f'  VolRatio={vol_ratio:.2f}x')
    
    # 最近3根K线
    for i in range(-3, 0):
        o, h, l, cl = opens[i], highs[i], lows[i], closes[i]
        chg = ((cl - o) / o) * 100
        print(f'  C{i}: O={o:,.0f} H={h:,.0f} L={l:,.0f} C={cl:,.0f} ({chg:+.1f}%)')

if __name__ == '__main__':
    print('=' * 60)
    print('BTC/USDT 多周期技术指标 (OKX)')
    print('=' * 60)
    
    tfs = ['1d', '4h', '1h', '15m']
    if len(sys.argv) > 1:
        tfs = [sys.argv[1]]
    
    for tf in tfs:
        calc_indicators(tf)
    
    print('\n' + '=' * 60)
    print('DONE')
