"""Dev.to 抓取器。拉最新文章,官方 REST API。"""
from datetime import datetime, timezone

import httpx

from .base import UA

URL = "https://dev.to/api/articles/latest?per_page=50"


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(URL, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for a in data:
        aid = a.get("id")
        if not aid:
            continue
        items.append({
            "source": "devto",
            "external_id": str(aid),
            "title": a.get("title", ""),
            "content": a.get("description") or "",
            "url": a.get("url", ""),
            "author": (a.get("user") or {}).get("username"),
            "created_at": a.get("published_at") or a.get("created_at") or "",
            "raw_score": a.get("comments_count") or 0,
        })
    return items
