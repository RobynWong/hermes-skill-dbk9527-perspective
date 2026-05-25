#!/usr/bin/env python3
"""大镖客BTC完整分析脚本 - 集成消息面+技术指标
用法：python3 btc_full_analysis.py [--hours 4] [--btc-only]
"""
import subprocess, json, sys, os, math
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cpi_checker():
    """检查CPI/PPI发布状态（v4: 本地记录优先）
    
    v4核心变更：先读本地cpi_records.json，有记录直接返回，不查不问。
    本月无记录才走API→日期推断的降级路径。
    """
    print("📅 正在检查CPI数据...")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'cpi_checker.py'), '--json']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        # 解析JSON输出
        cpi_info = None
        try:
            cpi_info = json.loads(result.stdout.strip())
        except:
            pass
        
        if result.returncode == 0 and cpi_info:
            status = cpi_info.get('status', '')
            source = cpi_info.get('source', '')
            data = cpi_info.get('data', {})
            
            if status == 'released':
                print(f"   ✅ CPI已确认公布（来源：{source}）")
                if data.get('cpi_yoy'):
                    print(f"   📊 CPI年率: {data['cpi_yoy']} (预期: {data.get('cpi_yoy_forecast', '?')}, 前值: {data.get('cpi_yoy_previous', '?')})")
                if data.get('cpi_mom'):
                    print(f"   📊 CPI月率: {data['cpi_mom']} (预期: {data.get('cpi_mom_forecast', '?')}, 前值: {data.get('cpi_mom_previous', '?')})")
                if data.get('core_cpi_mom'):
                    print(f"   📊 核心CPI月率: {data['core_cpi_mom']}")
                if data.get('vs_expected'):
                    print(f"   📊 vs预期: {data['vs_expected']}")
            elif status == 'released_no_data':
                print(f"   ⚠️ CPI已出但无具体数值（来源：{source}）")
                print("   建议：询问用户CPI数值后用 cpi_checker.py --save 补录")
        elif result.returncode == 1:
            print("   ⚠️ CPI可能已出但未确认——建议询问用户")
        elif result.returncode == 2:
            print("   📅 本月CPI未到发布期")
        else:
            print("   ❓ CPI状态未知")
        
        return result.returncode, cpi_info
    except Exception as e:
        print(f"⚠️ CPI检查异常: {e}")
        return -1, None

def run_jin10(hours=4, btc_only=True):
    """获取金十快讯消息面"""
    print("📡 正在获取金十快讯消息面...")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'jin10_news.py'),
           '--hours', str(hours), '--limit', '20']
    if btc_only:
        cmd.append('--btc-only')
    cmd.append('--json')
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # 找到JSON部分
            lines = result.stdout.strip().split('\n')
            json_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith('['):
                    json_start = i
                    break
            
            if json_start is not None:
                json_str = '\n'.join(lines[json_start:])
                return json.loads(json_str)
            else:
                return []
        else:
            print(f"⚠️ 金十快讯获取失败: {result.stderr}")
            return []
    except Exception as e:
        print(f"⚠️ 金十快讯获取异常: {e}")
        return []

def run_okx_indicators():
    """获取OKX技术指标"""
    print("📊 正在获取OKX技术指标...")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'btc_analysis_okx.py')]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"⚠️ 技术指标获取失败: {result.stderr}")
            return ""
    except Exception as e:
        print(f"⚠️ 技术指标获取异常: {e}")
        return ""

def run_etf_flow(days=7):
    """获取ETF资金流数据"""
    print("💰 正在获取ETF资金流数据...")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'etf_flow.py'),
           '--days', str(days), '--json']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != 'null':
            return json.loads(result.stdout)
        else:
            return None
    except Exception as e:
        print(f"⚠️ ETF数据获取异常: {e}")
        return None

def classify_news_impact(news_items):
    """分析消息面对BTC的潜在影响"""
    if not news_items:
        return {"sentiment": "neutral", "summary": "无最新消息"}
    
    bullish = []
    bearish = []
    neutral = []
    
    for item in news_items:
        content = item.get('content', '') + item.get('title', '')
        
        # 简单的情绪分类规则
        if any(kw in content for kw in ['ETF流入', '贝莱德买入', '微策略', '机构增持', '美联储降息', '通胀下降', '和平', '停火', '合作']):
            bullish.append(item)
        elif any(kw in content for kw in ['监管打击', '禁令', 'SEC诉讼', '黑客', '被盗', '美联储加息', '通胀上升', '战争', '制裁', '清算', '爆仓']):
            bearish.append(item)
        else:
            neutral.append(item)
    
    # 判断整体情绪
    bull_score = len(bullish) * 2 + sum(1 for n in bullish if n.get('important'))
    bear_score = len(bearish) * 2 + sum(1 for n in bearish if n.get('important'))
    
    if bull_score > bear_score + 2:
        sentiment = "bullish"
    elif bear_score > bull_score + 2:
        sentiment = "bearish"
    else:
        sentiment = "neutral"
    
    return {
        "sentiment": sentiment,
        "bullish_count": len(bullish),
        "bearish_count": len(bearish),
        "neutral_count": len(neutral),
        "key_bullish": [n['content'][:80] for n in bullish[:3]],
        "key_bearish": [n['content'][:80] for n in bearish[:3]],
        "important_news": [n['content'][:80] for n in news_items if n.get('important')][:5]
    }

