#!/usr/bin/env python3
"""BTC ETF资金流数据获取
使用多个数据源获取BTC ETF资金流信息
用法：python3 etf_flow.py [--days 7]
"""
import json, urllib.request, urllib.parse, re, sys, os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jin10_news import fetch_jin10, filter_important

def fetch_etf_from_news(days=7):
    """从金十新闻中提取ETF相关信息"""
    news_items = fetch_jin10()
    if not news_items:
        return None
    
    filtered = filter_important(news_items, hours=days*24, btc_only=False)
    
    etf_news = []
    for item in filtered:
        content = item.get('content', '') + item.get('title', '')
        if any(kw in content for kw in ['ETF', '贝莱德', '富达', '资金流向', '净流入', '净流出', '灰度']):
            etf_news.append(item)
    
    if not etf_news:
        return None
    
    # 提取资金流信息
    flows = []
    for item in etf_news:
        content = item.get('content', '')
        # 尝试提取数字
        numbers = re.findall(r'[\d.]+[亿百万]', content)
        if numbers:
            flows.append({
                'time': item.get('time', ''),
                'content': content[:100],
                'numbers': numbers
            })
    
    return {
        'news_count': len(etf_news),
        'flows': flows,
        'latest': etf_news[0] if etf_news else None
    }

def format_etf_for_dbk(etf_data):
    """格式化为大镖客风格"""
    if not etf_data:
        return "📭 无ETF资金流数据"
    
    lines = []
    lines.append("=== ETF资金流分析 ===")
    lines.append(f"相关新闻: {etf_data['news_count']}条")
    lines.append("")
    
    if etf_data.get('latest'):
        latest = etf_data['latest']
        lines.append(f"【最新ETF新闻】")
        lines.append(f"  时间: {latest.get('time', '')}")
        lines.append(f"  内容: {latest.get('content', '')[:120]}")
        lines.append("")
    
    if etf_data.get('flows'):
        lines.append("【资金流数据】")
        for flow in etf_data['flows'][:5]:
            lines.append(f"  [{flow['time']}] {' | '.join(flow['numbers'])}")
            lines.append(f"    {flow['content'][:80]}")
        lines.append("")
    
    lines.append("💡 大镖客使用建议：")
    lines.append("  • 将ETF资金流纳入消息面分析，作为机构行为的证据")
    lines.append("  • 连续流入+价格上涨=健康上涨；连续流入+价格下跌=机构接盘")
    lines.append("  • 资金流逆转往往是趋势转变的先行指标")
    
    return '\n'.join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='BTC ETF资金流数据获取')
    parser.add_argument('--days', type=int, default=7, help='获取最近N天数据')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    args = parser.parse_args()
    
    print(f"📊 正在获取BTC ETF资金流数据（最近{args.days}天）...")
    
    etf_data = fetch_etf_from_news(days=args.days)
    
    if args.json:
        print(json.dumps(etf_data, ensure_ascii=False, indent=2) if etf_data else "null")
    else:
        print(format_etf_for_dbk(etf_data))

if __name__ == '__main__':
    main()
