# Scrapling Enrichment Design

## Goal

Use Scrapling inside ItchFinder to improve AI pain-point detection by enriching high-signal candidate items with page/comment context before final AI scoring and summary generation.

This is an integration, not a replacement of ItchFinder. ItchFinder remains the product opportunity dashboard. Scrapling becomes the HTML parsing engine used by ItchFinder's enrichment layer.

## Confirmed First Scope

- Dependency mode: install Scrapling from PyPI, not from the local `/Users/rotas/Documents/my/learnai/Scrapling` checkout.
- First dependency target: `scrapling>=0.4.7`, without `scrapling[fetchers]`.
- First Scrapling responsibility: HTML parsing through Scrapling parser/Selector.
- Fetching stays on existing `httpx` for the first version.
- Sources in scope:
  - Reddit
  - Hacker News
  - GitHub Issues
- Trigger: enrichment runs automatically during the refresh pipeline after `insert_items` and before AI scoring.
- Candidate filter:
  - `pain_score > 0`
  - source in `reddit`, `hackernews`, `github`
  - not already enriched, or retryable failed enrichment
  - max 30 items per refresh
- AI summary generation:
  - only for final `ai_flagged=1` items
  - summary includes user pain, existing-solution gap, and possible product opportunity
- UI:
  - show AI summary in each enriched flagged item card
  - allow expanding raw enriched excerpts
- Enrichment runs for both scheduled and manual refreshes.
- Failed enrichment retries only after a 24-hour cooldown.
- Raw context display limits:
  - original post/body excerpt: max 800 characters
  - comments/replies: max 5 entries
  - each comment/reply excerpt: max 300 characters

## Proposed Data Flow

```text
fetchers
  -> db.insert_items
  -> enrich_new_candidates(max 30)
  -> run_ai_scoring using enriched_content when available
  -> summarize_ai_flagged missing ai_summary
  -> translate_new_items
  -> db.log_refresh
```

## Proposed Data Model Additions

Add these columns to `items`:

- `enriched_content TEXT`
- `enriched_at TEXT`
- `enrichment_status TEXT`
- `enrichment_error TEXT`
- `ai_summary TEXT`
- `ai_summary_at TEXT`

Expected `enrichment_status` values:

- `pending`
- `done`
- `failed`
- `skipped`

## Enrichment Behavior By Source

### Reddit

- Fetch the Reddit post page with `httpx`.
- Parse HTML with Scrapling.
- Extract original post text when available.
- Extract up to 5 useful comments.
- Keep raw excerpts concise enough for downstream AI prompts.

### Hacker News

- Fetch the HN item page.
- Parse HTML with Scrapling.
- Extract up to 8 discussion comments.
- Preserve comment order from the page.

### GitHub Issues

- Prefer GitHub API for issue comments when practical because it is structured and stable.
- Use Scrapling parsing as fallback for the HTML issue page.
- Combine issue body and selected comments.

## AI Scoring Changes

`run_ai_scoring` should prefer:

```text
title + content + enriched_content
```

It should fall back to the current behavior if no enriched content exists.

After scoring, a new summary step should generate `ai_summary` only for items where:

- `ai_flagged = 1`
- `ai_summary IS NULL`
- enough title/content/enriched content exists to summarize

Summary structure:

```text
用户痛点：
现有方案缺口：
可做产品机会：
```

## UI Behavior

Each item card can show:

- summary block if `ai_summary` exists
- compact enrichment status if enrichment failed or is pending
- expandable raw context section when `enriched_content` exists

Raw context should default collapsed to keep the dashboard scannable.

Expanded raw context should show at most 800 characters of original post/body text and at most 5 comments or replies, capped at 300 characters each. A separate detail page is out of first-version scope.

## Failure Handling

- Enrichment failure must not break refresh.
- Store short error text in `enrichment_error`.
- Mark failed candidates retryable after a 24-hour cooldown.
- Do not add `retry_count` in the first version.
- AI scoring must continue using original title/content if enrichment fails.

## First-Version Constraints

- Do not introduce browser automation yet.
- Do not use `scrapling[fetchers]` yet.
- Do not replace existing source fetchers with Scrapling.
- Do not crawl arbitrary links beyond the original item URL/comments page.
- Keep per-refresh enrichment bounded at 30 items.

## Explicit Compromises To Revisit

These are deliberate first-version compromises, not final architecture:

- Scrapling starts as parser-only. Later evaluate moving fetching to `scrapling.fetchers.AsyncFetcher`.
- No `scrapling[fetchers]` or browser support. Later evaluate for Reddit/知乎/少数派/掘金 pages that block `httpx`.
- Existing fetchers remain unchanged. Later evaluate a unified fetch abstraction with source-specific fetch strategy.
- Enrichment is inline in refresh. Later evaluate background async enrichment so refresh stays fast.
- Fixed limit of 30 candidates per refresh. Later make this configurable in `.env`.
- AI summaries are generated only for `ai_flagged=1`. Later evaluate summaries for starred or manually selected non-flagged candidates.
- Raw excerpts are stored as plain text. Later evaluate structured JSON with sections, comment metadata, scores, and source links.
- UI uses an inline collapsible block. Later evaluate a detail page or side panel for deeper opportunity analysis.
- GitHub comments prefer API while Scrapling is fallback. Later evaluate consistent extraction interfaces across all sources.
- No robust retry/backoff model in first version. Later add retry count, last error time, and source-specific cool-down.
- No quality scoring for comments in first version. Later rank comments by length, replies, score, pain keywords, and author signals.
- No robots/rate-limit policy layer yet. Later centralize per-domain throttling and robots-aware behavior.
- No prompt cost accounting. Later track tokens/cost per enrichment summary run.
- No automated evaluation dataset. Later create a small fixture set of known pain/non-pain examples and compare AI precision before/after enrichment.

## Confirmed Decisions

- Enrichment runs for both scheduled and manual refreshes.
- Failed enrichment is retryable only after a 24-hour cooldown.
- Raw context appears in a collapsed section with the first-version display limits described above.
