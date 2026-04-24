"""Lobsters 抓取器。拉 hottest。"""
import httpx

from .base import UA

URL = "https://lobste.rs/hottest.json"


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        r = await client.get(URL, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for s in data:
        sid = s.get("short_id")
        if not sid:
            continue
        items.append({
            "source": "lobsters",
            "external_id": sid,
            "title": s.get("title", ""),
            "content": s.get("description") or "",
            "url": s.get("url") or s.get("comments_url", ""),
            "author": (s.get("submitter_user") or {}).get("username") if isinstance(s.get("submitter_user"), dict) else s.get("submitter_user"),
            "created_at": s.get("created_at", ""),
            "raw_score": s.get("comment_count") or 0,
        })
    return items
