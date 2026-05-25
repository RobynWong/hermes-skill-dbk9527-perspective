#!/usr/bin/env python3
"""金十快讯采集 + BTC相关筛选
用于大镖客Skill的消息面分析
用法：python3 jin10_news.py [--hours 8] [--category all] [--limit 20]
"""
import json, urllib.request, urllib.parse, re, sys, argparse
from datetime import datetime, timedelta
from collections import defaultdict

# === 金十API配置 ===
JIN10_URL = 'https://flash-api.jin10.com/get_flash_list'
JIN10_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'x-app-id': 'bVBF4FyRTn5NJF5n',
    'x-version': '1.0.0'
}

# === 关键词配置 ===
CATEGORIES = {
    '地缘': ['伊朗', '特朗普', '关税', '制裁', '战争', '中东', '霍尔木兹', '革命卫队', '停火', '冲突', '地缘', '美军', '以色列', '俄乌', '台湾', '台海', '中美', '中美关系'],
    '宏观/美联储': ['美联储', '降息', '加息', '利率', 'CPI', '通胀', 'PCE', '鲍威尔', '沃什', '就业', '非农', 'GDP', '衰退', '美元', 'DXY', '国债', '收益率'],
    'ETF/机构': ['ETF', '贝莱德', '富达', '微策略', 'MicroStrategy', '桥水', '桥水基金', '机构', '资金流向', '净流入', '净流出', '持仓'],
    '链上/市场': ['巨鲸', '链上', '交易所', '清算', '爆仓', '杠杆', '资金费率', '持仓量', 'OI', '矿工', '算力', '减半', '比特币', 'BTC', '加密', 'Crypto'],
    '监管/政策': ['SEC', 'CFTC', '监管', '禁令', '合法', '法案', '财政部', '白宫', '财政部'],
    '其他重要': ['黑天鹅', '崩盘', '暴跌', '暴涨', '熔断', '恐慌', 'VIX', '黄金', '原油', '美股', '纳斯达克']
}

BTC_KEYWORDS = ['BTC', '比特币', '加密', 'Crypto', '加密货币', '以太坊', 'ETH', '山寨', 'SOL', 'DOGE', 'XRP', 'BNB', '链上', 'DeFi', 'Uniswap', 'NFT', '数字资产', '数字货币', '币安', 'Coinbase', 'MicroStrategy', '微策略', '灰度', 'Grayscale']

def clean_html(html):
    """清洗HTML标签"""
    if not html:
        return ''
    text = html.replace('<br/>', '\n').replace('<br>', '\n')
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return text.strip()

def fetch_jin10(max_time=None, channel='-8200', limit=50):
    """获取金十快讯"""
    params = f'channel={channel}&vip=1'
    if max_time:
        params += f'&max_time={urllib.parse.quote(max_time)}'
    
    url = f'{JIN10_URL}?{params}'
    req = urllib.request.Request(url, headers=JIN10_HEADERS)
    
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get('status') != 200:
            print(f'⚠️ API返回状态码: {data.get("status")}')
            return []
        return data.get('data', [])
    except Exception as e:
        print(f'❌ 请求失败: {e}')
        return []

def classify_news(content, title=''):
    """分类新闻内容"""
    text = (title or '') + content
    categories = []
    for cat, keywords in CATEGORIES.items():
        if any(kw in text for kw in keywords):
            categories.append(cat)
    return categories if categories else ['其他']

def is_btc_related(content, title=''):
    """判断是否与BTC/加密相关"""
    text = (title or '') + content
    return any(kw in text for kw in BTC_KEYWORDS + ['BTC', 'btc', 'Bitcoin'])

def filter_important(items, hours=24, btc_only=False):
    """筛选重要新闻"""
    cutoff = datetime.now() - timedelta(hours=hours)
    filtered = []
    
    for item in items:
        try:
            t_str = item.get('time', '')
            t = datetime.strptime(t_str, '%Y-%m-%d %H:%M:%S')
            if t < cutoff:
                continue
        except:
            pass
        
        content = clean_html(item.get('data', {}).get('content', ''))
        title = item.get('data', {}).get('title', '')
        important = item.get('important', False)
        
        if btc_only and not is_btc_related(content, title):
            continue
        
        cats = classify_news(content, title)
        
        filtered.append({
            'time': t_str,
            'important': important,
            'content': content,
            'title': title,
            'categories': cats
        })
    
    return filtered

def print_structured(items, btc_only=False):
    """结构化输出"""
    if not items:
        print('📭 没有符合条件的新闻')
        return
    
    # 按类别分组
    grouped = defaultdict(list)
    for item in items:
        for cat in item['categories']:
            grouped[cat].append(item)
    
    # 输出
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'\n=== 金十快讯 | {now} ===')
    if btc_only:
        print('（已筛选BTC/加密相关）')
    print(f'共 {len(items)} 条\n')
    
    for cat in ['地缘', '宏观/美联储', 'ETF/机构', '链上/市场', '监管/政策', '其他重要', '其他']:
        cat_items = grouped.get(cat, [])
        if not cat_items:
            continue
        
        print(f'--- [{cat}] ({len(cat_items)}条) ---')
        for item in cat_items:
            imp = '⭐' if item['important'] else '  '
            print(f'  {imp} [{item["time"]}] {item["content"][:150]}')
        print()
    
    # 因果链建议
    print('--- 消息面串联建议（大镖客模型10）---')
    print('检查是否有以下因果链：')
    geo_items = grouped.get('地缘', [])
    macro_items = grouped.get('宏观/美联储', [])
    etf_items = grouped.get('ETF/机构', [])
    
    if geo_items:
        print(f'  • 地缘事件可能影响市场情绪（当前{len(geo_items)}条地缘新闻）')
    if macro_items:
        print(f'  • 宏观政策可能影响流动性（当前{len(macro_items)}条宏观新闻）')
    if etf_items:
        print(f'  • ETF资金流可能影响价格（当前{len(etf_items)}条ETF/机构新闻）')
    
    # 检查是否有矛盾
    if geo_items and etf_items:
        print('  ⚠️ 地缘消息与ETF资金流可能矛盾，注意市场解读')
    
    print()
    print('💡 使用建议：将上述新闻按"第一脚→续命→临门一脚"的因果链串联')
    print('   例：地缘降温踢第一脚→机构资金续命→特朗普回应临门一脚')

def main():
    parser = argparse.ArgumentParser(description='金十快讯采集 + BTC筛选')
    parser.add_argument('--hours', type=int, default=24, help='获取最近N小时的数据 (默认24)')
    parser.add_argument('--btc-only', action='store_true', help='只显示BTC/加密相关')
    parser.add_argument('--limit', type=int, default=50, help='最多显示条数 (默认50)')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    args = parser.parse_args()
    
    # 获取数据（不过滤BTC，让AI判断相关性）
    news_items = fetch_jin10()
    if not news_items:
        print('📭 没有获取到数据')
        return
    
    # 筛选
    filtered = filter_important(news_items, hours=args.hours, btc_only=args.btc_only)
    
    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    else:
        print_structured(filtered[:args.limit], btc_only=args.btc_only)

if __name__ == '__main__':
    main()