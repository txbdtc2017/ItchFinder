import asyncio
import unittest
from unittest import mock

import enrichment


REDDIT_HTML = """
<html><body>
  <div data-test-id="post-content"><p>I spend hours copying reports by hand.</p></div>
  <div data-testid="comment"><p>Same here, every client wants a different format.</p></div>
  <div data-testid="comment"><p>I tried spreadsheets but the handoff still breaks.</p></div>
</body></html>
"""

HN_HTML = """
<html><body>
  <tr class="athing comtr"><td class="default"><div class="comment"><span class="commtext">I wish deploy logs were easier to compare.</span></div></td></tr>
  <tr class="athing comtr"><td class="default"><div class="comment"><span class="commtext">Existing dashboards hide the useful failure context.</span></div></td></tr>
</body></html>
"""

GITHUB_HTML = """
<html><body>
  <td class="comment-body"><p>The setup flow is confusing for non-admin users.</p></td>
  <td class="comment-body"><p>Please support exporting the audit trail.</p></td>
</body></html>
"""


class EnrichmentParserTests(unittest.TestCase):
    def test_trim_text_collapses_whitespace_and_limits_length(self):
        text = "  a\n\n  b\t c  " + ("x" * 1000)
        trimmed = enrichment.trim_text(text, 20)
        self.assertEqual(trimmed, "a b c xxxxxxxxxxxxxx")
        self.assertEqual(len(trimmed), 20)

    def test_reddit_extractor_returns_post_and_limited_comments(self):
        result = enrichment.extract_reddit_context(
            REDDIT_HTML,
            "https://www.reddit.com/r/test/comments/abc/title/",
        )

        self.assertIn("Post: I spend hours copying reports by hand.", result)
        self.assertIn("Comments:", result)
        self.assertIn("- Same here, every client wants a different format.", result)
        self.assertIn("- I tried spreadsheets but the handoff still breaks.", result)

    def test_hn_extractor_returns_ordered_comments(self):
        result = enrichment.extract_hn_context(
            HN_HTML,
            "https://news.ycombinator.com/item?id=1",
        )

        self.assertIn("Comments:", result)
        self.assertLess(
            result.index("I wish deploy logs"),
            result.index("Existing dashboards"),
        )

    def test_github_api_url_parser_accepts_issue_urls(self):
        api_url = enrichment.github_comments_api_url("https://github.com/acme/tool/issues/42")

        self.assertEqual(
            api_url,
            "https://api.github.com/repos/acme/tool/issues/42/comments",
        )

    def test_github_html_fallback_extracts_issue_comments(self):
        result = enrichment.extract_github_html_context(
            GITHUB_HTML,
            "https://github.com/acme/tool/issues/42",
        )

        self.assertIn("Comments:", result)
        self.assertIn("- The setup flow is confusing for non-admin users.", result)
        self.assertIn("- Please support exporting the audit trail.", result)

    def test_enrich_new_candidates_marks_success_and_failure(self):
        rows = [
            {"id": 1, "source": "reddit", "url": "https://www.reddit.com/r/test/comments/abc/title/"},
            {"id": 2, "source": "hackernews", "url": "https://news.ycombinator.com/item?id=1"},
        ]

        async def fake_fetch_html(client, url):
            if "reddit" in url:
                return REDDIT_HTML
            raise RuntimeError("network blocked")

        async def run():
            messages = []
            with mock.patch("db.get_enrichment_candidates", return_value=rows), \
                 mock.patch("db.mark_enriched") as mark_enriched, \
                 mock.patch("db.mark_enrichment_failed") as mark_failed, \
                 mock.patch.object(enrichment, "fetch_html", side_effect=fake_fetch_html):
                async for message in enrichment.enrich_new_candidates(limit=30):
                    messages.append(message)
            return messages, mark_enriched, mark_failed

        messages, mark_enriched, mark_failed = asyncio.run(run())

        self.assertTrue(any("提交 2 条候选" in message for message in messages))
        mark_enriched.assert_called_once()
        self.assertEqual(mark_enriched.call_args.args[0], 1)
        mark_failed.assert_called_once()
        self.assertEqual(mark_failed.call_args.args[0], 2)


if __name__ == "__main__":
    unittest.main()
