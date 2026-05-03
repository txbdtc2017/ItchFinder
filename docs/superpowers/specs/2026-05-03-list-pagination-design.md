# List Pagination Design

## Goal

Reduce page load and source-switch latency by rendering only a small slice of matching items at a time.

## Decisions

- Use server-side pagination backed by SQLite `LIMIT` and `OFFSET`.
- Default page size is `10` items.
- Pagination applies to the main dashboard and the starred page.
- Source/filter/toggle changes reset to page `1`.
- The total count shown in the UI is the count of all rows matching the current filters, not only the current page.
- `hide_all` keeps its existing product meaning: hide all rows matching the current filters, not only the visible page.

## User Experience

- The result count line shows total matching rows and current page size.
- Pagination controls appear when there is more than one page.
- Controls preserve current filters and search query.
- Out-of-range or invalid page values are clamped to a valid page.

## Implementation Shape

- Add database count helpers next to existing query helpers.
- Extend existing query helpers with `limit` and `offset`.
- Keep route logic responsible for page normalization and URL generation.
- Use a small shared pagination partial for dashboard and starred page controls.

## Testing

- Database tests cover count, limit, and offset.
- Route tests cover page clamping and query offset calculation.
- Template tests cover pagination controls and preserved page URLs.
- Full test suite must pass before Docker restart and push.

## Self-Review

- No placeholders remain.
- Scope is limited to read/list pagination plus the existing hide-all semantics.
- The default page size is explicitly `10`.
- The design does not introduce infinite scroll or client-side-only pagination.
