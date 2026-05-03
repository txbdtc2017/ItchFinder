import asyncio
import unittest
from unittest import mock

import httpx

from sources import rss_tech


RSS_XML = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Useful release notes</title>
      <link>https://example.com/release</link>
      <guid>release-1</guid>
      <description>Short summary</description>
    </item>
  </channel>
</rss>
"""


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, **kwargs):
        if "slow" in url:
            raise httpx.TimeoutException("slow feed")
        return FakeResponse(RSS_XML)


class RssTechTests(unittest.TestCase):
    def test_fetch_uses_http_timeout_and_continues_after_feed_failure(self):
        async def run():
            with mock.patch.object(
                rss_tech,
                "FEEDS",
                [("slow", "https://slow.example/feed"), ("ok", "https://ok.example/feed")],
            ), mock.patch.object(rss_tech.httpx, "AsyncClient", FakeAsyncClient):
                return await rss_tech.fetch()

        items = asyncio.run(run())

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "rss_tech")
        self.assertEqual(items[0]["title"], "Useful release notes")
        self.assertEqual(items[0]["url"], "https://example.com/release")


if __name__ == "__main__":
    unittest.main()
