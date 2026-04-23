# Claude Code Project Rules

## Session Startup

- New sessions should read `CLAUDE.md` and `docs/current_status.md` first.
- After reading `docs/current_status.md`, open the files listed in its `Read First` section before starting substantial work.
- Use `docs/session-handoff.md` as the full handoff workflow reference when rules need clarification.
- Use `docs/agent-entry-policy.md` as the authoritative writing policy for entry files.

## Entry File Rules

- Keep this file short. It is an agent entry file, not the main project knowledge base.
- Allowed here: startup rules, repo-wide workflow constraints, concise document-routing rules, and small Claude-specific behavior differences.
- Do not write here: current task state, debugging logs, long procedures, architecture detail, design docs, plans, or temporary instructions.
- Use `.claude/rules/` for Claude Code-specific workflow guidance.
- Stable project knowledge belongs in `docs/project-overview.md`.
- Runtime procedures and recurring incidents belong in `docs/dev-operations.md`.
- Current task state belongs in `docs/current_status.md`.
- Design belongs in `docs/superpowers/specs/`; plans belong in `docs/superpowers/plans/`.
- Target size: 20-60 lines; move content out before this file becomes long.
- If you think this file should change, propose the diff first and wait for user approval.

## Current Status Rules

- `docs/current_status.md` is a live status board, not a log.
- Update `docs/current_status.md` before ending substantial work.
- Keep `docs/current_status.md` concise: target 30-60 lines and overwrite in place.
- Move detailed reasoning, design, and execution steps into `docs/superpowers/specs/` and `docs/superpowers/plans/`, then link them from `docs/current_status.md`.

## Runtime Rules

- If a change requires restart, reload, or rebuild to take effect, perform that runtime action before verification and before claiming the work is complete.
- Use `docs/dev-operations.md` for runtime commands and verification guidance.

## Documentation Placement

- Stable project knowledge belongs in `docs/project-overview.md`.
- Operational procedures and recurring runtime incidents belong in `docs/dev-operations.md`.
- Task design belongs in `docs/superpowers/specs/`.
- Execution plans belong in `docs/superpowers/plans/`.
- Only current, still-relevant state belongs in `docs/current_status.md`.

## Git And Commit Rules

- Do not commit by default. Wait until the user explicitly asks for a commit.
- When the user asks to commit, first summarize the intended commit grouping and messages, then commit after confirmation.
- Use the repo style for commit messages: `feat:(中文描述)`, `refactor:(中文描述)`, `fix:(中文描述)`, `chore:(中文描述)`.
