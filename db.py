"""SQLite 持久化层。仅用 sqlite3 标准库。"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT NOT NULL,
            author TEXT,
            created_at TEXT NOT NULL,
            raw_score INTEGER DEFAULT 0,
            pain_score INTEGER DEFAULT 0,
            matched_keywords TEXT,
            is_starred INTEGER DEFAULT 0,
            is_hidden INTEGER DEFAULT 0,
            fetched_at TEXT NOT NULL,
            UNIQUE(source, external_id)
        );
        CREATE INDEX IF NOT EXISTS idx_pain_created
            ON items(pain_score DESC, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_starred ON items(is_starred);

        CREATE TABLE IF NOT EXISTS refresh_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            trigger TEXT NOT NULL,
            total_new INTEGER NOT NULL DEFAULT 0,
            stats_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_refresh_ts ON refresh_log(ts DESC);
        """)
        # 增量加列,已存在就跳过
        for col, default in [("ai_scored", "0"), ("ai_flagged", "0"), ("is_translated", "0")]:
            try:
                conn.execute(f"ALTER TABLE items ADD COLUMN {col} INTEGER DEFAULT {default}")
            except sqlite3.OperationalError:
                pass
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


def insert_items(items: list[dict]) -> tuple[int, int]:
    """批量插入。两层去重:
    1) (source, external_id) 已存在 → 跳过(SQL UNIQUE)
    2) (source, title) 已存在 → 跳过(应用层,处理 Reddit 同一帖子跨 sub 重复)
    返回 (新插入总数, 其中 pain_score>=1 的条数)。
    """
    if not items:
        return 0, 0
    # 延迟导入避免循环/初始化顺序问题
    from keywords import score_item

    now = datetime.now(timezone.utc).isoformat()
    total_new = 0
    new_high = 0
    with get_conn() as conn:
        for it in items:
            # 标题级去重:同 source + 同 title 已有就跳过
            dup = conn.execute(
                "SELECT 1 FROM items WHERE source = ? AND title = ? LIMIT 1",
                (it["source"], it["title"]),
            ).fetchone()
            if dup:
                continue

            score, matched = score_item(it["title"], it.get("content"))
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO items
                    (source, external_id, title, content, url, author,
                     created_at, raw_score, pain_score, matched_keywords, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    it["source"],
                    it["external_id"],
                    it["title"],
                    it.get("content"),
                    it["url"],
                    it.get("author"),
                    it["created_at"],
                    it.get("raw_score") or 0,
                    score,
                    json.dumps(matched, ensure_ascii=False),
                    now,
                ),
            )
            if cur.rowcount > 0:
                total_new += 1
                if score >= 1:
                    new_high += 1
    return total_new, new_high


def _item_filter_clause(
    source: str | None = None,
    min_score: int = 1,
    show_starred: bool = True,
    show_hidden: bool = False,
    search: str | None = None,
    only_ai: bool = False,
) -> tuple[str, list]:
    clauses = ["pain_score >= ?"]
    params: list = [min_score]
    if source:
        clauses.append("source = ?")
        params.append(source)
    if not show_starred:
        clauses.append("is_starred = 0")
    if not show_hidden:
        clauses.append("is_hidden = 0")
    if only_ai:
        clauses.append("ai_flagged = 1")
    if search:
        clauses.append("(LOWER(title) LIKE ? OR LOWER(COALESCE(content, '')) LIKE ?)")
        kw = f"%{search.lower()}%"
        params.extend([kw, kw])
    return " AND ".join(clauses), params


def query_items(
    source: str | None = None,
    min_score: int = 1,
    show_starred: bool = True,
    show_hidden: bool = False,
    search: str | None = None,
    only_ai: bool = False,
    limit: int = 500,
    offset: int = 0,
) -> list[sqlite3.Row]:
    where_sql, params = _item_filter_clause(
        source=source,
        min_score=min_score,
        show_starred=show_starred,
        show_hidden=show_hidden,
        search=search,
        only_ai=only_ai,
    )
    sql = f"SELECT * FROM items WHERE {where_sql} ORDER BY pain_score DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def count_items(
    source: str | None = None,
    min_score: int = 1,
    show_starred: bool = True,
    show_hidden: bool = False,
    search: str | None = None,
    only_ai: bool = False,
) -> int:
    where_sql, params = _item_filter_clause(
        source=source,
        min_score=min_score,
        show_starred=show_starred,
        show_hidden=show_hidden,
        search=search,
        only_ai=only_ai,
    )
    with get_conn() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM items WHERE {where_sql}", params).fetchone()
        return int(row["n"])


def query_starred(limit: int = 500, offset: int = 0) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM items WHERE is_starred = 1 "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()


