# Background Enrichment Design

## Goal

Keep Scrapling context enrichment running in the background without making manual refresh slow or spending enrichment work on rows that are already known to be non-recommended.

## Current Problem

The current refresh pipeline enriches up to 30 rows before AI scoring. This improves AI accuracy for those rows, but it also creates a large backlog because every `pain_score > 0` Reddit, Hacker News, and GitHub row is eligible even if AI later rejects it.

## Decisions

- Keep context enrichment valuable for high-signal rows before AI scoring.
- Do not enrich rows that were already AI-scored and not recommended.
- Add a low-frequency background enrichment job that keeps processing eligible rows in small batches.
- Use one in-process enrichment lock so manual refresh and background enrichment do not work the same queue at the same time.
- Keep batch sizes conservative to reduce Reddit/HN/GitHub blocking risk.

## Candidate Priority

Eligible sources remain:

- `reddit`
- `hackernews`
- `github`

Eligible statuses remain:

- `pending`
- `failed` after the existing cooldown

Skipped and done rows are not retried.

Priority groups:

1. Pre-AI high-signal rows: `ai_scored = 0` and `pain_score >= 3`
2. AI-recommended rows: `ai_flagged = 1`

Rows with `ai_scored = 1` and `ai_flagged = 0` are excluded from enrichment.

## Runtime Flow

Manual refresh:

```text
fetch sources
enrich pre-AI high-signal rows
AI scoring
enrich AI-recommended rows
AI summary
translation
```

Background job:

```text
every 2 minutes:
  if another enrichment job is active, skip
  enrich a small background batch using the same priority rules
```

## Non-Goals

- No unbounded all-at-once enrichment.
- No concurrent multi-worker queue.
- No database migration for a `processing` state in this iteration.
- No AI re-score loop in this iteration; the summary step benefits from post-AI recommended enrichment.

## Testing

- Database tests verify the candidate priority rules and exclusion of AI-rejected rows.
- Pipeline tests verify enrichment runs before AI scoring and again before summaries.
- Background tests verify the scheduled worker uses background mode and skip-if-busy behavior.
- Full test suite and Docker runtime verification are required.

## Self-Review

- No placeholders remain.
- Scope is one implementation plan.
- The no-rejected-row rule is explicit.
- The design keeps background work bounded instead of adding unlimited enrichment.
