#!/usr/bin/env python3
"""消息面因果链自动提取
基于金十快讯数据，自动识别消息之间的因果关系
用法：python3 news_causality.py [--hours 8]
"""
import json, sys, os, re
from datetime import datetime, timedelta
from collections import defaultdict

# 导入金十脚本的函数
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jin10_news import fetch_jin10, filter_important, clean_html

# 因果链模式定义
CAUSAL_PATTERNS = {
    '地缘升级': {
        'trigger': ['伊朗', '以色列', '特朗普', '霍尔木兹', '战争', '冲突', '袭击', '制裁'],
        'effect': ['油价', '黄金', '避险', '通胀', '供应链'],
        'weight': 3
    },
    '美联储政策': {
        'trigger': ['美联储', '利率', '降息', '加息', '鲍威尔', '点阵图', 'CPI', 'PCE'],
        'effect': ['美元', '流动性', '国债', '股市', 'BTC'],
        'weight': 3
    },
    'ETF资金流': {
        'trigger': ['ETF', '贝莱德', '富达', '资金流向', '净流入', '净流出'],
        'effect': ['BTC价格', '机构持仓', '市场情绪'],
        'weight': 2
    },
    '监管政策': {
        'trigger': ['SEC', 'CFTC', '监管', '禁令', '法案', '财政部'],
        'effect': ['交易所', '合规', '机构入场', '市场恐慌'],
        'weight': 2
    },
    '宏观经济': {
        'trigger': ['GDP', '就业', '非农', '衰退', 'PMI', '消费'],
        'effect': ['美联储政策', '市场情绪', '风险资产'],
        'weight': 2
    }
}

def extract_causal_chains(news_items, hours=8):
    """提取因果链"""
    if not news_items:
        return []
    
    # 按时间排序
    sorted_news = sorted(news_items, key=lambda x: x.get('time', ''))
    
    chains = []
    
    # 识别因果链模式
    for pattern_name, pattern in CAUSAL_PATTERNS.items():
        trigger_news = []
        effect_news = []
        
        for item in sorted_news:
            content = item.get('content', '') + item.get('title', '')
            
            # 检查是否匹配触发词
            if any(kw in content for kw in pattern['trigger']):
                trigger_news.append(item)
            
            # 检查是否匹配影响词
            if any(kw in content for kw in pattern['effect']):
                effect_news.append(item)
        
        # 如果有触发和影响，构建因果链
        if trigger_news and effect_news:
            chain = {
                'pattern': pattern_name,
                'weight': pattern['weight'],
                'triggers': trigger_news[:3],  # 最多3个触发事件
                'effects': effect_news[:3],    # 最多3个影响事件
                'timeline': []
            }
            
            # 构建时间线
            all_events = trigger_news + effect_news
            all_events.sort(key=lambda x: x.get('time', ''))
            
            for event in all_events[:5]:
                content = clean_html(event.get('content', ''))
                chain['timeline'].append({
                    'time': event.get('time', ''),
                    'important': event.get('important', False),
                    'content': content[:100]
                })
            
            chains.append(chain)
    
    return chains

def format_chain_for_dbk(chains):
    """格式化为大镖客风格的因果链输出"""
    if not chains:
        return "📭 未识别到明显因果链"
    
    lines = []
    lines.append("=== 消息面因果链分析（模型10）===")
    lines.append("")
    
    # 按权重排序
    chains.sort(key=lambda x: x['weight'], reverse=True)
    
    for i, chain in enumerate(chains, 1):
        lines.append(f"【因果链{i}】{chain['pattern']} (权重: {chain['weight']})")
        lines.append("")
        
        # 第一脚（触发事件）
        if chain['triggers']:
            first = chain['triggers'][0]
            content = first.get('content', '')[:80]
            lines.append(f"🦶 第一脚（触发）: [{first.get('time', '')}] {content}")
        
        # 续命/发展
        if len(chain['timeline']) > 2:
            for event in chain['timeline'][1:-1]:
                lines.append(f"🔗 发展: [{event['time']}] {event['content']}")
        
        # 临门一脚（最新影响）
        if chain['effects']:
            last = chain['effects'][-1]
            content = last.get('content', '')[:80]
            lines.append(f"🎯 临门一脚: [{last.get('time', '')}] {content}")
        
        lines.append("")
        if chain['timeline']:
            lines.append(f"因果逻辑: {' → '.join([e['content'][:30] for e in chain['timeline'][:3]])}")
        lines.append("")
        lines.append("-" * 50)
        lines.append("")
    
    # 总结
    lines.append("【综合判断】")
    total_weight = sum(c['weight'] for c in chains)
    if total_weight >= 6:
        lines.append("消息面影响强度: 🔴 高（多条重要因果链叠加）")
    elif total_weight >= 3:
        lines.append("消息面影响强度: 🟡 中（有明确因果链）")
    else:
        lines.append("消息面影响强度: 🟢 低（影响有限）")
    
    lines.append("")
    lines.append("💡 大镖客使用建议：")
    lines.append("  • 将因果链融入分析开头，说明当前行情的消息面驱动")
    lines.append("  • 用\"说白了就是...\"串联因果链，像讲故事一样")
    lines.append("  • 注意消息面与技术面的共振/背离")
    
    return '\n'.join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='消息面因果链自动提取')
    parser.add_argument('--hours', type=int, default=8, help='时间范围（小时）')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    args = parser.parse_args()
    
    # 获取数据
    news_items = fetch_jin10()
    if not news_items:
        print('📭 没有获取到数据')
        return
    
    # 筛选
    filtered = filter_important(news_items, hours=args.hours, btc_only=False)
    
    # 提取因果链
    chains = extract_causal_chains(filtered, hours=args.hours)
    
    if args.json:
        print(json.dumps(chains, ensure_ascii=False, indent=2))
    else:
        print(format_chain_for_dbk(chains))

if __name__ == '__main__':
    main()
