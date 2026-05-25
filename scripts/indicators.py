#!/usr/bin/env python3
"""
BTC多周期完整技术指标计算工具
覆盖：K线形态/MA/布林带/维加斯通道/MACD/RSI/KDJ/DMI-ADX/ATR/斐波那契/成交量/资金费率/持仓量
用法：python3 indicators.py [timeframes...] 
  默认: 1w 1d 4h 1h 15m
  示例: python3 indicators.py 1d 4h 1h
依赖：ccxt, numpy (pip install ccxt numpy)
代理：mihomo端口9981
"""
import sys
import numpy as np
from datetime import datetime
import os

# 统一配置（禁止硬编码）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import PROXY, SYMBOL, EXCHANGE

try:
    import ccxt
except ImportError:
    print("ERROR: ccxt not installed. Run: pip install ccxt numpy")
    sys.exit(1)

exchange = getattr(ccxt, EXCHANGE)({'proxies': PROXY})


def calc_ema(data, period):
    if len(data) < period:
        period = len(data)
    ema = float(np.mean(data[:period]))
    for price in data[period:]:
        ema = (price - ema) * (2 / (period + 1)) + ema
    return ema


def calc_rsi(closes, period=14):
    diffs = np.diff(closes)
    ups = np.where(diffs > 0, diffs, 0.0)
    downs = np.where(diffs < 0, -diffs, 0.0)
    avg_up = float(np.mean(ups[-period:]))
    avg_down = float(np.mean(downs[-period:]))
    if avg_down == 0:
        return 100.0
    return 100 - 100 / (1 + avg_up / avg_down)


def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return 0, 0, 0
    difs = []
    ema_f = float(np.mean(closes[:fast]))
    ema_s = float(np.mean(closes[:slow]))
    for i in range(slow, len(closes)):
        if i >= fast:
            ema_f = (closes[i] - ema_f) * (2 / (fast + 1)) + ema_f
        ema_s = (closes[i] - ema_s) * (2 / (slow + 1)) + ema_s
        difs.append(ema_f - ema_s)
    if len(difs) < signal:
        return difs[-1] if difs else 0, difs[-1] if difs else 0, 0
    dea = calc_ema(np.array(difs), signal)
    bar = 2 * (difs[-1] - dea)
    return difs[-1], dea, bar


def calc_boll(closes, period=20, std_mult=2):
    if len(closes) < period:
        period = len(closes)
    ma = float(np.mean(closes[-period:]))
    std = float(np.std(closes[-period:]))
    return ma + std_mult * std, ma, ma - std_mult * std, std_mult * 2 * std


def calc_atr(highs, lows, closes, period=14):
    trs = np.maximum(highs[1:] - lows[1:],
                     np.maximum(np.abs(highs[1:] - closes[:-1]),
                                np.abs(lows[1:] - closes[:-1])))
    if len(trs) < period:
        return float(np.mean(trs))
    return float(np.mean(trs[-period:]))


def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    if len(closes) < n:
        return 50, 50, 50
    k = 50.0
    d = 50.0
    for i in range(n - 1, len(closes)):
        ln = float(np.min(lows[i - n + 1:i + 1]))
        hn = float(np.max(highs[i - n + 1:i + 1]))
        rsv = (closes[i] - ln) / (hn - ln) * 100 if hn != ln else 50
        k = (2 / m1) * rsv + (1 - 2 / m1) * k
        d = (2 / m2) * k + (1 - 2 / m2) * d
    j = 3 * k - 2 * d
    return k, d, j


def calc_dmi(highs, lows, closes, period=14):
    if len(closes) < period * 2:
        return 0, 0, 0
    plus_dms, minus_dms, trs_list = [], [], []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        pdm = up if up > down and up > 0 else 0
        mdm = down if down > up and down > 0 else 0
        plus_dms.append(pdm)
        minus_dms.append(mdm)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs_list.append(tr)
    plus_dms = np.array(plus_dms)
    minus_dms = np.array(minus_dms)
    trs_arr = np.array(trs_list)
    s_pdm = float(np.mean(plus_dms[:period]))
    s_mdm = float(np.mean(minus_dms[:period]))
    s_tr = float(np.mean(trs_arr[:period]))
    for i in range(period, len(plus_dms)):
        s_pdm = (s_pdm * (period - 1) + plus_dms[i]) / period
        s_mdm = (s_mdm * (period - 1) + minus_dms[i]) / period
        s_tr = (s_tr * (period - 1) + trs_arr[i]) / period
    plus_di = 100 * s_pdm / s_tr if s_tr > 0 else 0
    minus_di = 100 * s_mdm / s_tr if s_tr > 0 else 0
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    adx = dx
    return plus_di, minus_di, adx


