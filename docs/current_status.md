# Current Status

## Read First

- `README.md`
- `main.py`
- `Dockerfile`
- `docker-compose.yml`
- `tests/test_main_entrypoint.py`
- `tests/test_docker_config.py`
- `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`
- `docs/superpowers/plans/2026-05-03-scrapling-enrichment.md`

## Active Work

- ItchFinder has been converted to Docker Compose service `itchfinder`.
- Host port is `18081`; container listens on `8000`.
- Compose sets `ITCHFINDER_HOST=0.0.0.0`, `ITCHFINDER_PORT=8000`, and `ITCHFINDER_PUBLIC_URL=http://127.0.0.1:18081`.
- Current project directory is bind-mounted to `/app`, so `data.db` remains in the project root.
- Local Python startup still supports automatic local port fallback for direct debugging.
- Scrapling integration design is written in `docs/superpowers/specs/2026-05-03-scrapling-enrichment-design.md`.
- Scrapling implementation plan is written in `docs/superpowers/plans/2026-05-03-scrapling-enrichment.md` and is awaiting user approval before execution.

## Verification

- Latest full test command: `.venv/bin/python -m unittest discover -s tests`
- Compose config parses with `docker compose config --quiet`.
- Docker image builds with `docker compose build itchfinder`.
- Runtime check: `docker compose up -d itchfinder`.
- HTTP checks returned 200 for both `http://127.0.0.1:18081/` and `http://localhost:18081/`.

## Notes

- No commit has been made yet.
- Existing uncommitted Docker/spec/test changes should be committed as Task 0 after plan approval.
- Container `itchfinder` is currently running unless stopped later with `docker compose down`.
