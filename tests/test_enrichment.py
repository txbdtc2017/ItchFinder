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

REDDIT_VERIFICATION_HTML = """
<html><head><title>Reddit - Please wait for verification</title></head><body></body></html>
"""

OLD_REDDIT_WITH_SIDEBAR_HTML = """
<html><body>
  <div class="side"><div class="usertext-body"><p>Community rules should not be the post.</p></div></div>
  <div class="thing link">
    <div class="entry">
      <div class="usertext-body"><div class="md"><p>Actual old Reddit post body.</p></div></div>
    </div>
  </div>
  <div class="comment"><div class="usertext-body"><p>Useful old Reddit comment.</p></div></div>
</body></html>
"""

HN_EMPTY_HTML = """
<html><body><table><tr class="athing"><td>Story with no comments</td></tr></table></body></html>
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

    def test_reddit_old_page_extractor_ignores_sidebar_usertext(self):
        result = enrichment.extract_reddit_context(
            OLD_REDDIT_WITH_SIDEBAR_HTML,
            "https://old.reddit.com/r/test/comments/abc/title/",
        )

        self.assertIn("Post: Actual old Reddit post body.", result)
        self.assertIn("- Useful old Reddit comment.", result)
        self.assertNotIn("Community rules", result)

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

    def test_reddit_old_url_converts_www_reddit_links(self):
        self.assertEqual(
            enrichment.reddit_old_url("https://www.reddit.com/r/test/comments/abc/title/"),
            "https://old.reddit.com/r/test/comments/abc/title/",
        )

    def test_hn_discussion_url_prefers_external_id_over_story_url(self):
        row = {
            "source": "hackernews",
            "external_id": "47992742",
            "url": "https://example.com/article",
        }

        self.assertEqual(
            enrichment.hn_discussion_url(row),
            "https://news.ycombinator.com/item?id=47992742",
        )

    def test_reddit_enrich_uses_old_reddit_page_before_falling_back_to_content(self):
        calls = []
        row = {
            "id": 1,
            "source": "reddit",
            "external_id": "abc",
            "content": "Existing post body",
            "url": "https://www.reddit.com/r/test/comments/abc/title/",
        }

        async def fake_fetch_html(client, url):
            calls.append(url)
            if "old.reddit.com" in url:
                return REDDIT_HTML
            return REDDIT_VERIFICATION_HTML

        async def run():
            with mock.patch.object(enrichment, "fetch_html", side_effect=fake_fetch_html):
                return await enrichment.enrich_item(object(), row)

        result = asyncio.run(run())

        self.assertEqual(calls, ["https://old.reddit.com/r/test/comments/abc/title/"])
        self.assertIn("Post: I spend hours copying reports by hand.", result)

    def test_reddit_enrich_falls_back_to_existing_content_when_fetch_is_blocked(self):
        row = {
            "id": 1,
            "source": "reddit",
            "external_id": "abc",
            "content": "Existing post body from original Reddit JSON",
            "url": "https://www.reddit.com/r/test/comments/abc/title/",
        }

        async def fake_fetch_html(client, url):
            raise RuntimeError("blocked")

        async def run():
            with mock.patch.object(enrichment, "fetch_html", side_effect=fake_fetch_html):
                return await enrichment.enrich_item(object(), row)

        result = asyncio.run(run())

        self.assertEqual(result, "Post: Existing post body from original Reddit JSON")

    def test_hn_enrich_fetches_hn_discussion_page_not_external_url(self):
        calls = []
        row = {
            "id": 2,
            "source": "hackernews",
            "external_id": "47992742",
            "content": "",
            "url": "https://example.com/article",
        }

        async def fake_fetch_html(client, url):
            calls.append(url)
            return HN_HTML

        async def run():
            with mock.patch.object(enrichment, "fetch_html", side_effect=fake_fetch_html):
                return await enrichment.enrich_item(object(), row)

        result = asyncio.run(run())

        self.assertEqual(calls, ["https://news.ycombinator.com/item?id=47992742"])
        self.assertIn("I wish deploy logs", result)

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

    def test_enrich_new_candidates_marks_empty_result_as_skipped_not_failed(self):
        rows = [
            {
                "id": 3,
                "source": "hackernews",
                "external_id": "123",
                "content": "",
                "url": "https://example.com/article",
            },
        ]

        async def fake_fetch_html(client, url):
            return HN_EMPTY_HTML

        async def run():
            messages = []
            with mock.patch("db.get_enrichment_candidates", return_value=rows), \
                 mock.patch("db.mark_enriched") as mark_enriched, \
                 mock.patch("db.mark_enrichment_failed") as mark_failed, \
                 mock.patch("db.mark_enrichment_skipped") as mark_skipped, \
                 mock.patch.object(enrichment, "fetch_html", side_effect=fake_fetch_html):
                async for message in enrichment.enrich_new_candidates(limit=30):
                    messages.append(message)
            return messages, mark_enriched, mark_failed, mark_skipped

        messages, mark_enriched, mark_failed, mark_skipped = asyncio.run(run())

        self.assertTrue(any("跳过" in message for message in messages))
        mark_enriched.assert_not_called()
        mark_failed.assert_not_called()
        mark_skipped.assert_called_once_with(3, "no extractable context")

    def test_enrich_new_candidates_passes_candidate_mode_to_database(self):
        async def run():
            with mock.patch("db.get_enrichment_candidates", return_value=[]) as get_candidates:
                messages = []
                async for message in enrichment.enrich_new_candidates(
                    limit=7,
                    mode="ai_flagged",
                    label="Scrapling推荐补齐",
                ):
                    messages.append(message)
            return messages, get_candidates

        messages, get_candidates = asyncio.run(run())

        get_candidates.assert_called_once_with(limit=7, mode="ai_flagged")
        self.assertEqual(messages, ["Scrapling推荐补齐: 没有需要补全的候选"])

    def test_background_enrichment_skips_when_another_enrichment_job_is_busy(self):
        async def run():
            await enrichment._ENRICHMENT_LOCK.acquire()
            try:
                with mock.patch("db.get_enrichment_candidates") as get_candidates:
                    messages = []
                    async for message in enrichment.enrich_new_candidates(skip_if_busy=True):
                        messages.append(message)
                return messages, get_candidates
            finally:
                enrichment._ENRICHMENT_LOCK.release()

        messages, get_candidates = asyncio.run(run())

        self.assertEqual(messages, ["Scrapling: 已有补齐任务运行,跳过本轮"])
        get_candidates.assert_not_called()


if __name__ == "__main__":
    unittest.main()
