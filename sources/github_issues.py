"""GitHub Issues 抓取器。搜索近 7 天内含痛点关键词的 issue。
无需认证,但限 10 次搜索/分钟。
"""
import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from .base import UA

SEARCH_URL = "https://api.github.com/search/issues"

# 分两组搜索,只要 feature request / UX 类,不要 bug 类
QUERIES = [
    '"feature request" OR "please add" OR "would be nice" OR "wish this"',
    '"hard to use" OR "confusing" OR "tedious" OR "would love" OR "please support"',
]


async def fetch() -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    headers = {
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
    }

    seen: set[str] = set()
    items: list[dict] = []

    async with httpx.AsyncClient(headers=headers) as client:
        for i, keywords in enumerate(QUERIES):
            if i:
                await asyncio.sleep(6)
            q = f"is:open is:issue comments:>3 created:>{since} {keywords}"
            try:
                r = await client.get(
                    SEARCH_URL,
                    params={"q": q, "sort": "created", "order": "desc", "per_page": 30},
                    timeout=15,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"[github] query {i} failed: {e}")
                continue

            for issue in data.get("items", []):
                eid = str(issue["id"])
                if eid in seen:
                    continue
                seen.add(eid)
                items.append({
                    "source": "github",
                    "external_id": eid,
                    "title": issue.get("title", ""),
                    "content": (issue.get("body") or "")[:500],
                    "url": issue.get("html_url", ""),
                    "author": (issue.get("user") or {}).get("login"),
                    "created_at": issue.get("created_at", ""),
                    "raw_score": issue.get("comments") or 0,
                })

    return items
