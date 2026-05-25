# Multi-Perspective Trading Analysis

> **Absorbed into `dbk9527-perspective` as a labeled subsection.**
> The parent skill `dbk9527-perspective` now contains all multi-perspective analysis workflow logic as an integrated component.

---

## Original Skill Summary

This skill performed multi-perspective trading analysis using 5 independent viewpoints:

| Perspective | Role | Source Skill |
|-------------|------|-------------|
| 1 | 大镖客（技术分析师） | `dbk9527-perspective` |
| 2 | 风控官（风险管理） | Built-in |
| 3 | 宏观交易员（基本面+大周期） | Built-in |
| 4 | 逆向思维（魔鬼代言人） | Built-in |
| 5 | 量化视角（数据驱动） | Built-in |

## How to Use

To run a multi-perspective analysis, use the `dbk9527-perspective` skill with the multi-perspective-analysis workflow pattern:

```
delegate_task(tasks=[
  {"goal": "大镖客视角分析：<question>", "toolsets": ["skills"]},
  {"goal": "风控官视角评估...", "toolsets": []},
  {"goal": "宏观交易员视角...", "toolsets": []},
  ...
], role="orchestrator")
```

Note: `max_concurrent_children=3` by default. For 5 perspectives, split into two batches (3+2).

## Key Constraints

- **Concurrency limit**: `max_concurrent_children=3` — split 5 perspectives into two batches
- **风控官否决权**: If risk officer returns "不通过", the overall verdict must be "有条件通过" with modifications or "不通过"
- **No vote counting**:综合判定不是5票投票，而是加权：风控官有否决权
- **All numbers from real data**: 禁止编造任何具体数字

## Trigger Phrases

- 「多维分析」「多视角」「5个视角」「帮我全面分析」