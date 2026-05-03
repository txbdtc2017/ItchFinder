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

SUMMARY_PROMPT = """你是一个产品机会分析助手。请为每个已确认的痛点生成中文总结。

每条总结必须包含三行:
用户痛点：
现有方案缺口：
可做产品机会：

只返回 JSON 对象,键是帖子 ID 字符串,值是对应中文总结。不要解释。
"""


def _row_value(row, key: str, default: str | None = None):
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def _safe_preview(value: str | None, limit: int) -> str:
    return (value or "")[:limit].replace("\n", " ").strip()


def _build_scoring_prompt(items: list) -> str:
    lines = []
    for it in items:
        content_preview = _safe_preview(_row_value(it, "content"), 180)
        enriched_preview = _safe_preview(_row_value(it, "enriched_content"), 900)
        line = f'[ID:{it["id"]}] {it["title"]}'
        if content_preview:
            line += f" — {content_preview}"
        if enriched_preview:
            line += f"\n上下文: {enriched_preview}"
        lines.append(line)

    return (
        "以下是从技术/创业社区抓取的帖子。请判断哪些描述了真正的用户痛点。\n"
        "如果有上下文,上下文里的评论和回复可以作为判断依据。\n"
        "只返回一个 JSON 数组,包含符合条件的帖子 ID(纯数字)。没有则返回 []。\n"
        "不要解释,只输出 JSON。\n\n"
        + "\n\n".join(lines)
    )


def _parse_flagged_ids(text: str) -> list[int]:
    match = re.search(r"\[[\d,\s]*\]", text)
    if match:
        return [int(x) for x in json.loads(match.group())]
    return []


def _call_minimax(items: list) -> list[int]:
    """同步调用 MiniMax,返回被标记为痛点的 ID 列表。"""
    api_key = os.environ["MINIMAX_API_KEY"]
    user_prompt = _build_scoring_prompt(items)

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
    return _parse_flagged_ids(text)


def _build_summary_prompt(items: list) -> str:
    blocks = []
    for it in items:
        content_preview = _safe_preview(_row_value(it, "content"), 500)
        enriched_preview = _safe_preview(_row_value(it, "enriched_content"), 2000)
        blocks.append(
            f'[ID:{it["id"]}] {it["title"]}\n'
            f"原始内容: {content_preview}\n"
            f"补全上下文: {enriched_preview}"
        )
    return "\n\n".join(blocks)


def _parse_summary_response(text: str) -> dict[int, str]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    data = json.loads(match.group())
    return {int(key): str(value).strip() for key, value in data.items() if str(value).strip()}


def _call_minimax_summaries(items: list) -> dict[int, str]:
    api_key = os.environ["MINIMAX_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key, base_url=BASE_URL)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=16384,
        system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": _build_summary_prompt(items)}],
    )
    text = ""
    for block in msg.content:
        if block.type == "text" and getattr(block, "text", ""):
            text = block.text.strip()
            break
    return _parse_summary_response(text)


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


async def summarize_ai_flagged() -> AsyncIterator[str]:
    if not os.getenv("MINIMAX_API_KEY"):
        yield "AI总结: 未配置 MINIMAX_API_KEY,跳过"
        return

    items = db.get_ai_summary_candidates(limit=30)
    if not items:
        yield "AI总结: 没有需要总结的条目"
        return

    yield f"AI总结: 提交 {len(items)} 条已推荐痛点给 MiniMax {MODEL}..."
    try:
        summaries = await asyncio.to_thread(_call_minimax_summaries, items)
    except Exception as e:
        yield f"✗ AI总结 API 失败: {str(e)[:80]}"
        return

    saved = 0
    for item in items:
        summary = summaries.get(item["id"])
        if summary:
            db.update_ai_summary(item["id"], summary)
            saved += 1

    yield f"✓ AI总结完成: {saved} 条已写入"
