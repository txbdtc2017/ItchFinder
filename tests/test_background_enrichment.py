import asyncio
import unittest
from unittest import mock

import main


class BackgroundEnrichmentTests(unittest.TestCase):
    def test_background_worker_uses_bounded_background_enrichment_mode(self):
        calls = []

        async def fake_enrich_new_candidates(limit=30, mode="background", label="Scrapling", skip_if_busy=False):
            calls.append(
                {
                    "limit": limit,
                    "mode": mode,
                    "label": label,
                    "skip_if_busy": skip_if_busy,
                }
            )
            yield "Scrapling后台补齐: done"

        async def run():
            with mock.patch.object(main, "enrich_new_candidates", side_effect=fake_enrich_new_candidates):
                await main.run_background_enrichment()

        asyncio.run(run())

        self.assertEqual(
            calls,
            [
                {
                    "limit": 20,
                    "mode": "background",
                    "label": "Scrapling后台补齐",
                    "skip_if_busy": True,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
