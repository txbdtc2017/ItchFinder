import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import db


class EnrichmentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.tmpdir.name) / "data.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmpdir.cleanup()

    def _insert_item(self, **overrides):
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "source": "reddit",
            "external_id": overrides.pop("external_id", "r1"),
            "title": overrides.pop("title", "wish there was a better workflow"),
            "content": overrides.pop("content", "manual reporting is painful"),
            "url": overrides.pop("url", "https://www.reddit.com/r/test/comments/r1/title/"),
            "author": overrides.pop("author", "alice"),
            "created_at": overrides.pop("created_at", now),
            "raw_score": overrides.pop("raw_score", 12),
        }
        item.update(overrides)
        with mock.patch("keywords.score_item", return_value=(2, ["wish there was"])):
            db.insert_items([item])
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM items WHERE external_id = ?",
                (item["external_id"],),
            ).fetchone()
            return row["id"]

    def test_init_db_adds_enrichment_and_summary_columns(self):
        with db.get_conn() as conn:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(items)").fetchall()}

        self.assertIn("enriched_content", cols)
        self.assertIn("enriched_at", cols)
        self.assertIn("enrichment_status", cols)
        self.assertIn("enrichment_error", cols)
        self.assertIn("ai_summary", cols)
        self.assertIn("ai_summary_at", cols)

    def test_get_enrichment_candidates_filters_sources_and_done_rows(self):
        reddit_id = self._insert_item(external_id="r1", source="reddit")
        self._insert_item(external_id="v1", source="v2ex", url="https://v2ex.com/t/1")
        github_id = self._insert_item(
            external_id="g1",
            source="github",
            url="https://github.com/acme/tool/issues/42",
        )
        db.mark_enriched(reddit_id, "Post: already enriched")

        rows = db.get_enrichment_candidates(limit=30)

        self.assertEqual([row["id"] for row in rows], [github_id])

    def test_failed_enrichment_retries_after_cooldown(self):
        item_id = self._insert_item(external_id="r2")
        db.mark_enrichment_failed(item_id, "blocked")

        fresh_rows = db.get_enrichment_candidates(limit=30, cooldown_hours=24)
        self.assertEqual(fresh_rows, [])

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        with db.get_conn() as conn:
            conn.execute("UPDATE items SET enriched_at = ? WHERE id = ?", (old_ts, item_id))

        retry_rows = db.get_enrichment_candidates(limit=30, cooldown_hours=24)
        self.assertEqual([row["id"] for row in retry_rows], [item_id])

    def test_summary_candidate_and_update_helpers(self):
        item_id = self._insert_item(external_id="r3")
        with db.get_conn() as conn:
            conn.execute("UPDATE items SET ai_flagged = 1 WHERE id = ?", (item_id,))

        rows = db.get_ai_summary_candidates(limit=10)
        self.assertEqual([row["id"] for row in rows], [item_id])

        db.update_ai_summary(
            item_id,
            "用户痛点：整理很慢\n现有方案缺口：工具割裂\n可做产品机会：自动汇总",
        )

        rows_after = db.get_ai_summary_candidates(limit=10)
        self.assertEqual(rows_after, [])
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT ai_summary, ai_summary_at FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()
        self.assertIn("用户痛点", row["ai_summary"])
        self.assertIsNotNone(row["ai_summary_at"])

    def test_get_conn_context_manager_closes_connection(self):
        with db.get_conn() as conn:
            conn.execute("SELECT 1")

        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
