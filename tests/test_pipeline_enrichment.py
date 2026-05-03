import asyncio
import unittest
from unittest import mock

import main


class PipelineEnrichmentOrderTests(unittest.TestCase):
    def test_pipeline_runs_enrichment_after_fetchers_and_before_ai(self):
        events = []

        async def fake_fetch():
            return [{
                "source": "reddit",
                "external_id": "r1",
                "title": "wish reports were automatic",
                "content": "manual reporting hurts",
                "url": "https://www.reddit.com/r/test/comments/r1/title/",
                "author": "alice",
                "created_at": "2026-05-03T00:00:00+00:00",
                "raw_score": 5,
            }]

        async def empty_fetch():
            return []

        async def fake_enrich_new_candidates(limit=30, mode="background", label="Scrapling", skip_if_busy=False):
            events.append(f"enrich:{mode}")
            yield f"{label}: done"

        async def fake_run_ai_scoring():
            events.append("ai")
            yield "AI: done"

        async def fake_summarize_ai_flagged():
            events.append("summary")
            yield "AI总结: done"

        async def fake_translate_new_items():
            events.append("translate")
            yield "translate: done"

        async def run():
            with mock.patch.object(main.hackernews, "fetch", side_effect=fake_fetch), \
                 mock.patch.object(main.v2ex, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.reddit, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.zhihu, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.sspai, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.github_issues, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.devto, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.lobsters, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.stackoverflow, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.juejin, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.rss_tech, "fetch", side_effect=empty_fetch), \
                 mock.patch.object(main.db, "insert_items", return_value=(1, 1)) as insert_items, \
                 mock.patch.object(main.db, "log_refresh") as log_refresh, \
                 mock.patch.object(main, "enrich_new_candidates", side_effect=fake_enrich_new_candidates), \
                 mock.patch.object(main, "run_ai_scoring", side_effect=fake_run_ai_scoring), \
                 mock.patch.object(main, "summarize_ai_flagged", side_effect=fake_summarize_ai_flagged), \
                 mock.patch.object(main, "translate_new_items", side_effect=fake_translate_new_items):
                messages = [message async for message in main.pipeline_events(trigger="manual")]
            return messages, insert_items, log_refresh

        messages, insert_items, log_refresh = asyncio.run(run())

        self.assertEqual(events, ["enrich:pre_ai", "ai", "enrich:ai_flagged", "summary", "translate"])
        self.assertIn("Scrapling预补齐: done", messages)
        self.assertIn("Scrapling推荐补齐: done", messages)
        insert_items.assert_called()
        log_refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()
