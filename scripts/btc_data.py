#!/usr/bin/env python3
"""获取BTC实时行情数据 - 大镖客Skill专用"""
import ccxt
import sys
from datetime import datetime

PROXY = {'https': 'http://127.0.0.1:9981', 'http': 'http://127.0.0.1:9981'}
SYMBOL = 'BTC/USDT'

def get_ticker():
    exchange = ccxt.binance({'proxies': PROXY})
    ticker = exchange.fetch_ticker(SYMBOL)
    print(f"=== BTC/USDT 实时行情 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    print(f"价格: ${ticker['last']:,.2f}")
    print(f"24h涨跌: {ticker['percentage']:+.2f}%")
    print(f"24h最高: ${ticker['high']:,.2f}")
    print(f"24h最低: ${ticker['low']:,.2f}")
    print(f"24h成交量: {ticker['quoteVolume']/1e9:.2f}B USDT")

def get_klines(timeframe='1d', limit=50):
    exchange = ccxt.binance({'proxies': PROXY})
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe, limit=limit)
    close_prices = [c[4] for c in ohlcv]
    
    ma20 = sum(close_prices[-20:]) / 20 if len(close_prices) >= 20 else 0
    ma50 = sum(close_prices[-50:]) / 50 if len(close_prices) >= 50 else 0
    current = close_prices[-1]
    
    print(f"\n=== {timeframe.upper()} K线分析 ===")
    print(f"当前: ${current:,.2f}")
    if ma20: print(f"MA20: ${ma20:,.2f} ({'上方✓' if current > ma20 else '下方▼'})")
    if ma50: print(f"MA50: ${ma50:,.2f} ({'上方✓' if current > ma50 else '下方▼'})")
    print(f"趋势: {'多头' if current > ma20 > ma50 else '空头' if current < ma20 < ma50 else '震荡'}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['1d', '4h', '1h', '15m']:
        get_klines(sys.argv[1])
    else:
        get_ticker()
        get_klines('1d')
        get_klines('4h')
        get_klines('1h')