def calc_vegas(closes):
    v144 = calc_ema(closes, 144) if len(closes) >= 20 else float(closes[-1])
    v169 = calc_ema(closes, 169) if len(closes) >= 20 else float(closes[-1])
    v576 = calc_ema(closes, 576) if len(closes) >= 576 else None
    v676 = calc_ema(closes, 676) if len(closes) >= 676 else None
    return v144, v169, v576, v676


def identify_candlestick(opens, closes, highs, lows, i):
    """识别单根K线形态"""
    body = closes[i] - opens[i]
    upper_w = highs[i] - max(closes[i], opens[i])
    lower_w = min(closes[i], opens[i]) - lows[i]
    body_pct = abs(body) / closes[i] * 100
    if body_pct < 0.15:
        return "十字星"
    elif body > 0:
        if upper_w > abs(body) * 2:
            return "射击之星"
        elif lower_w > abs(body) * 2:
            return "锤子线"
        else:
            return f"阳线({body_pct:.1f}%)"
    else:
        if lower_w > abs(body) * 2:
            return "倒锤"
        elif upper_w > abs(body) * 2:
            return "上影阴线"
        else:
            return f"阴线({body_pct:.1f}%)"


def fetch_funding_and_oi():
    """获取资金费率和持仓量"""
    print("\n" + "=" * 70)
    print("资金费率 & 持仓量")
    print("=" * 70)
    try:
        # OKX获取资金费率 via fetch_funding_rate
        funding = exchange.fetch_funding_rate(SYMBOL)
        if funding:
            rate = float(funding['fundingRate']) * 100
            next_funding = funding.get('nextFundingTime', 0)
            ts_str = datetime.fromtimestamp(next_funding / 1000).strftime('%m-%d %H:%M') if next_funding else 'N/A'
            print(f"  当前资金费率: {rate:+.4f}% (下次: {ts_str})")
        else:
            print("  资金费率获取失败")
    except Exception as e:
        print(f"  资金费率获取失败: {e}")


