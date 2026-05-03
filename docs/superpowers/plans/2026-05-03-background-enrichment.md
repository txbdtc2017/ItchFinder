# Background Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded background Scrapling enrichment while prioritizing high-signal pre-AI rows and AI-recommended rows.

**Architecture:** Database candidate selection will support enrichment modes (`pre_ai`, `ai_flagged`, `background`). The refresh pipeline will run a small pre-AI enrichment pass, AI scoring, then a post-AI recommended enrichment pass before summaries. APScheduler will run a separate background enrichment job every two minutes with skip-if-busy locking.

**Tech Stack:** Python 3 / FastAPI / APScheduler / SQLite / httpx / Scrapling / unittest / Docker Compose.

---

## Files

- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/db.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/enrichment.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/main.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_db_enrichment.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_enrichment.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_pipeline_enrichment.py`
- Create: `/Users/rotas/Documents/my/AIProjects/ItchFinder/tests/test_background_enrichment.py`
- Modify: `/Users/rotas/Documents/my/AIProjects/ItchFinder/docs/current_status.md`

## Task 1: Candidate Priority Rules

- [ ] **Step 1: Write failing database tests**

Add tests that create high unscored rows, low unscored rows, AI-recommended rows, and AI-rejected rows. Assert `mode="background"` returns only high unscored plus AI-recommended rows, `mode="pre_ai"` returns high unscored rows, and `mode="ai_flagged"` returns AI-recommended rows.

- [ ] **Step 2: Run RED**

```bash
.venv/bin/python -m unittest tests.test_db_enrichment
```

Expected: failures because `get_enrichment_candidates` has no mode filtering.

- [ ] **Step 3: Implement candidate modes**

Add `HIGH_ENRICHMENT_SCORE = 3`, extend `get_enrichment_candidates(..., mode="background")`, include `ai_scored` and `ai_flagged` in selected rows, and exclude `ai_scored = 1 AND ai_flagged = 0` rows.

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/python -m unittest tests.test_db_enrichment
```

Expected: database enrichment tests pass.

## Task 2: Enrichment Lock And Mode Labels

- [ ] **Step 1: Write failing enrichment tests**

Add tests asserting `enrich_new_candidates(mode="ai_flagged")` passes that mode to the database helper and that `skip_if_busy=True` returns a skip message when the enrichment lock is already held.

- [ ] **Step 2: Run RED**

```bash
.venv/bin/python -m unittest tests.test_enrichment
```

Expected: failures because mode and skip-if-busy are not supported.

- [ ] **Step 3: Implement lock and mode support**

Add a module-level `asyncio.Lock`, parameters `mode`, `label`, and `skip_if_busy` to `enrich_new_candidates`, and use the label in progress messages.

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/python -m unittest tests.test_enrichment
```

Expected: enrichment tests pass.

## Task 3: Pipeline And Background Scheduler

- [ ] **Step 1: Write failing pipeline/background tests**

Update the pipeline test to expect enrichment order `pre_ai -> ai -> ai_flagged -> summary -> translate`. Add a background worker test that verifies `run_background_enrichment` calls `enrich_new_candidates(limit=20, mode="background", skip_if_busy=True, label="Scrapling后台补齐")`.

- [ ] **Step 2: Run RED**

```bash
.venv/bin/python -m unittest tests.test_pipeline_enrichment tests.test_background_enrichment
```

Expected: failures because the second enrichment pass and background worker do not exist.

- [ ] **Step 3: Implement pipeline and scheduler**

Add `PRE_AI_ENRICHMENT_LIMIT = 10`, `POST_AI_ENRICHMENT_LIMIT = 20`, `BACKGROUND_ENRICHMENT_LIMIT = 20`, run the two enrichment passes in `pipeline_events`, add `run_background_enrichment`, and schedule it every two minutes with `max_instances=1`.

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/python -m unittest tests.test_pipeline_enrichment tests.test_background_enrichment
```

Expected: pipeline/background tests pass.

## Task 4: Verification And Commit

- [ ] **Step 1: Run full tests**

```bash
.venv/bin/python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Check port and rebuild Docker**

```bash
lsof -nP -iTCP:18081 -sTCP:LISTEN
docker compose up -d --build itchfinder
```

Expected: `18081` is only the ItchFinder Docker mapping, and the service rebuilds.

- [ ] **Step 3: Verify runtime logs**

```bash
docker compose logs --tail=120 itchfinder | rg "Scrapling预补齐|Scrapling推荐补齐|Scrapling后台补齐"
curl -fsS http://127.0.0.1:18081/ >/tmp/itchfinder_home.html
```

Expected: service is reachable and logs show the new enrichment labels once the relevant jobs run.

- [ ] **Step 4: Update status and push**

Update `docs/current_status.md`, then commit and push:

```bash
git add db.py enrichment.py main.py tests/test_db_enrichment.py tests/test_enrichment.py tests/test_pipeline_enrichment.py tests/test_background_enrichment.py docs/current_status.md docs/superpowers/specs/2026-05-03-background-enrichment-design.md docs/superpowers/plans/2026-05-03-background-enrichment.md
git commit -m "feat:(增加后台上下文补齐)"
git push
```

## Plan Self-Review

- Spec coverage: candidate priority, background scheduling, lock behavior, manual refresh sequencing, and verification are covered.
- Placeholder scan: no TODO/TBD placeholders remain.
- Type consistency: mode names are consistently `pre_ai`, `ai_flagged`, and `background`.
