# Scrapling Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user explicitly does not use git worktrees for Codex development, so execute in the current repository checkout.

**Goal:** Integrate Scrapling into ItchFinder as a bounded enrichment layer that adds source context before AI scoring and shows AI summaries plus expandable raw excerpts in the dashboard.

**Architecture:** Keep existing source fetchers and Docker runtime. Add a focused enrichment module that fetches candidate item pages with `httpx`, parses HTML with `scrapling.parser.Selector`, stores concise plain-text excerpts in SQLite, then lets AI scoring and summary generation use that context. Run enrichment automatically in the refresh pipeline after `db.insert_items()` and before AI scoring.

**Tech Stack:** Python 3.11 / FastAPI / SQLite / httpx / Scrapling `Selector` / MiniMax Anthropic-compatible API / Jinja2 / Docker Compose.

---

## Pre-Execution Confirmations

Plan approval means these decisions are accepted for this implementation run:

- Execute in `/Users/rotas/Documents/my/AIProjects/ItchFinder`; no git worktree.
- Use PyPI dependency `scrapling>=0.4.7`; do not use local `/Users/rotas/Documents/my/learnai/Scrapling`.
- Keep Scrapling parser-only for this version; fetching stays on `httpx`.
- Use mocks and fixtures for tests; no live network calls inside unit tests.
- Runtime continues on Docker Compose service `itchfinder`, host port `18081`, container port `8000`.
- When a task changes runtime dependencies or app code, rebuild/restart with `docker compose up -d --build itchfinder` before runtime verification.
- Existing uncommitted Docker/spec/test work is handled first as a baseline task, then Scrapling work starts from a clean committed baseline.
- After plan approval, each task below runs tests, reviews its diff, commits with a Chinese message, and pushes to `origin main`.

## Existing Uncommitted Baseline

Current working tree contains already-approved Docker/runtime/spec changes:

- `README.md`
- `main.py`
- `.dockerignore`
- `Dockerfile`
- `docker-compose.yml`
- `docs/current_status.md`
- `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`
- `tests/test_docker_config.py`
- `tests/test_main_entrypoint.py`

These are not part of Scrapling behavior, but they must be committed before task-by-task Scrapling commits stay readable.

## Target File Structure

Files created:

- `/Users/rotas/Documents/my/AIProjects/ItchFinder/enrichment.py`  
  Fetch and parse candidate item context. Owns source-specific extraction for Reddit, Hacker News, and GitHub Issues.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_db_enrichment.py`  
  SQLite schema, candidate selection, retry cooldown, and summary persistence tests.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_enrichment.py`  
  Scrapling parser extraction and enrichment orchestration tests using local HTML/API fixtures.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_pipeline_enrichment.py`  
  Refresh pipeline order tests.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_ai_scorer_enrichment.py`  
  Prompt-building and summary persistence tests without live API calls.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_templates_enrichment.py`  
  Dashboard rendering test for AI summary and collapsed raw context.

Files modified:

- `/Users/rotas/Documents/my/AIProjects/ItchFinder/requirements.txt`  
  Add Scrapling dependency.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/db.py`  
  Add enrichment and summary columns plus helper functions.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/ai_scorer.py`  
  Include enriched context in scoring prompt and add summary generation.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py`  
  Insert enrichment and summary stages into refresh pipeline.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/index.html`  
  Render AI summary, enrichment status, and collapsed raw excerpts.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/starred.html`  
  Keep starred view consistent with summary/raw context display.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/README.md`  
  Document Docker run, Scrapling enrichment, and verification commands.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/current_status.md`  
  Keep live status concise and link this plan.
- `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`  
  Keep the explicit compromise list as the source of later optimization points.

## Task 0: Commit Current Docker And Spec Baseline

**Files:**
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/README.md`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/.dockerignore`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/Dockerfile`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/docker-compose.yml`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/current_status.md`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_docker_config.py`
- Review: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_main_entrypoint.py`

- [ ] **Step 1: Inspect baseline diff**

Run:

```bash
git diff -- README.md main.py .dockerignore Dockerfile docker-compose.yml docs/current_status.md docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md tests/test_docker_config.py tests/test_main_entrypoint.py
```

Expected: diff only contains Docker runtime, port handling, tests, current status, and Scrapling design spec from the prior approved discussion.

- [ ] **Step 2: Run baseline tests**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
docker compose config --quiet
```

Expected: unittest passes all current tests; compose config returns exit code 0.

- [ ] **Step 3: Review status before commit**

Run:

```bash
git status --short
```

Expected: only the baseline files plus this plan file are uncommitted. If this plan file is uncommitted, include it in the baseline commit so the implementation has a reviewed plan in Git.

- [ ] **Step 4: Commit and push baseline**

Run:

```bash
git add README.md main.py .dockerignore Dockerfile docker-compose.yml docs/current_status.md docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md docs/superpowers/plans/2026-05-03-scrapling-enrichment.md tests/test_docker_config.py tests/test_main_entrypoint.py
git commit -m "chore: Docker化项目并记录Scrapling方案"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.

## Task 1: Add Enrichment Schema And DB Helpers

**Files:**
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/db.py`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_db_enrichment.py`

- [ ] **Step 1: Write failing DB tests**

Create `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_db_enrichment.py`:

```python
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import db


class EnrichmentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.tmpdir.name) / "data.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmpdir.cleanup()

    def _insert_item(self, **overrides):
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "source": "reddit",
            "external_id": overrides.pop("external_id", "r1"),
            "title": overrides.pop("title", "wish there was a better workflow"),
            "content": overrides.pop("content", "manual reporting is painful"),
            "url": overrides.pop("url", "https://www.reddit.com/r/test/comments/r1/title/"),
            "author": overrides.pop("author", "alice"),
            "created_at": overrides.pop("created_at", now),
            "raw_score": overrides.pop("raw_score", 12),
        }
        item.update(overrides)
        with mock.patch("keywords.score_item", return_value=(2, ["wish there was"])):
            db.insert_items([item])
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM items WHERE external_id = ?", (item["external_id"],)).fetchone()
            return row["id"]

    def test_init_db_adds_enrichment_and_summary_columns(self):
        with db.get_conn() as conn:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(items)").fetchall()}

        self.assertIn("enriched_content", cols)
        self.assertIn("enriched_at", cols)
        self.assertIn("enrichment_status", cols)
        self.assertIn("enrichment_error", cols)
        self.assertIn("ai_summary", cols)
        self.assertIn("ai_summary_at", cols)

    def test_get_enrichment_candidates_filters_sources_and_done_rows(self):
        reddit_id = self._insert_item(external_id="r1", source="reddit")
        self._insert_item(external_id="v1", source="v2ex", url="https://v2ex.com/t/1")
        github_id = self._insert_item(
            external_id="g1",
            source="github",
            url="https://github.com/acme/tool/issues/42",
        )
        db.mark_enriched(reddit_id, "Post: already enriched")

        rows = db.get_enrichment_candidates(limit=30)

        self.assertEqual([row["id"] for row in rows], [github_id])

    def test_failed_enrichment_retries_after_cooldown(self):
        item_id = self._insert_item(external_id="r2")
        db.mark_enrichment_failed(item_id, "blocked")

        fresh_rows = db.get_enrichment_candidates(limit=30, cooldown_hours=24)
        self.assertEqual(fresh_rows, [])

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        with db.get_conn() as conn:
            conn.execute("UPDATE items SET enriched_at = ? WHERE id = ?", (old_ts, item_id))

        retry_rows = db.get_enrichment_candidates(limit=30, cooldown_hours=24)
        self.assertEqual([row["id"] for row in retry_rows], [item_id])

    def test_summary_candidate_and_update_helpers(self):
        item_id = self._insert_item(external_id="r3")
        with db.get_conn() as conn:
            conn.execute("UPDATE items SET ai_flagged = 1 WHERE id = ?", (item_id,))

        rows = db.get_ai_summary_candidates(limit=10)
        self.assertEqual([row["id"] for row in rows], [item_id])

        db.update_ai_summary(item_id, "用户痛点：整理很慢\n现有方案缺口：工具割裂\n可做产品机会：自动汇总")

        rows_after = db.get_ai_summary_candidates(limit=10)
        self.assertEqual(rows_after, [])
        with db.get_conn() as conn:
            row = conn.execute("SELECT ai_summary, ai_summary_at FROM items WHERE id = ?", (item_id,)).fetchone()
        self.assertIn("用户痛点", row["ai_summary"])
        self.assertIsNotNone(row["ai_summary_at"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_db_enrichment
```

Expected: fails because the new DB columns and helper functions do not exist.

- [ ] **Step 3: Implement schema columns**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/db.py` inside `init_db()` after the existing incremental column loop:

```python
        for col, col_type in [
            ("enriched_content", "TEXT"),
            ("enriched_at", "TEXT"),
            ("enrichment_status", "TEXT DEFAULT 'pending'"),
            ("enrichment_error", "TEXT"),
            ("ai_summary", "TEXT"),
            ("ai_summary_at", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE items ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
```

- [ ] **Step 4: Implement enrichment and summary helpers**

Add these functions to `/Users/rotas/Documents/my/AIProjects/ItchFinder/db.py` after `get_unscored_items()`:

```python
def get_enrichment_candidates(limit: int = 30, cooldown_hours: int = 24) -> list[sqlite3.Row]:
    """取需要补全上下文的高信号候选。失败项过冷却期后重试。"""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
    ).isoformat()
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, source, title, content, url, pain_score, enriched_content,
                   enriched_at, enrichment_status, enrichment_error
            FROM items
            WHERE pain_score > 0
              AND source IN ('reddit', 'hackernews', 'github')
              AND COALESCE(enrichment_status, 'pending') != 'done'
              AND (
                    COALESCE(enrichment_status, 'pending') = 'pending'
                    OR (
                        enrichment_status = 'failed'
                        AND COALESCE(enriched_at, '') <= ?
                    )
                  )
            ORDER BY pain_score DESC, created_at DESC
            LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()


def mark_enriched(item_id: int, content: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE items
            SET enriched_content = ?,
                enriched_at = ?,
                enrichment_status = 'done',
                enrichment_error = NULL
            WHERE id = ?
            """,
            (content, now, item_id),
        )


def mark_enrichment_failed(item_id: int, error: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    short_error = error[:300]
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE items
            SET enriched_at = ?,
                enrichment_status = 'failed',
                enrichment_error = ?
            WHERE id = ?
            """,
            (now, short_error, item_id),
        )


def get_ai_summary_candidates(limit: int = 30) -> list[sqlite3.Row]:
    """取已被 AI 标记但还没有总结的条目。"""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, source, title, content, enriched_content
            FROM items
            WHERE ai_flagged = 1
              AND ai_summary IS NULL
            ORDER BY pain_score DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def update_ai_summary(item_id: int, summary: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE items SET ai_summary = ?, ai_summary_at = ? WHERE id = ?",
            (summary, now, item_id),
        )
```

Also add `timedelta` to the import line:

```python
from datetime import datetime, timedelta, timezone
```

- [ ] **Step 5: Include enriched content in unscored item rows**

Change `get_unscored_items()` query from:

```python
"SELECT id, source, title, content FROM items "
```

to:

```python
"SELECT id, source, title, content, enriched_content FROM items "
```

- [ ] **Step 6: Run DB and full tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_db_enrichment
.venv/bin/python -m unittest discover -s tests
```

Expected: new DB tests pass; full suite passes.

- [ ] **Step 7: Review, commit, and push**

Run:

```bash
git diff -- db.py tests/test_db_enrichment.py
git status --short
git add db.py tests/test_db_enrichment.py
git commit -m "feat: 增加补全数据模型"
git push origin main
```

Expected: commit and push succeed.

## Task 2: Add Scrapling Enrichment Parser

**Files:**
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/requirements.txt`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/enrichment.py`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_enrichment.py`

- [ ] **Step 1: Write failing enrichment tests**

Create `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_enrichment.py`:

```python
import unittest
from unittest import mock

import enrichment


REDDIT_HTML = """
<html><body>
  <div data-test-id="post-content"><p>I spend hours copying reports by hand.</p></div>
  <div data-testid="comment"><p>Same here, every client wants a different format.</p></div>
  <div data-testid="comment"><p>I tried spreadsheets but the handoff still breaks.</p></div>
</body></html>
"""

HN_HTML = """
<html><body>
  <tr class="athing comtr"><td class="default"><div class="comment"><span class="commtext">I wish deploy logs were easier to compare.</span></div></td></tr>
  <tr class="athing comtr"><td class="default"><div class="comment"><span class="commtext">Existing dashboards hide the useful failure context.</span></div></td></tr>
</body></html>
"""

GITHUB_HTML = """
<html><body>
  <td class="comment-body"><p>The setup flow is confusing for non-admin users.</p></td>
  <td class="comment-body"><p>Please support exporting the audit trail.</p></td>
</body></html>
"""


class EnrichmentParserTests(unittest.TestCase):
    def test_trim_text_collapses_whitespace_and_limits_length(self):
        text = "  a\\n\\n  b\\t c  " + ("x" * 1000)
        trimmed = enrichment.trim_text(text, 20)
        self.assertEqual(trimmed, "a b c xxxxxxxxxxxxxx")
        self.assertEqual(len(trimmed), 20)

    def test_reddit_extractor_returns_post_and_limited_comments(self):
        result = enrichment.extract_reddit_context(REDDIT_HTML, "https://www.reddit.com/r/test/comments/abc/title/")

        self.assertIn("Post: I spend hours copying reports by hand.", result)
        self.assertIn("Comments:", result)
        self.assertIn("- Same here, every client wants a different format.", result)
        self.assertIn("- I tried spreadsheets but the handoff still breaks.", result)

    def test_hn_extractor_returns_ordered_comments(self):
        result = enrichment.extract_hn_context(HN_HTML, "https://news.ycombinator.com/item?id=1")

        self.assertIn("Comments:", result)
        self.assertLess(
            result.index("I wish deploy logs"),
            result.index("Existing dashboards"),
        )

    def test_github_api_url_parser_accepts_issue_urls(self):
        api_url = enrichment.github_comments_api_url("https://github.com/acme/tool/issues/42")

        self.assertEqual(
            api_url,
            "https://api.github.com/repos/acme/tool/issues/42/comments",
        )

    def test_github_html_fallback_extracts_issue_comments(self):
        result = enrichment.extract_github_html_context(GITHUB_HTML, "https://github.com/acme/tool/issues/42")

        self.assertIn("Comments:", result)
        self.assertIn("- The setup flow is confusing for non-admin users.", result)
        self.assertIn("- Please support exporting the audit trail.", result)

    def test_enrich_new_candidates_marks_success_and_failure(self):
        rows = [
            {"id": 1, "source": "reddit", "url": "https://www.reddit.com/r/test/comments/abc/title/"},
            {"id": 2, "source": "hackernews", "url": "https://news.ycombinator.com/item?id=1"},
        ]

        async def fake_fetch_html(client, url):
            if "reddit" in url:
                return REDDIT_HTML
            raise RuntimeError("network blocked")

        async def run():
            messages = []
            with mock.patch("db.get_enrichment_candidates", return_value=rows), \
                 mock.patch("db.mark_enriched") as mark_enriched, \
                 mock.patch("db.mark_enrichment_failed") as mark_failed, \
                 mock.patch.object(enrichment, "fetch_html", side_effect=fake_fetch_html):
                async for message in enrichment.enrich_new_candidates(limit=30):
                    messages.append(message)
            return messages, mark_enriched, mark_failed

        import asyncio
        messages, mark_enriched, mark_failed = asyncio.run(run())

        self.assertTrue(any("提交 2 条候选" in message for message in messages))
        mark_enriched.assert_called_once()
        self.assertEqual(mark_enriched.call_args.args[0], 1)
        mark_failed.assert_called_once()
        self.assertEqual(mark_failed.call_args.args[0], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_enrichment
```

Expected: fails because `enrichment.py` and Scrapling dependency are not present.

- [ ] **Step 3: Add Scrapling dependency**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/requirements.txt`:

```text
fastapi>=0.110
uvicorn[standard]>=0.27
httpx>=0.27
apscheduler>=3.10
jinja2>=3.1
anthropic>=0.40
python-dotenv>=1.0
feedparser>=6.0
scrapling>=0.4.7
```

- [ ] **Step 4: Implement parser and orchestration module**

Create `/Users/rotas/Documents/my/AIProjects/ItchFinder/enrichment.py`:

```python
"""Scrapling-backed context enrichment for high-signal items."""
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

COMMON_HEADERS = {
    "User-Agent": "ItchFinder/0.1 enrichment",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def trim_text(text: str | None, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    return normalized[:limit]


def _selector_texts(page: Selector, selectors: list[str], limit: int) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for css in selectors:
        for node in page.css(css):
            text = trim_text(node.text, limit)
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
            "div.usertext-body",
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
    html = await fetch_html(client, url)
    if source == "reddit":
        return extract_reddit_context(html, url)
    if source == "hackernews":
        return extract_hn_context(html, url)
    return ""


async def enrich_new_candidates(limit: int = DEFAULT_LIMIT) -> AsyncIterator[str]:
    rows = db.get_enrichment_candidates(limit=limit)
    if not rows:
        yield "Scrapling: 没有需要补全的候选"
        return

    yield f"Scrapling: 提交 {len(rows)} 条候选补全上下文..."
    done = 0
    failed = 0
    async with httpx.AsyncClient() as client:
        for row in rows:
            try:
                content = trim_text(await enrich_item(client, row), 4000)
                if content:
                    db.mark_enriched(row["id"], content)
                    done += 1
                else:
                    db.mark_enrichment_failed(row["id"], "empty enrichment result")
                    failed += 1
            except Exception as exc:
                db.mark_enrichment_failed(row["id"], str(exc))
                failed += 1

    yield f"✓ Scrapling 补全完成: {done} 条成功, {failed} 条失败"
```

- [ ] **Step 5: Install dependency locally and run tests**

Run:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest tests.test_enrichment
.venv/bin/python -m unittest discover -s tests
```

Expected: Scrapling installs successfully; enrichment tests and full test suite pass.

- [ ] **Step 6: Review, commit, and push**

Run:

```bash
git diff -- requirements.txt enrichment.py tests/test_enrichment.py
git status --short
git add requirements.txt enrichment.py tests/test_enrichment.py
git commit -m "feat: 接入Scrapling上下文解析"
git push origin main
```

Expected: commit and push succeed.

## Task 3: Wire Enrichment Into Refresh Pipeline

**Files:**
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_pipeline_enrichment.py`

- [ ] **Step 1: Write failing pipeline order test**

Create `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_pipeline_enrichment.py`:

```python
import asyncio
import unittest
from unittest import mock

import main


class PipelineEnrichmentOrderTests(unittest.TestCase):
    def test_pipeline_runs_enrichment_after_fetchers_and_before_ai(self):
        events = []

        async def fake_fetch():
            return [{
                "source": "reddit",
                "external_id": "r1",
                "title": "wish reports were automatic",
                "content": "manual reporting hurts",
                "url": "https://www.reddit.com/r/test/comments/r1/title/",
                "author": "alice",
                "created_at": "2026-05-03T00:00:00+00:00",
                "raw_score": 5,
            }]

        async def empty_fetch():
            return []

        async def fake_enrich_new_candidates(limit=30):
            events.append("enrich")
            yield "Scrapling: done"

        async def fake_run_ai_scoring():
            events.append("ai")
            yield "AI: done"

        async def fake_translate_new_items():
            events.append("translate")
            yield "translate: done"

        async def run():
            with mock.patch.object(main.hackernews, "fetch", side_effect=fake_fetch), \
                 mock.patch.object(main.v2ex, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.reddit, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.zhihu, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.sspai, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.github_issues, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.devto, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.lobsters, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.stackoverflow, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.juejin, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.rss_tech, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.db, "insert_items", return_value=(1, 1)) as insert_items, \
                 mock.patch.object(main.db, "log_refresh") as log_refresh, \
                 mock.patch.object(main, "enrich_new_candidates", side_effect=fake_enrich_new_candidates), \
                 mock.patch.object(main, "run_ai_scoring", side_effect=fake_run_ai_scoring), \
                 mock.patch.object(main, "translate_new_items", side_effect=fake_translate_new_items):
                messages = [message async for message in main.pipeline_events(trigger="manual")]
            return messages, insert_items, log_refresh

        messages, insert_items, log_refresh = asyncio.run(run())

        self.assertEqual(events, ["enrich", "ai", "translate"])
        self.assertIn("Scrapling: done", messages)
        insert_items.assert_called()
        log_refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_pipeline_enrichment
```

Expected: fails because `main.enrich_new_candidates` is not imported and pipeline does not run it.

- [ ] **Step 3: Import enrichment stage**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py` imports:

```python
from ai_scorer import run_ai_scoring
from enrichment import enrich_new_candidates
```

- [ ] **Step 4: Insert enrichment before AI scoring**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py` inside `pipeline_events()` after the fetcher loop and before `run_ai_scoring()`:

```python
    async for m in enrich_new_candidates(limit=30):
        yield m

    # 先补全上下文,再 AI 评分(决定 ai_flagged),再翻译(只翻被推荐的),省时省钱
    async for m in run_ai_scoring():
        yield m
```

Remove or update the old comment that said AI scoring happens directly after insertion.

- [ ] **Step 5: Run pipeline and full tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_pipeline_enrichment
.venv/bin/python -m unittest discover -s tests
```

Expected: pipeline order test and full suite pass.

- [ ] **Step 6: Review, commit, and push**

Run:

```bash
git diff -- main.py tests/test_pipeline_enrichment.py
git status --short
git add main.py tests/test_pipeline_enrichment.py
git commit -m "feat: 在刷新流程中自动补全上下文"
git push origin main
```

Expected: commit and push succeed.

## Task 4: Use Enriched Content In AI Scoring And Generate Summaries

**Files:**
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/ai_scorer.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_ai_scorer_enrichment.py`

- [ ] **Step 1: Write failing AI scorer tests**

Create `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_ai_scorer_enrichment.py`:

```python
import asyncio
import unittest
from unittest import mock

import ai_scorer


class AIScorerEnrichmentTests(unittest.TestCase):
    def test_build_scoring_prompt_includes_enriched_context(self):
        rows = [{
            "id": 7,
            "title": "Need better reporting",
            "content": "Reports are manual",
            "enriched_content": "Comments:\\n- Every week I copy the same dashboard",
        }]

        prompt = ai_scorer._build_scoring_prompt(rows)

        self.assertIn("[ID:7] Need better reporting", prompt)
        self.assertIn("Reports are manual", prompt)
        self.assertIn("Every week I copy the same dashboard", prompt)

    def test_parse_flagged_ids_handles_json_array(self):
        self.assertEqual(ai_scorer._parse_flagged_ids("```json\\n[1, 3]\\n```"), [1, 3])

    def test_parse_summary_response_extracts_id_summary_map(self):
        text = '{"7": "用户痛点：慢\\n现有方案缺口：散\\n可做产品机会：自动汇总"}'

        parsed = ai_scorer._parse_summary_response(text)

        self.assertEqual(parsed[7], "用户痛点：慢\n现有方案缺口：散\n可做产品机会：自动汇总")

    def test_summarize_ai_flagged_persists_model_summaries(self):
        rows = [{
            "id": 7,
            "title": "Need better reporting",
            "content": "Reports are manual",
            "enriched_content": "Comments:\\n- Every week I copy the same dashboard",
        }]

        async def run():
            with mock.patch.dict("os.environ", {"MINIMAX_API_KEY": "test-key"}, clear=True), \
                 mock.patch.object(ai_scorer.db, "get_ai_summary_candidates", return_value=rows), \
                 mock.patch.object(ai_scorer, "_call_minimax_summaries", return_value={7: "用户痛点：慢"}), \
                 mock.patch.object(ai_scorer.db, "update_ai_summary") as update_ai_summary:
                messages = [message async for message in ai_scorer.summarize_ai_flagged()]
            return messages, update_ai_summary

        messages, update_ai_summary = asyncio.run(run())

        self.assertTrue(any("AI总结" in message for message in messages))
        update_ai_summary.assert_called_once_with(7, "用户痛点：慢")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_ai_scorer_enrichment
```

Expected: fails because prompt builder, parsers, and summary generator do not exist.

- [ ] **Step 3: Refactor scoring prompt builder**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/ai_scorer.py` by adding these helpers before `_call_minimax()`:

```python
def _safe_preview(value: str | None, limit: int) -> str:
    return (value or "")[:limit].replace("\n", " ").strip()


def _build_scoring_prompt(items: list) -> str:
    lines = []
    for it in items:
        content_preview = _safe_preview(it["content"], 180)
        enriched_preview = _safe_preview(
            it["enriched_content"] if "enriched_content" in it.keys() else None,
            900,
        )
        line = f'[ID:{it["id"]}] {it["title"]}'
        if content_preview:
            line += f" — {content_preview}"
        if enriched_preview:
            line += f"\n上下文: {enriched_preview}"
        lines.append(line)

    return (
        "以下是从技术/创业社区抓取的帖子。请判断哪些描述了真正的用户痛点。\n"
        "如果有上下文,上下文里的评论和回复可以作为判断依据。\n"
        "只返回一个 JSON 数组,包含符合条件的帖子 ID(纯数字)。没有则返回 []。\n"
        "不要解释,只输出 JSON。\n\n"
        + "\n\n".join(lines)
    )


def _parse_flagged_ids(text: str) -> list[int]:
    match = re.search(r"\[[\d,\s]*\]", text)
    if match:
        return [int(x) for x in json.loads(match.group())]
    return []
```

- [ ] **Step 4: Update `_call_minimax()` to use helpers**

Replace prompt-building and JSON parsing inside `_call_minimax()` with:

```python
    user_prompt = _build_scoring_prompt(items)
```

and replace the final parsing block with:

```python
    return _parse_flagged_ids(text)
```

- [ ] **Step 5: Add summary prompt and parser**

Add these functions to `/Users/rotas/Documents/my/AIProjects/ItchFinder/ai_scorer.py` after `_call_minimax()`:

```python
SUMMARY_PROMPT = """你是一个产品机会分析助手。请为每个已确认的痛点生成中文总结。

每条总结必须包含三行:
用户痛点：
现有方案缺口：
可做产品机会：

只返回 JSON 对象,键是帖子 ID 字符串,值是对应中文总结。不要解释。
"""


def _build_summary_prompt(items: list) -> str:
    blocks = []
    for it in items:
        content_preview = _safe_preview(it["content"], 500)
        enriched_preview = _safe_preview(
            it["enriched_content"] if "enriched_content" in it.keys() else None,
            2000,
        )
        blocks.append(
            f'[ID:{it["id"]}] {it["title"]}\n'
            f"原始内容: {content_preview}\n"
            f"补全上下文: {enriched_preview}"
        )
    return "\n\n".join(blocks)


def _parse_summary_response(text: str) -> dict[int, str]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    data = json.loads(match.group())
    return {int(key): str(value).strip() for key, value in data.items() if str(value).strip()}


def _call_minimax_summaries(items: list) -> dict[int, str]:
    api_key = os.environ["MINIMAX_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key, base_url=BASE_URL)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=16384,
        system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": _build_summary_prompt(items)}],
    )
    text = ""
    for block in msg.content:
        if block.type == "text" and getattr(block, "text", ""):
            text = block.text.strip()
            break
    return _parse_summary_response(text)
```

- [ ] **Step 6: Add async summary generator**

Add to `/Users/rotas/Documents/my/AIProjects/ItchFinder/ai_scorer.py` after `run_ai_scoring()`:

```python
async def summarize_ai_flagged() -> AsyncIterator[str]:
    if not os.getenv("MINIMAX_API_KEY"):
        yield "AI总结: 未配置 MINIMAX_API_KEY,跳过"
        return

    items = db.get_ai_summary_candidates(limit=30)
    if not items:
        yield "AI总结: 没有需要总结的条目"
        return

    yield f"AI总结: 提交 {len(items)} 条已推荐痛点给 MiniMax {MODEL}..."
    try:
        summaries = await asyncio.to_thread(_call_minimax_summaries, items)
    except Exception as e:
        yield f"✗ AI总结 API 失败: {str(e)[:80]}"
        return

    saved = 0
    for item in items:
        summary = summaries.get(item["id"])
        if summary:
            db.update_ai_summary(item["id"], summary)
            saved += 1

    yield f"✓ AI总结完成: {saved} 条已写入"
```

- [ ] **Step 7: Wire summary stage into pipeline**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py` import:

```python
from ai_scorer import run_ai_scoring, summarize_ai_flagged
```

Modify `pipeline_events()` after `run_ai_scoring()` and before `translate_new_items()`:

```python
    async for m in summarize_ai_flagged():
        yield m

    async for m in translate_new_items():
        yield m
```

- [ ] **Step 8: Run AI tests and full tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_ai_scorer_enrichment
.venv/bin/python -m unittest tests.test_pipeline_enrichment
.venv/bin/python -m unittest discover -s tests
```

Expected: AI tests, pipeline test, and full suite pass.

- [ ] **Step 9: Review, commit, and push**

Run:

```bash
git diff -- ai_scorer.py main.py tests/test_ai_scorer_enrichment.py
git status --short
git add ai_scorer.py main.py tests/test_ai_scorer_enrichment.py
git commit -m "feat: 基于补全上下文生成AI总结"
git push origin main
```

Expected: commit and push succeed.

## Task 5: Render Summary And Raw Context In Dashboard

**Files:**
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/index.html`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/starred.html`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_templates_enrichment.py`

- [ ] **Step 1: Write failing template rendering test**

Create `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_templates_enrichment.py`:

```python
import unittest
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]


class TemplateEnrichmentTests(unittest.TestCase):
    def _render_index(self, item):
        env = Environment(
            loader=FileSystemLoader(str(ROOT / "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["matched"] = lambda value: []
        env.filters["rel_time"] = lambda value: "刚刚"
        env.filters["abs_time"] = lambda value: "05-03 12:00"
        env.globals["recent_refreshes"] = lambda: []
        env.globals["parse_json"] = lambda value: {}
        template = env.get_template("index.html")
        return template.render(
            items=[item],
            source="",
            min_score=1,
            show_starred=1,
            show_hidden=0,
            q="",
            only_ai=1,
        )

    def test_index_renders_ai_summary_and_collapsed_raw_context(self):
        item = SimpleNamespace(
            id=1,
            source="reddit",
            title="Need better reporting",
            content="Reports are manual",
            url="https://example.com",
            ai_flagged=1,
            is_translated=0,
            pain_score=3,
            matched_keywords="[]",
            created_at="2026-05-03T00:00:00+00:00",
            author="alice",
            is_starred=0,
            ai_summary="用户痛点：报表整理慢\n现有方案缺口：工具割裂\n可做产品机会：自动生成周报",
            enriched_content="Post: Reports are manual\nComments:\n- Same issue here",
            enrichment_status="done",
            enrichment_error=None,
        )

        html = self._render_index(item)

        self.assertIn("AI 总结", html)
        self.assertIn("用户痛点：报表整理慢", html)
        self.assertIn("<details", html)
        self.assertIn("原始上下文", html)
        self.assertIn("Same issue here", html)

    def test_index_renders_enrichment_failure_status(self):
        item = SimpleNamespace(
            id=2,
            source="github",
            title="Export is hard",
            content="Need better export",
            url="https://github.com/acme/tool/issues/42",
            ai_flagged=0,
            is_translated=0,
            pain_score=2,
            matched_keywords="[]",
            created_at="2026-05-03T00:00:00+00:00",
            author="bob",
            is_starred=0,
            ai_summary=None,
            enriched_content=None,
            enrichment_status="failed",
            enrichment_error="rate limited",
        )

        html = self._render_index(item)

        self.assertIn("补全失败", html)
        self.assertIn("rate limited", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_templates_enrichment
```

Expected: fails because summary/raw context UI is not rendered.

- [ ] **Step 3: Add summary and context block to index card**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/index.html` after the content preview block:

```html
      {% if it.ai_summary %}
        <div class="mb-2 rounded border border-purple-100 bg-purple-50 px-3 py-2">
          <div class="text-[11px] font-semibold text-purple-700 mb-1">AI 总结</div>
          <p class="text-xs text-purple-900 whitespace-pre-line leading-relaxed">{{ it.ai_summary }}</p>
        </div>
      {% endif %}

      {% if it.enrichment_status == 'failed' %}
        <div class="mb-2 text-[11px] text-red-500">
          补全失败{% if it.enrichment_error %}: {{ it.enrichment_error[:120] }}{% endif %}
        </div>
      {% elif it.enrichment_status == 'pending' %}
        <div class="mb-2 text-[11px] text-gray-400">等待上下文补全</div>
      {% endif %}

      {% if it.enriched_content %}
        <details class="mb-2 rounded border border-gray-100 bg-gray-50 px-3 py-2">
          <summary class="cursor-pointer text-[11px] font-medium text-gray-500">原始上下文</summary>
          <pre class="mt-2 whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-600">{{ it.enriched_content[:2600] }}</pre>
        </details>
      {% endif %}
```

- [ ] **Step 4: Add the same display block to starred card**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/starred.html` in the same position after the content preview:

```html
      {% if it.ai_summary %}
        <div class="mb-2 rounded border border-purple-100 bg-purple-50 px-3 py-2">
          <div class="text-[11px] font-semibold text-purple-700 mb-1">AI 总结</div>
          <p class="text-xs text-purple-900 whitespace-pre-line leading-relaxed">{{ it.ai_summary }}</p>
        </div>
      {% endif %}

      {% if it.enrichment_status == 'failed' %}
        <div class="mb-2 text-[11px] text-red-500">
          补全失败{% if it.enrichment_error %}: {{ it.enrichment_error[:120] }}{% endif %}
        </div>
      {% elif it.enrichment_status == 'pending' %}
        <div class="mb-2 text-[11px] text-gray-400">等待上下文补全</div>
      {% endif %}

      {% if it.enriched_content %}
        <details class="mb-2 rounded border border-gray-100 bg-gray-50 px-3 py-2">
          <summary class="cursor-pointer text-[11px] font-medium text-gray-500">原始上下文</summary>
          <pre class="mt-2 whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-600">{{ it.enriched_content[:2600] }}</pre>
        </details>
      {% endif %}
```

- [ ] **Step 5: Run template and full tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_templates_enrichment
.venv/bin/python -m unittest discover -s tests
```

Expected: template tests and full suite pass.

- [ ] **Step 6: Review, commit, and push**

Run:

```bash
git diff -- templates/index.html templates/starred.html tests/test_templates_enrichment.py
git status --short
git add templates/index.html templates/starred.html tests/test_templates_enrichment.py
git commit -m "feat: 展示AI总结和原始上下文"
git push origin main
```

Expected: commit and push succeed.

## Task 6: Rebuild Docker Runtime And Update Docs

**Files:**
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/README.md`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/current_status.md`

- [ ] **Step 1: Update README with enrichment behavior**

Modify `/Users/rotas/Documents/my/AIProjects/ItchFinder/README.md` by adding this section after the Docker run instructions:

```markdown
## Scrapling 上下文补全

刷新流程会先抓取数据,再对 Reddit / Hacker News / GitHub Issues 的高信号候选使用 Scrapling 解析页面上下文,然后再交给 AI 评分。

第一版补全规则:

- 每次刷新最多补全 30 条候选
- 候选要求 `pain_score > 0`
- 只处理 `reddit`、`hackernews`、`github`
- 补全失败不会中断刷新,24 小时后重试
- AI 推荐条目会额外生成中文总结

当前版本只使用 Scrapling parser,抓取仍由 `httpx` 完成。
```

- [ ] **Step 2: Update current status**

Replace `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/current_status.md` with concise live state:

```markdown
# Current Status

## Read First

- `README.md`
- `main.py`
- `db.py`
- `ai_scorer.py`
- `enrichment.py`
- `templates/index.html`
- `Dockerfile`
- `docker-compose.yml`
- `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`
- `docs/superpowers/plans/2026-05-03-scrapling-enrichment.md`

## Active Work

- ItchFinder runs through Docker Compose service `itchfinder`.
- Host port is `18081`; container listens on `8000`.
- Scrapling enrichment is integrated as parser-only context enrichment for Reddit, Hacker News, and GitHub Issues.
- Refresh flow is fetch -> insert -> Scrapling enrichment -> AI scoring -> AI summary -> translation -> refresh log.

## Verification

- `.venv/bin/python -m unittest discover -s tests`
- `docker compose config --quiet`
- `docker compose build itchfinder`
- `docker compose up -d itchfinder`
- `curl -fsS http://127.0.0.1:18081/`

## Notes

- Container `itchfinder` can stay running for local use.
- Later optimization points are tracked in `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`.
```

- [ ] **Step 3: Rebuild and restart Docker runtime**

Run:

```bash
docker compose config --quiet
docker compose build itchfinder
docker compose up -d itchfinder
docker compose ps
curl -fsS http://127.0.0.1:18081/ >/tmp/itchfinder-home.html
```

Expected: compose config passes; image builds with Scrapling installed; container is running; curl exits 0.

- [ ] **Step 4: Run full verification**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
docker compose logs --tail=80 itchfinder
```

Expected: tests pass; logs do not show import errors for Scrapling, missing DB columns, or failed startup.

- [ ] **Step 5: Review, commit, and push**

Run:

```bash
git diff -- README.md docs/current_status.md
git status --short
git add README.md docs/current_status.md
git commit -m "chore: 更新Scrapling补全文档和状态"
git push origin main
```

Expected: commit and push succeed.

## Task 7: Final Review And Runtime Smoke

**Files:**
- Review: full repository diff against `origin/main`

- [ ] **Step 1: Confirm git is clean**

Run:

```bash
git status --short --branch
```

Expected:

```text
## main...origin/main
```

- [ ] **Step 2: Run final verification commands**

Run:

```bash
.venv/bin/python -m unittest discover -s tests
docker compose config --quiet
docker compose up -d --build itchfinder
curl -fsS http://127.0.0.1:18081/ >/tmp/itchfinder-final-home.html
docker compose logs --tail=120 itchfinder
```

Expected: tests pass; compose config passes; Docker rebuild/restart succeeds; HTTP returns 200; logs show no startup traceback.

- [ ] **Step 3: Inspect runtime page output**

Run:

```bash
python - <<'PY'
from pathlib import Path
html = Path('/tmp/itchfinder-final-home.html').read_text()
print('AI summary label:', 'AI 总结' in html)
print('Raw context label:', '原始上下文' in html)
print('ItchFinder title:', 'ItchFinder' in html)
PY
```

Expected: `ItchFinder title: True`. The summary/context labels can be `False` if the local database has no enriched rows yet; template unit tests cover their rendering.

- [ ] **Step 4: Final task status update without commit**

If `docs/current_status.md` is already accurate and git is clean, do not create an empty commit. If final verification reveals a still-relevant status change, update `docs/current_status.md`, rerun verification, then commit:

```bash
git add docs/current_status.md
git commit -m "chore: 记录Scrapling最终验证状态"
git push origin main
```

Expected: final state is pushed, or no commit is made because no file changed.

## Self-Review

Spec coverage:

- PyPI `scrapling>=0.4.7` is in Task 2.
- Parser-only Scrapling with `httpx` fetching is in Task 2.
- Reddit, Hacker News, and GitHub Issues extraction are in Task 2.
- Automatic refresh integration before AI scoring is in Task 3.
- Candidate filtering, max 30, retry after 24 hours, and no retry count are in Task 1 and Task 2.
- AI scoring uses `title + content + enriched_content` in Task 4.
- AI summary only for `ai_flagged=1` is in Task 1 and Task 4.
- UI summary and collapsed raw context are in Task 5.
- Failure persistence without breaking refresh is in Task 1 and Task 2.
- Docker rebuild/runtime verification is in Task 6 and Task 7.
- Later optimization compromises remain in the spec and are linked from current status in Task 6.

Placeholder scan:

- This plan avoids unresolved red-flag markers and contains concrete file paths, commands, expected outcomes, and code snippets for each implementation step.

Type consistency:

- DB helpers use `id`, `source`, `title`, `content`, `url`, `pain_score`, `enriched_content`, `enriched_at`, `enrichment_status`, `enrichment_error`, `ai_summary`, and `ai_summary_at` consistently.
- Source value for GitHub candidates is `github`, matching `sources/github_issues.py` inserts and templates.
- Pipeline stage names are `enrich_new_candidates`, `run_ai_scoring`, `summarize_ai_flagged`, and `translate_new_items`.
