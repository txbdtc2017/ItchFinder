"""FastAPI 入口:调度、pipeline、路由。"""
import asyncio
import json
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

import db
from ai_scorer import run_ai_scoring, summarize_ai_flagged
from enrichment import enrich_new_candidates
from sources import (
    devto,
    github_issues,
    hackernews,
    juejin,
    lobsters,
    reddit,
    rss_tech,
    sspai,
    stackoverflow,
    v2ex,
    zhihu,
)
from translator import translate_new_items

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
PAGE_SIZE = 10
PRE_AI_ENRICHMENT_LIMIT = 10
POST_AI_ENRICHMENT_LIMIT = 20
BACKGROUND_ENRICHMENT_LIMIT = 20


def rel_time(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        t = datetime.fromisoformat(iso)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except Exception:
        return iso
    diff = (datetime.now(timezone.utc) - t).total_seconds()
    if diff < 60:
        return "刚刚"
    if diff < 3600:
        return f"{int(diff // 60)}分钟前"
    if diff < 86400:
        return f"{int(diff // 3600)}小时前"
    if diff < 86400 * 30:
        return f"{int(diff // 86400)}天前"
    return t.strftime("%Y-%m-%d")


def abs_time(iso: str | None) -> str:
    """ISO UTC 转本地时区的 'MM-DD HH:MM'。"""
    if not iso:
        return ""
    try:
        t = datetime.fromisoformat(iso)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t.astimezone().strftime("%m-%d %H:%M")
    except Exception:
        return iso


def matched_list(s: str | None) -> list[str]:
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []


templates.env.filters["rel_time"] = rel_time
templates.env.filters["abs_time"] = abs_time
templates.env.filters["matched"] = matched_list
templates.env.globals["recent_refreshes"] = lambda: db.get_recent_refreshes(8)
templates.env.globals["parse_json"] = json.loads


SOURCE_NAMES = {
    "hackernews": "HN", "v2ex": "V2EX", "reddit": "Reddit",
    "zhihu": "知乎", "sspai": "少数派", "github_issues": "GitHub Issues",
    "devto": "Dev.to", "lobsters": "Lobsters", "stackoverflow": "StackOverflow",
    "juejin": "掘金", "rss_tech": "科技 RSS",
}


async def run_all_fetchers() -> None:
    """调度任务入口,打印到日志。"""
    async for msg in pipeline_events(trigger="scheduled"):
        print(f"[pipeline] {msg}")


async def run_background_enrichment() -> None:
    async for msg in enrich_new_candidates(
        limit=BACKGROUND_ENRICHMENT_LIMIT,
        mode="background",
        label="Scrapling后台补齐",
        skip_if_busy=True,
    ):
        print(f"[background-enrichment] {msg}")


async def pipeline_events(trigger: str = "manual"):
    """async generator:逐步 yield 进度字符串。供调度任务和 SSE 共用。结束时写 refresh_log。"""
    stats: dict[str, int] = {}
    for mod in (
        hackernews, v2ex, reddit, zhihu, sspai, github_issues,
        devto, lobsters, stackoverflow, juejin, rss_tech,
    ):
        key = mod.__name__.split(".")[-1]
        name = SOURCE_NAMES.get(key, key)
        yield f"正在抓取 {name}..."
        try:
            items = await mod.fetch()
            total, high = db.insert_items(items)
            stats[name] = high  # 只计入选条数
            yield f"✓ {name}: 抓取 {len(items)} 条, 入库 {total} 条, 入选 {high} 条"
        except Exception as e:
            stats[name] = 0
            yield f"✗ {name} 失败: {str(e)[:80]}"

    async for m in enrich_new_candidates(
        limit=PRE_AI_ENRICHMENT_LIMIT,
        mode="pre_ai",
        label="Scrapling预补齐",
    ):
        yield m

    # 高分候选先补上下文再评分;AI 推荐项再补一次,让总结尽量拿到上下文。
    async for m in run_ai_scoring():
        yield m

    async for m in enrich_new_candidates(
        limit=POST_AI_ENRICHMENT_LIMIT,
        mode="ai_flagged",
        label="Scrapling推荐补齐",
    ):
        yield m

    async for m in summarize_ai_flagged():
        yield m

    async for m in translate_new_items():
        yield m

    db.log_refresh(trigger, sum(stats.values()), stats)


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler.add_job(
        run_all_fetchers,
        "interval",
        hours=1,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        run_background_enrichment,
        "interval",
        minutes=2,
        next_run_time=datetime.now() + timedelta(minutes=2),
        id="background_enrichment",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


def _bool_param(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "none", "null"}
    return bool(value)


def _pagination(page: int, total_count: int, page_size: int = PAGE_SIZE) -> tuple[int, int, int]:
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    current_page = min(max(page, 1), total_pages)
    offset = (current_page - 1) * page_size
    return current_page, total_pages, offset


def _index_page_url_prefix(
    source: str,
    min_score: int,
    show_starred: int,
    show_hidden: int,
    only_ai: int,
    q: str,
) -> str:
    params = {
        "applied": 1,
        "source": source,
        "min_score": min_score,
        "show_starred": show_starred,
        "show_hidden": show_hidden,
        "only_ai": only_ai,
        "q": q,
        "page": "",
    }
    return "/?" + urlencode(params)


@app.get("/")
def index(
    request: Request,
    source: str | None = None,
    min_score: int = 1,
    show_starred: int | None = None,
    show_hidden: int | None = None,
    q: str | None = None,
    only_ai: int | None = None,
    applied: int = 0,
    page: int = 1,
):
    # applied=1 来自表单隐藏字段,区分"首次访问"和"提交了表单但 checkbox 未勾选"
    eff_starred = bool(show_starred) if applied else True
    eff_hidden = bool(show_hidden) if applied else False
    # only_ai 默认 True(首次访问只看 AI 推荐),用户点按钮后可关
    eff_only_ai = bool(only_ai) if applied else True
    total_count = db.count_items(
        source=source or None,
        min_score=min_score,
        show_starred=eff_starred,
        show_hidden=eff_hidden,
        search=q or None,
        only_ai=eff_only_ai,
    )
    page, total_pages, offset = _pagination(page, total_count)
    rows = db.query_items(
        source=source or None,
        min_score=min_score,
        show_starred=eff_starred,
        show_hidden=eff_hidden,
        search=q or None,
        only_ai=eff_only_ai,
        limit=PAGE_SIZE,
        offset=offset,
    )
    source_value = source or ""
    q_value = q or ""
    show_starred_value = 1 if eff_starred else 0
    show_hidden_value = 1 if eff_hidden else 0
    only_ai_value = 1 if eff_only_ai else 0
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "items": rows,
            "source": source_value,
            "min_score": min_score,
            "show_starred": show_starred_value,
            "show_hidden": show_hidden_value,
            "q": q_value,
            "only_ai": only_ai_value,
            "page": page,
            "page_size": PAGE_SIZE,
            "total_count": total_count,
            "total_pages": total_pages,
            "page_url_prefix": _index_page_url_prefix(
                source_value,
                min_score,
                show_starred_value,
                show_hidden_value,
                only_ai_value,
                q_value,
            ),
        },
    )


