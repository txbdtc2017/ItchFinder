import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request

import db
import main


ROOT = Path(__file__).resolve().parents[1]


class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.tmpdir.name) / "data.db"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmpdir.cleanup()

    def _insert_items(self, count: int = 15) -> None:
        base = datetime(2026, 5, 3, tzinfo=timezone.utc)
        items = []
        for idx in range(count):
            items.append(
                {
                    "source": "reddit",
                    "external_id": f"r{idx}",
                    "title": f"Need better workflow {idx}",
                    "content": "manual reporting is painful",
                    "url": f"https://www.reddit.com/r/test/comments/r{idx}/title/",
                    "author": "alice",
                    "created_at": (base + timedelta(minutes=idx)).isoformat(),
                    "raw_score": idx,
                }
            )
        with mock.patch("keywords.score_item", return_value=(2, ["manual"])):
            db.insert_items(items)

    def _make_request(self, path: str = "/", query_string: bytes = b"") -> Request:
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": path,
                "query_string": query_string,
                "headers": [],
            }
        )

    def _template_env(self) -> Environment:
        env = Environment(
            loader=FileSystemLoader(str(ROOT / "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["matched"] = lambda value: []
        env.filters["rel_time"] = lambda value: "刚刚"
        env.filters["abs_time"] = lambda value: "05-03 12:00"
        env.globals["recent_refreshes"] = lambda: []
        env.globals["parse_json"] = lambda value: {}
        return env

    def _item(self) -> SimpleNamespace:
        return SimpleNamespace(
            id=1,
            source="reddit",
            title="Need better reporting",
            content="Reports are manual",
            url="https://example.com",
            ai_flagged=1,
            is_translated=0,
            pain_score=3,
            matched_keywords="[]",
            created_at="2026-05-03T00:00:00+00:00",
            author="alice",
            is_starred=0,
            ai_summary=None,
            enriched_content=None,
            enrichment_status="pending",
            enrichment_error=None,
        )

    def test_query_items_returns_total_count_and_requested_page_slice(self):
        self._insert_items(15)

        self.assertEqual(db.count_items(source="reddit", min_score=1), 15)
        rows = db.query_items(source="reddit", min_score=1, limit=10, offset=10)

        self.assertEqual([row["external_id"] for row in rows], ["r4", "r3", "r2", "r1", "r0"])

    def test_query_starred_returns_total_count_and_requested_page_slice(self):
        self._insert_items(15)
        with db.get_conn() as conn:
            conn.execute("UPDATE items SET is_starred = 1")

        self.assertEqual(db.count_starred(), 15)
        rows = db.query_starred(limit=10, offset=10)

        self.assertEqual([row["external_id"] for row in rows], ["r4", "r3", "r2", "r1", "r0"])

    def test_index_route_clamps_page_and_queries_expected_offset(self):
        request = self._make_request()
        with mock.patch.object(main.db, "count_items", return_value=25) as count_items, \
             mock.patch.object(main.db, "query_items", return_value=[]) as query_items:
            response = main.index(
                request,
                source="reddit",
                min_score=1,
                show_starred=1,
                show_hidden=0,
                q="workflow",
                only_ai=0,
                applied=1,
                page=3,
            )

        count_items.assert_called_once()
        query_items.assert_called_once()
        self.assertEqual(query_items.call_args.kwargs["limit"], 10)
        self.assertEqual(query_items.call_args.kwargs["offset"], 20)
        self.assertEqual(response.context["page"], 3)
        self.assertEqual(response.context["total_pages"], 3)
        self.assertEqual(response.context["total_count"], 25)
        self.assertIn("source=reddit", response.context["page_url_prefix"])
        self.assertTrue(response.context["page_url_prefix"].endswith("page="))

    def test_starred_route_clamps_invalid_page_to_first_page(self):
        request = self._make_request("/starred")
        with mock.patch.object(main.db, "count_starred", return_value=7), \
             mock.patch.object(main.db, "query_starred", return_value=[]) as query_starred:
            response = main.starred(request, page=0)

        query_starred.assert_called_once_with(limit=10, offset=0)
        self.assertEqual(response.context["page"], 1)
        self.assertEqual(response.context["total_pages"], 1)
        self.assertEqual(response.context["total_count"], 7)

    def test_index_template_renders_pagination_controls(self):
        html = self._template_env().get_template("index.html").render(
            items=[self._item()],
            source="reddit",
            min_score=1,
            show_starred=1,
            show_hidden=0,
            q="workflow",
            only_ai=0,
            page=2,
            page_size=10,
            total_count=25,
            total_pages=3,
            page_url_prefix="/?applied=1&source=reddit&page=",
        )

        self.assertIn("共 25 条", html)
        self.assertIn("当前显示 1 条", html)
        self.assertIn("第 2 / 3 页", html)
        self.assertIn("上一页", html)
        self.assertIn("下一页", html)
        self.assertIn('href="/?applied=1&amp;source=reddit&amp;page=1"', html)
        self.assertIn('href="/?applied=1&amp;source=reddit&amp;page=3"', html)

    def test_starred_template_renders_pagination_controls(self):
        item = self._item()
        item.is_starred = 1
        html = self._template_env().get_template("starred.html").render(
            items=[item],
            page=2,
            page_size=10,
            total_count=21,
            total_pages=3,
            page_url_prefix="/starred?page=",
        )

        self.assertIn("已标记的条目 (21)", html)
        self.assertIn("第 2 / 3 页", html)
        self.assertIn('href="/starred?page=1"', html)
        self.assertIn('href="/starred?page=3"', html)


if __name__ == "__main__":
    unittest.main()
