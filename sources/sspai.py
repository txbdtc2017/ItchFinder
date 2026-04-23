"""少数派首页推荐文章抓取器。"""
from datetime import datetime, timezone

import httpx

from .base import UA

URL = "https://sspai.com/api/v1/article/index/page/get?limit=40&offset=0"


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(URL, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for a in data.get("data", []):
        aid = a.get("id")
        if not aid:
            continue
        items.append({
            "source": "sspai",
            "external_id": str(aid),
            "title": a.get("title", ""),
            "content": a.get("summary") or "",
            "url": f"https://sspai.com/post/{aid}",
            "author": (a.get("author") or {}).get("nickname"),
            "created_at": datetime.fromtimestamp(
                a.get("released_time") or a.get("created_time", 0),
                tz=timezone.utc,
            ).isoformat(),
            "raw_score": a.get("like_count") or 0,
        })
    return items
