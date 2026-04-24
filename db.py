"""SQLite 持久化层。仅用 sqlite3 标准库。"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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


def insert_items(items: list[dict]) -> tuple[int, int]:
    """批量插入,(source, external_id) 已存在的跳过。
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


def query_items(
    source: str | None = None,
    min_score: int = 1,
    show_starred: bool = True,
    show_hidden: bool = False,
    search: str | None = None,
    only_ai: bool = False,
    limit: int = 500,
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM items WHERE pain_score >= ?"
    params: list = [min_score]
    if source:
        sql += " AND source = ?"
        params.append(source)
    if not show_starred:
        sql += " AND is_starred = 0"
    if not show_hidden:
        sql += " AND is_hidden = 0"
    if only_ai:
        sql += " AND ai_flagged = 1"
    if search:
        sql += " AND (LOWER(title) LIKE ? OR LOWER(COALESCE(content, '')) LIKE ?)"
        kw = f"%{search.lower()}%"
        params.extend([kw, kw])
    sql += " ORDER BY pain_score DESC, created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def query_starred(limit: int = 500) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM items WHERE is_starred = 1 "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


def toggle_starred(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE items SET is_starred = 1 - is_starred WHERE id = ?",
            (item_id,),
        )


def toggle_hidden(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE items SET is_hidden = 1 - is_hidden WHERE id = ?",
            (item_id,),
        )


def get_unscored_items(limit: int = 100) -> list[sqlite3.Row]:
    """取 pain_score > 0 且未被 AI 评估过的条目。"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, source, title, content FROM items "
            "WHERE pain_score > 0 AND ai_scored = 0 "
            "ORDER BY pain_score DESC LIMIT ?",
            (limit,),
        ).fetchall()


def get_untranslated(sources: list[str], limit: int = 200) -> list[sqlite3.Row]:
    """取指定 source 中未翻译的条目。高分优先,用户看得见的先翻译。"""
    if not sources:
        return []
    placeholders = ",".join("?" for _ in sources)
    with get_conn() as conn:
        return conn.execute(
            f"SELECT id, title, content FROM items "
            f"WHERE source IN ({placeholders}) AND is_translated = 0 "
            f"ORDER BY pain_score DESC, id DESC LIMIT ?",
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
