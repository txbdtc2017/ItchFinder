"""Hacker News 抓取器。拉最新 200 条 story,并发 10。"""
import asyncio
from datetime import datetime, timezone

import httpx

from .base import UA

NEWSTORIES_URL = "https://hacker-news.firebaseio.com/v0/newstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
TOP_N = 200
CONCURRENCY = 10


async def _fetch_detail(client: httpx.AsyncClient, sem: asyncio.Semaphore, item_id: int):
    async with sem:
        try:
            r = await client.get(ITEM_URL.format(id=item_id), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[hackernews] item {item_id} failed: {e}")
            return None


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(NEWSTORIES_URL, timeout=10)
        r.raise_for_status()
        ids = r.json()[:TOP_N]
        sem = asyncio.Semaphore(CONCURRENCY)
        details = await asyncio.gather(
            *[_fetch_detail(client, sem, i) for i in ids]
        )

    items: list[dict] = []
    for d in details:
        if not d or d.get("dead") or d.get("deleted"):
            continue
        if d.get("type") != "story" or not d.get("title"):
            continue
        item_id = d["id"]
        items.append({
            "source": "hackernews",
            "external_id": str(item_id),
            "title": d["title"],
            "content": d.get("text") or "",
            "url": d.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
            "author": d.get("by"),
            "created_at": datetime.fromtimestamp(d["time"], tz=timezone.utc).isoformat(),
            "raw_score": d.get("descendants") or 0,
        })
    return items
