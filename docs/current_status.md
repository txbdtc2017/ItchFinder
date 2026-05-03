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

## Active References

- Spec: `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`
- Plan: `docs/superpowers/plans/2026-05-03-scrapling-enrichment.md`
- Read the spec or plan only when changing requirements, reviewing decisions, or resuming task execution.

## Verification

- `.venv/bin/python -m unittest discover -s tests`
- `docker compose config --quiet`
- `docker compose build itchfinder`
- `docker compose up -d itchfinder`
- `curl -fsS http://127.0.0.1:18081/`

## Notes

- Container `itchfinder` can stay running for local use.
- Later optimization points are tracked in the Scrapling design spec.