def count_starred() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM items WHERE is_starred = 1").fetchone()
        return int(row["n"])


def toggle_starred(item_id: int) -> None:
    """按 (source, title) 联动:Reddit 等跨 sub 重复时,同标题一起切换。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT source, title, is_starred FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if not row:
            return
        new_state = 0 if row["is_starred"] else 1
        conn.execute(
            "UPDATE items SET is_starred = ? WHERE source = ? AND title = ?",
            (new_state, row["source"], row["title"]),
        )


def toggle_hidden(item_id: int) -> None:
    """按 (source, title) 联动。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT source, title, is_hidden FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if not row:
            return
        new_state = 0 if row["is_hidden"] else 1
        conn.execute(
            "UPDATE items SET is_hidden = ? WHERE source = ? AND title = ?",
            (new_state, row["source"], row["title"]),
        )


def hide_all_matching(
    source: str | None = None,
    min_score: int = 1,
    show_starred: bool = True,
    show_hidden: bool = False,
    search: str | None = None,
    only_ai: bool = False,
) -> int:
    """把当前 query_items 筛出来的 + 还没隐藏的全部 is_hidden=1。返回受影响行数。"""
    sql = "UPDATE items SET is_hidden = 1 WHERE pain_score >= ? AND is_hidden = 0"
    params: list = [min_score]
    if source:
        sql += " AND source = ?"
        params.append(source)
    if not show_starred:
        sql += " AND is_starred = 0"
    if not show_hidden:
        # show_hidden=False 时本来就过滤掉已隐藏,is_hidden=0 已加,跳过
        pass
    if only_ai:
        sql += " AND ai_flagged = 1"
    if search:
        sql += " AND (LOWER(title) LIKE ? OR LOWER(COALESCE(content, '')) LIKE ?)"
        kw = f"%{search.lower()}%"
        params.extend([kw, kw])
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount


def get_unscored_items(limit: int = 100) -> list[sqlite3.Row]:
    """取 pain_score > 0 且未被 AI 评估过的条目。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, source, title, content, enriched_content FROM items "
            "WHERE pain_score > 0 AND ai_scored = 0 "
            "ORDER BY pain_score DESC LIMIT ?",
            (limit,),
        ).fetchall()


def get_enrichment_candidates(limit: int = 30, cooldown_hours: int = 24) -> list[sqlite3.Row]:
    """取需要补全上下文的高信号候选。失败项过冷却期后重试。"""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
    ).isoformat()
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, source, external_id, title, content, url, pain_score, enriched_content,
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


def mark_enrichment_skipped(item_id: int, reason: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    short_reason = reason[:300]
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE items
            SET enriched_at = ?,
                enrichment_status = 'skipped',
                enrichment_error = ?
            WHERE id = ?
            """,
            (now, short_reason, item_id),
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


def get_untranslated(sources: list[str], limit: int = 200) -> list[sqlite3.Row]:
    """取指定 source 中 AI 推荐过且未翻译的条目。非推荐条目不翻,省时间。"""
    if not sources:
        return []
    placeholders = ",".join("?" for _ in sources)
    with get_conn() as conn:
        return conn.execute(
            f"SELECT id, title, content FROM items "
            f"WHERE source IN ({placeholders}) AND is_translated = 0 AND ai_flagged = 1 "
            f"ORDER BY id DESC LIMIT ?",
            [*sources, limit],
        ).fetchall()


def update_translated(item_id: int, title: str, content: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE items SET title = ?, content = ?, is_translated = 1 WHERE id = ?",
            (title, content, item_id),
        )


def log_refresh(trigger: str, total_new: int, stats: dict) -> None:
    """记录一次 pipeline 执行的统计。trigger: 'scheduled' 或 'manual'。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO refresh_log (ts, trigger, total_new, stats_json) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                trigger,
                total_new,
                json.dumps(stats, ensure_ascii=False),
            ),
        )


def get_recent_refreshes(limit: int = 10) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT ts, trigger, total_new, stats_json FROM refresh_log "
            "ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()


def mark_ai_results(scored_ids: list[int], flagged_ids: list[int]) -> None:
    """标记 AI 评估结果:scored_ids 全部标 ai_scored=1,flagged_ids 额外标 ai_flagged=1。"""
    if not scored_ids:
        return
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in scored_ids)
        conn.execute(
            f"UPDATE items SET ai_scored = 1 WHERE id IN ({placeholders})",
            scored_ids,
        )
        if flagged_ids:
            placeholders = ",".join("?" for _ in flagged_ids)
            conn.execute(
                f"UPDATE items SET ai_flagged = 1 WHERE id IN ({placeholders})",
                flagged_ids,
            )
