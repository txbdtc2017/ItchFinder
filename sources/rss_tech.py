"""RSS 聚合器。一次抓多个中文科技 RSS 源。
每个 feed 失败不影响其它。feedparser 是同步的,放线程里跑。
"""
import asyncio
import hashlib
from datetime import datetime, timezone

import feedparser
import httpx

from .base import UA

FEEDS = [
    ("36kr", "https://36kr.com/feed"),
    ("appinn", "https://www.appinn.com/feed/"),
    ("huxiu", "https://www.huxiu.com/rss/0.xml"),
]

RSS_TIMEOUT = 12


def _parse_feed_content(name: str, content: bytes) -> list[dict]:
    try:
        d = feedparser.parse(content)
    except Exception as e:
        print(f"[rss_tech/{name}] parse failed: {e}")
        return []

    items: list[dict] = []
    for e in d.entries[:50]:
        link = e.get("link") or ""
        eid = e.get("id") or link
        if not eid:
            continue
        # 用 md5 保证长度可控 + 不会冲突
        ext_id = hashlib.md5(f"{name}:{eid}".encode()).hexdigest()[:16]

        # 发布时间
        created = ""
        for key in ("published_parsed", "updated_parsed"):
            t = e.get(key)
            if t:
                try:
                    created = datetime(*t[:6], tzinfo=timezone.utc).isoformat()
                    break
                except Exception:
                    pass

        items.append({
            "source": "rss_tech",
            "external_id": ext_id,
            "title": e.get("title", ""),
            "content": (e.get("summary") or e.get("description") or "")[:500],
            "url": link,
            "author": e.get("author"),
            "created_at": created or datetime.now(timezone.utc).isoformat(),
            "raw_score": 0,
        })
    return items


async def fetch() -> list[dict]:
    flat: list[dict] = []
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True) as client:
        for name, url in FEEDS:
            try:
                response = await client.get(url, timeout=RSS_TIMEOUT)
                response.raise_for_status()
                items = await asyncio.to_thread(_parse_feed_content, name, response.content)
                flat.extend(items)
            except Exception as e:
                print(f"[rss_tech/{name}] failed: {e}")
    return flat
