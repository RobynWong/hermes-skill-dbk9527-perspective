#!/usr/bin/env python3
"""大镖客BTC实时技术分析 - OKX数据源"""
import ccxt, math, sys

okx = ccxt.okx({'proxies': {'https': 'http://127.0.0.1:9981', 'http': 'http://127.0.0.1:9981'}})

def ema(data, span):
    k = 2/(span+1); r = [data[0]]
    for d in data[1:]: r.append(d*k + r[-1]*(1-k))
    return r

def calc(tf, limit=250):
    ohlcv = okx.fetch_ohlcv('BTC/USDT:USDT', tf, limit=limit)
    c = [x[4] for x in ohlcv]; h = [x[2] for x in ohlcv]; l = [x[3] for x in ohlcv]
    o = [x[1] for x in ohlcv]; v = [x[5] for x in ohlcv]
    n = len(c); price = c[-1]
    ma20 = sum(c[-20:])/20; ma50 = sum(c[-50:])/50
    ma120 = sum(c[-120:])/120 if n >= 120 else 0
    ma200 = sum(c[-200:])/200 if n >= 200 else 0
    # RSI
    deltas = [c[i]-c[i-1] for i in range(1,n)]
    gains = [d if d>0 else 0 for d in deltas]; losses = [-d if d<0 else 0 for d in deltas]
    ag = sum(gains[-14:])/14; al = sum(losses[-14:])/14
    rs = ag/al if al>0 else 100; rsi = 100-(100/(1+rs))
    # MACD
    e12 = ema(c,12); e26 = ema(c,26)
    dif = [e12[i]-e26[i] for i in range(n)]; dea = ema(dif,9)
    macd_hist = 2*(dif[-1]-dea[-1])
    # BB
    mid = sum(c[-20:])/20; std = math.sqrt(sum((x-mid)**2 for x in c[-20:])/20)
    bb_u = mid+2*std; bb_l = mid-2*std
    # KDJ
    kv=[50]; dv=[50]
    for i in range(1,n):
        lo=min(l[max(0,i-8):i+1]); hi=max(h[max(0,i-8):i+1])
        r=(c[i]-lo)/(hi-lo)*100 if hi!=lo else 50
        k_val=r*(1/3)+kv[-1]*(2/3); d_val=k_val*(1/3)+dv[-1]*(2/3)
        kv.append(k_val); dv.append(d_val)
    k_val,d_val,j_val = kv[-1],dv[-1],3*kv[-1]-2*dv[-1]
    # ATR
    trs = [max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)]
    atr = sum(trs[-14:])/14
    # Vegas
    ema144 = ema(c,144)[-1]; ema169 = ema(c,169)[-1]
    # DMI
    plus_dm=[]; minus_dm=[]; tr_list=[]
    for i in range(1,n):
        up=h[i]-h[i-1]; down=l[i-1]-l[i]
        plus_dm.append(up if up>down and up>0 else 0)
        minus_dm.append(down if down>up and down>0 else 0)
        tr_list.append(max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])))
    atr14=sum(tr_list[:14])/14 if len(tr_list)>=14 else sum(tr_list)/len(tr_list)
    pdi_s=sum(plus_dm[-14:]); mdi_s=sum(minus_dm[-14:])
    plus_di=100*pdi_s/(14*atr14) if atr14>0 else 0
    minus_di=100*mdi_s/(14*atr14) if atr14>0 else 0
    dx=100*abs(plus_di-minus_di)/(plus_di+minus_di) if (plus_di+minus_di)>0 else 0
    # Vol
    vr = v[-1]/sum(v[-20:])*20 if sum(v[-20:])>0 else 0

    print(f'\n=== [{tf.upper()}] Price: {price:,.1f} ===')
    ma120_s = f'{ma120:,.0f}' if ma120 > 0 else '0'
    ma200_s = f'{ma200:,.0f}' if ma200 > 0 else '0'
    print(f'  MA20={ma20:,.0f} MA50={ma50:,.0f} MA120={ma120_s} MA200={ma200_s}')
    print(f'  RSI={rsi:.1f} | MACD DIF={dif[-1]:,.1f} DEA={dea[-1]:,.1f} Hist={macd_hist:.1f}')
    print(f'  BB U={bb_u:,.0f} M={mid:,.0f} L={bb_l:,.0f} Width={2*std/mid*100:.1f}%')
    print(f'  KDJ K={k_val:.1f} D={d_val:.1f} J={j_val:.1f} | ATR={atr:,.0f}')
    print(f'  Vegas 144={ema144:,.0f} 169={ema169:,.0f} | VolRatio={vr:.2f}x')
    print(f'  DMI +DI={plus_di:.1f} -DI={minus_di:.1f} ADX={dx:.1f}')
    # Recent 5 candles
    print(f'  Recent 5 candles:')
    for i in range(-5,0):
        body = c[i]-o[i]
        direction = '阳' if body>0 else '阴' if body<0 else '十'
        upper_w = h[i]-max(o[i],c[i])
        lower_w = min(o[i],c[i])-l[i]
        print(f'    {direction} O={o[i]:,.0f} H={h[i]:,.0f} L={l[i]:,.0f} C={c[i]:,.0f} V={v[i]:,.0f}')

    # Fibonacci (1d only)
    if tf == '1d':
        swing_h = max(h[-60:]); swing_l = min(l[-60:])
        diff = swing_h - swing_l
        fib_382 = swing_h - diff*0.382
        fib_5 = swing_h - diff*0.5
        fib_618 = swing_h - diff*0.618
        fib_786 = swing_h - diff*0.786
        print(f'  Fibonacci (60日波段): H={swing_h:,.0f} L={swing_l:,.0f}')
        print(f'    0.382={fib_382:,.0f} 0.5={fib_5:,.0f} 0.618={fib_618:,.0f} 0.786={fib_786:,.0f}')
    return price

# Ticker info
ticker = okx.fetch_ticker('BTC/USDT:USDT')
print(f'=== BTC/USDT Ticker ===')
print(f'  Price: {ticker["last"]:,.1f}')
print(f'  24h Change: {ticker["percentage"]:+.2f}%')
print(f'  24h High: {ticker.get("high", "N/A")}')
print(f'  24h Low: {ticker.get("low", "N/A")}')
vol = ticker.get("quoteVolume")
print(f'  24h Vol(USDT): {vol:,.0f}' if vol else '  24h Vol(USDT): N/A')
if 'fundingRate' in ticker and ticker['fundingRate'] is not None:
    print(f'  Funding Rate: {ticker["fundingRate"]*100:.4f}%')

# Try to get funding rate separately
try:
    fr = okx.fetch_funding_rate('BTC/USDT:USDT')
    if fr:
        print(f'  Funding Rate (API): {fr.get("fundingRate", "N/A")}')
except:
    pass

# Try OI
try:
    oi = okx.fetch_open_interest('BTC/USDT:USDT')
    if oi:
        print(f'  Open Interest: {oi.get("openInterestAmount", "N/A")}')
except:
    pass

for tf in ['1d','4h','1h','15m']:
    try:
        calc(tf)
    except Exception as e:
        print(f'Error on {tf}: {e}')
