#!/usr/bin/env python3
"""
大镖客Skill自检清单
每次优化后运行，确保skill可用

用法：python3 self_check.py
"""
import sys
import os

# 颜色输出
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def ok(msg): print(f"{GREEN}✓{RESET} {msg}")
def fail(msg): print(f"{RED}✗{RESET} {msg}")
def warn(msg): print(f"{YELLOW}⚠{RESET} {msg}")

skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.join(skill_dir, 'scripts')

print("=== 大镖客Skill自检 ===\n")

# 1. 检查scripts完整性
required = ['btc_data.py', 'indicators.py', 'btc_full_analysis.py', 'cpi_checker.py', 'config.py']
print("1. Scripts完整性检查")
for f in required:
    path = os.path.join(scripts_dir, f)
    if os.path.exists(path):
        ok(f)
    else:
        fail(f"缺失: {f}")

# 2. 检查indicators.py配置
print("\n2. indicators.py API配置检查")
with open(os.path.join(scripts_dir, 'indicators.py')) as f:
    content = f.read()
if 'from config import' in content and 'EXCHANGE' in content:
    ok("使用统一config.py配置")
elif 'ccxt.okx' in content and 'BTC/USDT:USDT' in content:
    warn("仍硬编码配置，建议改用config.py")
elif 'binance' in content.lower():
    fail("仍使用Binance API（会451封锁）")
else:
    warn("未检测到明确配置")

# 3. 测试数据获取
print("\n3. 数据获取测试（indicators.py 1d 4h）")
sys.path.insert(0, scripts_dir)
try:
    import indicators
    ok("indicators.py可导入")
except Exception as e:
    fail(f"导入失败: {e}")

# 4. 测试实际数据获取
print("\n4. 实际数据获取测试")
try:
    import ccxt
    from config import PROXY, SYMBOL, EXCHANGE
    ex = getattr(ccxt, EXCHANGE)({'proxies': PROXY})
    ticker = ex.fetch_ticker(SYMBOL)
    price = ticker['last']
    ok(f"获取到当前价: ${price:,.0f}")
except Exception as e:
    fail(f"数据获取失败: {e}")

# 5. 测试消息面获取
print("\n5. 消息面获取测试")
try:
    import subprocess
    result = subprocess.run(['python3', 'scripts/jin10_news.py'], 
                          capture_output=True, text=True, timeout=30, cwd=scripts_dir)
    if result.returncode == 0 and '金十快讯' in result.stdout:
        lines = result.stdout.split('\n')
        for line in lines:
            if '共' in line and '条' in line:
                ok(f"消息面: {line.strip()}")
                break
    else:
        warn("消息面获取异常")
except Exception as e:
    warn(f"消息面获取跳过: {e}")

print("\n=== 自检完成 ===")
print("如有问题请修复后再合并到master")