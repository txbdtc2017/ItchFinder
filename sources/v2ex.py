"""V2EX 抓取器。拉 latest topics,单请求。"""
from datetime import datetime, timezone

import httpx

from .base import UA

URL = "https://www.v2ex.com/api/topics/latest.json"


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(URL, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for t in data:
        tid = t["id"]
        items.append({
            "source": "v2ex",
            "external_id": str(tid),
            "title": t.get("title", ""),
            "content": t.get("content") or "",
            "url": t.get("url") or f"https://www.v2ex.com/t/{tid}",
            "author": (t.get("member") or {}).get("username"),
            "created_at": datetime.fromtimestamp(t["created"], tz=timezone.utc).isoformat(),
            "raw_score": t.get("replies") or 0,
        })
    return items
