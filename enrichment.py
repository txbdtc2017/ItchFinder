"""Scrapling-backed context enrichment for high-signal items."""
import asyncio
import re
from collections.abc import AsyncIterator

import httpx
from scrapling.parser import Selector

import db
from sources.reddit import BROWSER_UA as REDDIT_UA

DEFAULT_LIMIT = 30
POST_LIMIT = 800
COMMENT_LIMIT = 300
MAX_COMMENTS = 5
_ENRICHMENT_LOCK = asyncio.Lock()

COMMON_HEADERS = {
    "User-Agent": "ItchFinder/0.1 enrichment",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _row_value(row, key: str, default: str | None = None):
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def trim_text(text: str | None, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    return normalized[:limit]


def _selector_texts(page: Selector, selectors: list[str], limit: int) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for css in selectors:
        for node in page.css(css):
            text = trim_text(node.get_all_text() or node.text, limit)
            if text and text not in seen:
                seen.add(text)
                values.append(text)
    return values


def _format_context(post: str | None, comments: list[str]) -> str:
    sections: list[str] = []
    if post:
        sections.append(f"Post: {trim_text(post, POST_LIMIT)}")
    if comments:
        sections.append("Comments:")
        sections.extend(f"- {trim_text(comment, COMMENT_LIMIT)}" for comment in comments[:MAX_COMMENTS])
    return "\n".join(sections).strip()


def extract_reddit_context(html: str, url: str) -> str:
    page = Selector(content=html, url=url)
    posts = _selector_texts(
        page,
        [
            "[data-test-id='post-content']",
            "[data-testid='post-content']",
            "div.thing.link div.usertext-body",
            "div.link div.usertext-body",
            "div.thing.link div.md",
            "div[data-click-id='text']",
        ],
        POST_LIMIT,
    )
    comments = _selector_texts(
        page,
        [
            "[data-testid='comment'] p",
            "div.comment div.usertext-body",
            "shreddit-comment div[slot='comment']",
        ],
        COMMENT_LIMIT,
    )
    return _format_context(posts[0] if posts else None, comments)


def extract_hn_context(html: str, url: str) -> str:
    page = Selector(content=html, url=url)
    comments = _selector_texts(
        page,
        [
            "span.commtext",
            "div.comment",
        ],
        COMMENT_LIMIT,
    )
    return _format_context(None, comments[:8])


def reddit_old_url(url: str) -> str:
    return re.sub(r"https://(www\.)?reddit\.com", "https://old.reddit.com", url, count=1)


def hn_discussion_url(row) -> str:
    external_id = str(_row_value(row, "external_id") or "").strip()
    if external_id:
        return f"https://news.ycombinator.com/item?id={external_id}"
    url = _row_value(row, "url", "") or ""
    return url


def github_comments_api_url(url: str) -> str | None:
    match = re.search(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", url)
    if not match:
        return None
    owner, repo, number = match.groups()
    return f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"


async def fetch_github_api_comments(client: httpx.AsyncClient, url: str) -> list[str]:
    api_url = github_comments_api_url(url)
    if not api_url:
        return []
    response = await client.get(
        api_url,
        headers={
            "User-Agent": COMMON_HEADERS["User-Agent"],
            "Accept": "application/vnd.github+json",
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    return [trim_text(item.get("body") or "", COMMENT_LIMIT) for item in payload if item.get("body")]


def extract_github_html_context(html: str, url: str) -> str:
    page = Selector(content=html, url=url)
    comments = _selector_texts(
        page,
        [
            "td.comment-body",
            "div.comment-body",
            "div.markdown-body",
        ],
        COMMENT_LIMIT,
    )
    return _format_context(None, comments)


async def fetch_html(client: httpx.AsyncClient, url: str) -> str:
    headers = COMMON_HEADERS.copy()
    if "reddit.com" in url:
        headers["User-Agent"] = REDDIT_UA
    response = await client.get(url, headers=headers, timeout=20, follow_redirects=True)
    response.raise_for_status()
    return response.text


async def enrich_item(client: httpx.AsyncClient, row) -> str:
    source = row["source"]
    url = row["url"]
    if source == "github":
        comments = await fetch_github_api_comments(client, url)
        if comments:
            base = trim_text(row["content"], POST_LIMIT)
            return _format_context(base, comments)
        html = await fetch_html(client, url)
        return extract_github_html_context(html, url)
    if source == "reddit":
        try:
            old_url = reddit_old_url(url)
            html = await fetch_html(client, old_url)
            context = extract_reddit_context(html, old_url)
            if context:
                return context
        except Exception:
            if not _row_value(row, "content"):
                raise
        return _format_context(trim_text(_row_value(row, "content"), POST_LIMIT), [])
    if source == "hackernews":
        discussion_url = hn_discussion_url(row)
        html = await fetch_html(client, discussion_url)
        context = extract_hn_context(html, discussion_url)
        if context:
            return context
        return _format_context(trim_text(_row_value(row, "content"), POST_LIMIT), [])
    return ""


async def enrich_new_candidates(
    limit: int = DEFAULT_LIMIT,
    mode: str = "background",
    label: str = "Scrapling",
    skip_if_busy: bool = False,
) -> AsyncIterator[str]:
    if skip_if_busy and _ENRICHMENT_LOCK.locked():
        yield f"{label}: 已有补齐任务运行,跳过本轮"
        return

    async with _ENRICHMENT_LOCK:
        rows = db.get_enrichment_candidates(limit=limit, mode=mode)
        if not rows:
            yield f"{label}: 没有需要补全的候选"
            return

        yield f"{label}: 提交 {len(rows)} 条候选补全上下文..."
        done = 0
        failed = 0
        skipped = 0
        async with httpx.AsyncClient() as client:
            for row in rows:
                try:
                    content = trim_text(await enrich_item(client, row), 4000)
                    if content:
                        db.mark_enriched(row["id"], content)
                        done += 1
                    else:
                        db.mark_enrichment_skipped(row["id"], "no extractable context")
                        skipped += 1
                except Exception as exc:
                    db.mark_enrichment_failed(row["id"], str(exc))
                    failed += 1

        yield f"✓ {label}完成: {done} 条成功, {failed} 条失败, {skipped} 条跳过"