def analyze_timeframe(tf, limit):
    """分析单个时间周期"""
    ohlcv = exchange.fetch_ohlcv(SYMBOL, tf, limit=limit)
    closes = np.array([float(k[4]) for k in ohlcv], dtype=float)
    highs = np.array([float(k[2]) for k in ohlcv], dtype=float)
    lows = np.array([float(k[3]) for k in ohlcv], dtype=float)
    volumes = np.array([float(k[5]) for k in ohlcv], dtype=float)
    opens_arr = np.array([float(k[1]) for k in ohlcv], dtype=float)

    last_ts = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
    print(f"\n{'=' * 70}")
    print(f"[{tf}] 最新K线: {last_ts} | 价格: {closes[-1]:,.0f}")
    print(f"{'=' * 70}")

    # K线形态
    print("  -- K线形态(近5根) --")
    for i in range(-5, 0):
        pattern = identify_candlestick(opens_arr, closes, highs, lows, i)
        ts_i = datetime.fromtimestamp(ohlcv[i][0] / 1000)
        print(f"    {ts_i}: O={opens_arr[i]:,.0f} H={highs[i]:,.0f} L={lows[i]:,.0f} C={closes[i]:,.0f} → {pattern}")

    # MA均线
    ma20 = calc_ema(closes, 20)
    ma50 = calc_ema(closes, 50)
    ma120 = calc_ema(closes, 120) if len(closes) >= 120 else None
    ma200 = calc_ema(closes, 200) if len(closes) >= 200 else None
    print("  -- MA均线 --")
    print(f"    MA20={ma20:,.0f} {'上方' if closes[-1] > ma20 else '下方'} | MA50={ma50:,.0f} {'上方' if closes[-1] > ma50 else '下方'}", end="")
    if ma120:
        print(f" | MA120={ma120:,.0f} {'上方' if closes[-1] > ma120 else '下方'}", end="")
    if ma200:
        print(f" | MA200={ma200:,.0f} {'上方' if closes[-1] > ma200 else '下方'}", end="")
    print()
    arr = "多头排列" if ma20 > ma50 and (ma120 is None or ma50 > ma120) else ("空头排列" if ma20 < ma50 else "交叉")
    print(f"    排列: {arr}")

    # 布林带
    boll_u, boll_m, boll_l, boll_w = calc_boll(closes)
    pos = "上轨区" if closes[-1] > boll_m + (boll_u - boll_m) * 0.7 else (
        "下轨区" if closes[-1] < boll_m - (boll_m - boll_l) * 0.7 else "中轨区")
    print("  -- 布林带(20,2) --")
    print(f"    上={boll_u:,.0f} 中={boll_m:,.0f} 下={boll_l:,.0f} 宽={boll_w:,.0f} 位置={pos}")

    # 维加斯通道
    if tf in ['1d', '4h', '1h']:
        v144, v169, v576, v676 = calc_vegas(closes)
        vu = max(v144, v169)
        vl = min(v144, v169)
        vp = "上方多头" if closes[-1] > vu else ("下方空头" if closes[-1] < vl else "通道内")
        print("  -- 维加斯通道 --")
        print(f"    EMA144={v144:,.0f} EMA169={v169:,.0f}", end="")
        if v576:
            print(f" EMA576={v576:,.0f}", end="")
        if v676:
            print(f" EMA676={v676:,.0f}", end="")
        print(f" | 通道={vl:,.0f}-{vu:,.0f} 价格{vp}")

    # MACD
    dif, dea, bar = calc_macd(closes)
    macd_pos = "零上" if dif > 0 else "零下"
    cross = "金叉" if dif > dea else "死叉"
    print("  -- MACD(12,26,9) --")
    print(f"    DIF={dif:.1f} DEA={dea:.1f} 柱={bar:.1f} | {macd_pos} {cross}")

    # RSI
    rsi = calc_rsi(closes)
    rsi_s = "超买" if rsi > 70 else ("超卖" if rsi < 30 else ("偏多" if rsi > 50 else "偏空"))
    print("  -- RSI(14) --")
    print(f"    RSI={rsi:.1f} {rsi_s}")

    # KDJ
    k, d, j = calc_kdj(highs, lows, closes)
    j_s = "超买" if j > 100 else ("超卖" if j < 0 else "正常")
    print("  -- KDJ(9,3,3) --")
    print(f"    K={k:.1f} D={d:.1f} J={j:.1f} | {'金叉' if k > d else '死叉'} J={j_s}")

    # DMI/ADX
    pdi, mdi, adx = calc_dmi(highs, lows, closes)
    trend_s = "强趋势" if adx > 25 else ("弱趋势" if adx < 20 else "趋势形成中")
    dir_s = "多头" if pdi > mdi else "空头"
    print("  -- DMI/ADX(14) --")
    print(f"    +DI={pdi:.1f} -DI={mdi:.1f} ADX={adx:.1f} | {dir_s}主导 {trend_s}")

    # ATR
    atr = calc_atr(highs, lows, closes)
    print("  -- ATR(14) --")
    print(f"    ATR={atr:,.0f} ({atr / closes[-1] * 100:.2f}%)")

    # 斐波那契
    n_bars = min(100, len(closes))
    sh = float(np.max(highs[-n_bars:]))
    sl = float(np.min(lows[-n_bars:]))
    diff = sh - sl
    print("  -- 斐波那契回撤 --")
    print(f"    高={sh:,.0f} 低={sl:,.0f}")
    print(f"    0.382={sh - diff * 0.382:,.0f} 0.5={sh - diff * 0.5:,.0f} 0.618={sh - diff * 0.618:,.0f} 0.786={sh - diff * 0.786:,.0f}")

    # 成交量
    vol_ma5 = float(np.mean(volumes[-5:]))
    vol_ma20 = float(np.mean(volumes[-20:]))
    vr = volumes[-1] / vol_ma20 if vol_ma20 > 0 else 1
    vol_s = "放量" if vr > 1.5 else ("缩量" if vr < 0.6 else "正常")
    print("  -- 成交量 --")
    print(f"    当前={volumes[-1]:,.0f} MA5={vol_ma5:,.0f} MA20={vol_ma20:,.0f} 量比={vr:.2f}x {vol_s}")


def main():
    default_tfs = {'1w': 52, '1d': 200, '4h': 200, '1h': 200, '15m': 100}
    if len(sys.argv) > 1:
        tfs = {tf: default_tfs.get(tf, 100) for tf in sys.argv[1:]}
    else:
        tfs = default_tfs

    print("=" * 70)
    print("BTC/USDT 完整技术分析 - 多周期指标")
    print("=" * 70)

    # 先获取资金费率和持仓量
    fetch_funding_and_oi()

    # 逐周期分析
    for tf, limit in tfs.items():
        try:
            analyze_timeframe(tf, limit)
        except Exception as e:
            print(f"\n[{tf}] 分析失败: {e}")

    print(f"\n{'=' * 70}")
    print("DONE")


if __name__ == '__main__':
    main()
