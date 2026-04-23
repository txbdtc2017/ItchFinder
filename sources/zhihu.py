"""知乎热榜抓取器。拉热榜 Top 50。"""
from datetime import datetime, timezone

import httpx

from .base import UA

URL = "https://api.zhihu.com/topstory/hot-lists/total?limit=50"


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(URL, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for entry in data.get("data", []):
        t = entry.get("target", {})
        qid = t.get("id")
        if not qid:
            continue
        items.append({
            "source": "zhihu",
            "external_id": str(qid),
            "title": t.get("title", ""),
            "content": t.get("excerpt") or "",
            "url": f"https://www.zhihu.com/question/{qid}",
            "author": (t.get("author") or {}).get("name"),
            "created_at": datetime.fromtimestamp(
                t.get("created", 0), tz=timezone.utc
            ).isoformat(),
            "raw_score": t.get("answer_count") or 0,
        })
    return items
