"""FastAPI 入口:调度、pipeline、路由。"""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import db
from ai_scorer import run_ai_scoring
from sources import github_issues, hackernews, reddit, sspai, v2ex, zhihu
from translator import translate_new_items

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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


def matched_list(s: str | None) -> list[str]:
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []


templates.env.filters["rel_time"] = rel_time
templates.env.filters["matched"] = matched_list


async def run_all_fetchers() -> None:
    """跑一遍所有 source,单个失败不影响其它。最后跑 AI 评分。"""
    for mod in (hackernews, v2ex, reddit, zhihu, sspai, github_issues):
        name = mod.__name__.split(".")[-1]
        try:
            items = await mod.fetch()
            n = db.insert_items(items)
            print(f"[{name}] fetched {len(items)}, inserted {n}")
        except Exception as e:
            print(f"[{name}] pipeline error: {e}")
    # 先翻译英文条目,再跑 AI 打分(都是同步,放线程里不阻塞 event loop)
    try:
        await asyncio.to_thread(translate_new_items)
    except Exception as e:
        print(f"[translate] error: {e}")
    try:
        await asyncio.to_thread(run_ai_scoring)
    except Exception as e:
        print(f"[ai] scoring error: {e}")


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
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def index(
    request: Request,
    source: str | None = None,
    min_score: int = 1,
    show_starred: int | None = None,
    show_hidden: int | None = None,
    q: str | None = None,
    applied: int = 0,
):
    # applied=1 来自表单隐藏字段,区分"首次访问"和"提交了表单但 checkbox 未勾选"
    eff_starred = bool(show_starred) if applied else True
    eff_hidden = bool(show_hidden) if applied else False
    rows = db.query_items(
        source=source or None,
        min_score=min_score,
        show_starred=eff_starred,
        show_hidden=eff_hidden,
        search=q or None,
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "items": rows,
            "source": source or "",
            "min_score": min_score,
            "show_starred": 1 if eff_starred else 0,
            "show_hidden": 1 if eff_hidden else 0,
            "q": q or "",
        },
    )


@app.get("/starred")
def starred(request: Request):
    rows = db.query_starred()
    return templates.TemplateResponse(
        request,
        "starred.html",
        {"items": rows},
    )


@app.post("/star/{item_id}")
def star(item_id: int, request: Request):
    db.toggle_starred(item_id)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


@app.post("/hide/{item_id}")
def hide(item_id: int, request: Request):
    db.toggle_hidden(item_id)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
