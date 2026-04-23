# ItchFinder / Pain Dashboard — V0 实现计划

> 这是 V0 自用工具的实现计划。目标:跑通流程,代码 ≤ 800 行,尽量简洁。
> 实现时按步骤来,每完成一步停下等确认。

**Goal:** 每小时从 HN / V2EX / Reddit 抓取最新内容,关键词打分,在一个本地网页上列出按分数排序的"抱怨类"条目,支持标记/隐藏/筛选/搜索。

**Architecture:** 单进程 FastAPI 应用。APScheduler 进程内调度抓取器,SQLite 存储,Jinja2 服务端渲染。所有抓取器返回统一字典格式,由 pipeline 统一去重/打分/入库。

**Tech Stack:** Python 3.11+ / FastAPI / httpx / APScheduler / sqlite3 标准库 / Jinja2 / Tailwind CDN(待确认)

---

## 项目结构(目标)

```
ItchFinder/                  # 当前工作目录,直接做项目根
├── main.py                  # FastAPI + APScheduler + pipeline + routes  (~150 行)
├── db.py                    # sqlite3 连接、init、helpers                  (~60 行)
├── keywords.py              # 关键词列表 + score_item()                   (~40 行)
├── sources/
│   ├── __init__.py
│   ├── base.py              # Item TypedDict / normalize 辅助              (~20 行)
│   ├── hackernews.py        # 抓 HN newstories top 200                     (~60 行)
│   ├── v2ex.py              # 抓 V2EX latest                                (~40 行)
│   └── reddit.py            # 抓 5 个 subreddit 的 new                      (~50 行)
├── templates/
│   ├── base.html            # 通用布局 + 顶部导航                          (~50 行)
│   ├── index.html           # 主列表 + 筛选器 + 搜索框                    (~100 行)
│   └── starred.html         # 已标记列表                                  (~40 行)
├── data.db                  # SQLite 数据文件(运行时生成)
├── requirements.txt
└── README.md                # 装/跑/改关键词/改 subreddit                 (~40 行)
```

估算总计 **~650 行**(留有冗余)。

---

## 统一数据格式

每个抓取器的输出元素(Python dict):

```python
{
    "source": "hackernews" | "v2ex" | "reddit",
    "external_id": str,        # 平台上的唯一 ID
    "title": str,
    "content": str | None,     # 正文/摘要
    "url": str,                # 原始链接
    "author": str | None,
    "created_at": str,         # ISO-8601 UTC
    "raw_score": int | None,   # 评论数或点赞数
}
```

入库时额外计算 `pain_score` 与 `matched_keywords`,写入 `fetched_at`。

---

## 实现步骤

每一步做完我会停下,告诉你并等你验证再继续。

### Step 1 — 项目骨架 + requirements.txt

**Files:**
- Create: `requirements.txt`
- Create: `sources/__init__.py`(空文件)
- Create: 空的 `templates/` 目录占位(通过写后续文件自然创建)

**requirements.txt:**
```
fastapi>=0.110
uvicorn[standard]>=0.27
httpx>=0.27
apscheduler>=3.10
jinja2>=3.1
```

**验证:** `pip install -r requirements.txt` 成功。

---

### Step 2 — `db.py`:SQLite 连接与建表

**Files:**
- Create: `db.py`

**职责:**
- `get_conn()`:返回 `sqlite3.Connection`(`row_factory = sqlite3.Row`,`PRAGMA foreign_keys=ON`,`PRAGMA journal_mode=WAL`)
- `init_db()`:建 `items` 表和两个索引(按 spec)
- `insert_items(items)`:批量 `INSERT OR IGNORE`,返回新插入数
- `query_items(...)`:支持 source / 最小分数 / 是否含已标记 / 是否含已隐藏 / 搜索词 / 排序 的参数化查询
- `toggle_starred(id)` / `toggle_hidden(id)`:反转 `is_starred` / `is_hidden`

**关键实现点:**
- 查询时过滤用 `?` 参数化;搜索用 `title LIKE ? OR content LIKE ?`,大小写通过 `LOWER()` 处理
- `insert_items` 里每条 item 先算 `pain_score` 和 `matched_keywords`(调用 `keywords.py` 的函数),再 insert

**验证:** `python -c "import db; db.init_db(); print('ok')"` 无异常,生成 `data.db`。

---

### Step 3 — `keywords.py`:关键词与打分

**Files:**
- Create: `keywords.py`

**内容:**
- `PAIN_KEYWORDS_ZH` / `PAIN_KEYWORDS_EN`(按 spec 的列表)
- `score_item(title: str, content: str | None) -> tuple[int, list[str]]`:
  - 对每个关键词:大小写无关地在 `title` 和 `content` 中找
  - 命中标题 +2,命中正文 +1,同关键词只计一次较高分
  - 返回 `(score, [matched_keyword, ...])`

