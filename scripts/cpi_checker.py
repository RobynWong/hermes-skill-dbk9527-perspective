#!/usr/bin/env python3
"""CPI/PPI数据查询 v5 — 本地记录优先 + 三条规则

v5新增规则（用户指定 2026-05-14）：
1. 每月8号之前不查询CPI（CPI最早12号发布，8号前查无意义）
2. CPI发布日期以BLS官方schedule为准，记录预公布日期（release_date字段）
3. CPI公布一周后不再分析CPI对BTC影响（已完全price in，price_in_deadline字段）

返回退出码：
  0 = CPI已确认公布
  1 = CPI可能已出但未确认（需询问用户）
  2 = 本月CPI还未到发布时间 / 8号前不查询
  3 = CPI已完全price in（公布超过一周，无需分析影响）
"""

import json, sys, os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, '..', 'data', 'cpi_records.json')

def load_records():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"_meta": {"description": "CPI/PPI月度数据记录", "rules": {"rule1": "每月8号之前不查询CPI", "rule2": "CPI发布日期以BLS官方schedule为准", "rule3": "CPI公布一周后不再分析CPI对BTC影响"}, "source_priority": ["local_record > web_search > faireconomy_api > user_input"]}}

def save_records(records):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def get_current_month_key():
    now = datetime.now()
    return f"{now.year}-{now.month:02d}"

def check_local_record(records, month_key=None):
    if month_key is None:
        month_key = get_current_month_key()
    record = records.get(month_key)
    if record and record.get('released'):
        return True, record
    return False, None

def check_query_allowed(records, month_key=None):
    """规则1：8号之前不查询CPI"""
    if month_key is None:
        month_key = get_current_month_key()
    now = datetime.now()
    record = records.get(month_key, {})
    query_start = record.get('query_start_date', '')
    if query_start:
        query_date = datetime.strptime(query_start, '%Y-%m-%d').date()
        if now.date() < query_date:
            return False, f"今天{now.day}日，CPI查询起始日为{query_start}（规则1：8号前不查）"
    else:
        if now.day < 8:
            return False, f"今天{now.day}日，8号之前不查询CPI（规则1）"
    return True, "允许查询"

def check_price_in_deadline(records, month_key=None):
    """规则3：CPI公布一周后不再分析影响"""
    if month_key is None:
        month_key = get_current_month_key()
    now = datetime.now()
    record = records.get(month_key, {})
    deadline = record.get('price_in_deadline', '')
    if deadline:
        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
        if now.date() > deadline_date:
            return True, f"CPI已公布超过一周（{deadline}后），已完全price in（规则3）"
    return False, "CPI影响仍在分析窗口内"

def check_faireconomy_calendar():
    try:
        import urllib.request
        proxy = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:9981', 'https': 'http://127.0.0.1:9981'})
        opener = urllib.request.build_opener(proxy)
        results = []
        for suffix in ['thisweek', 'lastweek']:
            url = f"https://nfs.faireconomy.media/ff_calendar_{suffix}.json"
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(url, headers=headers)
            resp = opener.open(req, timeout=10)
            data = json.loads(resp.read().decode('utf-8'))
            for item in data:
                title = item.get('title', '')
                country = item.get('country', '')
                if 'CPI' in title.upper() and country == 'USD':
                    results.append(item)
        return results
    except Exception as e:
        return None

def infer_cpi_status():
    now = datetime.now()
    day = now.day
    hour = now.hour
    if day < 8:
        return 'too_early', f"今天{day}日，8号之前不查询CPI（规则1）"
    if 8 <= day < 12:
        return 'not_yet', f"今天{day}日，CPI通常12-15日发布"
    if day >= 16:
        return 'released', f"今天{day}日，已过CPI发布期，本月CPI肯定已出"
    if 12 <= day <= 15 and hour >= 21:
        return 'released', f"今天{day}日{hour}点，CPI大概率已出"
    if 12 <= day <= 15 and 20 <= hour < 21:
        return 'uncertain', f"今天{day}日{hour}点，CPI可能在20:30刚发布"
    if 12 <= day <= 15 and hour < 20:
        for d in range(12, day):
            if now.replace(day=d).weekday() < 5:
                return 'released', f"本月{d}日(工作日)已过，CPI大概率已发布"
        return 'waiting', f"今天{day}日，CPI可能在今晚20:30发布"

