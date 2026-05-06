# Current Status

## Read First

- `README.md`
- `main.py`
- `db.py`
- `ai_scorer.py`
- `enrichment.py`
- `Dockerfile`
- `docker-compose.yml`

## Current Reality

- ItchFinder runs through Docker Compose service `itchfinder`.
- Host port is `18081`; container listens on `8000`.
- Compose sets `ITCHFINDER_HOST=0.0.0.0`, `ITCHFINDER_PORT=8000`, and `ITCHFINDER_PUBLIC_URL=http://127.0.0.1:18081`.
- Current project directory is bind-mounted to `/app`, so `data.db` remains in the project root.
- Scrapling enrichment is integrated as parser-only context enrichment for Reddit, Hacker News, and GitHub Issues.
- Refresh flow is fetch -> insert -> Scrapling enrichment -> AI scoring -> AI summary -> translation -> refresh log.
- RSS feeds are fetched with explicit `httpx` timeouts so one slow feed cannot block the refresh pipeline.
- Reddit enrichment now prefers `old.reddit.com` and falls back to the existing Reddit JSON content when HTML fetch is blocked.
- Hacker News enrichment now uses `external_id` to fetch the HN discussion page instead of the external article URL.
- Empty enrichment results are marked `skipped`, not `failed`, so they do not repeat as noisy failures.
- Main and starred lists use server-side pagination with `10` items per page.
- Enrichment candidate selection excludes rows already AI-scored and not recommended.
- Refresh now runs pre-AI high-score enrichment, AI scoring, AI-recommended enrichment, AI summary, then translation.
- A bounded background enrichment job runs every 2 minutes with batch size `20` and skips if another enrichment pass is active.
- SQLite WAL mode is set during DB initialization; runtime connections use a busy timeout to reduce read/write contention.
- Browser pages auto-reload after waking or returning from a hidden state longer than 5 minutes.
- Latest Docker runtime is running and reachable at `http://127.0.0.1:18081/`.

## Active References

- Spec: `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`
- Plan: `docs/superpowers/plans/2026-05-03-scrapling-enrichment.md`
- Pagination spec: `docs/superpowers/specs/2026-05-03-list-pagination-design.md`
- Pagination plan: `docs/superpowers/plans/2026-05-03-list-pagination.md`
- Background enrichment spec: `docs/superpowers/specs/2026-05-03-background-enrichment-design.md`
- Background enrichment plan: `docs/superpowers/plans/2026-05-03-background-enrichment.md`
- Read the spec or plan only when changing requirements, reviewing decisions, or resuming task execution.

## Verification

- `.venv/bin/python -m unittest discover -s tests` passes 47 tests.
- `docker compose config --quiet`
- `docker compose up -d --build itchfinder`
- `curl -fsS http://127.0.0.1:18081/`
- Latest startup pipeline reached Scrapling enrichment and AI summary without crashing.
- Latest Scrapling Docker run completed `29` success, `0` failure, `1` skipped.
- Current homepage no longer renders `补全失败` labels after historical empty/blocked failures were reset to pending.
- Latest pagination check loaded page `2` for Reddit with pagination controls rendered.
- Latest background enrichment candidate check: `300` eligible rows after Docker verification.
- Latest runtime logs show `Scrapling推荐补齐` completed `20` success, `0` failure, and background enrichment skipped while that pass was active.
- Latest wake-refresh template check verifies visibility/focus/pageshow handlers and the 5-minute wake reload threshold.

## Notes

- Container `itchfinder` can stay running for local use.
- Later optimization points are tracked in the Scrapling design spec.
