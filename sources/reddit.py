"""Reddit 抓取器。遍历 SUBREDDITS,每个 sub 的 new 拉 limit=50。
改订阅的 subreddit 直接改下面的列表。

Reddit 对未鉴权请求很敏感:
- 必须用"看起来像浏览器"的 UA(base.UA 在这里会被拒)
- 并发会立刻触发 403/503,必须顺序拉 + 适当 sleep
- 同一 IP 被标记后要等几分钟才恢复
"""
import asyncio
from datetime import datetime, timezone

import httpx

# Reddit 会拒 base.UA 那种短 UA,必须伪装浏览器
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

SUBREDDITS = [
    "SideProject",
    "Entrepreneur",
    "SaaS",
    "indiehackers",
    "smallbusiness",
]

URL_TMPL = "https://old.reddit.com/r/{sub}/new.json?limit=50"


async def _fetch_sub(client: httpx.AsyncClient, sub: str) -> list[dict]:
    url = URL_TMPL.format(sub=sub)
    data = None
    for attempt in range(3):
        try:
            r = await client.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            print(f"[reddit/{sub}] failed after 3 tries: {e}")
            return []
    if data is None:
        return []

    items: list[dict] = []
    for child in data.get("data", {}).get("children", []):
        p = child.get("data", {})
        pid = p.get("id")
        if not pid:
            continue
        items.append({
            "source": "reddit",
            "external_id": pid,
            "title": p.get("title", ""),
            "content": p.get("selftext") or "",
            "url": f"https://www.reddit.com{p.get('permalink', '')}",
            "author": p.get("author"),
            "created_at": datetime.fromtimestamp(
                p.get("created_utc", 0), tz=timezone.utc
            ).isoformat(),
            "raw_score": p.get("score") or 0,
        })
    return items


async def fetch() -> list[dict]:
    """Reddit 未鉴权接口对并发敏感,顺序拉并短暂 sleep。"""
    flat: list[dict] = []
    # 尽量贴近 Chrome 的完整 header 集,Reddit 会筛异常组合
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for i, s in enumerate(SUBREDDITS):
            if i:
                await asyncio.sleep(1.5)
            flat.extend(await _fetch_sub(client, s))
    return flat