def save_cpi_data(yoy=None, mom=None, core_mom=None, vs_expected=None, release_date=None, source="user"):
    records = load_records()
    month_key = get_current_month_key()
    record = records.get(month_key, {})
    record['released'] = True
    record['date'] = datetime.now().strftime('%Y-%m-%d')
    record['source'] = source
    record['updated_at'] = datetime.now().isoformat()
    if yoy: record['cpi_yoy'] = yoy
    if mom: record['cpi_mom'] = mom
    if core_mom: record['core_cpi_mom'] = core_mom
    if vs_expected: record['vs_expected'] = vs_expected
    if release_date:
        record['release_date'] = release_date
        rd = datetime.strptime(release_date, '%Y-%m-%d').date()
        record['price_in_deadline'] = (rd + timedelta(days=7)).strftime('%Y-%m-%d')
    records[month_key] = record
    save_records(records)
    return record

def main():
    import argparse
    parser = argparse.ArgumentParser(description='CPI数据查询 v5')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--yoy', type=str)
    parser.add_argument('--mom', type=str)
    parser.add_argument('--core-mom', type=str)
    parser.add_argument('--vs-expected', type=str)
    parser.add_argument('--release-date', type=str, help='BLS发布日期(规则2)')
    parser.add_argument('--source', type=str, default='user')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if args.save:
        if not args.yoy and not args.mom:
            print("⚠️ 需要至少提供 --yoy 或 --mom")
            print("用法: python3 cpi_checker.py --save --yoy 3.7% --mom 0.6% --release-date 2026-06-11")
            sys.exit(1)
        record = save_cpi_data(yoy=args.yoy, mom=args.mom, core_mom=args.core_mom, vs_expected=args.vs_expected, release_date=args.release_date, source=args.source)
        print(f"✅ CPI数据已保存 | 月份: {get_current_month_key()}")
        for k, v in record.items():
            if k != 'released' and v: print(f"   {k}: {v}")
        sys.exit(0)

    now = datetime.now()
    month_key = get_current_month_key()
    records = load_records()

    if not args.json:
        print("=== CPI数据查询 v5 ===")
        print(f"查询时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 月份：{month_key}")
        print()

    # 规则1：8号前不查
    allowed, allow_msg = check_query_allowed(records, month_key)
    if not allowed:
        if args.json:
            print(json.dumps({"status": "too_early", "month": month_key, "message": allow_msg}, ensure_ascii=False))
        else:
            print(f"📅 {allow_msg}")
            print("   8号之前不查询CPI，分析中无需提及CPI")
        sys.exit(2)

    # 规则3：已price in
    priced_in, price_msg = check_price_in_deadline(records, month_key)

    # Step 1: 本地记录
    if not args.json: print("📂 [1/3] 检查本地记录...")
    found, record = check_local_record(records=records)

    if found:
        if priced_in:
            if args.json:
                print(json.dumps({"status": "price_in", "month": month_key, "message": price_msg, "data": record}, ensure_ascii=False))
            else:
                print(f"  ✅ 本地记录命中，但CPI已完全price in")
                print(f"  📊 {price_msg}")
                print("✅ CPI已完全price in，分析中无需提及CPI影响（规则3）")
            sys.exit(3)
        if args.json:
            print(json.dumps({"status": "released", "month": month_key, "source": "local_record", "data": record}, ensure_ascii=False))
        else:
            print(f"  ✅ 本地记录命中！CPI已确认公布")
            print(f"  📅 发布日期: {record.get('release_date', record.get('date', '未知'))}")
            if record.get('cpi_yoy_actual'): print(f"  📊 CPI年率: {record['cpi_yoy_actual']} (预期: {record.get('cpi_yoy_forecast','?')}, 前值: {record.get('cpi_yoy_previous','?')})")
            elif record.get('cpi_yoy'): print(f"  📊 CPI年率: {record['cpi_yoy']} (预期: {record.get('cpi_yoy_forecast','?')}, 前值: {record.get('cpi_yoy_previous','?')})")
            if record.get('cpi_mom_actual'): print(f"  📊 CPI月率: {record['cpi_mom_actual']} (预期: {record.get('cpi_mom_forecast','?')}, 前值: {record.get('cpi_mom_previous','?')})")
            elif record.get('cpi_mom'): print(f"  📊 CPI月率: {record['cpi_mom']} (预期: {record.get('cpi_mom_forecast','?')}, 前值: {record.get('cpi_mom_previous','?')})")
            if record.get('vs_expected'): print(f"  📊 vs预期: {record['vs_expected']}")
            if record.get('impact'): print(f"  📊 BTC影响: {record['impact']}")
            dl = record.get('price_in_deadline','')
            if dl: print(f"  📊 price in截止: {dl}")
            print("✅ CPI已确认公布（本地记录），可直接分析")
        sys.exit(0)
    else:
        if not args.json: print("  ℹ️ 本月无本地记录")

    # Step 2: API查询
    if not args.json: print("\n📡 [2/3] 查询faireconomy日历API...")
    cpi_items = check_faireconomy_calendar()
    api_found = False
    api_data = {}

    if cpi_items is not None:
        for item in cpi_items:
            actual = item.get('actual', '')
            title = item.get('title', '')
            forecast = item.get('forecast', '')
            previous = item.get('previous', '')
            item_date = item.get('date', '')
            if not args.json:
                print(f"  {'✅' if actual and actual.strip() else 'ℹ️'} {title}: actual={actual or '空'}, forecast={forecast}")
            if actual and actual.strip():
                api_found = True
                if 'y/y' in title.lower(): api_data.update({'cpi_yoy': actual, 'cpi_yoy_forecast': forecast, 'cpi_yoy_previous': previous})
                elif 'm/m' in title.lower():
                    if 'core' in title.lower(): api_data.update({'core_cpi_mom': actual, 'core_cpi_mom_forecast': forecast, 'core_cpi_mom_previous': previous})
                    else: api_data.update({'cpi_mom': actual, 'cpi_mom_forecast': forecast, 'cpi_mom_previous': previous})
                if item_date:
                    try:
                        api_data['release_date'] = item_date[:10]
                        rd = datetime.strptime(item_date[:10], '%Y-%m-%d').date()
                        api_data['price_in_deadline'] = (rd + timedelta(days=7)).strftime('%Y-%m-%d')
                    except: pass
    else:
        if not args.json: print("  ⚠️ API不可用")

    if api_found:
        records = load_records()
        api_data.update({'released': True, 'date': now.strftime('%Y-%m-%d'), 'source': 'faireconomy_api', 'updated_at': now.isoformat()})
        records[month_key] = api_data
        save_records(records)
        if args.json:
            print(json.dumps({"status": "released", "month": month_key, "source": "faireconomy_api", "data": api_data}, ensure_ascii=False))
        else:
            print("\n  ✅ API确认CPI已公布，已写入本地记录")
            print("✅ CPI已确认公布（API+已缓存）")
        sys.exit(0)

    # Step 3: 日期推断（优先用记录中的release_date）
    if not args.json: print("\n📅 [3/3] 日期推断...")
    month_record = records.get(month_key, {})
    recorded_release = month_record.get('release_date', '')

    if recorded_release:
        try:
            release_date = datetime.strptime(recorded_release, '%Y-%m-%d').date()
            if now.date() > release_date:
                date_status, date_msg = 'released', f"BLS发布日{recorded_release}已过，CPI已出（规则2）"
            elif now.date() == release_date and now.hour >= 21:
                date_status, date_msg = 'released', f"今天是BLS发布日{recorded_release}，已过20:30"
            else:
                date_status, date_msg = 'waiting', f"BLS发布日{recorded_release}，尚未到发布时间"
        except: date_status, date_msg = infer_cpi_status()
    else:
        date_status, date_msg = infer_cpi_status()

    if not args.json: print(f"  {date_msg}")

    if not args.json: print("\n" + "="*50 + "\n=== 综合判断 ===\n")

    if date_status == 'released':
        records = load_records()
        rec = {'released': True, 'date': now.strftime('%Y-%m-%d'), 'release_date': recorded_release or now.strftime('%Y-%m-%d'), 'source': 'date_inference', 'updated_at': now.isoformat(), 'note': '日期推断CPI已出，建议--save补录'}
        if recorded_release:
            rd = datetime.strptime(recorded_release, '%Y-%m-%d').date()
            rec['price_in_deadline'] = (rd + timedelta(days=7)).strftime('%Y-%m-%d')
        records[month_key] = rec
        save_records(records)
        if args.json:
            print(json.dumps({"status": "released_no_data", "month": month_key, "message": "CPI已出但无具体数值"}, ensure_ascii=False))
        else:
            print("⚠️ CPI已出但无具体数值，建议 --save 补录")
        sys.exit(0)

    if date_status in ('uncertain', 'waiting'):
        if args.json:
            print(json.dumps({"status": "not_confirmed", "month": month_key, "message": date_msg}, ensure_ascii=False))
        else:
            print("⚠️ 未能确认CPI已出，建议询问用户")
        sys.exit(1)

    if date_status in ('too_early', 'not_yet', 'last_month_released'):
        if args.json:
            print(json.dumps({"status": "not_yet", "month": month_key, "message": date_msg}, ensure_ascii=False))
        else:
            print(f"📅 {date_msg}")
        sys.exit(2)

if __name__ == '__main__':
    main()