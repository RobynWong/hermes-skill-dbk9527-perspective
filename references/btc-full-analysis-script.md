# BTC 多周期技术指标分析脚本

## 使用方式

```bash
# 推荐：indicators.py（已验证可用）
python3 ~/.hermes/skills/dbk9527-perspective/scripts/indicators.py

# 输出1w/1d/4h/1h/15m全部周期：K线形态、MA、布林、维加斯、MACD、RSI、KDJ、DMI/ADX、ATR、斐波那契、成交量、资金费率、持仓量
```

## ⚠️ 关键注意事项

1. **必须用 `terminal` 执行**，不能用 `execute_code` 沙箱
   - execute_code调ccxt会报 `ModuleNotFoundError: No module named 'ccxt'`

2. **代理配置**：mihomo端口9981

3. **必须用OKX，Binance对中国IP返回451封锁**
   ```python
   exchange = ccxt.okx({
       'proxies': {'https': 'http://127.0.0.1:9981', 'http': 'http://127.0.0.1:9981'}
   })
   # 永续合约格式：'BTC/USDT:USDT'
   ```

4. **CCXT异常处理**：
   - 超时/连接失败：重试1次，仍失败降级到Web搜索
   - API限流（429）：等待10秒后重试
   - 数据异常（价格为0）：跳过该周期，标注缺失

## 备选方案：terminal curl → /tmp → execute_code（无需ccxt）

当 `indicators.py` 不可用或太慢时，用OKX公开API直接拉数据，保存到 `/tmp`，用 `execute_code` 纯Python计算指标（不依赖ccxt）：

```bash
# terminal执行：拉三个周期数据到/tmp
curl -s --proxy http://127.0.0.1:9981 "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=100" -o /tmp/btc_1h.json
curl -s --proxy http://127.0.0.1:9981 "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=4H&limit=100" -o /tmp/btc_4h.json
curl -s --proxy http://127.0.0.1:9981 "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=30" -o /tmp/btc_1d.json
```

```python
# execute_code执行：读取/tmp JSON，纯Python计算所有指标（无需ccxt）
import json, re

def load_candles(path):
    with open(path) as f:
        d = json.load(f)
    rows = d['data']
    # OKX格式：[ts, open, high, low, close, vol, quoteVol...]
    closes = [float(r[4]) for r in rows]
    highs  = [float(r[2]) for r in rows]
    lows   = [float(r[3]) for r in rows]
    vols   = [float(r[5]) for r in rows]
    closes.reverse(); highs.reverse(); lows.reverse(); vols.reverse()
    return closes, highs, lows, vols

c1h, h1h, l1h, v1h = load_candles('/tmp/btc_1h.json')
c4h, h4h, l4h, v4h = load_candles('/tmp/btc_4h.json')
cd,  hd,  ld,  vd  = load_candles('/tmp/btc_1d.json')
```

**注意**：OKX API返回 newest-first 顺序，必须 `.reverse()` 才能得到时间正序。

## 验证记录

- 2026-05-20：indicators.py正常运行，输出完整多周期指标
- 2026-05-20：OKX获取BTC/USDT:USDT永续合约数据成功
- 2026-05-20：terminal curl → /tmp → execute_code 模式验证成功（execute_code无ccxt时的备用方案）

## 历史版本

| 版本 | 说明 |
|------|------|
| v1 | 2026-05-04初版 |
| v2 | 2026-05-20更新：indicators.py已稳定，OKX替换Binance |
