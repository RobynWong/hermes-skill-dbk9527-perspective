#!/usr/bin/env python3
"""
dbk9527-perspective 校验脚本
检查 SKILL.md 的 frontmatter 与实际内容是否一致

用法: python3 validate_skill.py [--fix]
  --fix: 自动修复 frontmatter 中的 heuristics_count

退出码:
  0 = 一致
  1 = 不一致（需修复或手动确认）
  2 = 错误
"""

import re
import sys
import os
from pathlib import Path

SKILL_PATH = Path(__file__).parent.parent / "SKILL.md"
AUTO_FIX = "--fix" in sys.argv


def extract_frontmatter(content: str) -> dict:
    """从 SKILL.md 头部提取 frontmatter"""
    fm = {}
    in_fm = False
    for line in content.split("\n"):
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if in_fm:
            m = re.match(r"(\w+):\s*(.*)", line)
            if m:
                fm[m.group(1).strip()] = m.group(2).strip()
    return fm


def count_actual_heuristics(content: str) -> dict:
    """
    统计实际启发式数量
    返回: {
        'numbered': [1, 2, ..., 38],  # 1-38编号的
        'new_sections': [39, 40, ..., 55],  # ### 新增启发式XX：
        'total': 55
    }
    """
    # 1-38编号的启发式（段落以 "数字. **[" 开头）
    numbered = set()
    for m in re.finditer(r"^\s*(\d+)\.\s+\*\*\[", content, re.MULTILINE):
        numbered.add(int(m.group(1)))

    # 新增启发式 section（### 新增启发式XX：）
    new_sections = set()
    for m in re.finditer(r"^###\s+新增启发式(\d+)：", content, re.MULTILINE):
        new_sections.add(int(m.group(1)))

    return {
        "numbered": sorted(numbered),
        "new_sections": sorted(new_sections),
        "total": len(numbered) + len(new_sections),
    }


def check_heuristic_references(content: str, actual: dict) -> list:
    """
    检查正文中的启发式引用是否都有对应的定义
    返回: [错误信息列表]
    """
    errors = []

    # 构造所有已知编号集合
    all_nums = set(actual["numbered"])
    # 新增启发式 39+ 也在此集合
    for n in actual["new_sections"]:
        if n >= 39:
            all_nums.add(n)

    # 找正文中的所有 "启发式XX" 引用（在 达尔文评估记录 之前的正文中）
    darwin_pos = content.find("## 达尔文评估记录")
    body = content[:darwin_pos] if darwin_pos > 0 else content

    # 匹配 "启发式数字" 但排除 frontmatter 和 section header
    for m in re.finditer(r"启发式(\d+)([^\d]?)", body):
        num = int(m.group(1))
        suffix = m.group(2)
        # section header "### 新增启发式XX：" 不算正文引用，跳过
        start = max(0, m.start() - 20)
        end = min(len(body), m.end() + 5)
        context = body[start:end]
        if re.match(r"^\s*###\s+新增启发式", context):
            continue
        if num not in all_nums:
            errors.append(f"  启发式{num}{suffix} 引用了不存在的编号（上下文: ...{context.strip()}...）")

    return errors


def check_frontmatter_count(content: str, actual: dict, fm: dict) -> tuple:
    """比对 frontmatter heuristics_count 与实际数量"""
    errors = []
    fm_count_str = fm.get("heuristics_count", "NOT FOUND")

    try:
        fm_count = int(re.search(r"\d+", fm_count_str).group())
    except (ValueError, AttributeError):
        return [f"  frontmatter heuristics_count 无法解析: '{fm_count_str}'"], fm_count_str

    actual_total = actual["total"]
    if fm_count != actual_total:
        errors.append(
            f"  frontmatter: {fm_count} 条\n"
            f"  实际: {actual_total} 条 (1-38编号:{len(actual['numbered'])} + 新增section:{len(actual['new_sections'])})\n"
            f"  差异: {fm_count - actual_total}"
        )

    return errors, fm_count_str


def main():
    print("=" * 50)
    print("dbk9527-perspective SKILL.md 校验")
    print("=" * 50)

    if not SKILL_PATH.exists():
        print(f"❌ 错误: {SKILL_PATH} 不存在")
        sys.exit(2)

    content = SKILL_PATH.read_text(encoding="utf-8")

    # 1. 提取 frontmatter
    fm = extract_frontmatter(content)
    print(f"\n📋 Frontmatter:")
    for k, v in fm.items():
        print(f"   {k}: {v}")

    # 2. 统计实际内容
    actual = count_actual_heuristics(content)
    print(f"\n📊 实际内容:")
    print(f"   1-38编号: {len(actual['numbered'])} 条 {actual['numbered']}")
    print(f"   新增section: {len(actual['new_sections'])} 条 {actual['new_sections']}")
    print(f"   总计: {actual['total']} 条")

    all_errors = []

    # 3. 比对 frontmatter count
    count_errors, fm_count = check_frontmatter_count(content, actual, fm)
    all_errors.extend(count_errors)

    # 4. 检查正文引用
    ref_errors = check_heuristic_references(content, actual)
    all_errors.extend(ref_errors)

    # 5. 检查新增section编号是否连续（39-55，跳过45/46/47）
    new_nums = actual["new_sections"]
    for n in range(39, 56):
        if n in (45, 46, 47):
            continue  # 已知跳过
        if n not in new_nums:
            all_errors.append(f"  警告: 缺少新增编号 {n}")

    # 输出结果
    print(f"\n{'=' * 50}")
    if not all_errors:
        print("✅ 一致性校验通过")
        print(f"   frontmatter: {fm_count}")
        print(f"   实际: {actual['total']} 条")
        sys.exit(0)
    else:
        print("❌ 发现不一致:")
        for err in all_errors:
            print(err)

        if AUTO_FIX:
            print(f"\n🔧 自动修复...")
            # 只修复 frontmatter heuristics_count
            new_count = str(actual["total"])
            new_content = re.sub(
                r"(\w+: \|?\s*)(.* heuristics_count: )\d+",
                rf"\1\2{new_count}",
                content,
                count=1
            )
            SKILL_PATH.write_text(new_content, encoding="utf-8")
            print(f"   已将 frontmatter heuristics_count 更新为 {new_count}")
            sys.exit(0)
        else:
            print(f"\n💡 提示: 用 --fix 自动修复 frontmatter")
            sys.exit(1)


if __name__ == "__main__":
    main()
