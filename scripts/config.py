# BTC分析脚本统一配置
# 所有btc分析脚本必须从此文件导入配置，禁止硬编码

PROXY = {'https': 'http://127.0.0.1:9981', 'http': 'http://127.0.0.1:9981'}

# OKX永续合约格式（Binance对中国IP返回451，必须用OKX）
EXCHANGE = 'okx'
SYMBOL = 'BTC/USDT:USDT'