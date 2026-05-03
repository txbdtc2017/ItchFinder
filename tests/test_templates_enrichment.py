import unittest
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]


class TemplateEnrichmentTests(unittest.TestCase):
    def _render_index(self, item):
        env = Environment(
            loader=FileSystemLoader(str(ROOT / "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["matched"] = lambda value: []
        env.filters["rel_time"] = lambda value: "刚刚"
        env.filters["abs_time"] = lambda value: "05-03 12:00"
        env.globals["recent_refreshes"] = lambda: []
        env.globals["parse_json"] = lambda value: {}
        template = env.get_template("index.html")
        return template.render(
            items=[item],
            source="",
            min_score=1,
            show_starred=1,
            show_hidden=0,
            q="",
            only_ai=1,
        )

    def test_index_renders_ai_summary_and_collapsed_raw_context(self):
        item = SimpleNamespace(
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
            ai_summary="用户痛点：报表整理慢\n现有方案缺口：工具割裂\n可做产品机会：自动生成周报",
            enriched_content="Post: Reports are manual\nComments:\n- Same issue here",
            enrichment_status="done",
            enrichment_error=None,
        )

        html = self._render_index(item)

        self.assertIn("AI 总结", html)
        self.assertIn("用户痛点：报表整理慢", html)
        self.assertIn("<details", html)
        self.assertIn("原始上下文", html)
        self.assertIn("Same issue here", html)

    def test_index_renders_enrichment_failure_status(self):
        item = SimpleNamespace(
            id=2,
            source="github",
            title="Export is hard",
            content="Need better export",
            url="https://github.com/acme/tool/issues/42",
            ai_flagged=0,
            is_translated=0,
            pain_score=2,
            matched_keywords="[]",
            created_at="2026-05-03T00:00:00+00:00",
            author="bob",
            is_starred=0,
            ai_summary=None,
            enriched_content=None,
            enrichment_status="failed",
            enrichment_error="rate limited",
        )

        html = self._render_index(item)

        self.assertIn("补全失败", html)
        self.assertIn("rate limited", html)


if __name__ == "__main__":
    unittest.main()