**验证:** 快速手测:
```python
from keywords import score_item
print(score_item("wish there was a better way to do X", None))
# 应该返回 (2, ['wish there was']) 之类
```

---

### Step 4 — `sources/base.py` + `sources/hackernews.py`

**Files:**
- Create: `sources/base.py`
- Create: `sources/hackernews.py`

**base.py:**
- `Item = dict`(或 TypedDict,仅类型提示用)
- `UA = "ItchFinder/0.1 (personal tool)"` 常量(给 Reddit 和其他源共用)

**hackernews.py:**
- `async def fetch() -> list[Item]`
- 步骤:
  1. GET `https://hacker-news.firebaseio.com/v0/newstories.json` → 取前 200 个 id
  2. 用 `asyncio.Semaphore(10)` 限流并发 GET 每个 item 详情
  3. 跳过 `dead` / `deleted` / `type != "story"` 的
  4. 映射到统一格式:
     - `external_id = str(id)`
     - `title = title`
     - `content = text or ""`(HN 大部分 story 没 text,留空)
     - `url = url or f"https://news.ycombinator.com/item?id={id}"`
     - `author = by`
     - `created_at = datetime.fromtimestamp(time, tz=UTC).isoformat()`
     - `raw_score = descendants`(评论数)
- 异常 log + 返回空列表(不抛)

**验证:** `python -c "import asyncio; from sources.hackernews import fetch; r = asyncio.run(fetch()); print(len(r), r[0])"` 打印数量和一条样例。

---

### Step 5 — `sources/v2ex.py`

**Files:**
- Create: `sources/v2ex.py`

**实现:**
- `async def fetch() -> list[Item]`
- GET `https://www.v2ex.com/api/topics/latest.json`(加 User-Agent)
- 每个 topic:
  - `external_id = str(id)`
  - `title = title`
  - `content = content`(V2EX 返回的是 Markdown 原文)
  - `url = url`
  - `author = member["username"]`
  - `created_at = datetime.fromtimestamp(created, tz=UTC).isoformat()`
  - `raw_score = replies`
- 异常 log + 返回 []

**验证:** 同上方式 smoke-test。

---

### Step 6 — `sources/reddit.py`

**Files:**
- Create: `sources/reddit.py`

**实现:**
- 顶部常量 `SUBREDDITS = ["SideProject", "Entrepreneur", "SaaS", "indiehackers", "smallbusiness"]`(注释说明"自己改这里")
- `async def fetch() -> list[Item]`:对每个 subreddit GET `https://www.reddit.com/r/{sub}/new.json?limit=50`(必须带 `User-Agent`)
- 每个 post(`data.children[*].data`):
  - `external_id = id`
  - `title = title`
  - `content = selftext`(外链帖为 "")
  - `url = f"https://www.reddit.com{permalink}"`
  - `author = author`
  - `created_at = datetime.fromtimestamp(created_utc, tz=UTC).isoformat()`
  - `raw_score = score`
- 并发用 `asyncio.gather`,单个 sub 失败不影响其它

**验证:** smoke-test 同上。

---

### Step 7 — `main.py`:FastAPI + Scheduler + 路由

**Files:**
- Create: `main.py`

**结构:**
```python
# 1. 依赖与初始化
app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.filters["rel_time"] = ...  # 自定义相对时间过滤器
scheduler = AsyncIOScheduler()

# 2. pipeline
async def run_all_fetchers():
    from sources import hackernews, v2ex, reddit
    for src in (hackernews, v2ex, reddit):
        try:
            items = await src.fetch()
            n = db.insert_items(items)
            print(f"[{src.__name__}] fetched {len(items)}, inserted {n}")
        except Exception as e:
            print(f"[{src.__name__}] error: {e}")

# 3. startup
@app.on_event("startup")
async def startup():
    db.init_db()
    scheduler.add_job(run_all_fetchers, "interval", hours=1,
                     next_run_time=datetime.now())
    scheduler.start()

# 4. 路由
@app.get("/")  # 主列表,读 query params,调 db.query_items,渲染 index.html
@app.get("/starred")  # 已标记列表
@app.post("/star/{id}")  # 切换 starred,重定向回来源
@app.post("/hide/{id}")  # 切换 hidden,重定向回来源
```

**相对时间 filter:** 取 `now - t`,按大小返回 "X分钟前" / "X小时前" / "X天前"。

**验证:**
- `python -m uvicorn main:app` 启动无报错
- 等 10~60 秒,三个源抓完,`/` 页先不看样式只看有没有数据(templates 还没写完,见 Step 8)
- 先只渲染一个占位页面测通连接

**备注:** 先写一个最小 `templates/base.html` + `templates/index.html` 骨架用于这步的联通测试,样式放 Step 8。

---

