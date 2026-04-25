"""用 MiniMax (Anthropic 兼容接口) 批量评估哪些条目是真正的用户痛点。
run_ai_scoring 是 async generator,yield 进度字符串。
"""
import asyncio
import json
import os
import re
from collections.abc import AsyncIterator

import anthropic

import db

MODEL = "MiniMax-M2.7-highspeed"
BASE_URL = "https://api.minimaxi.com/anthropic"
BATCH_LIMIT = 80

SYSTEM_PROMPT = """你是一个独立开发者的产品机会分析助手。目标是筛出"能被软件/App/自动化工具解决的用户痛点",用于挖掘开发需求。

符合下列任一条件的算"痛点":
(a) 用户想要某个目前不存在的软件/App/工具
(b) 用户对某个现有命名产品的使用体验(UX)/ 功能缺失/ 上手难度 抱怨
   例如"XX 软件真难用"、"XX 这个功能怎么这么绕"、"XX 为什么不能做 YY"
(c) 用户描述了一个重复的手工流程,可以被软件自动化
(d) 用户在"求推荐某类软件/工具"(因为现有的都不够好)

以下情况**不算**痛点(明确排除):
- 具体的 bug / 崩溃 / 报错(这是临时缺陷,不是产品机会)
- 新闻/公告/产品发布
- 自我推广的项目展示
- 纯技术实现讨论(没有抱怨成分)
- 招聘/求职信息
- 与软件无关的纯生活/消费/情绪抱怨(感情、餐饮、服装等)"""


def _call_minimax(items: list) -> list[int]:
    """同步调用 MiniMax,返回被标记为痛点的 ID 列表。"""
    api_key = os.environ["MINIMAX_API_KEY"]
    lines = []
    for it in items:
        preview = (it["content"] or "")[:120].replace("\n", " ")
        lines.append(f'[ID:{it["id"]}] {it["title"]}' + (f" — {preview}" if preview else ""))

    user_prompt = (
        "以下是从技术/创业社区抓取的帖子。请判断哪些描述了真正的用户痛点。\n"
        "只返回一个 JSON 数组,包含符合条件的帖子 ID(纯数字)。没有则返回 []。\n"
        "不要解释,只输出 JSON。\n\n"
        + "\n".join(lines)
    )

    client = anthropic.Anthropic(api_key=api_key, base_url=BASE_URL)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=16384,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = ""
    for block in msg.content:
        if block.type == "text" and getattr(block, "text", ""):
            text = block.text.strip()
            break
    match = re.search(r"\[[\d,\s]*\]", text)
    if match:
        return [int(x) for x in json.loads(match.group())]
    return []


async def run_ai_scoring() -> AsyncIterator[str]:
    if not os.getenv("MINIMAX_API_KEY"):
        yield "AI: 未配置 MINIMAX_API_KEY,跳过"
        return

    items = db.get_unscored_items(limit=BATCH_LIMIT)
    if not items:
        yield "AI: 没有需要评估的条目"
        return

    yield f"AI: 提交 {len(items)} 条候选给 MiniMax {MODEL}..."
    try:
        flagged_ids = await asyncio.to_thread(_call_minimax, items)
    except Exception as e:
        yield f"✗ AI API 失败: {str(e)[:80]}"
        return

    all_ids = [it["id"] for it in items]
    db.mark_ai_results(scored_ids=all_ids, flagged_ids=flagged_ids)
    yield f"✓ AI 评分完成: {len(all_ids)} 条已评估, {len(flagged_ids)} 条被标记为痛点"