def format_news_for_dbk(news_items, impact):
    """格式化为大镖客风格的消息面分析"""
    if not news_items:
        return "📭 无最新消息面数据"
    
    lines = []
    lines.append("=== 消息面分析（金十快讯）===")
    lines.append(f"整体情绪: {impact['sentiment'].upper()}")
    lines.append(f"利多: {impact['bullish_count']}条 | 利空: {impact['bearish_count']}条 | 中性: {impact['neutral_count']}条")
    lines.append("")
    
    # 重要新闻
    if impact.get('important_news'):
        lines.append("【重要新闻】")
        for news in impact['important_news']:
            lines.append(f"  ⭐ {news}")
        lines.append("")
    
    # 利多因素
    if impact.get('key_bullish'):
        lines.append("【利多因素】")
        for news in impact['key_bullish']:
            lines.append(f"  + {news}")
        lines.append("")
    
    # 利空因素
    if impact.get('key_bearish'):
        lines.append("【利空因素】")
        for news in impact['key_bearish']:
            lines.append(f"  - {news}")
        lines.append("")
    
    # 因果链建议（模型10）
    lines.append("【消息面串联建议（模型10）】")
    lines.append("检查是否有以下因果链：")
    lines.append("  • 地缘事件→市场情绪变化")
    lines.append("  • 宏观政策→流动性变化")
    lines.append("  • ETF资金流→价格影响")
    lines.append("")
    lines.append("💡 使用'第一脚→续命→临门一脚'框架串联消息面")
    
    return '\n'.join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='大镖客BTC完整分析')
    parser.add_argument('--hours', type=int, default=4, help='消息面时间范围（小时）')
    parser.add_argument('--etf-days', type=int, default=7, help='ETF数据天数')
    args = parser.parse_args()
    
    print("="*60)
    print("大镖客BTC完整分析系统")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print()
    
    # 0. CPI数据检查（v4: 本地记录优先，有记录直接用）
    cpi_code, cpi_info = run_cpi_checker()
    if cpi_code == 0 and cpi_info:
        cpi_data = cpi_info.get('data', {})
        print(f"   ✅ CPI数据可直接使用（本地缓存）")
    elif cpi_code == 0:
        print("   ✅ CPI已确认公布")
    elif cpi_code == 1:
        print("   ⚠️ CPI可能已出但未确认——建议询问用户或用 cpi_checker.py --save 记录")
    elif cpi_code == 2:
        print("   📅 本月CPI未到发布期")
    else:
        print("   ❓ CPI状态未知")
    print()
    
    # 1. 获取消息面
    news_items = run_jin10(hours=args.hours, btc_only=False)
    news_impact = classify_news_impact(news_items)
    news_formatted = format_news_for_dbk(news_items, news_impact)
    
    # 2. 获取因果链
    print("🔗 正在分析消息面因果链...")
    causality_cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'news_causality.py'),
                     '--hours', str(args.hours)]
    try:
        result = subprocess.run(causality_cmd, capture_output=True, text=True, timeout=30)
        causality_formatted = result.stdout if result.returncode == 0 else "⚠️ 因果链分析失败"
    except:
        causality_formatted = "⚠️ 因果链分析异常"
    
    # 3. 获取ETF资金流
    etf_data = run_etf_flow(days=args.etf_days)
    from etf_flow import format_etf_for_dbk
    etf_formatted = format_etf_for_dbk(etf_data)
    
    # 4. 获取技术指标
    indicators = run_okx_indicators()
    
    # 5. 输出整合结果
    print()
    print("="*60)
    print("第一部分：消息面分析（金十快讯）")
    print("="*60)
    print(news_formatted)
    
    print()
    print("="*60)
    print("第二部分：消息面因果链（模型10）")
    print("="*60)
    print(causality_formatted)
    
    print()
    print("="*60)
    print("第三部分：ETF资金流")
    print("="*60)
    print(etf_formatted)
    
    print()
    print("="*60)
    print("第四部分：技术指标")
    print("="*60)
    print(indicators)
    
    print()
    print("="*60)
    print("分析完成 - 请基于以上数据进行大镖客视角分析")
    print("="*60)

if __name__ == '__main__':
    main()
