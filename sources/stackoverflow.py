"""Stack Overflow 抓取器。抓最新活跃问题,官方 Stack Exchange API。
无需 API key,匿名每天 10,000 次。
"""
from datetime import datetime, timezone

import httpx

from .base import UA

URL = "https://api.stackexchange.com/2.3/questions"


async def fetch() -> list[dict]:
    params = {
        "site": "stackoverflow",
        "order": "desc",
        "sort": "activity",
        "pagesize": 50,
        "filter": "!-*jbN.OXKfDP",  # 默认 filter 已含 body_markdown
    }
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for q in data.get("items", []):
        qid = q.get("question_id")
        if not qid:
            continue
        items.append({
            "source": "stackoverflow",
            "external_id": str(qid),
            "title": q.get("title", ""),
            "content": (q.get("body_markdown") or "")[:500],
            "url": q.get("link", f"https://stackoverflow.com/questions/{qid}"),
            "author": (q.get("owner") or {}).get("display_name"),
            "created_at": datetime.fromtimestamp(
                q.get("creation_date", 0), tz=timezone.utc
            ).isoformat(),
            "raw_score": q.get("answer_count") or 0,
        })
    return items
