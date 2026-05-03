# List Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-side pagination to the main dashboard and starred page with a default page size of 10.

**Architecture:** SQLite query helpers will expose total counts plus paged result slices. FastAPI routes will normalize page values, compute offsets, and pass pagination metadata to templates. Templates will render a shared pagination partial while preserving current filters.

**Tech Stack:** Python 3 / FastAPI / SQLite / Jinja2 / unittest / Docker Compose.

---

## Files

- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/db.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/index.html`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/starred.html`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/templates/_pagination.html`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_pagination.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/current_status.md`

## Task 1: Database Pagination Helpers

- [ ] **Step 1: Write failing database tests**

Add tests in `tests/test_pagination.py` that insert 15 matching rows, assert `count_items(...) == 15`, assert `query_items(..., limit=10, offset=10)` returns the final 5 rows, insert starred rows, and assert `count_starred()` plus `query_starred(limit=10, offset=10)`.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_pagination
```

Expected: failure because `count_items` and `count_starred` do not exist.

- [ ] **Step 3: Implement database helpers**

Refactor the repeated item filter SQL into a private helper in `db.py`, add `count_items(...)`, extend `query_items(...)` with `offset`, add `count_starred()`, and extend `query_starred(...)` with `offset`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_pagination
```

Expected: tests pass.

## Task 2: Route Pagination

- [ ] **Step 1: Write failing route tests**

Add route tests in `tests/test_pagination.py` that patch DB helpers, call `main.index(...)` with `page=3`, and assert `limit=10`, `offset=20`, `page=3`, and `total_pages=3`. Add a starred route test with `page=0` and assert it clamps to page `1`.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_pagination
```

Expected: failure because routes do not accept or pass pagination metadata.

- [ ] **Step 3: Implement route pagination**

Add `PAGE_SIZE = 10`, page normalization helpers, URL-prefix generation with `urllib.parse.urlencode`, and pass `page`, `page_size`, `total_count`, `total_pages`, and `page_url_prefix` to templates.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_pagination
```

Expected: tests pass.

## Task 3: Template Controls

- [ ] **Step 1: Write failing template tests**

Add template tests in `tests/test_pagination.py` that render `index.html` and `starred.html` with `total_pages=3` and assert they show `上一页`, `下一页`, page text, and preserved page URLs.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_pagination
```

Expected: failure because pagination controls are absent.

- [ ] **Step 3: Implement templates**

Create `templates/_pagination.html`, include it at the bottom of `index.html` and `starred.html`, update count labels to show total rows and current-page rows, and add `page=1` to filter/toggle links.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_pagination
```

Expected: tests pass.

## Task 4: Verification, Runtime, And Commit

- [ ] **Step 1: Run full tests**

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Check Docker port and rebuild**

```bash
lsof -nP -iTCP:18081 -sTCP:LISTEN
docker compose up -d --build itchfinder
```

Expected: only the ItchFinder Docker mapping uses `18081`; the service rebuilds and starts.

- [ ] **Step 3: Verify HTTP and rendered pagination**

```bash
curl -fsS "http://127.0.0.1:18081/?applied=1&source=reddit&min_score=1&show_starred=1&show_hidden=0&only_ai=0&q=&page=2" >/tmp/itchfinder_page2.html
rg "上一页|下一页|第 2 /" /tmp/itchfinder_page2.html
```

Expected: the page is reachable and contains pagination controls.

- [ ] **Step 4: Update current status**

Record that list pagination is server-side with page size 10 and update latest verification evidence.

- [ ] **Step 5: Commit and push**

```bash
git add db.py main.py templates/index.html templates/starred.html templates/_pagination.html tests/test_pagination.py docs/current_status.md docs/superpowers/specs/2026-05-03-list-pagination-design.md docs/superpowers/plans/2026-05-03-list-pagination.md
git commit -m "feat:(增加列表分页)"
git push
```

## Plan Self-Review

- Spec coverage: server-side pagination, page size 10, dashboard/starred coverage, filter-preserving controls, count display, clamping, and hide-all semantics are covered.
- Placeholder scan: no TBD/TODO/fill-in placeholders remain.
- Type consistency: route metadata names match template names: `page`, `page_size`, `total_count`, `total_pages`, and `page_url_prefix`.