@app.get("/starred")
def starred(request: Request, page: int = 1):
    total_count = db.count_starred()
    page, total_pages, offset = _pagination(page, total_count)
    rows = db.query_starred(limit=PAGE_SIZE, offset=offset)
    return templates.TemplateResponse(
        request,
        "starred.html",
        {
            "items": rows,
            "page": page,
            "page_size": PAGE_SIZE,
            "total_count": total_count,
            "total_pages": total_pages,
            "page_url_prefix": "/starred?page=",
        },
    )


@app.get("/refresh/stream")
async def refresh_stream():
    async def event_gen():
        async for msg in pipeline_events():
            # 每条消息前加 "data: ",最后 \n\n 表示一条 SSE event
            yield f"data: {msg}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/star/{item_id}")
def star(item_id: int, request: Request):
    db.toggle_starred(item_id)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


@app.post("/hide/{item_id}")
def hide(item_id: int, request: Request):
    db.toggle_hidden(item_id)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


@app.post("/hide_all")
async def hide_all(request: Request):
    body = await request.json()
    applied = int(body.get("applied", 0))
    only_ai = body.get("only_ai")
    show_starred = body.get("show_starred")
    eff_starred = _bool_param(show_starred) if applied else True
    eff_only_ai = _bool_param(only_ai) if applied else True
    n = db.hide_all_matching(
        source=body.get("source") or None,
        min_score=int(body.get("min_score", 1)),
        show_starred=eff_starred,
        show_hidden=False,
        search=body.get("q") or None,
        only_ai=eff_only_ai,
    )
    return {"hidden": n}


@app.post("/translate")
async def translate_text(request: Request):
    body = await request.json()
    text = body.get("text", "")
    if not text:
        return {"translated": ""}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text},
            timeout=10,
        )
        r.raise_for_status()
        result = r.json()
    translated = "".join(p[0] for p in result[0] if p[0])
    return {"translated": translated}


def _localhost_port_available(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=0.2):
            return False
    except OSError:
        pass

    probes = [("127.0.0.1", socket.AF_INET)]
    if socket.has_ipv6:
        probes.append(("::1", socket.AF_INET6))

    for host, family in probes:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
        except OSError:
            return False
    return True


def _find_local_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    for port in range(start_port, start_port + max_attempts):
        if _localhost_port_available(port):
            return port
    end_port = start_port + max_attempts - 1
    raise RuntimeError(f"No available localhost port in range {start_port}-{end_port}")


def _resolve_bind_address() -> tuple[str, int]:
    host = os.getenv("ITCHFINDER_HOST", "127.0.0.1")
    start_port = int(os.getenv("ITCHFINDER_PORT", "8000"))
    if host in {"127.0.0.1", "localhost"}:
        return host, _find_local_port(start_port)
    return host, start_port


def _resolve_public_url(host: str, port: int) -> str:
    if public_url := os.getenv("ITCHFINDER_PUBLIC_URL"):
        return public_url
    open_host = "127.0.0.1" if host == "0.0.0.0" else host
    return f"http://{open_host}:{port}"


if __name__ == "__main__":
    import uvicorn

    host, port = _resolve_bind_address()
    if port != 8000:
        print(f"[ItchFinder] localhost:8000 is busy; using 127.0.0.1:{port}", flush=True)
    print(f"[ItchFinder] Open {_resolve_public_url(host, port)}", flush=True)
    uvicorn.run("main:app", host=host, port=port, reload=False)
