"""掘金抓取器。拉综合推荐 feed。"""
from datetime import datetime, timezone

import httpx

from .base import UA

URL = "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed"
BODY = {
    "id_type": 2,
    "client_type": 2608,
    "sort_type": 200,
    "cursor": "0",
    "limit": 40,
}


async def fetch() -> list[dict]:
    async with httpx.AsyncClient(headers={"User-Agent": UA, "Content-Type": "application/json"}) as client:
        r = await client.post(URL, json=BODY, timeout=15)
        r.raise_for_status()
        data = r.json()

    items: list[dict] = []
    for entry in data.get("data") or []:
        if entry.get("item_type") != 2:  # 只要文章
            continue
        info = entry.get("item_info", {})
        article_info = info.get("article_info", {})
        author_info = info.get("author_user_info", {})
        aid = article_info.get("article_id")
        if not aid:
            continue
        ctime = article_info.get("ctime")
        created = ""
        if ctime:
            try:
                created = datetime.fromtimestamp(int(ctime), tz=timezone.utc).isoformat()
            except Exception:
                created = ""
        items.append({
            "source": "juejin",
            "external_id": str(aid),
            "title": article_info.get("title", ""),
            "content": article_info.get("brief_content") or "",
            "url": f"https://juejin.cn/post/{aid}",
            "author": author_info.get("user_name"),
            "created_at": created,
            "raw_score": article_info.get("comment_count") or 0,
        })
    return items
