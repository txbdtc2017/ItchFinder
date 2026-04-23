"""用 MiniMax (Anthropic 兼容接口) 批量评估哪些条目是真正的用户痛点。"""
import json
import os
import re

import anthropic

import db

MODEL = "MiniMax-M2.7-highspeed"
BASE_URL = "https://api.minimaxi.com/anthropic"

SYSTEM_PROMPT = """你是一个产品机会分析助手。你的任务是从一批社区帖子中筛选出真正描述了"用户痛点"的帖子。

"用户痛点"的定义:
- 用户明确抱怨某个工具/流程/体验不好用
- 用户在寻找某个问题的解决方案但找不到好的
- 用户描述了一个反复出现的、令人沮丧的问题
- 用户希望有某个产品/功能但目前不存在

不算痛点的:
- 单纯的新闻/公告/分享
- 自我推广的项目展示
- 纯技术讨论(无抱怨成分)
- 招聘/求职信息"""


def run_ai_scoring() -> None:
    """拉未评估的条目,批量调 MiniMax,标记结果。"""
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("[ai] MINIMAX_API_KEY not set, skipping")
        return

    items = db.get_unscored_items(limit=80)
    if not items:
        print("[ai] no new items to score")
        return

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
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=16384,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # MiniMax M2.7 默认开 thinking,需要找 TextBlock
        text = ""
        for block in msg.content:
            if block.type == "text" and getattr(block, "text", ""):
                text = block.text.strip()
                break
        print(f"[ai] response: {text[:300]}")

        # 从回复中提取 JSON 数组
        match = re.search(r"\[[\d,\s]*\]", text)
        if match:
            flagged_ids = [int(x) for x in json.loads(match.group())]
        else:
            flagged_ids = []
    except Exception as e:
        print(f"[ai] API error: {e}")
        return

    all_ids = [it["id"] for it in items]
    db.mark_ai_results(scored_ids=all_ids, flagged_ids=flagged_ids)
    print(f"[ai] scored {len(all_ids)}, flagged {len(flagged_ids)}")
