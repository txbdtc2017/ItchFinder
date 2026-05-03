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
        score = overrides.pop("score", 2)
        now = datetime.now(timezone.utc).isoformat()
        external_id = overrides.pop("external_id", "r1")
        item = {
            "source": "reddit",
            "external_id": external_id,
            "title": overrides.pop("title", f"wish there was a better workflow {external_id}"),
            "content": overrides.pop("content", "manual reporting is painful"),
            "url": overrides.pop("url", "https://www.reddit.com/r/test/comments/r1/title/"),
            "author": overrides.pop("author", "alice"),
            "created_at": overrides.pop("created_at", now),
            "raw_score": overrides.pop("raw_score", 12),
        }
        item.update(overrides)
        with mock.patch("keywords.score_item", return_value=(score, ["wish there was"])):
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
        reddit_id = self._insert_item(external_id="r1", source="reddit", score=3)
        self._insert_item(external_id="v1", source="v2ex", url="https://v2ex.com/t/1")
        github_id = self._insert_item(
            external_id="g1",
            source="github",
            url="https://github.com/acme/tool/issues/42",
            score=3,
        )
        db.mark_enriched(reddit_id, "Post: already enriched")

        rows = db.get_enrichment_candidates(limit=30)

        self.assertEqual([row["id"] for row in rows], [github_id])
        self.assertEqual(rows[0]["external_id"], "g1")

    def test_failed_enrichment_retries_after_cooldown(self):
        item_id = self._insert_item(external_id="r2", score=3)
        db.mark_enrichment_failed(item_id, "blocked")

        fresh_rows = db.get_enrichment_candidates(limit=30, cooldown_hours=24)
        self.assertEqual(fresh_rows, [])

        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        with db.get_conn() as conn:
            conn.execute("UPDATE items SET enriched_at = ? WHERE id = ?", (old_ts, item_id))

        retry_rows = db.get_enrichment_candidates(limit=30, cooldown_hours=24)
        self.assertEqual([row["id"] for row in retry_rows], [item_id])

    def test_enrichment_candidates_prioritize_high_unscored_and_ai_flagged_rows(self):
        high_unscored_id = self._insert_item(external_id="high", score=4)
        low_unscored_id = self._insert_item(external_id="low", score=1)
        ai_rejected_id = self._insert_item(external_id="rejected", score=5)
        ai_flagged_id = self._insert_item(external_id="flagged", score=1)

        with db.get_conn() as conn:
            conn.execute(
                "UPDATE items SET ai_scored = 1, ai_flagged = 0 WHERE id = ?",
                (ai_rejected_id,),
            )
            conn.execute(
                "UPDATE items SET ai_scored = 1, ai_flagged = 1 WHERE id = ?",
                (ai_flagged_id,),
            )

        background_rows = db.get_enrichment_candidates(limit=30, mode="background")
        pre_ai_rows = db.get_enrichment_candidates(limit=30, mode="pre_ai")
        flagged_rows = db.get_enrichment_candidates(limit=30, mode="ai_flagged")

        self.assertEqual([row["id"] for row in background_rows], [high_unscored_id, ai_flagged_id])
        self.assertEqual([row["id"] for row in pre_ai_rows], [high_unscored_id])
        self.assertEqual([row["id"] for row in flagged_rows], [ai_flagged_id])
        self.assertNotIn(low_unscored_id, [row["id"] for row in background_rows])
        self.assertNotIn(ai_rejected_id, [row["id"] for row in background_rows])

    def test_skipped_enrichment_is_not_retried_as_candidate(self):
        item_id = self._insert_item(external_id="r4")
        db.mark_enrichment_skipped(item_id, "no extractable context")

        rows = db.get_enrichment_candidates(limit=30)

        self.assertEqual(rows, [])
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT enrichment_status, enrichment_error FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()
        self.assertEqual(row["enrichment_status"], "skipped")
        self.assertEqual(row["enrichment_error"], "no extractable context")

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

    def test_get_conn_does_not_switch_wal_mode_on_every_connection(self):
        class FakeConnection:
            row_factory = None

            def __init__(self):
                self.executed = []

            def execute(self, sql):
                self.executed.append(sql)
                return self

        fake = FakeConnection()

        with mock.patch("sqlite3.connect", return_value=fake):
            conn = db.get_conn()

        self.assertIs(conn, fake)
        self.assertIn("PRAGMA busy_timeout=30000", fake.executed)
        self.assertIn("PRAGMA foreign_keys=ON", fake.executed)
        self.assertNotIn("PRAGMA journal_mode=WAL", fake.executed)


if __name__ == "__main__":
    unittest.main()