### Step 8 — `templates/base.html` + `templates/index.html` 完整样式

**Files:**
- Create/Overwrite: `templates/base.html`、`templates/index.html`

**base.html:**
- 引入 Tailwind CDN `<script src="https://cdn.tailwindcss.com"></script>`
- 顶部导航:站名 / "主页" / "已标记" 链接
- `{% block content %}{% endblock %}`

**index.html:**
- 顶部筛选表单(GET /,不用 JS):
  - 平台:`<select name="source">` 选项 全部/HN/V2EX/Reddit
  - 最低分:`<input name="min_score" type="number" value="{{ min_score }}">`(默认 1)
  - checkbox:`show_starred`(默认勾)、`show_hidden`(默认不勾)
  - 搜索框:`<input name="q">`
  - 提交按钮
- 列表:每条一张 card,展示:
  - 平台徽章(HN 橙、V2EX 绿、Reddit 红橙,用 Tailwind color classes)
  - 标题 `<a target="_blank" href="{{ item.url }}">`
  - 内容预览(`item.content[:200]`)
  - 一行小字:pain_score / 命中关键词 / 相对时间 / author
  - 两个 `<form method="post">`:star 和 hide(重定向回 `request.url`)
  - 已标记的行背景色区分(`bg-yellow-50`)

**验证:** 访问 `/`,看到抓来的条目,能点平台筛选、改最低分、搜索、标记、隐藏。

---

### Step 9 — `templates/starred.html`

**Files:**
- Create: `templates/starred.html`
- Modify: `main.py` — 确保 `/starred` 渲染它

**实现:** 复用 index.html 的 card 结构(用 `{% include %}` 或直接抄一份;V0 优先简单,就抄),只显示 `is_starred=1` 的条目。

**验证:** 访问 `/starred`,能看到之前标记过的所有条目。

---

### Step 10 — `README.md`

**Files:**
- Create: `README.md`

**内容(仅):**
- 简介 2 行
- 装:`pip install -r requirements.txt`
- 跑:`python -m uvicorn main:app --reload`,访问 `http://localhost:8000`
- 改关键词:编辑 `keywords.py` 里的列表
- 改 subreddit:编辑 `sources/reddit.py` 顶部的 `SUBREDDITS` 常量

---

## 验收 checklist(对应 spec 的验收标准)

- [ ] `pip install -r requirements.txt` 装好依赖
- [ ] `python -m uvicorn main:app` 启动(注:我用的是 uvicorn 命令,不是 `python main.py`;见下方决策 #7)
- [ ] 首次启动立即抓一次,之后每小时
- [ ] 页面按 pain_score 排序展示三个源的内容
- [ ] 能标记、能隐藏、能搜索、能按平台筛选
- [ ] `/starred` 可看已标记
- [ ] 重启数据不丢(`data.db` 持久化)

---

## 需要你确认的设计决策

以下是 spec 未明说、我犹豫过的点。请确认或调整:

1. **工程根目录**:当前在 `/Users/rotas/Documents/my/AIProjects/ItchFinder/`,spec 里写的是 `pain-dashboard/`。我打算**直接用当前目录作为项目根**(不再套一层 `pain-dashboard/`)。OK?

2. **样式方案**:spec 给了两个选项。我倾向 **Tailwind CDN**(零配置,类名即样式,不用写 CSS 文件)。OK?如果你希望纯手写 CSS,告诉我,我会把 CSS 写在 `static/style.css`。

3. **标记/隐藏是否可撤销**:spec 说"点击后变灰",没明说能不能再点一下取消。我打算设计为**可切换**(再点一次取消标记/取消隐藏)——因为无法取消会让误操作无法挽回。OK?

4. **Python 版本**:假定 **3.11+**(用到 `str | None` 联合类型语法)。如果你用的是更老版本告诉我,我用 `Optional`。

5. **并发抓取**:HN 要抓 200 条详情,**用 asyncio + Semaphore(10) 并发**;V2EX/Reddit 请求数少,简单 gather 即可。OK?

6. **时间存储**:DB 里统一存 ISO-8601 UTC 字符串,前端展示时转相对时间("3小时前")。OK?

7. **启动命令**:spec 里验收标准写的是 `python main.py`,但 FastAPI 通常用 `uvicorn main:app`。两种都可以做到:
   - (a) 在 `main.py` 里加 `if __name__ == "__main__": uvicorn.run(app, ...)`,保持 `python main.py` 能跑
   - (b) README 直接写 `uvicorn main:app`
   我倾向 **(a),保持 spec 验收一致**。OK?

8. **内容预览截断**:spec 说"最多 200 字"。中文字符也按 200 算?直接 `content[:200]`?OK?(简单粗暴,够用)

---

**下一步:** 你确认上面 8 个点后(或指出调整),我从 Step 1 开始实现,每完成一步停下来让你检查。
